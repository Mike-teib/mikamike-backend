"""
Session 5 — E2E backend COMPLET de la release candidate, en MIKA_AUTH_MODE=enforce :

parent inscription → vérification e-mail (transport factice) → enfant (premier rattachement par
l'opérateur) → invitation → rattachement → login → création de séance → exercice → quiz → Mika →
progression → tableau parent → export RGPD → révocation → suppression → anciens jetons refusés.

Routes publiques uniquement (sauf l'outil opérateur du premier rattachement et la lecture de la
boîte factice). Acteurs, contenus et réponses FICTIFS. Aucun courriel réel.

Quiz : aucune route HTTP de quiz n'existe dans l'API (le module `quiz_types` est prêt mais n'est
exposé nulle part) ; l'étape « quiz » est donc vérifiée EN PROCESSUS, sur une question liée à la
même notion que le tutorat. Voir RELEASE_CANDIDATE.md (manques front/API).
"""

import datetime as _dt
import re

import pytest

from app.api.v1.tutorat import contenu
from app.curriculum.fixtures import referentiel_fictif
from paiement_comptes import crud_billing
from tests_cloud.test_mika_api import EXO, PLAN, PREREQ, _exercice

ENFANT = "enfant-rc1-01"
MDP = "motdepasse-rc1-0001"
EMAIL = "parent.rc1@example.com"
EMAIL2 = "parent2.rc1@example.com"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _jeton_verification(email):
    from app.core.courriel import boite_de_test

    return boite_de_test().derniers(email)[-1].metadonnees["jeton"]


@pytest.fixture()
def rc(client, monkeypatch, capsys):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    monkeypatch.setenv("MIKA_RATE_LIMIT", "on")
    monkeypatch.setenv("MIKA_EMAIL_TRANSPORT", "faux")
    monkeypatch.delenv("MIKA_PROGRESSION_MOTEUR", raising=False)
    from app.core.courriel import boite_de_test

    boite_de_test().vider()
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [_exercice()], {EXO: PLAN},
                                                       autoriser_fictif=True))
    yield client, capsys
    contenu.definir_catalogue(None)


