"""
R19 — vérification de l'adresse e-mail (transport FAUX : aucun envoi réel) et cycle de vie du
compte (déconnexion, mot de passe, adresse, suppression, révocation). Comptes FICTIFS.
"""

import datetime as _dt
import logging
import threading

import jwt
import pytest

from app.core import courriel
from app.core.pseudonymisation import hmac_eleve
from paiement_comptes import crud_billing, liens
from paiement_comptes import verification_email as ve
from paiement_comptes.database import SessionLocal as BillingSession

MDP = "motdepasse-r19-0001"
BOITE = courriel.boite_de_test()


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture()
def c(client, monkeypatch):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    BOITE.vider()
    yield client
    BOITE.vider()


def _inscrire(c, email="p@example.com", role="parent"):
    r = c.post("/api/v1/comptes/inscription", json={"email": email, "mot_de_passe": MDP, "role": role})
    assert r.status_code == 201
    return r.json()["token"]


def _jeton_mail(email):
    return BOITE.derniers(email)[-1].metadonnees["jeton"]


def _confirmer(c, jeton):
    return c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": jeton})


# --------------------------------------------------------------------------- #
# Cycle PARENT_CREATED → … → INVITATION_ACCEPT_ALLOWED
# --------------------------------------------------------------------------- #
def test_cycle_complet(c):
    t = _inscrire(c)
    assert len(BOITE.derniers("p@example.com")) == 1  # un courriel (factice) à l'inscription
    assert c.get("/api/v1/comptes/verification-email", headers=_h(t)).json()["statut"] == "VERIFICATION_TOKEN_CREATED"
    assert _confirmer(c, _jeton_mail("p@example.com")).json() == {"statut": "EMAIL_VERIFIED"}
    assert c.get("/api/v1/comptes/verification-email", headers=_h(t)).json()["statut"] == "EMAIL_VERIFIED"
    assert c.get("/api/v1/comptes/moi", headers=_h(t)).json()["email_verifie"] is True


def test_jeton_jamais_dans_une_reponse_http(c):
    r = c.post("/api/v1/comptes/inscription", json={"email": "q@example.com", "mot_de_passe": MDP})
    jeton = _jeton_mail("q@example.com")
    assert jeton not in r.text
    r2 = c.post("/api/v1/comptes/verification-email", headers=_h(r.json()["token"]))
    assert r2.status_code == 202 and _jeton_mail("q@example.com") not in r2.text


def test_jeton_aleatoire_et_stocke_hache(c):
    _inscrire(c)
    jetons = set()
    db = BillingSession()
    try:
        compte = crud_billing.get_compte_par_email(db, "p@example.com")
        for _ in range(30):
            jetons.add(ve.creer_jeton(db, compte))
        brut = repr(db.execute(ve.select(ve.VerificationEmail.__table__)).fetchall())
    finally:
        db.close()
    assert len(jetons) == 30 and all(len(j) >= 43 for j in jetons)  # 256 bits en base64url
    assert not any(j in brut for j in jetons)


def test_usage_unique_et_rejeu(c):
    _inscrire(c)
    j = _jeton_mail("p@example.com")
    assert _confirmer(c, j).status_code == 200
    r = _confirmer(c, j)
    assert (r.status_code, r.json()["detail"]) == (400, "jeton_invalide_ou_expire")


def test_tous_les_jetons_invalides_apres_succes(c):
    t = _inscrire(c)
    j1 = _jeton_mail("p@example.com")
    c.post("/api/v1/comptes/verification-email", headers=_h(t))
    j2 = _jeton_mail("p@example.com")
    assert _confirmer(c, j2).status_code == 200
    assert _confirmer(c, j1).status_code == 400


def test_expiration(c, monkeypatch):
    _inscrire(c)
    j = _jeton_mail("p@example.com")
    futur = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) + _dt.timedelta(hours=25)
    monkeypatch.setattr(ve, "_maintenant", lambda: futur)
    assert _confirmer(c, j).status_code == 400


@pytest.mark.parametrize("jeton", ["x", "A" * 43, "é" * 20, "' OR 1=1 --"])
def test_jeton_inconnu_meme_reponse(c, jeton):
    r = _confirmer(c, jeton)
    assert (r.status_code, r.json()) == (400, {"detail": "jeton_invalide_ou_expire"})


def test_jeton_trop_long_refuse(c):
    assert _confirmer(c, "a" * 129).status_code == 422


def test_changement_d_adresse_invalide_les_jetons(c):
    t = _inscrire(c)
    ancien = _jeton_mail("p@example.com")
    r = c.post("/api/v1/comptes/email", json={"nouvel_email": "nouveau@example.com", "mot_de_passe": MDP},
               headers=_h(t))
    assert r.status_code == 200 and r.json()["compte"]["email_verifie"] is False
    assert _confirmer(c, ancien).status_code == 400  # jeton envoyé à l'ANCIENNE adresse : mort
    assert _confirmer(c, _jeton_mail("nouveau@example.com")).status_code == 200


