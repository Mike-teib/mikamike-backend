"""
Tests d'intégration du Moteur de Mémorisation Espacée (Tâche #28).
10 scénarios validant la fragilité, la courbe d'oubli d'Ebbinghaus et la planification J+1, J+3, J+7, J+14.
"""

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.memory.router import memory_router
from app.api.v1.memory.spaced_repetition import MoteurCourbeOubliEbbinghaus, MemoryBase, TacheRappelMemoire
from app.api.v1.mikamike.store import engine, SessionLocal
from sqlalchemy import delete

app_memory_test = FastAPI()
app_memory_test.include_router(memory_router, prefix="/api/v1")

client = TestClient(app_memory_test)

@pytest.fixture(autouse=True)
def init_tables():
    MemoryBase.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(delete(TacheRappelMemoire))
        db.commit()
    finally:
        db.close()
    yield


def test_scenario_1_echec_initial_fragilite():
    """Scénario 1 : Échec initial -> Marquage immédiat en 'fragile' et rappel J+1."""
    payload = {"user_id": "eleve_mem_01", "notion_id": "maths_5e_equations", "mastery_event": "FAILURE"}
    res = client.post("/api/v1/memory/schedule", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["statut_fragilite"] is True
    assert data["intervalle_jours"] == 1
    assert data["repetition_count"] == 0
    assert data["courbe_ebbinghaus"]["statut_memoire"] == "FRAGILE"


def test_scenario_2_premiere_reussite_j1():
    """Scénario 2 : Première réussite -> Statut non fragile, rappel à J+1."""
    payload = {"user_id": "eleve_mem_02", "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"}
    res = client.post("/api/v1/memory/schedule", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["statut_fragilite"] is False
    assert data["intervalle_jours"] == 1
    assert data["repetition_count"] == 1


def test_scenario_3_deuxieme_reussite_j3():
    """Scénario 3 : Deuxième réussite consécutive -> Progression vers l'intervalle J+3."""
    user = "eleve_mem_03"
    client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    res = client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    data = res.json()

    assert data["repetition_count"] == 2
    assert data["intervalle_jours"] == 3


def test_scenario_4_troisieme_reussite_j7():
    """Scénario 4 : Troisième réussite consécutive -> Progression vers l'intervalle J+7."""
    user = "eleve_mem_04"
    for _ in range(3):
        res = client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    data = res.json()

    assert data["repetition_count"] == 3
    assert data["intervalle_jours"] == 7
    assert data["courbe_ebbinghaus"]["statut_memoire"] in ("SOLIDE", "EN_CONSOLIDATION")


def test_scenario_5_quatrieme_reussite_j14():
    """Scénario 5 : Quatrième réussite consécutive -> Palier maximal à J+14."""
    user = "eleve_mem_05"
    for _ in range(4):
        res = client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    data = res.json()

    assert data["repetition_count"] == 4
    assert data["intervalle_jours"] == 14
    assert data["courbe_ebbinghaus"]["statut_memoire"] == "SOLIDE"


def test_scenario_6_echec_apres_maitrise_reinitialise():
    """Scénario 6 : Échec survie après maîtrise -> Retombée en 'fragile' et rappel à J+1."""
    user = "eleve_mem_06"
    # Réussite préalable
    client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    # Échec ultérieur
    res = client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "FAILURE"})
    data = res.json()

    assert data["statut_fragilite"] is True
    assert data["intervalle_jours"] == 1
    assert data["repetition_count"] == 0


def test_scenario_7_rattrapage_progressif():
    """Scénario 7 : Rattrapage progressif après échec (FAILURE puis SUCCESS)."""
    user = "eleve_mem_07"
    client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "FAILURE"})
    res = client.post("/api/v1/memory/schedule", json={"user_id": user, "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    data = res.json()

    assert data["statut_fragilite"] is False
    assert data["repetition_count"] == 1
    assert data["intervalle_jours"] == 1


def test_scenario_8_calcul_courbe_ebbinghaus_retention():
    """Scénario 8 : Validation mathématique de la formule d'Ebbinghaus R = e^(-t/S)."""
    ret_0 = MoteurCourbeOubliEbbinghaus.estimer_retention_ebbinghaus(jours_ecoules=0.0, force_memoire=2.0)
    ret_2 = MoteurCourbeOubliEbbinghaus.estimer_retention_ebbinghaus(jours_ecoules=2.0, force_memoire=2.0)

    assert ret_0 == 1.0
    assert ret_2 < 0.50  # La rétention diminue avec le temps


def test_scenario_9_latence_inferieure_200ms():
    """Scénario 9 : Vérification de la latence de réponse (< 200 ms)."""
    start_time = time.time()
    res = client.post("/api/v1/memory/schedule", json={"user_id": "eleve_perf", "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    elapsed_ms = (time.time() - start_time) * 1000

    assert res.status_code == 200
    assert elapsed_ms < 200  # Critère d'acceptation : Latence < 200 ms


def test_scenario_10_endpoint_api_memory_schedule():
    """Scénario 10 : Validation du schéma de réponse complet de l'API /api/v1/memory/schedule."""
    res = client.post("/api/v1/memory/schedule", json={"user_id": "eleve_schema", "notion_id": "maths_5e_equations", "mastery_event": "SUCCESS"})
    assert res.status_code == 200
    data = res.json()

    assert "user_id" in data
    assert "notion_id" in data
    assert "statut_fragilite" in data
    assert "prochain_rappel_date" in data
    assert "courbe_ebbinghaus" in data
    assert "force_memoire_S" in data["courbe_ebbinghaus"]
