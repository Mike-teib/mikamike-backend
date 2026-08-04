"""schemas.py — Contrats d'E/S des endpoints MikaMike (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SoumissionIn(BaseModel):
    """Contrat aligné sur test_mika_suite (champ `reponse`)."""

    exercice_id: str
    student_pseudo_id: str = Field(description="Identifiant déjà pseudonymisé (RGPD)")
    reponse: str
    avec_aide: bool = False


class Remediation(BaseModel):
    explication_concept: str
    exercice_prerequis: Optional[str] = None
    competence_lacune: Optional[str] = None


class SoumissionOut(BaseModel):
    est_correct: bool
    etat_maitrise: str
    message: Optional[str] = None
    remediation: Optional[Remediation] = None


class DashboardOut(BaseModel):
    pseudo_id: str
    statistiques_pedagogiques: Dict[str, Any]


class ProchaineEtapeOut(BaseModel):
    student_pseudo_id: str
    niveau: str
    notion_id: str
    exercice_id: str
    consigne: str
    competence: Optional[str] = None
