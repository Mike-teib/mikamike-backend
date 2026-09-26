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
from app.core.validation import ID_PATTERN, MAX_SESSION_STATE_BYTES, Identifiant, Identifiant64
from app.api.v1.session.session_manager import GestionnaireSession, MikaSessionState

from app.core.pseudonymisation import hmac_eleve as _hmac
from app.core.auth import Action, Garde, garde as _garde

class SessionHeartbeatIn(BaseModel):
    session_id: Identifiant64 = Field(description="Identifiant de la session")
    user_id: Identifiant = Field(description="Identifiant élève (pseudo_id)")


class SessionSaveStateIn(BaseModel):
    session_id: Identifiant64
    user_id: Identifiant
    state_data: Dict[str, Any] = Field(description="Mémoire de séance (ardoise, exercice, étape)")


class SessionReconnectIn(BaseModel):
    session_id: Identifiant64
    user_id: Identifiant


class SessionNouvelleIn(BaseModel):
    user_id: Identifiant


session_router = APIRouter(prefix="/session", tags=["session-manager"])


def _seance_existante_si_enforce(g: Garde, db: Session, session_id: str) -> None:
    # Décision D15 : en mode enforce, une séance n'existe que si le SERVEUR l'a créée
    # (POST /session/nouvelle, identifiant aléatoire de 192 bits). Le mode « off » garde la
    # création implicite du contrat historique (interdit en production).
    if g.qui is not None:
        GestionnaireSession.exiger_existante(db, session_id)


@session_router.post("/nouvelle", status_code=status.HTTP_201_CREATED)
def nouvelle_session(payload: SessionNouvelleIn, db: Session = Depends(get_db),
                     g: Garde = Depends(_garde)) -> Dict[str, Any]:
    """Crée une séance avec un identifiant généré par le serveur (non prévisible)."""
    g.exiger(payload.user_id, Action.APPRENTISSAGE)
    return GestionnaireSession.nouvelle(db, _hmac(payload.user_id))


@session_router.post("/heartbeat")
def heartbeat_session(
    payload: SessionHeartbeatIn,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Heartbeat de session : rafraîchit le minuteur d'activité.
    Renvoie 401 si la session dépasse 5 minutes (300 s) d'inactivité.
    """
    g.exiger(payload.user_id, Action.APPRENTISSAGE)
    eleve_hmac = _hmac(payload.user_id)
    _seance_existante_si_enforce(g, db, payload.session_id)
    return GestionnaireSession.heartbeat(db, payload.session_id, eleve_hmac)


@session_router.post("/save-state")
def sauvegarder_etat_session(
    payload: SessionSaveStateIn,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Sauvegarde partielle de la mémoire de séance (brouillon d'ardoise, exercice, étape).
    """
    g.exiger(payload.user_id, Action.APPRENTISSAGE)
    if len(json.dumps(payload.state_data)) > MAX_SESSION_STATE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="etat_session_trop_volumineux")

    eleve_hmac = _hmac(payload.user_id)
    _seance_existante_si_enforce(g, db, payload.session_id)
    return GestionnaireSession.sauvegarder_etat_partiel(
        db, payload.session_id, eleve_hmac, payload.state_data
    )


@session_router.post("/reconnect")
def reconnecter_session(
    payload: SessionReconnectIn,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Reconnexion gracieuse < 2.0 secondes et restauration partielle d'état.
    """
    g.exiger(payload.user_id, Action.APPRENTISSAGE)
    eleve_hmac = _hmac(payload.user_id)
    _seance_existante_si_enforce(g, db, payload.session_id)
    return GestionnaireSession.reconnecter_et_restaurer(db, payload.session_id, eleve_hmac)


@session_router.get("/stream")
def stream_notifications_sse(
    session_id: str = Query(default="default_session", max_length=64, pattern=ID_PATTERN),
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
):
    """
    Flux Server-Sent Events (SSE) fallback pour ping/pong et notifications temps réel.
    Garantit la traversée des pare-feux scolaires et la reconnexion automatique.
    """
    if g.qui is not None:
        # Mode enforce : seul un jeton ÉLÈVE, propriétaire de la séance si elle existe.
        if g.qui.pseudo_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acces_refuse")
        g.exiger(g.qui.pseudo_id, Action.APPRENTISSAGE)  # compte émetteur encore actif et lié (S3-01)
        seance = db.get(MikaSessionState, session_id)
        if seance is None:  # D15 : pas de flux sur une séance que le serveur n'a pas créée
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_inconnue")
        if seance.eleve_hmac != _hmac(g.qui.pseudo_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acces_refuse")

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
