import pytest
from fastapi.testclient import TestClient
from main import app
from app.api.v1.mikamike.catalogue import EXERCICES

client = TestClient(app)

def test_soumettre_reponse_fausse():
    # Attempting to submit a wrong answer to an exercise
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths_5e_04-0",
        "student_pseudo_id": "anon-tester-1",
        "reponse": "non_correct"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["est_correct"] is False
    assert data["remediation"] is not None
    assert data["remediation"]["exercice_prerequis"] is not None

def test_soumettre_reponse_juste():
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths_5e_04-0",
        "student_pseudo_id": "anon-tester-1",
        "reponse": "oui"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["est_correct"] is True
    assert data["remediation"] is None

def test_soumettre_exercice_inconnu():
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-inexistant-1234",
        "student_pseudo_id": "anon-tester-1",
        "reponse": "oui"
    })
    assert r.status_code == 404

def test_prochaine_etape_reelle():
    r = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-1&niveau=5e")
    assert r.status_code == 200
    data = r.json()
    assert "exercice_id" in data
    assert data["exercice_id"] in EXERCICES
    assert data["consigne"] == EXERCICES[data["exercice_id"]]["enonce"]

def test_prochaine_etape_deterministe():
    r1 = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-new&niveau=5e")
    r2 = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-new&niveau=5e")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["exercice_id"] == r2.json()["exercice_id"]

def test_prochaine_etape_evolue_apres_reussite():
    r1 = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-evol&niveau=5e")
    exo1 = r1.json()["exercice_id"]

    # 2 consecutive successful answers to master the notion and force evolution
    client.post("/api/v1/exercices/soumettre", json={"exercice_id": exo1, "student_pseudo_id": "anon-tester-evol", "reponse": "oui"})
    client.post("/api/v1/exercices/soumettre", json={"exercice_id": exo1, "student_pseudo_id": "anon-tester-evol", "reponse": "oui"})

    r2 = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-evol&niveau=5e")
    exo2 = r2.json()["exercice_id"]
    assert exo1 != exo2

def test_dashboard_rgpd():
    r = client.get("/api/v1/parents/dashboard/anon-tester-1")
    assert r.status_code == 200
    data = r.json()
    for k in ["nom", "prenom", "email", "telephone"]:
        assert k not in data

def test_dashboard_evolue_apres_soumission():
    r1 = client.get("/api/v1/parents/dashboard/anon-tester-dashboard")
    t1 = r1.json()["statistiques_pedagogiques"]["exercices_tentes"]

    client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths_5e_04-0",
        "student_pseudo_id": "anon-tester-dashboard",
        "reponse": "oui"
    })

    r2 = client.get("/api/v1/parents/dashboard/anon-tester-dashboard")
    t2 = r2.json()["statistiques_pedagogiques"]["exercices_tentes"]
    assert t2 > t1

def test_couverture_notions():
    # Already checked in script, here just ensure we have 164 math exercises
    assert len(EXERCICES) == 164

def test_integrite_remediation():
    for exo_id, exo in EXERCICES.items():
        prereq = exo.get("exercice_prerequis")
        if prereq is not None:
            assert prereq in EXERCICES
            assert prereq != exo_id

def test_absence_routes_dupliquees():
    routes = [route.path for route in app.routes]
    assert len(routes) == len(set(routes))

def test_absence_placeholders_backend():
    r = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-clean&niveau=5e")
    data = r.json()
    assert data["exercice_id"] != "exo-default"
    assert data["notion_id"] != "notion-default"

def test_absence_secret_par_defaut():
    from app.core.security_config import get_pseudo_secret
    secret = get_pseudo_secret()
    assert secret != "secret-default"
    assert secret is not None
    assert len(secret) > 0

def test_coherence_etat_partage():
    r = client.get("/api/v1/parcours/prochaine-etape?student_pseudo_id=anon-tester-coherent&niveau=5e")
    data = r.json()

    client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": data["exercice_id"],
        "student_pseudo_id": "anon-tester-coherent",
        "reponse": "oui"
    })

    r2 = client.get("/api/v1/parents/dashboard/anon-tester-coherent")
    stats = r2.json()["statistiques_pedagogiques"]
    assert stats["exercices_tentes"] >= 1
    assert data["competence"] in stats["competences"]
