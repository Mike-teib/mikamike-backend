"""
level_lexicon.py — Heuristiques DÉTERMINISTES d'adéquation au niveau.

AVERTISSEMENT : ce module est une HEURISTIQUE. Il repère des termes dont le niveau de
première apparition dans les programmes français est connu avec une confiance élevée,
et quelques signaux de contenu trop simple. Il ne remplace pas une revue humaine :
toutes les anomalies qu'il produit sont des WARNING (jamais BLOCKER ni ERROR), à
confirmer par une personne. Les seuils sont volontairement PRUDENTS (niveau minimal le
plus bas plausible) pour limiter les faux positifs ; ils ne sont pas vérifiés contre les
textes officiels (aucune source officielle récupérée à ce stade).

API :
  check_text_level(text, subject, level) -> List[(terme, niveau_min)]   (TOO_ADVANCED)
  is_too_simple(text, level, difficulty) -> bool                        (TOO_SIMPLE)
"""

from __future__ import annotations

import re
import unicodedata
from typing import FrozenSet, List, NamedTuple, Optional, Tuple

from pedagogy.models import LEVEL_RANK, DifficultyBand, Level, Subject

M, PC, SVT, ST, ES = (Subject.MATHS, Subject.PHYSIQUE_CHIMIE, Subject.SVT,
                      Subject.SCIENCES_TECHNOLOGIE, Subject.ENSEIGNEMENT_SCIENTIFIQUE)


class LexiconEntry(NamedTuple):
    term: str                       # libellé affiché dans l'anomalie
    pattern: str                    # regex appliquée au texte sans accents, en minuscules
    min_level: Level                # premier niveau où le terme est attendu
    subjects: Optional[FrozenSet[Subject]]  # None = toutes matières


def _s(*subjects: Subject) -> FrozenSet[Subject]:
    return frozenset(subjects)


# Chaque entrée : (terme, motif, niveau minimal, matières concernées) + justification.
LEXICON: Tuple[LexiconEntry, ...] = (
    # Dérivation : introduite en 1re (spécialité et tronc commun). « dérivation » seul est
    # restreint aux maths car « montage en dérivation » est du vocabulaire de PC collège.
    LexiconEntry("dérivée", r"\b(fonction derivee|derivees?|nombre derive)\b", Level.PREMIERE, None),
    LexiconEntry("dérivation", r"\bderivation\b", Level.PREMIERE, _s(M)),
    # Logarithme (népérien ou décimal) : Terminale en maths.
    LexiconEntry("logarithme", r"\blogarithmes?\b|\bln\s*\(", Level.TERMINALE, _s(M)),
    # Calcul intégral et primitives : Terminale. « primitive » limité aux maths
    # (« atmosphère primitive » en SVT).
    LexiconEntry("intégrale", r"\bintegrales?\b", Level.TERMINALE, _s(M, PC)),
    LexiconEntry("primitive", r"\bprimitives?\b", Level.TERMINALE, _s(M)),
    # Vecteurs : Seconde (le collège voit les translations). Exclu en SVT (« vecteur » d'une maladie).
    LexiconEntry("vecteur", r"\bvecteurs?\b", Level.SECONDE, _s(M, PC)),
    # Discriminant du second degré : 1re.
    LexiconEntry("discriminant", r"\bdiscriminant\b", Level.PREMIERE, _s(M)),
    # Fonction exponentielle : 1re.
    LexiconEntry("exponentielle", r"\bexponentielles?\b", Level.PREMIERE, _s(M, PC)),
    # Produit scalaire : 1re.
    LexiconEntry("produit scalaire", r"\bproduits? scalaires?\b", Level.PREMIERE, None),
    # Suites arithmétiques / géométriques : 1re.
    LexiconEntry("suite arithmétique/géométrique", r"\bsuites? (arithmetiques?|geometriques?)\b", Level.PREMIERE, _s(M)),
    # Nombres complexes, matrices : Terminale (maths expertes).
    LexiconEntry("nombre complexe", r"\bnombres? complexes?\b", Level.TERMINALE, _s(M)),
    LexiconEntry("matrice", r"\bmatrices?\b", Level.TERMINALE, _s(M)),
    # Équations différentielles, loi binomiale : Terminale.
    LexiconEntry("équation différentielle", r"\bequations? differentielles?\b", Level.TERMINALE, None),
    LexiconEntry("loi binomiale", r"\blois? binomiales?\b", Level.TERMINALE, _s(M)),
    # Trigonométrie du triangle rectangle : cosinus au cycle 4 (souvent 4e ; seuil prudent 4E),
    # sinus et tangente en 3e.
    LexiconEntry("cosinus", r"\bcosinus\b", Level.QUATRIEME, _s(M)),
    LexiconEntry("sinus", r"\bsinus\b", Level.TROISIEME, _s(M)),
    # Théorèmes de Pythagore et de Thalès, racine carrée : cycle 4 (seuil prudent 4E).
    LexiconEntry("Pythagore", r"\bpythagore\b", Level.QUATRIEME, _s(M)),
    LexiconEntry("Thalès", r"\bthales\b", Level.QUATRIEME, _s(M)),
    LexiconEntry("racine carrée", r"\bracines? carrees?\b", Level.QUATRIEME, _s(M)),
    # Nombres relatifs / négatifs : 5e (hors programme de cycle 3).
    LexiconEntry("nombre relatif / négatif", r"\bnombres? (relatifs?|negatifs?)\b|\bentiers? relatifs?\b", Level.CINQUIEME, _s(M, ST)),
    # Mole et quantité de matière : Seconde (physique-chimie).
    LexiconEntry("mole / quantité de matière", r"\bmoles?\b|\bquantites? de matiere\b|\bmol/l\b", Level.SECONDE, None),
    # Isotopes : Seconde (structure de l'atome approfondie).
    LexiconEntry("isotope", r"\bisotopes?\b", Level.SECONDE, _s(PC, ST)),
    # ADN, gènes, allèles : cycle 4 (souvent 3e ; seuil prudent 4E). Hors cycle 3.
    LexiconEntry("ADN / gène", r"\badn\b|\bgenes?\b|\balleles?\b", Level.QUATRIEME, _s(SVT, ST)),
    # Mitose / méiose : au plus tôt en 3e.
    LexiconEntry("mitose / méiose", r"\bmitoses?\b|\bmeioses?\b", Level.TROISIEME, _s(SVT, ST)),
)

