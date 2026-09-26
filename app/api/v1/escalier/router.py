"""
router.py — Endpoint de l'Orchestrateur Escalier Mika en 8 Étapes.
==================================================================
Expose POST /api/v1/escalier/etape pour dérouler la boucle pédagogique déterministe.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.escalier.orchestrator import OrchestrateurEscalier
from app.api.v1.mikamike.store import get_db
from app.core.auth import Action, Garde, garde as _garde
from app.core.validation import Identifiant, ReponseEleve


class EscalierEtapeIn(BaseModel):
    """Payload d'entrée pour l'exécution d'une étape d'escalier."""
    student_pseudo_id: Identifiant = Field(description="Identifiant élève pseudonymisé (RGPD)")
    competence_objectif: Identifiant = Field(description="Compétence visée (ex: equations_1er_degre)")
    exercice_id: Identifiant = Field(description="Identifiant de l'exercice soumis")
    reponse_eleve: Optional[ReponseEleve] = Field(default=None, description="Réponse saisie par l'élève (None pour le démarrage)")
    avec_aide: bool = Field(default=False, description="Vrai si l'élève a utilisé un indice/aide")


escalier_router = APIRouter(prefix="/escalier", tags=["escalier-mika"])


@escalier_router.post("/etape")
def executer_etape_escalier(
    payload: EscalierEtapeIn,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Déroule l'orchestrateur de l'Escalier Mika en 8 étapes :
    Objectif -> Analyse Erreur -> Prérequis -> Explication -> Micro-remédiation -> Vérification Moteur -> Retour Objectif -> Mémoire
    """
    g.exiger(payload.student_pseudo_id, Action.APPRENTISSAGE)
    orchestrateur = OrchestrateurEscalier(db, payload.student_pseudo_id)
    return orchestrateur.executer_pipeline_8_etapes(
        competence_objectif=payload.competence_objectif,
        exercice_id=payload.exercice_id,
        reponse_eleve=payload.reponse_eleve,
        avec_aide=payload.avec_aide
    )
