"""
Décision D12 — critère BACKEND du passage en MIKA_AUTH_MODE=enforce : le flux parent/enfant
complet, de bout en bout, en mode enforce, avec les seules routes publiques (aucun appel
interne sauf l'outil opérateur du premier rattachement). Le passage en production exige EN
PLUS le front conforme et ses tests E2E verts (FRONT_AUTH_INTEGRATION.md §7).
Acteurs et contenus FICTIFS.
"""

import re

import pytest

from app.api.v1.tutorat import contenu
from app.curriculum.fixtures import referentiel_fictif
from paiement_comptes import crud_billing
from tests_cloud.test_mika_api import EXO, PLAN, PREREQ, _exercice

ENFANT = "enfant-e2e-01"
MDP = "motdepasse-e2e-0001"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _verifier_email(c, email):
    """Transport FAUX (aucun envoi réel) : le jeton est lu dans la boîte de test."""
    from app.core.courriel import boite_de_test

    jeton = boite_de_test().derniers(email)[-1].metadonnees["jeton"]
    r = c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": jeton})
    assert r.json() == {"statut": "EMAIL_VERIFIED"}


@pytest.fixture()
def e2e(client, monkeypatch, capsys):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    monkeypatch.setenv("MIKA_RATE_LIMIT", "on")
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [_exercice()], {EXO: PLAN},
                                                       autoriser_fictif=True))
    yield client, capsys
    contenu.definir_catalogue(None)


