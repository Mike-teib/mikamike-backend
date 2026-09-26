"""
Décision D8 — lien parent ↔ élève par invitation à code unique, expirable, non devinable,
validée par le parent. Jamais par simple pseudo-id. Comptes FICTIFS, secrets de test.
"""

import datetime as _dt
import re
import threading
from pathlib import Path

import pytest

from app.core.pseudonymisation import hmac_eleve
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal as BillingSession
from paiement_comptes.router_comptes import creer_token

ELEVE = "eleve-inv-01"
MDP = "motdepasse-de-test-1"
URL_INV, URL_ACC = "/api/v1/liens/invitations", "/api/v1/liens/accepter"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture()
def acteurs(client, monkeypatch):
    """p1 : parent déjà lié (rattaché par l'opérateur) ; p2, p3 : parents non liés ; ce : compte élève."""
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    db = BillingSession()
    c = {n: crud_billing.creer_compte(db, email=f"{n}@example.com", mot_de_passe=MDP, role=r)
         for n, r in (("p1", "parent"), ("p2", "parent"), ("p3", "parent"), ("ce", "eleve"))}
    for x in c.values():  # R19 (session 4) : adresses vérifiées (la vérification a ses propres tests)
        x.email_verifie = True
    db.commit()
    liens.lier(db, c["p1"].id, hmac_eleve(ELEVE), "parent")
    jetons = {n: creer_token(x) for n, x in c.items()}
    ids = {n: x.id for n, x in c.items()}
    db.close()
    r = client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ELEVE}, headers=_h(jetons["p1"]))
    jetons["eleve"] = r.json()["token"]
    return client, jetons, ids


def _inviter(client, jeton, eleve=ELEVE, **kw):
    return client.post(URL_INV, json={"student_pseudo_id": eleve, **kw}, headers=_h(jeton))


def _accepter(client, jeton, code, confirmation=True):
    return client.post(URL_ACC, json={"code": code, "confirmation": confirmation}, headers=_h(jeton))


# --------------------------------------------------------------------------- #
# Code : non devinable, usage unique, jamais stocké en clair
# --------------------------------------------------------------------------- #
def test_code_aleatoire_120_bits_et_unique(acteurs):
    db = BillingSession()
    codes = set()
    try:
        for i in range(200):
            code, _ = liens.creer_invitation(db, f"e{i}", hmac_eleve(f"e{i}"), emis_par="test")
            assert re.fullmatch(r"[A-Z2-7]{4}(-[A-Z2-7]{4}){5}", code)
            codes.add(code)
    finally:
        db.close()
    assert len(codes) == 200


def test_code_jamais_stocke_en_clair(acteurs, tmp_path):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    db = BillingSession()
    try:
        lignes = [tuple(r) for r in db.execute(liens.select(liens.InvitationLien.__table__)).fetchall()]
    finally:
        db.close()
    brut = repr(lignes)
    assert code not in brut and code.replace("-", "") not in brut


def test_parcours_nominal_eleve_invite_parent_accepte(acteurs):
    client, j, ids = acteurs
    r = _inviter(client, j["eleve"])
    assert r.status_code == 201 and r.json()["usage_unique"] and r.json()["expires_in"] == 48 * 3600
    r2 = _accepter(client, j["p2"], r.json()["code"].lower())  # casse tolérée
    assert r2.status_code == 201
    assert r2.json() == {"statut": "lien_cree", "relation": "parent", "student_pseudo_id": ELEVE}
    # Le parent p2 peut désormais obtenir un jeton élève et lire le tableau de bord.
    t = client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ELEVE}, headers=_h(j["p2"]))
    assert t.status_code == 200
    # Minimisation : le pseudo-id n'est plus conservé dans l'invitation consommée.
    db = BillingSession()
    try:
        inv = db.query(liens.InvitationLien).one()
        assert inv.pseudo_id is None and inv.utilise_par == ids["p2"]
    finally:
        db.close()


