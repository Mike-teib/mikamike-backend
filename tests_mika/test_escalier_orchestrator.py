"""
Tests unitaires et d'intégration de l'Orchestrateur Escalier Mika 8 Étapes.
Conforme au Cahier des Charges §4.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.escalier.orchestrator import OrchestrateurEscalier
from app.api.v1.escalier.router import escalier_router
from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import MikaBase, engine, get_db

# Application de test dédiée à l'escalier
app_escalier_test = FastAPI()
app_escalier_test.include_router(escalier_router, prefix="/api/v1")

client = TestClient(app_escalier_test)


@pytest.fixture(autouse=True)
def init_tables():
    MikaBase.metadata.create_all(bind=engine)
    yield


def test_etape1_objectif_demarrage():
    """Étape 1 (Objectif) : Chargement initial sans réponse élève."""
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        orch = OrchestrateurEscalier(db, "eleve_test_etape1")
        res = orch.executer_pipeline_8_etapes(
            competence_objectif="equations_1er_degre",
            exercice_id="exo-maths-algebre-1"
        )
        assert res["etape_courante"] == 1
        assert res["nom_etape"] == "OBJECTIF"
        assert res["competence_objectif"] == "equations_1er_degre"
        assert res["est_correct"] is None
        assert res["details_pipeline_8_etapes"]["1_objectif"] == "equations_1er_degre"
    finally:
        db.close()


def test_etapes_2_a_5_erreur_et_remontee_prerequis():
    """
    Étapes 2 à 5 :
    2. Analyse erreur (Faux) -> 3. Remontée aux prérequis -> 4. Explication -> 5. Micro-remédiation
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        orch = OrchestrateurEscalier(db, "eleve_test_erreur")
        res = orch.executer_pipeline_8_etapes(
            competence_objectif="equations_1er_degre",
            exercice_id="exo-maths-algebre-1",
            reponse_eleve="x = 999"  # Faux
        )

        assert res["est_correct"] is False
        assert res["etape_courante"] == 5
        assert res["nom_etape"] == "MICRO_REMEDIATION"
        assert res["remediation"] is not None
        assert "explication_concept" in res["remediation"]
        assert res["details_pipeline_8_etapes"]["2_analyse_erreur"] == "reponse_incorrecte"
    finally:
        db.close()


def test_etape6_verification_moteur_et_le06_aide():
    """Étape 6 (Vérification Moteur) : Succès avec aide -> Plafonnement LE-06 strict."""
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        orch = OrchestrateurEscalier(db, "eleve_test_aide")
        res = orch.executer_pipeline_8_etapes(
            competence_objectif="equations_1er_degre",
            exercice_id="exo-maths-algebre-1",
            reponse_eleve="3",  # Correct
            avec_aide=True
        )

        assert res["est_correct"] is True
        # Règle LE-06 : Succès avec aide = ACQUIS_ASSISTE
        assert res["etat_maitrise"] == "ACQUIS_ASSISTE"
        assert res["details_pipeline_8_etapes"]["6_verification_moteur"] == "OK_ENGINE_ONLY"
    finally:
        db.close()


def test_etape7_et_8_reussite_retour_objectif_et_memoire():
    """
    Étapes 7 et 8 :
    7. Retour à l'objectif -> 8. Mémoire (Persistance DB effective)
    """
    pseudo_id = "eleve_test_reussite"
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        orch = OrchestrateurEscalier(db, pseudo_id)
        res = orch.executer_pipeline_8_etapes(
            competence_objectif="equations_1er_degre",
            exercice_id="exo-maths-algebre-1",
            reponse_eleve="3",  # Correct sans aide
            avec_aide=False
        )

        assert res["est_correct"] is True
        assert res["etape_courante"] == 7
        assert res["nom_etape"] == "RETOUR_OBJECTIF"

        # Étape 8 : Vérification de la persistance en DB
        eleve_hmac = orch.eleve_hmac
        tentatives = crud.get_tentatives(db, eleve_hmac)
        assert len(tentatives) >= 1
        assert tentatives[0].est_correct is True

        etats = crud.get_etats(db, eleve_hmac)
        assert "equations_1er_degre" in etats
    finally:
        db.close()


def test_endpoint_api_escalier_etape():
    """Test HTTP POST /api/v1/escalier/etape via FastAPI TestClient."""
    payload = {
        "student_pseudo_id": "eleve_api_test",
        "competence_objectif": "equations_1er_degre",
        "exercice_id": "exo-maths-algebre-1",
        "reponse_eleve": "3",
        "avec_aide": False
    }

    res = client.post("/api/v1/escalier/etape", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "etape_courante" in data
    assert "nom_etape" in data
    assert "details_pipeline_8_etapes" in data
    assert data["details_pipeline_8_etapes"]["6_verification_moteur"] == "OK_ENGINE_ONLY"
