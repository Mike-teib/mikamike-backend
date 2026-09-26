"""
dispatch.py — Point d'entrée unique : type de vérification → vérificateur.

Types :
  maths_symbolique     params : forme_requise
  physique_grandeur    params : unite_requise, tolerance_relative,
                                chiffres_significatifs_requis, notation_scientifique, unite_imposee
  physique_incertitude          « (x ± u) unité » : u à 1-2 CS, x à la décimale de u
  physique_ordre_de_grandeur    attendue = puissance de dix ; params : valeur (grandeur de référence)
  svt_vocabulaire      params : termes_requis, termes_errones, termes_hors_niveau
                       (terme requis seulement en proposition négative ⇒ revue)
  svt_definition       params : terme_defini, elements_essentiels, confusions
  texte_exact          comparaison normalisée stricte (aucune tolérance floue)
Type inconnu ⇒ NEEDS_HUMAN_REVIEW (jamais VALID par défaut).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Mapping

from app.curriculum.verifiers import maths, physique, physique_etendu, svt, svt_raisonnement
from app.curriculum.verifiers.base import Resultat, Verdict, invalide, revue, valide

TYPES_VERIFICATION = ("maths_symbolique", "physique_grandeur", "physique_incertitude", "physique_ordre_de_grandeur",
                      "svt_vocabulaire", "svt_definition", "texte_exact")


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
        if type_verification == "physique_incertitude":
            return physique_etendu.verifier_incertitude(attendue, reponse, **p)
        if type_verification == "physique_ordre_de_grandeur":
            valeur = p.pop("valeur", None)
            if not isinstance(valeur, str) or p:
                return revue("parametres_de_verification_invalides")
            # L'attendue (puissance de dix) doit elle-même être l'ordre de grandeur de `valeur`.
            if physique_etendu.verifier_ordre_de_grandeur(valeur, attendue).verdict != Verdict.VALID:
                return revue("attendue_incoherente_avec_valeur")
            return physique_etendu.verifier_ordre_de_grandeur(valeur, reponse)
        if type_verification == "svt_vocabulaire":
            return svt.verifier_vocabulaire(
                reponse, p.get("termes_requis", ()),
                termes_errones=p.get("termes_errones", ()),
                termes_hors_niveau=p.get("termes_hors_niveau", ()),
            )
        if type_verification == "svt_definition":
            return svt_raisonnement.verifier_definition(
                p.pop("terme_defini"), reponse, p.pop("elements_essentiels"), **p)
        if type_verification == "texte_exact":
            if not (reponse or "").strip():
                return invalide("reponse_vide")
            if not (attendue or "").strip():
                return revue("attendue_vide")
            return valide("texte_identique") if _norm_exact(attendue) == _norm_exact(reponse) \
                else invalide("texte_different")
    except (TypeError, KeyError):
        return revue("parametres_de_verification_invalides")
    return revue(f"type_verification_inconnu:{type_verification}")
