"""
Tests unitaires et d'intégration de la Robustesse de Session (Tâche #37).
Valide :
- Timeout d'inactivité de 5 min (300 s)
- Reconnexion gracieuse < 2.0 secondes
- Restauration de l'état partiel (mémoire de séance)
- Stream SSE fallback
- Matrice de compatibilité 4 plateformes
"""

import datetime as _dt
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from main import app
from app.api.v1.mikamike.store import engine, SessionLocal
from app.api.v1.session.session_manager import SessionBase, MikaSessionState

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    SessionBase.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(delete(MikaSessionState))
        db.commit()
    finally:
        db.close()
    yield


def test_heartbeat_active_session_succes():
    """Heartbeat sur une session active -> Réponse 200 OK."""
    payload = {"session_id": "sess_test_01", "user_id": "eleve_test_01"}
    res = client.post("/api/v1/session/heartbeat", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["statut"] in ("heartbeat_ok", "session_creee")
    assert data["session_id"] == "sess_test_01"
    assert data["is_active"] is True


def test_timeout_5min_inactivite_expiration():
    """Timeout d'inactivité de 5 minutes (300 s) -> Refus 401 (session_inactivite_5min)."""
    db = SessionLocal()
    session_id = "sess_timeout_test"
    try:
        # Création d'une session inactive depuis 6 minutes (360 secondes)
        past_ts = _dt.datetime.utcnow() - _dt.timedelta(seconds=360)
        session_obj = MikaSessionState(
            session_id=session_id,
            eleve_hmac="hmac_timeout",
            is_active=True,
            last_activity_ts=past_ts
        )
        db.add(session_obj)
        db.commit()
    finally:
        db.close()

    # Tentative d'accès après 5 min d'inactivité
    res = client.post("/api/v1/session/heartbeat", json={"session_id": session_id, "user_id": "eleve_timeout"})
    assert res.status_code == 401
    assert res.json()["detail"] == "session_inactivite_5min"


def test_sauvegarde_et_restauration_etat_partiel():
    """Sauvegarde du brouillon d'ardoise et de l'exercice courant, puis restauration à la reconnexion."""
    session_id = "sess_state_test"
    user_id = "eleve_state_test"
    state_payload = {
        "exercice_courant_id": "exo-maths-algebre-5",
        "ardoise_draft": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "step_escalier": 5,
        "notion_active": "equations_1er_degre"
    }

    # 1. Sauvegarde d'état
    res_save = client.post("/api/v1/session/save-state", json={
        "session_id": session_id,
        "user_id": user_id,
        "state_data": state_payload
    })
    assert res_save.status_code == 200
    assert res_save.json()["statut"] == "etat_sauvegarde"

    # 2. Reconnexion & Restauration
    res_rec = client.post("/api/v1/session/reconnect", json={
        "session_id": session_id,
        "user_id": user_id
    })
    assert res_rec.status_code == 200
    data = res_rec.json()

    assert data["statut"] == "reconnexion_reussie"
    assert data["session_state"]["exercice_courant_id"] == "exo-maths-algebre-5"
    assert data["session_state"]["step_escalier"] == 5
    assert data["session_state"]["notion_active"] == "equations_1er_degre"


def test_reconnexion_timing_inferieur_2_secondes():
    """Benchmark de reconnexion : Garantie d'une réponse en < 2.0 secondes (SLA < 2000 ms)."""
    session_id = "sess_perf_test"
    user_id = "eleve_perf"

    start_time = time.time()
    res = client.post("/api/v1/session/reconnect", json={"session_id": session_id, "user_id": user_id})
    elapsed_ms = (time.time() - start_time) * 1000

    assert res.status_code == 200
    data = res.json()
    assert data["reconnexion_inf_2s"] is True
    assert elapsed_ms < 2000.0  # Timing effectif constaté < 2000 ms


def test_sse_stream_fallback_endpoint():
    """Test du flux Server-Sent Events (SSE) fallback en text/event-stream."""
    res = client.get("/api/v1/session/stream?session_id=sess_sse_test")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    assert "data:" in res.text


def test_matrice_4_plateformes_session():
    """Validation de la gestion de session sur la matrice des 4 plateformes."""
    plateformes = [
        {"name": "Desktop Chrome", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"},
        {"name": "Mobile iOS PWA", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148"},
        {"name": "Tablette iPadOS", "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15"},
        {"name": "Chromebook Touch", "user_agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) Chrome/122.0"}
    ]

    for plat in plateformes:
        res = client.post(
            "/api/v1/session/heartbeat",
            json={"session_id": f"sess_{plat['name'].replace(' ', '_')}", "user_id": "eleve_multi"},
            headers={"User-Agent": plat["user_agent"]}
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is True
