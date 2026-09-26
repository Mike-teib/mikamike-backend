"""
router.py — Endpoint du Graphe de Compétences et Parcours Personnalisé (Tâche #27).
====================================================================================
Expose POST /api/v1/parcours
"""

from __future__ import annotations

from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.learning_engine import pseudonymiser_code
from app.api.v1.mikamike.store import get_db
from app.api.v1.parcours.curriculum_dataset import (
    ReferentielInconnu,
    obtenir_graphe_competences,
    generer_parcours_personnalise,
    valider_graphe_sans_cycles,
    normaliser_niveau,
    normaliser_matiere,
)

from app.core.security_config import get_pseudo_secret as _get_pseudo_secret
from app.core.validation import ID_PATTERN, Identifiant

_PSEUDO_SECRET = _get_pseudo_secret()


def _hmac(student_pseudo_id: str) -> str:
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)


def _resoudre_referentiel(level: str, subject: str):
    """Normalise niveau/matière et charge le graphe ; 422 si inconnu, 404 si absent."""
    try:
        level_norm = normaliser_niveau(level)
        subject_norm = normaliser_matiere(subject)
    except ReferentielInconnu as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    nodes = obtenir_graphe_competences(level_norm, subject_norm)
    if not nodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="programme_indisponible")
    return level_norm, subject_norm, nodes


class ParcoursRequest(BaseModel):
    user_id: Identifiant = Field(description="Identifiant élève (pseudo_id)")
    level: str = Field(default="5e", max_length=32, description="Niveau d'études (primaire, 6e, 5e, 4e, 3e, 2de, 1re, tle)")
    subject: str = Field(default="Maths", max_length=32, description="Matière (Maths, Physique, Chimie, SVT)")


class ParcoursResponse(BaseModel):
    user_id: str
    level: str
    subject: str
    total_notions: int
    graph_valide_dag: bool
    competency_graph: List[Dict[str, Any]]
    personalized_learning_path: List[Dict[str, Any]]


parcours_graph_router = APIRouter(prefix="/parcours", tags=["parcours-graph"])


@parcours_graph_router.post("", response_model=ParcoursResponse)
@parcours_graph_router.post("/", response_model=ParcoursResponse, include_in_schema=False)
def charger_parcours_competences(
    payload: ParcoursRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Génère le graphe de compétences complet et le parcours personnalisé (3 premières notions).
    """
    eleve_hmac = _hmac(payload.user_id)
    etats_db = crud.get_etats(db, eleve_hmac)

    level_norm, subject_norm, nodes = _resoudre_referentiel(payload.level, payload.subject)
    is_dag = valider_graphe_sans_cycles(nodes)

    competency_graph = []
    for node in nodes:
        etat_str = etats_db.get(node.notion_id, "INCONNU")
        mastery_status = 1 if etat_str in ("ACQUIS_AUTONOME", "MAITRISE") else 0
        competency_graph.append(node.to_dict(mastery_status=mastery_status))

    personalized_path = generer_parcours_personnalise(nodes, etats_db)

    return {
        "user_id": payload.user_id,
        "level": level_norm,
        "subject": subject_norm.capitalize() if subject_norm != "svt" else "SVT",
        "total_notions": len(competency_graph),
        "graph_valide_dag": is_dag,
        "competency_graph": competency_graph,
        "personalized_learning_path": personalized_path
    }


@parcours_graph_router.get("/{user_id}/{level}/{subject}")
def obtenir_parcours_seul(
    user_id: str = Path(max_length=128, pattern=ID_PATTERN),
    level: str = Path(max_length=32),
    subject: str = Path(max_length=32),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retourne uniquement le parcours personnalisé (learning path) pour un élève, niveau et matière.
    """
    eleve_hmac = _hmac(user_id)
    etats_db = crud.get_etats(db, eleve_hmac)

    level_norm, subject_norm, nodes = _resoudre_referentiel(level, subject)
    personalized_path = generer_parcours_personnalise(nodes, etats_db)

    return {
        "user_id": user_id,
        "level": level_norm,
        "subject": subject_norm.capitalize() if subject_norm != "svt" else "SVT",
        "personalized_learning_path": personalized_path
    }

