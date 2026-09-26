"""
pseudonymisation.py — Point UNIQUE de calcul de la clé interne d'un élève.

Auparavant, six modules relisaient chacun MIKA_PSEUDO_SECRET et redéfinissaient
leur propre `_hmac` (dette relevée en revue session 2, R2-15). Le secret reste lu
au chargement (fail-closed : l'application refuse de démarrer sans secret valide).
"""

from __future__ import annotations

from app.api.v1.mikamike.learning_engine import pseudonymiser_code
from app.core.security_config import get_pseudo_secret

_PSEUDO_SECRET = get_pseudo_secret()


def hmac_eleve(student_pseudo_id: str) -> str:
    """HMAC-SHA256 tronqué (16 hex) de l'identifiant pseudonyme reçu du client."""
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)