def test_flux_parent_enfant_complet_en_enforce(e2e):
    c, capsys = e2e
    # 1. Inscription + connexion du parent (aucun cookie, jeton de compte).
    assert c.post("/api/v1/comptes/inscription", json={"email": "parent1@example.com", "mot_de_passe": MDP}).status_code == 201
    r = c.post("/api/v1/comptes/connexion", json={"email": "parent1@example.com", "mot_de_passe": MDP})
    assert r.status_code == 200 and "set-cookie" not in r.headers
    p1 = r.json()["token"]
    assert r.json()["compte"]["email_verifie"] is False
    # R19 : sans adresse vérifiée, aucun rattachement possible.
    code_test = c.post("/api/v1/liens/accepter", json={"code": "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", "confirmation": True},
                       headers=_h(p1))
    assert (code_test.status_code, code_test.json()["detail"]) == (403, "email_non_verifie")
    _verifier_email(c, "parent1@example.com")
    # Sans lien : AUCUN accès à l'enfant, même en connaissant son pseudo-id (D8).
    assert c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT}, headers=_h(p1)).status_code == 403
    assert c.post("/api/v1/liens/invitations", json={"student_pseudo_id": ENFANT}, headers=_h(p1)).status_code == 403

    # 2. Premier rattachement : l'opérateur émet un code, le parent le VALIDE.
    from tools.liens import main as outil_liens

    assert outil_liens(["inviter", ENFANT]) == 0
    code = re.search(r"code: (\S+)", capsys.readouterr().out).group(1)
    r = c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(p1))
    assert r.status_code == 201 and r.json()["student_pseudo_id"] == ENFANT

    # 3. Jeton de séance élève.
    r = c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": ENFANT}, headers=_h(p1))
    assert r.status_code == 200
    je = r.json()["token"]

    # 4. Séance : identifiant généré par le serveur (D15).
    sid = c.post("/api/v1/session/nouvelle", json={"user_id": ENFANT}, headers=_h(je)).json()["session_id"]
    assert c.post("/api/v1/session/heartbeat", json={"session_id": sid, "user_id": ENFANT}, headers=_h(je)).status_code == 200
    assert c.post("/api/v1/session/save-state", json={"session_id": sid, "user_id": ENFANT,
                                                      "state_data": {"ardoise": "5x"}}, headers=_h(je)).status_code == 200
    r = c.post("/api/v1/session/reconnect", json={"session_id": sid, "user_id": ENFANT}, headers=_h(je))
    assert r.json()["session_state"]["ardoise"] == "5x"

    # 5. Exercice du catalogue historique : équivalence symbolique démontrée acceptée (D5).
    r = c.post("/api/v1/exercices/soumettre", headers=_h(je),
               json={"exercice_id": "exo-maths-calcul-litteral-1", "student_pseudo_id": ENFANT, "reponse": "5*x"})
    assert r.status_code == 200 and r.json()["est_correct"] is True

    # 6. Tuteur Mika : aide, réussite, compréhension RATÉE ⇒ non comptée (D14).
    from app.api.v1.mikamike import crud
    from app.api.v1.mikamike.store import SessionLocal
    from app.core.pseudonymisation import hmac_eleve

    db = SessionLocal()
    crud.upsert_etat(db, hmac_eleve(ENFANT), PREREQ, "ACQUIS_AUTONOME")
    db.close()
    t = c.post("/api/v1/mika/session/start", headers=_h(je),
               json={"student_pseudo_id": ENFANT, "requete_id": "e2e-1", "exercice_id": EXO}).json()

    def op(nom, req, **kw):
        corps = {"student_pseudo_id": ENFANT, "requete_id": req, "tutorat_id": t["tutorat_id"], "version": t["version"], **kw}
        r = c.post(f"/api/v1/mika/session/{nom}", json=corps, headers=_h(je))
        assert r.status_code == 200, r.text
        return r.json()

    t = op("help", "e2e-2")
    t = op("answer", "e2e-3", reponse="0,7")
    assert t["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    t = op("comprehension", "e2e-4", reponse="12")
    assert t["etat"]["niveau_estime"] == "FRAGILE"

    # 7. L'enfant invite un second parent, qui valide depuis SON compte.
    code2 = c.post("/api/v1/liens/invitations", json={"student_pseudo_id": ENFANT}, headers=_h(je)).json()["code"]
    c.post("/api/v1/comptes/inscription", json={"email": "parent2@example.com", "mot_de_passe": MDP})
    p2 = c.post("/api/v1/comptes/connexion", json={"email": "parent2@example.com", "mot_de_passe": MDP}).json()["token"]
    _verifier_email(c, "parent2@example.com")
    assert c.post("/api/v1/liens/accepter", json={"code": code2, "confirmation": True}, headers=_h(p2)).status_code == 201

    # 8. Tableau de bord et export RGPD par les parents liés.
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(p2)).status_code == 200
    export = c.get(f"/api/v1/rgpd/export/{ENFANT}", headers=_h(p1)).json()
    assert export["tutorats_mika"] and len(export["liens_comptes"]) == 2 and len(export["invitations_liens"]) == 2
    assert code not in str(export) and code2 not in str(export)

    # 9. L'enfant ne peut pas s'effacer (D9) ; le parent efface ⇒ tout est coupé.
    assert c.delete(f"/api/v1/rgpd/effacer/{ENFANT}", headers=_h(je)).status_code == 403
    r = c.delete(f"/api/v1/rgpd/effacer/{ENFANT}", headers=_h(p1))
    assert r.status_code == 200 and r.json()["liens_compte_supprimes"] == 2
    r = c.post("/api/v1/session/heartbeat", json={"session_id": sid, "user_id": ENFANT}, headers=_h(je))
    assert (r.status_code, r.json()["detail"]) == (401, "jeton_revoque")
    assert c.get(f"/api/v1/parents/dashboard/{ENFANT}", headers=_h(p2)).status_code == 403
    assert c.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=_h(p2)).status_code == 400

    # 10. Limitation R7 active sur la connexion.
    codes = [c.post("/api/v1/comptes/connexion", json={"email": "parent1@example.com", "mot_de_passe": "faux-mdp-0000"}).status_code
             for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_configuration_de_production_demarre(monkeypatch, client):
    """Configuration cible du passage (D12) : production + enforce + limitation actives."""
    from fastapi.testclient import TestClient

    import main

    from app.core import courriel

    monkeypatch.setenv("MIKA_ENV", "production")
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    monkeypatch.setenv("MIKA_RATE_LIMIT", "on")
    # Production : un fournisseur de courriel RÉEL est exigé ; on en simule l'enregistrement.
    monkeypatch.setitem(courriel._FABRIQUES, "fournisseur-simule", courriel.TransportFaux)
    monkeypatch.setenv("MIKA_EMAIL_TRANSPORT", "fournisseur-simule")
    with TestClient(main.create_app()) as c:
        assert c.get("/health").status_code == 200
        assert c.post("/api/v1/exercices/soumettre", json={}).status_code == 401
    for var, val in (("MIKA_AUTH_MODE", "off"), ("MIKA_RATE_LIMIT", "off"), ("MIKA_EMAIL_TRANSPORT", "faux"),
                     ("MIKA_EMAIL_VERIFICATION", "off")):
        monkeypatch.setenv(var, val)
        with pytest.raises(Exception):
            with TestClient(main.create_app()):
                pass
        monkeypatch.setenv(var, {"MIKA_AUTH_MODE": "enforce", "MIKA_RATE_LIMIT": "on",
                                 "MIKA_EMAIL_TRANSPORT": "fournisseur-simule",
                                 "MIKA_EMAIL_VERIFICATION": "requise"}[var])