def test_usage_unique(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    assert _accepter(client, j["p2"], code).status_code == 201
    r = _accepter(client, j["p3"], code)
    assert (r.status_code, r.json()["detail"]) == (400, "invitation_invalide")


def test_expiree(acteurs, monkeypatch):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    futur = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) + _dt.timedelta(hours=49)
    monkeypatch.setattr(liens, "_maintenant", lambda: futur)
    r = _accepter(client, j["p2"], code)
    assert (r.status_code, r.json()["detail"]) == (400, "invitation_invalide")


@pytest.mark.parametrize("code", ["AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", "pas-un-code", "", "1111-1111-1111-1111-1111-1111"])
def test_code_inconnu_ou_malforme_meme_reponse(acteurs, code):
    client, j, _ = acteurs
    r = _accepter(client, j["p2"], code)
    if code == "":
        assert r.status_code == 422
    else:
        assert (r.status_code, r.json()) == (400, {"detail": "invitation_invalide"})


# --------------------------------------------------------------------------- #
# Validation par le parent (compte connecté, bon rôle, confirmation explicite)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("confirmation", [False, None, "oui", 1])
def test_confirmation_explicite_obligatoire(acteurs, confirmation):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    corps = {"code": code} if confirmation is None else {"code": code, "confirmation": confirmation}
    assert client.post(URL_ACC, json=corps, headers=_h(j["p2"])).status_code == 422
    assert _accepter(client, j["p2"], code).status_code == 201  # code NON consommé par l'échec


