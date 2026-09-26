"""
router.py — Endpoint de Mémorisation Espacée (Spaced Repetition Engine) — Tâche #28.
===================================================================================
Expose POST /api/v1/memory/schedule
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.mikamike.learning_engine import pseudonymiser_code
from app.api.v1.mikamike.store import get_db
from app.api.v1.memory.spaced_repetition import (
    MoteurCourbeOubliEbbinghaus,
    MemoryBase
)

from app.core.security_config import get_pseudo_secret as _get_pseudo_secret

_PSEUDO_SECRET = _get_pseudo_secret()


def _hmac(student_pseudo_id: str) -> str:
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)


class MemoryScheduleRequest(BaseModel):
    user_id: str = Field(description="Identifiant élève (pseudo_id)")
    notion_id: str = Field(description="Identifiant de la compétence/notion")
    mastery_event: str = Field(default="SUCCESS", description="Événement : SUCCESS ou FAILURE")


class MemoryScheduleResponse(BaseModel):
    user_id: str
    notion_id: str
    mastery_event: str
    statut_fragilite: bool
    repetition_count: int
    intervalle_jours: int
    prochain_rappel_date: str
    courbe_ebbinghaus: Dict[str, Any]


class DetectFragileRequest(BaseModel):
    user_id: Optional[str] = Field(default="eleve_test", description="Identifiant élève")
    scores: List[float] = Field(description="Historique récent des scores de réussite (0.0 à 1.0)")
    seuil_fragilite: float = Field(default=0.70, description="Seuil sous lequel la notion est jugée fragile")


MemoryScheduleRequest.model_rebuild()
MemoryScheduleResponse.model_rebuild()
DetectFragileRequest.model_rebuild()

memory_router = APIRouter(prefix="/memory", tags=["memory-engine"])


@memory_router.post("/schedule", response_model=MemoryScheduleResponse)
def planifier_rappel_memoire(
    payload: MemoryScheduleRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Planifie les rappels de mémorisation espacée (J+1, J+3, J+7, J+14) et calcule la courbe d'oubli d'Ebbinghaus.
    """
    # Auto-création des tables de mémoire si nécessaire
    try:
        MemoryBase.metadata.create_all(bind=db.get_bind())
    except Exception:
        pass

    eleve_hmac = _hmac(payload.user_id)
    res = MoteurCourbeOubliEbbinghaus.traiter_evenement_apprentissage(
        db,
        eleve_hmac=eleve_hmac,
        notion_id=payload.notion_id,
        mastery_event=payload.mastery_event
    )

    return {
        "user_id": payload.user_id,
        "notion_id": payload.notion_id,
        "mastery_event": res["mastery_event"],
        "statut_fragilite": res["statut_fragilite"],
        "repetition_count": res["repetition_count"],
        "intervalle_jours": res["intervalle_jours"],
        "prochain_rappel_date": res["prochain_rappel_date"],
        "courbe_ebbinghaus": res["courbe_ebbinghaus"]
    }


@memory_router.post("/detect-fragile")
def dectecter_fragilite_scores(payload: DetectFragileRequest) -> Dict[str, Any]:
    """
    Détecte la fragilité d'une notion basée sur la moyenne ou la pente des derniers scores d'exercices.
    """
    if not payload.scores:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="liste_scores_vide")

    score_moyen = round(sum(payload.scores) / len(payload.scores), 3)
    is_fragile = score_moyen < payload.seuil_fragilite

    return {
        "user_id": payload.user_id,
        "scores": payload.scores,
        "score_moyen": score_moyen,
        "seuil": payload.seuil_fragilite,
        "is_fragile": is_fragile,
        "recommandation": "Revoir la marche d'en dessous (remédiation active)" if is_fragile else "Notion consolidée"
    }