def test_jeton_lie_a_l_adresse_meme_si_non_supprime(c):
    """Défense en profondeur : même si un jeton survivait à un changement d'adresse, il ne
    vérifierait pas la NOUVELLE adresse (email_cible ≠ email actuel)."""
    _inscrire(c)
    j = _jeton_mail("p@example.com")
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, "p@example.com")
    compte.email = "autre@example.com"
    db.commit()
    db.close()
    assert _confirmer(c, j).status_code == 400


def test_au_plus_trois_jetons_actifs(c):
    _inscrire(c)
    db = BillingSession()
    try:
        compte = crud_billing.get_compte_par_email(db, "p@example.com")
        for _ in range(5):
            ve.creer_jeton(db, compte)
        n = db.query(ve.VerificationEmail).filter_by(compte_id=compte.id, utilise_le=None).count()
    finally:
        db.close()
    assert n == ve.MAX_JETONS_ACTIFS


def test_confirmations_concurrentes_un_seul_succes(c):
    _inscrire(c)
    j = _jeton_mail("p@example.com")
    barriere, res = threading.Barrier(4), []

    def run():
        s = BillingSession()
        barriere.wait()
        try:
            res.append(ve.confirmer(s, j))
        except ve.JetonVerificationInvalide:
            res.append("refus")
        finally:
            s.close()

    ths = [threading.Thread(target=run) for _ in range(4)]
    [t.start() for t in ths]
    [t.join(20) for t in ths]
    assert res.count("refus") == 3


def test_force_brute_confirmation_limitee(c):
    for i in range(20):
        assert _confirmer(c, f"faux-{i}").status_code == 400
    assert _confirmer(c, "faux-final").status_code == 429


def test_quota_de_demandes(c):
    t = _inscrire(c)
    codes = [c.post("/api/v1/comptes/verification-email", headers=_h(t)).status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]


def test_deja_verifie_aucun_courriel(c):
    t = _inscrire(c)
    _confirmer(c, _jeton_mail("p@example.com"))
    BOITE.vider()
    assert c.post("/api/v1/comptes/verification-email", headers=_h(t)).json() == {"statut": "EMAIL_VERIFIED"}
    assert BOITE.derniers("p@example.com") == []


# --------------------------------------------------------------------------- #
# Garde sur l'acceptation d'invitation
# --------------------------------------------------------------------------- #
def test_invitation_refusee_tant_que_non_verifie(c):
    t = _inscrire(c)
    db = BillingSession()
    code, _ = liens.creer_invitation(db, "eleve-r19", hmac_eleve("eleve-r19"), emis_par="operateur")
    db.close()
    r = c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(t))
    assert (r.status_code, r.json()["detail"]) == (403, "email_non_verifie")
    _confirmer(c, _jeton_mail("p@example.com"))
    r = c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(t))
    assert r.status_code == 201  # le code n'avait PAS été consommé par le refus


def test_verification_desactivable_hors_production(c, monkeypatch):
    monkeypatch.setenv("MIKA_EMAIL_VERIFICATION", "off")
    assert ve.verification_requise() is False
    monkeypatch.setenv("MIKA_ENV", "production")
    with pytest.raises(ValueError):
        ve.verification_requise()


# --------------------------------------------------------------------------- #
# Transports
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nom", ["faux", "journal", ""])
def test_transports_de_test_interdits_en_production(monkeypatch, nom):
    monkeypatch.setenv("MIKA_ENV", "production")
    monkeypatch.setenv("MIKA_EMAIL_TRANSPORT", nom)
    with pytest.raises(courriel.ConfigCourrielInvalide):
        courriel.nom_transport()


def test_transport_inconnu_refuse(monkeypatch):
    monkeypatch.setenv("MIKA_EMAIL_TRANSPORT", "smtp-imaginaire")
    with pytest.raises(courriel.ConfigCourrielInvalide):
        courriel.nom_transport()


def test_fournisseur_enregistrable_mais_noms_reserves():
    with pytest.raises(ValueError):
        courriel.enregistrer_transport("faux", courriel.TransportFaux)


def test_transport_journal_sans_adresse_ni_jeton(caplog):
    with caplog.at_level(logging.INFO, logger="mikamike.courriel"):
        courriel.TransportJournal().envoyer(courriel.Message("secret@example.com", "s", "jeton-XYZ", "VERIFICATION_EMAIL"))
    assert "secret@example.com" not in caplog.text and "jeton-XYZ" not in caplog.text and "VERIFICATION_EMAIL" in caplog.text


