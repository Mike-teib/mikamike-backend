"""
test_learning_engine_staging.py — Tests d'intégration Staging des 4 endpoints Learning Engine.
=================================================================================================
1. POST /api/v1/parcours (level=5e, subject=Maths)
2. GET  /api/v1/parcours/{user_id}/5e/Maths
3. POST /api/v1/memory/schedule
4. POST /api/v1/memory/detect-fragile
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from app.api.v1.memory.spaced_repetition import MemoryBase, TacheRappelMemoire
from app.api.v1.mikamike.store import MikaBase, engine, SessionLocal
from sqlalchemy import delete

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    MikaBase.metadata.create_all(bind=engine)
    MemoryBase.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(delete(TacheRappelMemoire))
        db.commit()
    finally:
        db.close()
    yield


def test_endpoint_1_post_parcours():
    """1. POST /api/v1/parcours (level=5e, subject=Maths) -> graph + learning path."""
    res = client.post("/api/v1/parcours", json={"user_id": "test_staging_user", "level": "5e", "subject": "Maths"})
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "test_staging_user"
    assert data["level"] == "5e"
    assert data["subject"] == "Maths"
    assert data["graph_valide_dag"] is True
    assert data["total_notions"] >= 5
    assert len(data["personalized_learning_path"]) == 3


def test_endpoint_2_get_parcours_user_level_subject():
    """2. GET /api/v1/parcours/{user_id}/5e/Maths -> learning path seul."""
    res = client.get("/api/v1/parcours/test_staging_user/5e/Maths")
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "test_staging_user"
    assert data["level"] == "5e"
    assert data["subject"] == "Maths"
    assert "personalized_learning_path" in data
    assert len(data["personalized_learning_path"]) == 3


def test_endpoint_3_post_memory_schedule():
    """3. POST /api/v1/memory/schedule (mastery_event=SUCCESS) -> scheduled_review_date = J+1."""
    res = client.post("/api/v1/memory/schedule", json={
        "user_id": "test_staging_user",
        "notion_id": "maths_5e_equations",
        "mastery_event": "SUCCESS"
    })
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "test_staging_user"
    assert data["notion_id"] == "maths_5e_equations"
    assert data["mastery_event"] == "SUCCESS"
    assert data["statut_fragilite"] is False
    assert data["intervalle_jours"] == 1
    assert "prochain_rappel_date" in data


def test_endpoint_4_post_memory_detect_fragile():
    """4. POST /api/v1/memory/detect-fragile (scores=[0.6, 0.65, 0.68]) -> is_fragile=True."""
    res = client.post("/api/v1/memory/detect-fragile", json={
        "user_id": "test_staging_user",
        "scores": [0.6, 0.65, 0.68]
    })
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "test_staging_user"
    assert data["score_moyen"] == 0.643
    assert data["is_fragile"] is True
    assert "Revoir" in data["recommandation"]