def test_e2e_release_candidate_complet_en_enforce(rc):
    c, capsys = rc

    # 1. Inscription du parent : compte créé, adresse NON vérifiée, courriel émis (transport factice).
    r = c.post("/api/v1/comptes/inscription", json={"email": EMAIL, "mot_de_passe": MDP})
    assert r.status_code == 201
    t_inscription = r.json()["token"]
    assert r.json()["compte"]["email_verifie"] is False
    jeton_verif = _jeton_verification(EMAIL)
    assert jeton_verif not in r.text  # le jeton ne transite JAMAIS par la réponse HTTP

    # 2. Vérification d'adresse (lien reçu par courriel), usage unique.
    r = c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": jeton_verif})
    assert r.json() == {"statut": "EMAIL_VERIFIED"}
    r = c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": jeton_verif})
    assert (r.status_code, r.json()["detail"]) == (400, "jeton_invalide_ou_expire")

    # 3. Enfant : sans lien, aucun accès (D8) ; premier rattachement par l'opérateur.
    assert c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT},
                  headers=_h(t_inscription)).status_code == 403
    from tools.liens import main as outil_liens

    assert outil_liens(["inviter", ENFANT]) == 0
    code = re.search(r"code: (\S+)", capsys.readouterr().out).group(1)

    # 4. Invitation → rattachement (le parent VALIDE depuis son compte, confirmation explicite).
    r = c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": False}, headers=_h(t_inscription))
    assert r.status_code == 422
    r = c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(t_inscription))
    assert r.status_code == 201 and r.json()["student_pseudo_id"] == ENFANT
    assert c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True},
                  headers=_h(t_inscription)).status_code == 400  # usage unique

    # 5. Login (nouvelle connexion : jeton distinct, même compte).
    r = c.post("/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP})
    assert r.status_code == 200 and r.json()["compte"]["email_verifie"] is True
    t_parent = r.json()["token"]

    # 6. Jeton de séance élève + séance générée par le serveur (D15).
    je = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT}, headers=_h(t_parent)).json()["token"]
    r = c.post("/api/v1/session/nouvelle", json={"user_id": ENFANT}, headers=_h(je))
    assert r.status_code == 201
    sid = r.json()["session_id"]
    assert len(sid) >= 32
    assert c.post("/api/v1/session/heartbeat", json={"session_id": "invente-par-le-client", "user_id": ENFANT},
                  headers=_h(je)).status_code == 404  # D15 : identifiant non créé par le serveur

    # 7. Exercice : moteur de progression sur historique (pas de diagnostic sur une réponse).
    def soumettre(reponse, aide=False):
        r = c.post("/api/v1/exercices/soumettre", headers=_h(je), json={
            "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": ENFANT, "reponse": reponse, "avec_aide": aide})
        assert r.status_code == 200, r.text
        return r.json()

    premier = soumettre("x = 999")
    assert premier["est_correct"] is False and premier["remediation"]
    assert premier["progression"]["niveau"] == "NON_EVALUEE" and premier["etat_maitrise"] == "INCONNU"
    assert soumettre("3", aide=True)["etat_maitrise"] == "ACQUIS_ASSISTE"
    troisieme = soumettre("3")
    assert troisieme["progression"]["observations"] == 3 and troisieme["progression"]["niveau"] != "MAITRISEE"

    # 8. Quiz (en processus : aucune route HTTP n'existe) — correction EXACTE uniquement.
    from app.curriculum.quiz_types import QuestionVraiFaux, corriger, valider
    from app.curriculum.verifiers.base import Verdict

    idx = referentiel_fictif().index()
    n = idx.notions["notion:fictif:fractions-decimales"]
    q = QuestionVraiFaux(id="quiz:fictif:rc1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                         enonce="7/10 est égal à 0,7.", explication="Sept dixièmes : 0,7.", affirmation_vraie=True)
    assert valider(q, idx, autoriser_fictif=True) == []
    assert corriger(q, True).verdict == Verdict.VALID and corriger(q, False).verdict == Verdict.INVALID

    # 9. Tuteur Mika : prérequis consolidé, réponse juste en autonomie.
    from app.api.v1.mikamike import crud
    from app.api.v1.mikamike.store import SessionLocal
    from app.core.pseudonymisation import hmac_eleve

    db = SessionLocal()
    crud.upsert_etat(db, hmac_eleve(ENFANT), PREREQ, "ACQUIS_AUTONOME")
    db.close()
    t = c.post("/api/v1/mika/session/start", headers=_h(je),
               json={"student_pseudo_id": ENFANT, "requete_id": "rc1-1", "exercice_id": EXO}).json()
    r = c.post("/api/v1/mika/session/answer", headers=_h(je), json={
        "student_pseudo_id": ENFANT, "requete_id": "rc1-2", "tutorat_id": t["tutorat_id"],
        "version": t["version"], "reponse": "0,7"})
    assert r.status_code == 200 and r.json()["etat"]["termine"]
    assert r.json()["etat"]["avec_aide"] is False

    # 10. Progression : la notion du tutorat est journalisée, sans diagnostic sur une réponse.
    db = SessionLocal()
    etats = crud.get_etats(db, hmac_eleve(ENFANT))
    db.close()
    assert etats["notion:fictif:fractions-decimales"] == "EN_COURS"
    assert etats["equations_1er_degre"] in {"EN_COURS", "ACQUIS_ASSISTE"}

    # 11. Tableau de bord parent : agrégats seulement (schéma fermé), aucune donnée nominative.
    r = c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(t_parent))
    assert r.status_code == 200
    stats = r.json()["statistiques_pedagogiques"]
    assert stats["exercices_tentes"] == 4 and stats["exercices_reussis"] == 3
    assert EMAIL not in r.text and "0,7" not in r.text and "x = 999" not in r.text
    # L'élève lit ses propres agrégats (Action.LECTURE sur son pseudo-id) : même schéma fermé.
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(je)).status_code == 200

    # 12. Export RGPD : données de l'élève (parent lié) et du compte (titulaire).
    exp = c.get(f"/api/v1/rgpd/export/{ENFANT}", headers=_h(t_parent))
    assert exp.status_code == 200 and exp.json()["total_tentatives"] == 4
    assert code not in exp.text
    moi = c.get("/api/v1/comptes/moi/export", headers=_h(t_parent)).json()
    assert moi["compte"]["email"] == EMAIL and len(moi["liens_eleves"]) == 1
    assert "mot_de_passe" not in str(moi).replace("mot_de_passe_", "") and jeton_verif not in str(moi)

    # 13. Révocation : déconnexion GLOBALE ⇒ tous les jetons antérieurs refusés (compte + élève).
    assert c.post("/api/v1/comptes/deconnexion", headers=_h(t_parent)).status_code == 204
    for ancien in (t_inscription, t_parent):
        r = c.get("/api/v1/comptes/moi", headers=_h(ancien))
        assert (r.status_code, r.json()["detail"]) == (401, "jeton_revoque")
    r = c.post("/api/v1/session/heartbeat", json={"session_id": sid, "user_id": ENFANT}, headers=_h(je))
    assert (r.status_code, r.json()["detail"]) == (401, "jeton_revoque")

    # Reconnexion : nouveau jeton valide.
    t_neuf = c.post("/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP}).json()["token"]
    assert c.get("/api/v1/comptes/moi", headers=_h(t_neuf)).status_code == 200
    je2 = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT}, headers=_h(t_neuf)).json()["token"]

    # 14. Suppression du compte (mot de passe exigé) ⇒ plus rien ne passe.
    r = c.request("DELETE", "/api/v1/comptes/moi", json={"mot_de_passe": "mauvais-mdp-000", "confirmation": True}, headers=_h(t_neuf))
    assert r.status_code == 403
    r = c.request("DELETE", "/api/v1/comptes/moi", json={"mot_de_passe": MDP, "confirmation": True}, headers=_h(t_neuf))
    assert r.status_code == 200, r.text

    # 15. Anciens jetons refusés (compte et élève), connexion impossible, pas de réinscription fantôme.
    for ancien in (t_inscription, t_parent, t_neuf):
        assert c.get("/api/v1/comptes/moi", headers=_h(ancien)).status_code == 401
    for jeton_eleve in (je, je2):
        r = c.post("/api/v1/session/heartbeat", json={"session_id": sid, "user_id": ENFANT}, headers=_h(jeton_eleve))
        assert r.status_code == 401
        assert c.post("/api/v1/exercices/soumettre", headers=_h(jeton_eleve), json={
            "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": ENFANT, "reponse": "3"}).status_code == 401
    assert c.post("/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP}).status_code == 401
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(t_neuf)).status_code == 401
    # Les données d'apprentissage appartiennent à l'élève : intactes jusqu'à /rgpd/effacer (D9).
    db = SessionLocal()
    assert len(crud.get_tentatives(db, hmac_eleve(ENFANT))) == 4
    db.close()


