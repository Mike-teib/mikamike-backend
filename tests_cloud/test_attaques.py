"""
Tests d'attaque (lot F). Index des scénarios couverts ailleurs, pour éviter les doublons :
  IDOR, auth bypass, confusion JWT, jeton d'un autre rôle, alg none ........ test_auth.py
  SymPy DoS, expressions hostiles ............................................ test_review_session1.py (R2-03)
  manifest altéré, SHA incorrect, source falsifiée, chapitre incohérent,
  notion non prouvée, texte tronqué, duplicata, traversée (import) ........... test_import_v2_integrite.py
  JSON profondément imbriqué (import) ......................................... test_review_session1.py (R2-04)
Ici : surface HTTP (taille, Unicode, traversée, charges SQL, JSON imbriqué, DoS via l'API).
"""

import time

import pytest

from app.api.v1.mikamike.store import SessionLocal, TentativeExercice

SOUMETTRE = "/api/v1/exercices/soumettre"


def _corps(pseudo="eleve-att-1", reponse="3"):
    return {"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pseudo, "reponse": reponse}


# --------------------------------------------------------------------------- #
# Entrée énorme
# --------------------------------------------------------------------------- #
def test_content_length_enorme_refuse_avant_lecture(client):
    r = client.post(SOUMETTRE, content=b"{" + b" " * (5 * 1024 * 1024) + b"}",
                    headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_corps_chunked_enorme_refuse(client):
    def flux():
        for _ in range(80):
            yield b" " * 65536

    r = client.post(SOUMETTRE, content=flux(), headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_content_length_invalide(client):
    r = client.post(SOUMETTRE, content=b"{}", headers={"content-type": "application/json", "content-length": "-1"})
    assert r.status_code in (400, 413)


def test_corps_normal_accepte(client):
    assert client.post(SOUMETTRE, json=_corps()).status_code == 200


def test_reponse_trop_longue(client):
    assert client.post(SOUMETTRE, json=_corps(reponse="1" * 501)).status_code == 422


# --------------------------------------------------------------------------- #
# Unicode hostile dans les identifiants
# --------------------------------------------------------------------------- #
HOSTILES_ID = [
    "eleve‮1",           # RLO (inversion d'affichage)
    "eleve​1",           # espace de largeur nulle
    "eleve\x001",             # NUL
    "еleve-1",                # « е » cyrillique (homoglyphe)
    "élève-1",                # accents (PII possible : prénom)
    "eleve 1",                # espace
    "eleve@exemple.fr",       # e-mail
    "../../etc/passwd",       # traversée
    "x" * 129,                # longueur
    "",                       # vide
]


@pytest.mark.parametrize("pid", HOSTILES_ID)
def test_identifiant_hostile_refuse(client, pid):
    assert client.post(SOUMETTRE, json=_corps(pseudo=pid)).status_code == 422
    assert client.post("/api/v1/session/heartbeat", json={"session_id": "s1", "user_id": pid}).status_code == 422
    assert client.post("/api/v1/mika/session/start", json={"student_pseudo_id": pid, "requete_id": "r",
                                                          "exercice_id": "exo:x"}).status_code == 422


@pytest.mark.parametrize("chemin", ["/api/v1/rgpd/export/..%2F..%2Fetc%2Fpasswd", "/api/v1/rgpd/export/%00",
                                    "/api/v1/parents/dashboard/a%20b", "/api/v1/parcours/u1/..%2F..%2F/maths",
                                    "/api/v1/mika/session/..%2F..%2Fetc"])
def test_traversee_dans_les_chemins(client, chemin):
    r = client.get(chemin, params={"student_id": "u1"})
    assert r.status_code in (404, 422), (chemin, r.status_code)


# --------------------------------------------------------------------------- #
# Charges « SQL-like » : jamais interprétées
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("charge", ["' OR '1'='1", "1; DROP TABLE mika_tentatives; --",
                                    "\" OR 1=1 --", "%' UNION SELECT * FROM comptes --"])
def test_charge_sql_dans_une_reponse_libre(client, charge):
    r = client.post(SOUMETTRE, json=_corps(reponse=charge))
    assert r.status_code == 200 and r.json()["est_correct"] is False
    db = SessionLocal()
    try:
        assert db.query(TentativeExercice).count() == 1  # table intacte, 1 ligne
    finally:
        db.close()


@pytest.mark.parametrize("charge", ["' OR '1'='1", "1;DROP TABLE x", "a'--"])
def test_charge_sql_dans_un_identifiant(client, charge):
    assert client.post(SOUMETTRE, json=_corps(pseudo=charge)).status_code == 422


# --------------------------------------------------------------------------- #
# JSON profondément imbriqué / types inattendus
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("profondeur", [900, 100_000])
def test_json_imbrique_sur_l_api(client, profondeur):
    corps = ('{"session_id":"s1","user_id":"u1","state_data":{"a":' + "[" * profondeur
             + "]" * profondeur + "}}")
    r = client.post("/api/v1/session/save-state", content=corps, headers={"content-type": "application/json"})
    assert r.status_code in (200, 400, 413, 422)
    assert client.get("/health").status_code == 200  # le serveur répond toujours


@pytest.mark.parametrize("corps", [[], "texte", 42, None, {"exercice_id": ["liste"]}, {"avec_aide": "oui-non"}])
def test_types_inattendus(client, corps):
    assert client.post(SOUMETTRE, json=corps).status_code == 422


# --------------------------------------------------------------------------- #
# DoS applicatif via le tuteur (réponse mathématique hostile)
# --------------------------------------------------------------------------- #
def test_reponse_mathematique_hostile_via_tuteur(client):
    from app.api.v1.mikamike import crud
    from app.api.v1.tutorat import contenu
    from app.core.pseudonymisation import hmac_eleve
    from tests_cloud.test_mika_api import EXO, PLAN, PREREQ, _exercice
    from app.curriculum.fixtures import referentiel_fictif

    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [_exercice()], {EXO: PLAN},
                                                       autoriser_fictif=True))
    try:
        db = SessionLocal()
        crud.upsert_etat(db, hmac_eleve("eleve-dos"), PREREQ, "MAITRISE")
        db.close()
        t = client.post("/api/v1/mika/session/start", json={"student_pseudo_id": "eleve-dos", "requete_id": "r0",
                                                            "exercice_id": EXO}).json()
        for i, hostile in enumerate(["9^(59*59*59*59*59)", "(x+y+z+1)^60", "exp(exp(exp(59)))"]):
            debut = time.perf_counter()
            r = client.post("/api/v1/mika/session/answer", json={
                "student_pseudo_id": "eleve-dos", "requete_id": f"r{i + 1}", "tutorat_id": t["tutorat_id"],
                "version": t["version"], "reponse": hostile})
            assert time.perf_counter() - debut < 3 and r.status_code == 200
            t = r.json()
            assert t["reponse"]["action"] in ("DEMANDER_REFORMULATION", "REVUE_HUMAINE")
            if t["etat"]["termine"]:
                break
    finally:
        contenu.definir_catalogue(None)


# --------------------------------------------------------------------------- #
# Fuite d'information dans les erreurs
# --------------------------------------------------------------------------- #
def test_erreurs_sans_trace_ni_secret(client):
    import os

    for r in (client.post(SOUMETTRE, json={"exercice_id": "inconnu", "student_pseudo_id": "u", "reponse": "1"}),
              client.get("/api/v1/rgpd/export/inconnu-total"),
              client.post("/api/v1/comptes/connexion", json={"email": "x@example.com", "mot_de_passe": "faux-mdp-1"})):
        txt = r.text
        assert "Traceback" not in txt and "sqlalchemy" not in txt.lower()
        assert os.environ["MIKA_JWT_SECRET"] not in txt and os.environ["MIKA_PSEUDO_SECRET"] not in txt
