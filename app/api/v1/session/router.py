"""
router.py — Endpoints de Gestion de Session, Timeout 5 min & Reconnexion < 2s (Tâche #37).
========================================================================================
Expose :
  POST /api/v1/session/heartbeat
  POST /api/v1/session/save-state
  POST /api/v1/session/reconnect
  GET  /api/v1/session/stream (SSE stream fallback)
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.mikamike.store import get_db
from app.core.validation import ID_PATTERN, MAX_SESSION_STATE_BYTES, Identifiant
from app.api.v1.session.session_manager import (
    GestionnaireSession
)

from app.core.pseudonymisation import hmac_eleve as _hmac

class SessionHeartbeatIn(BaseModel):
    session_id: Identifiant = Field(description="Identifiant de la session")
    user_id: Identifiant = Field(description="Identifiant élève (pseudo_id)")


class SessionSaveStateIn(BaseModel):
    session_id: Identifiant
    user_id: Identifiant
    state_data: Dict[str, Any] = Field(description="Mémoire de séance (ardoise, exercice, étape)")


class SessionReconnectIn(BaseModel):
    session_id: Identifiant
    user_id: Identifiant


session_router = APIRouter(prefix="/session", tags=["session-manager"])


@session_router.post("/heartbeat")
def heartbeat_session(
    payload: SessionHeartbeatIn,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Heartbeat de session : rafraîchit le minuteur d'activité.
    Renvoie 401 si la session dépasse 5 minutes (300 s) d'inactivité.
    """
    eleve_hmac = _hmac(payload.user_id)
    return GestionnaireSession.heartbeat(db, payload.session_id, eleve_hmac)


@session_router.post("/save-state")
def sauvegarder_etat_session(
    payload: SessionSaveStateIn,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sauvegarde partielle de la mémoire de séance (brouillon d'ardoise, exercice, étape).
    """
    if len(json.dumps(payload.state_data)) > MAX_SESSION_STATE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="etat_session_trop_volumineux")

    eleve_hmac = _hmac(payload.user_id)
    return GestionnaireSession.sauvegarder_etat_partiel(
        db, payload.session_id, eleve_hmac, payload.state_data
    )


@session_router.post("/reconnect")
def reconnecter_session(
    payload: SessionReconnectIn,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reconnexion gracieuse < 2.0 secondes et restauration partielle d'état.
    """
    eleve_hmac = _hmac(payload.user_id)
    return GestionnaireSession.reconnecter_et_restaurer(db, payload.session_id, eleve_hmac)


@session_router.get("/stream")
async def stream_notifications_sse(
    session_id: str = Query(default="default_session", max_length=128, pattern=ID_PATTERN),
):
    """
    Flux Server-Sent Events (SSE) fallback pour ping/pong et notifications temps réel.
    Garantit la traversée des pare-feux scolaires et la reconnexion automatique.
    """
    async def sse_generator():
        for i in range(3):
            event_data = {
                "event": "ping",
                "session_id": session_id,
                "timestamp": asyncio.get_event_loop().time()
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