def test_e2e_second_parent_revocation_ciblee(rc):
    """Un second parent rattaché par invitation de l'enfant garde son accès quand le premier se
    déconnecte ; il le perd dès que le lien disparaît (effacement RGPD par un parent)."""
    c, capsys = rc
    for email in (EMAIL, EMAIL2):
        assert c.post("/api/v1/comptes/inscription", json={"email": email, "mot_de_passe": MDP}).status_code == 201
        c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": _jeton_verification(email)})
    p1 = c.post("/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP}).json()["token"]
    p2 = c.post("/api/v1/comptes/connexion", json={"email": EMAIL2, "mot_de_passe": MDP}).json()["token"]
    from tools.liens import main as outil_liens

    outil_liens(["inviter", ENFANT])
    code = re.search(r"code: (\S+)", capsys.readouterr().out).group(1)
    assert c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(p1)).status_code == 201
    je = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT}, headers=_h(p1)).json()["token"]
    code2 = c.post("/api/v1/liens/invitations", json={"student_pseudo_id": ENFANT}, headers=_h(je)).json()["code"]
    assert c.post("/api/v1/liens/accepter", json={"code": code2, "confirmation": True}, headers=_h(p2)).status_code == 201

    assert c.post("/api/v1/comptes/deconnexion", headers=_h(p1)).status_code == 204
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(p2)).status_code == 200
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(p1)).status_code == 401

    r = c.delete(f"/api/v1/rgpd/effacer/{ENFANT}", headers=_h(p2))
    assert r.status_code == 200
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(p2)).status_code == 403


def test_e2e_jeton_expire_refuse(rc, monkeypatch):
    """Un jeton de compte expiré est refusé (401), sans fuite de raison interne."""
    import jwt

    c, _ = rc
    c.post("/api/v1/comptes/inscription", json={"email": EMAIL, "mot_de_passe": MDP})
    t = c.post("/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP}).json()["token"]
    claims = jwt.decode(t, options={"verify_signature": False})
    claims["exp"] = int((_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=5)).timestamp())
    from app.core.security_config import get_jwt_secret

    vieux = jwt.encode(claims, get_jwt_secret(), algorithm="HS256")
    r = c.get("/api/v1/comptes/moi", headers=_h(vieux))
    assert r.status_code == 401
    assert "Traceback" not in r.text and "ExpiredSignature" not in r.text