def test_jeton_eleve_ne_peut_pas_accepter(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    r = _accepter(client, j["eleve"], code)
    assert (r.status_code, r.json()["detail"]) == (401, "jeton_compte_requis")


def test_compte_eleve_ne_peut_pas_accepter_une_invitation_parent(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    assert _accepter(client, j["ce"], code).status_code == 400
    assert _accepter(client, j["p2"], code).status_code == 201  # non consommée par le refus


def test_invitation_relation_eleve_pour_le_compte_eleve(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["p1"], relation="eleve").json()["code"]
    assert _accepter(client, j["p2"], code).status_code == 400  # un parent ne prend pas le rôle élève
    assert _accepter(client, j["ce"], code).json()["relation"] == "eleve"


def test_deja_lie_ne_consomme_pas(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    r = _accepter(client, j["p1"], code)
    assert (r.status_code, r.json()["detail"]) == (409, "deja_lie")
    assert _accepter(client, j["p2"], code).status_code == 201


def test_sans_jeton_refus_meme_en_mode_off(acteurs, monkeypatch):
    client, j, _ = acteurs
    monkeypatch.setenv("MIKA_AUTH_MODE", "off")
    assert client.post(URL_INV, json={"student_pseudo_id": ELEVE}).status_code == 401
    assert client.post(URL_ACC, json={"code": "x", "confirmation": True}).status_code == 401


# --------------------------------------------------------------------------- #
# Émission : jamais par simple pseudo-id
# --------------------------------------------------------------------------- #
def test_emission_refusee_sans_lien(acteurs):
    client, j, _ = acteurs
    assert _inviter(client, j["p2"]).status_code == 403            # parent non lié
    assert _inviter(client, j["eleve"], eleve="autre-eleve").status_code == 403  # jeton d'un autre élève
    assert _inviter(client, j["ce"]).status_code == 403            # compte élève non titulaire


def test_parent_lie_peut_inviter_un_second_parent(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["p1"]).json()["code"]
    assert _accepter(client, j["p3"], code).status_code == 201


def test_aucune_route_ne_lie_par_simple_pseudo():
    """Seul le module d'invitation appelle `lier` / crée LienCompteEleve dans le code applicatif."""
    racine = Path(__file__).resolve().parents[1]
    fautifs = []
    for f in list((racine / "app").rglob("*.py")) + list((racine / "paiement_comptes").rglob("*.py")):
        texte = f.read_text("utf-8")
        if re.search(r"\blier\(|LienCompteEleve\(", texte) and f.name != "liens.py":
            fautifs.append(str(f))
    assert fautifs == []


def test_max_invitations_actives(acteurs):
    client, j, _ = acteurs
    codes = [_inviter(client, j["p1"]).status_code for _ in range(6)]
    assert codes == [201] * 5 + [409]


# --------------------------------------------------------------------------- #
# Force brute, quotas, concurrence
# --------------------------------------------------------------------------- #
def test_force_brute_bloquee_par_compte_sans_toucher_les_autres(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    for i in range(5):
        assert _accepter(client, j["p3"], f"AAAA-AAAA-AAAA-AAAA-AAAA-AAA{'ABCDE'[i]}").status_code == 400
    r = _accepter(client, j["p3"], code)
    assert r.status_code == 429 and "Retry-After" in r.headers  # même avec le bon code
    assert _accepter(client, j["p2"], code).status_code == 201  # autre compte : non affecté


def test_quota_d_emission(acteurs):
    client, j, _ = acteurs

    def liberer():  # le quota (10/h) est distinct du plafond d'invitations ACTIVES (5)
        db = BillingSession()
        db.query(liens.InvitationLien).delete()
        db.commit()
        db.close()

    codes = []
    for _ in range(11):
        codes.append(_inviter(client, j["p1"]).status_code)
        liberer()
    assert codes[:10] == [201] * 10 and codes[10] == 429


def test_acceptations_concurrentes_une_seule_gagne(acteurs):
    client, j, ids = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    db = BillingSession()
    comptes = [crud_billing.get_compte(db, ids["p2"]), crud_billing.get_compte(db, ids["p3"])]
    db.close()
    barriere, res = threading.Barrier(2), []

    def run(compte):
        s = BillingSession()
        barriere.wait()
        try:
            res.append(liens.accepter_invitation(s, code, compte))
        except liens.InvitationInvalide:
            res.append("refus")
        finally:
            s.close()

    ths = [threading.Thread(target=run, args=(c,)) for c in comptes]
    [t.start() for t in ths]
    [t.join(20) for t in ths]
    assert sorted(map(str, res)).count("refus") == 1
    db = BillingSession()
    try:
        assert db.query(liens.LienCompteEleve).filter_by(eleve_hmac=hmac_eleve(ELEVE)).count() == 2  # p1 + gagnant
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# RGPD, configuration, outil opérateur
# --------------------------------------------------------------------------- #
def test_rgpd_export_sans_code_et_effacement(acteurs):
    client, j, _ = acteurs
    code = _inviter(client, j["eleve"]).json()["code"]
    client.post("/api/v1/memory/schedule", json={"user_id": ELEVE, "notion_id": "n1", "mastery_event": "SUCCESS"},
                headers=_h(j["eleve"]))
    out = client.get(f"/api/v1/rgpd/export/{ELEVE}", headers=_h(j["p1"])).json()
    assert len(out["invitations_liens"]) == 1 and code not in str(out) and "@" not in str(out["invitations_liens"])
    r = client.delete(f"/api/v1/rgpd/effacer/{ELEVE}", headers=_h(j["p1"]))
    assert r.json()["invitations_supprimees"] == 1
    assert _accepter(client, j["p2"], code).status_code == 400  # code mort avec l'effacement


@pytest.mark.parametrize("ttl", ["9", "10081", "abc"])
def test_ttl_invalide(monkeypatch, ttl):
    monkeypatch.setenv("MIKA_INVITATION_TTL_MIN", ttl)
    with pytest.raises(ValueError):
        liens.ttl_invitation_min()


def test_outil_operateur(acteurs, capsys):
    from tools.liens import main

    assert main(["inviter", "eleve-sans-lien"]) == 0
    code = re.search(r"code: (\S+)", capsys.readouterr().out).group(1)
    client, j, _ = acteurs
    assert _accepter(client, j["p2"], code).json()["student_pseudo_id"] == "eleve-sans-lien"
    assert main(["inviter", "pseudo invalide"]) == 1