_COMPILED = tuple((e, re.compile(e.pattern)) for e in LEXICON)

LYCEE_LEVELS = frozenset({Level.SECONDE, Level.PREMIERE, Level.TERMINALE})


def fold(text: str) -> str:
    """Minuscules, sans accents, espaces simples (forme de recherche du lexique)."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(t.split())


def check_text_level(text: str, subject: Subject, level: Level) -> List[Tuple[str, Level]]:
    """Termes trop avancés pour ``level`` : liste triée de (terme, niveau minimal)."""
    folded = fold(text)
    hits = set()
    for entry, rx in _COMPILED:
        if entry.subjects is not None and subject not in entry.subjects:
            continue
        if LEVEL_RANK[level] < LEVEL_RANK[entry.min_level] and rx.search(folded):
            hits.add((entry.term, entry.min_level))
    return sorted(hits, key=lambda h: (LEVEL_RANK[h[1]], h[0]))


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_SIMPLE_OP_RE = re.compile(r"\d\s*[+\-*/×÷x:]\s*\d")
_LETTER_VAR_RE = re.compile(r"(?<![a-z])[a-z]\s*[=+\-*/^²]|\^|²|√")


def is_too_simple(text: str, level: Level, difficulty: DifficultyBand) -> bool:
    """
    Contenu DISCOVERY d'un niveau lycée dont les seuls nombres sont des chiffres isolés
    (0-9) combinés par une opération arithmétique élémentaire, sans variable ni puissance.
    """
    if level not in LYCEE_LEVELS or difficulty != DifficultyBand.DISCOVERY:
        return False
    t = text or ""
    for a, b in (("×", "*"), ("·", "*"), ("÷", "/"), ("−", "-"), ("²", "^2"), ("³", "^3"), ("√", "^")):
        t = t.replace(a, b)
    folded = fold(t)
    numbers = _NUMBER_RE.findall(folded)
    if not numbers or any(len(n) > 1 for n in numbers):
        return False
    if not _SIMPLE_OP_RE.search(folded):
        return False
    return not _LETTER_VAR_RE.search(folded)
