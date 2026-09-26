"""
Vérificateurs déterministes par matière.

Contrat commun : chaque vérification renvoie un `Resultat` dont le verdict est
VALID, INVALID, AMBIGUOUS ou NEEDS_HUMAN_REVIEW. JAMAIS VALID par défaut : toute
entrée non analysable, hors périmètre ou incertaine aboutit à NEEDS_HUMAN_REVIEW
ou AMBIGUOUS.
"""

from app.curriculum.verifiers.base import Resultat, Verdict

__all__ = ["Resultat", "Verdict"]
