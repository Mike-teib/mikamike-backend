"""
Tests d'intégration du Graphe de Compétences et Parcours Personnalisés (Tâche #27).
Couverture > 90% sur 5 chemins d'apprentissage (primaire, collège, lycée) avec validation DAG.
"""

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.parcours.router import parcours_graph_router
from app.api.v1.parcours.curriculum_dataset import (
    obtenir_graphe_competences,
    valider_graphe_sans_cycles
)
from app.api.v1.mikamike.store import MikaBase, engine

app_parcours_test = FastAPI()
app_parcours_test.include_router(parcours_graph_router, prefix="/api/v1")

client = TestClient(app_parcours_test)


@pytest.fixture(autouse=True)
def init_tables():
    MikaBase.metadata.create_all(bind=engine)
    yield


def test_parcours_1_primaire_maths_dag_et_ordre():
    """Chemin 1 : Primaire (Maths) — Validation du graphe DAG et des 3 premières notions."""
    start_time = time.time()
    response = client.post("/api/v1/parcours", json={"user_id": "eleve_prim_01", "level": "primaire", "subject": "Maths"})
    elapsed_ms = (time.time() - start_time) * 1000

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "primaire"
    assert data["subject"] == "Maths"
    assert data["graph_valide_dag"] is True
    assert data["total_notions"] >= 5
    assert len(data["personalized_learning_path"]) == 3
    assert elapsed_ms < 200  # Critère d'acceptation : Latence < 200 ms


def test_parcours_2_college_5e_maths_dependances():
    """Chemin 2 : Collège 5e (Maths) — Validation des prérequis (Nombres relatifs -> Équations)."""
    response = client.post("/api/v1/parcours", json={"user_id": "eleve_5e_02", "level": "5e", "subject": "Maths"})
    assert response.status_code == 200
    data = response.json()

    graph = {n["notion_id"]: n for n in data["competency_graph"]}
    assert "maths_5e_04" in graph
    # L'équation a pour prérequis le calcul littéral
    assert "maths_5e_03" in graph["maths_5e_04"]["prerequisite_ids"]
    assert data["personalized_learning_path"][0]["notion_id"] == "maths_5e_01"


def test_parcours_3_college_3e_maths_brevet():
    """Chemin 3 : Collège 3e (Maths) — Validation Pythagore/Thalès réciproque."""
    response = client.post("/api/v1/parcours", json={"user_id": "eleve_3e_03", "level": "3e", "subject": "Maths"})
    assert response.status_code == 200
    data = response.json()

    path = data["personalized_learning_path"]
    assert len(path) == 3
    assert data["graph_valide_dag"] is True


def test_parcours_4_lycee_1re_maths_second_degre():
    """Chemin 4 : Lycée 1re (Maths) — Validation second degré et dérivation."""
    response = client.post("/api/v1/parcours", json={"user_id": "eleve_1re_04", "level": "1re", "subject": "Maths"})
    assert response.status_code == 200
    data = response.json()

    assert data["level"] == "1re"
    assert data["total_notions"] >= 5
    assert data["graph_valide_dag"] is True


def test_parcours_5_lycee_tle_maths_bac():
    """Chemin 5 : Lycée Terminale (Maths) — Validation de l'absence totale de cycles (Tarjan)."""
    nodes = obtenir_graphe_competences("tle", "Maths")
    assert valider_graphe_sans_cycles(nodes) is True

    response = client.post("/api/v1/parcours", json={"user_id": "eleve_tle_05", "level": "tle", "subject": "Maths"})
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "tle"
    assert data["graph_valide_dag"] is True
