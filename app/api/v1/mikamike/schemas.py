"""schemas.py — Contrats d'E/S des endpoints MikaMike (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.validation import Identifiant, ReponseEleve


class SoumissionIn(BaseModel):
    """Contrat aligné sur test_mika_suite (champ `reponse`)."""
    model_config = ConfigDict(extra="forbid")  # lot 21 : pas d'affectation de masse

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


class _Ferme(BaseModel):
    # Lot 19 (S4) : minimisation — schéma FERMÉ. Un champ ajouté côté agrégation (réponse
    # d'élève, horodatage, échange avec le tuteur…) fait échouer la réponse (fail-closed)
    # au lieu d'être transmis au parent.
    model_config = ConfigDict(extra="forbid")


class StatCompetence(_Ferme):
    tentatives: int
    reussites: int
    etat: str


class StatistiquesParent(_Ferme):
    exercices_tentes: int
    exercices_reussis: int
    taux_reussite: float
    competences: Dict[str, StatCompetence]
    niveau_actuel: str


class DashboardOut(_Ferme):
    pseudo_id: str
    statistiques_pedagogiques: StatistiquesParent


class ProchaineEtapeOut(BaseModel):
    exercice_id: str
    niveau: str
    competence: str
    consigne: str
