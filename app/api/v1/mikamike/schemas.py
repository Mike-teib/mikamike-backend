"""schemas.py — Contrats d'E/S des endpoints MikaMike (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.validation import Identifiant, ReponseEleve


class SoumissionIn(BaseModel):
    """Contrat aligné sur test_mika_suite (champ `reponse`)."""

    exercice_id: Identifiant
    student_pseudo_id: Identifiant = Field(description="Identifiant déjà pseudonymisé (RGPD)")
    reponse: ReponseEleve
    avec_aide: bool = False


class Remediation(BaseModel):
    explication_concept: str
    exercice_prerequis: str
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
    exercice_id: str
    niveau: str
    competence: str
    consigne: str