def test_boite_de_test_bornee():
    b = courriel.TransportFaux()
    for i in range(b.MAX + 50):
        b.envoyer(courriel.Message(f"{i}@x.invalid", "s", "c", "T"))
    assert len(b.messages) == b.MAX


# --------------------------------------------------------------------------- #
# Cycle de vie du compte : révocation
# --------------------------------------------------------------------------- #
def _parent_lie(c, email="lie@example.com", eleve="eleve-cv"):
    t = _inscrire(c, email)
    _confirmer(c, _jeton_mail(email))
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, email)
    liens.lier(db, compte.id, hmac_eleve(eleve), "parent")
    db.close()
    je = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": eleve}, headers=_h(t)).json()["token"]
    return t, je


def _soumettre(c, je, eleve="eleve-cv"):
    return c.post("/api/v1/memory/schedule", json={"user_id": eleve, "notion_id": "n1", "mastery_event": "SUCCESS"},
                  headers=_h(je))


def test_deconnexion_revoque_compte_et_jetons_eleve(c):
    t, je = _parent_lie(c)
    assert _soumettre(c, je).status_code == 200
    assert c.post("/api/v1/comptes/deconnexion", headers=_h(t)).status_code == 204
    r = c.get("/api/v1/comptes/moi", headers=_h(t))
    assert (r.status_code, r.json()["detail"]) == (401, "jeton_revoque")
    assert c.get("/api/v1/rgpd/export/eleve-cv", headers=_h(t)).status_code == 401
    assert _soumettre(c, je).json()["detail"] == "jeton_revoque"
    t2 = c.post("/api/v1/comptes/connexion", json={"email": "lie@example.com", "mot_de_passe": MDP}).json()["token"]
    assert c.get("/api/v1/comptes/moi", headers=_h(t2)).status_code == 200


def test_changement_de_mot_de_passe(c):
    t, je = _parent_lie(c)
    r = c.post("/api/v1/comptes/mot-de-passe", json={"ancien": MDP, "nouveau": "nouveau-mdp-0001"}, headers=_h(t))
    assert r.status_code == 200
    nouveau = r.json()["token"]
    assert c.get("/api/v1/comptes/moi", headers=_h(t)).status_code == 401       # jeton volé : mort
    assert _soumettre(c, je).status_code == 401                                  # jetons élève aussi
    assert c.get("/api/v1/comptes/moi", headers=_h(nouveau)).status_code == 200
    assert c.post("/api/v1/comptes/connexion", json={"email": "lie@example.com", "mot_de_passe": MDP}).status_code == 401
    assert c.post("/api/v1/comptes/connexion", json={"email": "lie@example.com",
                                                     "mot_de_passe": "nouveau-mdp-0001"}).status_code == 200


def test_mot_de_passe_actuel_exige_et_limite(c):
    t = _inscrire(c)
    codes = [c.post("/api/v1/comptes/mot-de-passe", json={"ancien": "faux-0000", "nouveau": "nouveau-mdp-0001"},
                    headers=_h(t)).status_code for _ in range(6)]
    assert codes == [403] * 5 + [429]


def test_changement_d_adresse_revoque_et_exige_mot_de_passe(c):
    t, je = _parent_lie(c)
    assert c.post("/api/v1/comptes/email", json={"nouvel_email": "n@example.com", "mot_de_passe": "faux-0000"},
                  headers=_h(t)).status_code == 403
    r = c.post("/api/v1/comptes/email", json={"nouvel_email": "n@example.com", "mot_de_passe": MDP}, headers=_h(t))
    assert r.status_code == 200
    assert c.get("/api/v1/comptes/moi", headers=_h(t)).status_code == 401
    assert _soumettre(c, je).status_code == 401
    assert c.post("/api/v1/comptes/connexion", json={"email": "lie@example.com", "mot_de_passe": MDP}).status_code == 401


def test_changement_vers_adresse_prise(c):
    _inscrire(c, "prise@example.com")
    t = _inscrire(c, "moi@example.com")
    r = c.post("/api/v1/comptes/email", json={"nouvel_email": "PRISE@example.com", "mot_de_passe": MDP}, headers=_h(t))
    assert (r.status_code, r.json()["detail"]) == (400, "email_indisponible")


def test_jeton_historique_sans_ver_accepte_puis_revoque(c):
    t = _inscrire(c)
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, "p@example.com")
    ancien = jwt.encode({"sub": str(compte.id), "typ": "compte", "role": "parent",
                         "exp": int(_dt.datetime.now(_dt.timezone.utc).timestamp()) + 600},
                        "test-jwt-secret-not-for-prod-0123456789", algorithm="HS256")
    db.close()
    assert c.get("/api/v1/comptes/moi", headers=_h(ancien)).status_code == 200
    c.post("/api/v1/comptes/deconnexion", headers=_h(t))
    assert c.get("/api/v1/comptes/moi", headers=_h(ancien)).status_code == 401


