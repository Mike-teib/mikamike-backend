"""
Module Escalier Mika — Orchestrateur Pédagogique 8 Étapes.
Conforme au Cahier des Charges §4.
"""

from app.api.v1.escalier.router import escalier_router
from app.api.v1.escalier.orchestrator import OrchestrateurEscalier

__all__ = ["escalier_router", "OrchestrateurEscalier"]
