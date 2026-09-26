"""
dispatch.py — Point d'entrée unique : type de vérification → vérificateur.

Types :
  maths_symbolique     params : forme_requise
  physique_grandeur    params : unite_requise, tolerance_relative,
                                chiffres_significatifs_requis, notation_scientifique
  svt_vocabulaire      params : termes_requis, termes_errones, termes_hors_niveau
  texte_exact          comparaison normalisée stricte (aucune tolérance floue)
Type inconnu ⇒ NEEDS_HUMAN_REVIEW (jamais VALID par défaut).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Mapping

from app.curriculum.verifiers import maths, physique, svt
from app.curriculum.verifiers.base import Resultat, invalide, revue, valide

TYPES_VERIFICATION = ("maths_symbolique", "physique_grandeur", "svt_vocabulaire", "texte_exact")


def _norm_exact(t: str) -> str:
    return " ".join(unicodedata.normalize("NFC", t or "").casefold().split())


def verifier(type_verification: str, attendue: str, reponse: str,
             params: Mapping[str, Any] | None = None) -> Resultat:
    p = dict(params or {})
    try:
        if type_verification == "maths_symbolique":
            return maths.verifier_reponse(attendue, reponse, p.get("forme_requise"))
        if type_verification == "physique_grandeur":
            return physique.verifier_grandeur(attendue, reponse, **p)
        if type_verification == "svt_vocabulaire":
            return svt.verifier_vocabulaire(
                reponse, p.get("termes_requis", ()),
                termes_errones=p.get("termes_errones", ()),
                termes_hors_niveau=p.get("termes_hors_niveau", ()),
            )
        if type_verification == "texte_exact":
            if not (reponse or "").strip():
                return invalide("reponse_vide")
            if not (attendue or "").strip():
                return revue("attendue_vide")
            return valide("texte_identique") if _norm_exact(attendue) == _norm_exact(reponse) \
                else invalide("texte_different")
    except TypeError:
        return revue("parametres_de_verification_invalides")
    return revue(f"type_verification_inconnu:{type_verification}")
