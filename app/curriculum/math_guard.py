"""
math_guard.py — Préservation EXACTE des expressions mathématiques dans les textes.

Deux outils :
1. `appliquer_sans_toucher_maths(texte, transformation)` : masque les expressions
   mathématiques par des jetons opaques, applique une transformation de texte
   (normalisation, nettoyage…), puis restaure les expressions À L'IDENTIQUE.
2. `verifier_preservation(source, sortie)` : compare un texte source et un texte
   transformé et signale toute altération mathématique :
     FRACTION_PERDUE, FRACTION_CONVERTIE (ex. 1/10 → 0,1), EXPOSANT_PERDU,
     PARENTHESES_MODIFIEES, SYMBOLE_MODIFIE, RACINE_PERDUE, OPERATEUR_MODIFIE,
     CARACTERE_CORROMPU.

Aucune dépendance externe ; déterministe.
"""

from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction
from typing import Callable, List, Tuple

_FRACTION = re.compile(r"(?<![\w.,])(\d+)\s*/\s*(\d+)(?![\w.,])")
_EXPOSANT_CARET = re.compile(r"\^\s*\(?\s*[-−]?\s*[\w.]+\s*\)?")
_EXPOSANT_UNICODE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿ]+")
_RACINE = re.compile(r"√\s*(\([^)]*\)|[\w.]+)")
_SYMBOLES = "≤≥≠≈∈∉⊂⊄∪∩∞π∑∏∫→↦±×÷∀∃ℕℤℚℝℂ∅°"
_OPERATEURS = "=<>≤≥≠"

# Expression « maths » à protéger : suite de jetons mathématiques contigus.
_EXPRESSION = re.compile(
    r"(?:[\w.,]*[\d)][\w.,]*|[a-zA-Z])?"          # opérande de départ éventuel
    r"(?:\s*(?:[=<>≤≥≠+\-−×÷*/^√()]|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿ])+\s*[\w.,()]*)+"
)
_JETON = "⁣MATH{}⁣"  # séparateur invisible : ne peut pas apparaître par hasard


def _est_mathematique(fragment: str) -> bool:
    return bool(re.search(r"[\d)]\s*[/^]|[\^√⁰¹²³⁴⁵⁶⁷⁸⁹⁻]|[=<>≤≥≠]|\d\s*[+\-−×÷*]\s*\w|\w\s*[+\-−×÷*]\s*\d", fragment))


def proteger(texte: str) -> Tuple[str, List[str]]:
    """Remplace chaque expression mathématique par un jeton ; renvoie (texte, expressions)."""
    expressions: List[str] = []

    def _sub(m: re.Match) -> str:
        frag = m.group(0)
        if not _est_mathematique(frag):
            return frag
        expressions.append(frag)
        return _JETON.format(len(expressions) - 1)

    return _EXPRESSION.sub(_sub, texte), expressions


def restaurer(texte: str, expressions: List[str]) -> str:
    for i, expr in enumerate(expressions):
        jeton = _JETON.format(i)
        if texte.count(jeton) != 1:
            raise ValueError(f"jeton_mathematique_{i}_altere")
        texte = texte.replace(jeton, expr)
    return texte


def appliquer_sans_toucher_maths(texte: str, transformation: Callable[[str], str]) -> str:
    """Applique `transformation` au texte en garantissant l'intégrité des expressions."""
    masque, expressions = proteger(texte)
    return restaurer(transformation(masque), expressions)


# --------------------------------------------------------------------------- #
# Vérification de préservation
# --------------------------------------------------------------------------- #
def _fractions(t: str) -> Counter:
    return Counter(f"{a}/{b}" for a, b in _FRACTION.findall(t))


def _compte(t: str, caracteres: str) -> Counter:
    return Counter(c for c in t if c in caracteres)


def _decimal_fr(fr: Fraction) -> List[str]:
    """Écritures décimales plausibles d'une fraction décimale (0,1 / 0.1)."""
    if fr.denominator == 0:
        return []
    val = fr.numerator / fr.denominator
    s = f"{val:.10f}".rstrip("0").rstrip(".")
    return [s, s.replace(".", ",")]


def verifier_preservation(source: str, sortie: str) -> List[str]:
    anomalies: List[str] = []

    f_src, f_out = _fractions(source), _fractions(sortie)
    for frac, n in f_src.items():
        if f_out[frac] < n:
            a, b = (int(x) for x in frac.split("/"))
            convertie = b != 0 and any(d in sortie for d in _decimal_fr(Fraction(a, b)))
            anomalies.append(f"FRACTION_CONVERTIE:{frac}" if convertie else f"FRACTION_PERDUE:{frac}")

    exp_src = len(_EXPOSANT_CARET.findall(source)) + sum(len(x) for x in _EXPOSANT_UNICODE.findall(source))
    exp_out = len(_EXPOSANT_CARET.findall(sortie)) + sum(len(x) for x in _EXPOSANT_UNICODE.findall(sortie))
    if exp_out < exp_src:
        anomalies.append("EXPOSANT_PERDU")

    for ouv, ferm in ("()", "[]", "{}"):
        if (source.count(ouv), source.count(ferm)) != (sortie.count(ouv), sortie.count(ferm)):
            anomalies.append("PARENTHESES_MODIFIEES")
            break

    if Counter(_RACINE.findall(source)) - Counter(_RACINE.findall(sortie)):
        anomalies.append("RACINE_PERDUE")
    if _compte(source, _SYMBOLES) != _compte(sortie, _SYMBOLES):
        anomalies.append("SYMBOLE_MODIFIE")
    if _compte(source, _OPERATEURS) != _compte(sortie, _OPERATEURS):
        anomalies.append("OPERATEUR_MODIFIE")
    if "�" in sortie and "�" not in source:
        anomalies.append("CARACTERE_CORROMPU")
    return anomalies