# --------------------------------------------------------------------------- #
# Suppression du compte / RGPD du titulaire
# --------------------------------------------------------------------------- #
def test_export_du_compte_sans_secret(c):
    t, _ = _parent_lie(c)
    out = c.get("/api/v1/comptes/moi/export", headers=_h(t)).json()
    assert out["compte"]["email"] == "lie@example.com" and out["verification_email"]["email_verifie"] is True
    assert len(out["liens_eleves"]) == 1
    brut = str(out)
    assert "mot_de_passe" not in brut and "$2b$" not in brut and "jeton" not in brut.replace("verification", "")


def test_suppression_du_compte(c):
    t, je = _parent_lie(c)
    t_autre, je_autre = _parent_lie(c, "autre@example.com")  # autre parent du MÊME élève
    assert _soumettre(c, je).status_code == 200
    c.post("/api/v1/comptes/email", json={"nouvel_email": "lie2@example.com", "mot_de_passe": MDP}, headers=_h(t))
    t = c.post("/api/v1/comptes/connexion", json={"email": "lie2@example.com", "mot_de_passe": MDP}).json()["token"]
    db = BillingSession()
    cid = crud_billing.get_compte_par_email(db, "lie2@example.com").id
    assert db.query(ve.VerificationEmail).filter_by(compte_id=cid).count() == 1  # jeton en attente
    db.close()
    je = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": "eleve-cv"}, headers=_h(t)).json()["token"]
    corps = {"mot_de_passe": MDP, "confirmation": True}
    assert c.request("DELETE", "/api/v1/comptes/moi", json={**corps, "confirmation": False}, headers=_h(t)).status_code == 422
    assert c.request("DELETE", "/api/v1/comptes/moi", json={**corps, "mot_de_passe": "faux-0000"},
                     headers=_h(t)).status_code == 403
    r = c.request("DELETE", "/api/v1/comptes/moi", json=corps, headers=_h(t))
    assert r.json() == {"statut": "compte_supprime", "liens_supprimes": 1}
    assert c.get("/api/v1/comptes/moi", headers=_h(t)).status_code == 401
    assert _soumettre(c, je).status_code == 401                       # jetons élève du compte supprimé
    assert _soumettre(c, je_autre).status_code == 200                  # l'autre parent n'est pas affecté
    export = c.get("/api/v1/rgpd/export/eleve-cv", headers=_h(t_autre)).json()
    assert export["total_competences_suivies"] >= 0 and len(export["liens_comptes"]) == 1
    db = BillingSession()
    try:
        assert db.query(ve.VerificationEmail).filter_by(compte_id=cid).count() == 0
        assert db.query(liens.LienCompteEleve).filter_by(compte_id=cid).count() == 0
        from paiement_comptes.models_billing import Abonnement

        assert db.query(Abonnement).filter_by(compte_id=cid).count() == 0
    finally:
        db.close()
    # Réinscription possible avec la même adresse.
    assert c.post("/api/v1/comptes/inscription", json={"email": "lie2@example.com", "mot_de_passe": MDP}).status_code == 201


def test_suppression_refusee_si_abonnement_en_cours(c):
    from paiement_comptes.models_billing import Abonnement, StatutAbonnement

    t = _inscrire(c)
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, "p@example.com")
    db.query(Abonnement).filter_by(compte_id=compte.id).update({"statut": StatutAbonnement.ACTIF})
    db.commit()
    db.close()
    r = c.request("DELETE", "/api/v1/comptes/moi", json={"mot_de_passe": MDP, "confirmation": True}, headers=_h(t))
    assert (r.status_code, r.json()["detail"]) == (409, "abonnement_en_cours")


def test_role_admin_sans_aucun_privilege(c):
    """Le rôle « admin » existe dans le modèle mais AUCUNE route ne l'honore : même lié, il
    n'obtient rien (relation ≠ rôle ⇒ 403), et l'inscription ne peut pas le créer."""
    db = BillingSession()
    admin = crud_billing.creer_compte(db, email="admin@example.com", mot_de_passe=MDP, role="admin")
    admin.email_verifie = True
    db.commit()
    liens.lier(db, admin.id, hmac_eleve("eleve-adm"), "parent")
    from paiement_comptes.router_comptes import creer_token

    t = creer_token(admin)
    db.close()
    assert c.get("/api/v1/rgpd/export/eleve-adm", headers=_h(t)).status_code == 403
    assert c.request("DELETE", "/api/v1/rgpd/effacer/eleve-adm", headers=_h(t)).status_code == 403
    assert c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": "eleve-adm"}, headers=_h(t)).status_code == 403
    r = c.post("/api/v1/comptes/inscription", json={"email": "x@example.com", "mot_de_passe": MDP, "role": "admin"})
    assert r.json()["compte"]["role"] == "parent"
