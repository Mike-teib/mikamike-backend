"""
recurrence.py — Pédagogie dédiée au raisonnement par récurrence.

1. Diagnostic de la RÉDACTION d'un élève, découpée en 4 parties
   (initialisation, hypothèse, hérédité, conclusion). Confusions détectées :
     INIT_ABSENTE, INIT_MAUVAIS_RANG, INIT_SUPPOSEE (on suppose au lieu de vérifier)
     HYP_POUR_TOUT_N (hypothèse circulaire « pour tout n »),
     HYP_SUR_P_N_PLUS_1 (on suppose P(n+1)),
     HER_OBJECTIF_P_N (l'hérédité vise P(n) au lieu de P(n+1)),
     HER_UTILISE_P_N_PLUS_1 (on utilise ce qu'on veut démontrer),
     HER_SANS_HYPOTHESE (l'hypothèse de récurrence n'est pas utilisée),
     CONCL_ABSENTE, CONCL_P_N_PLUS_1_SEULEMENT, CONCL_SANS_RANG.
   Chaque confusion a une question de guidage qui NE donne PAS la réponse.

2. Vérification MATHÉMATIQUE (SymPy, déterministe) :
   - formule explicite d'une suite définie par récurrence u(n+1) = f(u(n)) ;
   - hérédité via FONCTION AUXILIAIRE : f croissante sur [a, b] et f([a, b]) ⊂ [a, b]
     (cas classique « a ≤ u(n) ≤ b ⇒ a ≤ u(n+1) ≤ b »).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Mapping, Optional

import sympy
from sympy import is_increasing

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide
from app.curriculum.verifiers.maths import EntreeRefusee, analyser

QUESTIONS_GUIDAGE: Dict[str, str] = {
    "INIT_ABSENTE": "Par quel rang commence la propriété, et l'as-tu vérifiée à ce rang précis ?",
    "INIT_MAUVAIS_RANG": "À partir de quel entier l'énoncé demande-t-il de démontrer la propriété ?",
    "INIT_SUPPOSEE": "Dans l'initialisation, as-tu le droit de supposer, ou dois-tu vérifier par un calcul ?",
    "HYP_POUR_TOUT_N": "Si tu supposes la propriété vraie pour tout n, que reste-t-il à démontrer ?",
    "HYP_SUR_P_N_PLUS_1": "Quelle propriété supposes-tu vraie : celle au rang n ou celle au rang n+1 ?",
    "HER_OBJECTIF_P_N": "Dans l'hérédité, qu'est-ce que tu cherches à démontrer : P(n) ou P(n+1) ?",
    "HER_UTILISE_P_N_PLUS_1": "Peux-tu utiliser dans ta preuve ce que tu es justement en train de démontrer ?",
    "HER_SANS_HYPOTHESE": "À quel moment de ton calcul utilises-tu l'hypothèse de récurrence ?",
    "CONCL_ABSENTE": "Qu'as-tu finalement démontré, et pour quels entiers ?",
    "CONCL_P_N_PLUS_1_SEULEMENT": "Ta conclusion porte-t-elle sur un seul rang, ou sur tous les rangs à partir du premier ?",
    "CONCL_SANS_RANG": "À partir de quel rang la propriété est-elle vraie ?",
    # Session 4 (lot 12)
    "PROP_NON_DEFINIE": "Quelle est exactement la propriété P(n) que tu veux démontrer ?",
    "HYP_ABSENTE": "Qu'est-ce que tu supposes vrai avant de démontrer l'hérédité ?",
    "HYP_SANS_RANG": "Pour quels entiers n ton hypothèse est-elle posée : un entier quelconque, ou à partir d'un certain rang ?",
    "HER_IMPLICATION_INVERSEE": "Dans l'hérédité, dans quel sens va l'implication : de P(n) vers P(n+1), ou l'inverse ?",
    "CONCL_QUANTIFICATEUR_EXISTENTIEL": "As-tu montré la propriété pour UN entier, ou pour TOUS les entiers à partir du premier rang ?",
}

# Étape de la démonstration à laquelle appartient chaque confusion (ordre de la démonstration).
ETAPES = ("propriete", "initialisation", "hypothese", "heredite", "conclusion")
ETAPE_DE = {
    "PROP_NON_DEFINIE": "propriete",
    "INIT_ABSENTE": "initialisation", "INIT_MAUVAIS_RANG": "initialisation", "INIT_SUPPOSEE": "initialisation",
    "HYP_ABSENTE": "hypothese", "HYP_POUR_TOUT_N": "hypothese", "HYP_SUR_P_N_PLUS_1": "hypothese",
    "HYP_SANS_RANG": "hypothese",
    "HER_OBJECTIF_P_N": "heredite", "HER_UTILISE_P_N_PLUS_1": "heredite", "HER_SANS_HYPOTHESE": "heredite",
    "HER_IMPLICATION_INVERSEE": "heredite",
    "CONCL_ABSENTE": "conclusion", "CONCL_P_N_PLUS_1_SEULEMENT": "conclusion", "CONCL_SANS_RANG": "conclusion",
    "CONCL_QUANTIFICATEUR_EXISTENTIEL": "conclusion",
}

SECTIONS = ("initialisation", "hypothese", "heredite", "conclusion")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").lower()
    t = t.replace("≥", ">=").replace(" ", " ")
    t = re.sub(r"\s+", " ", t)
    # Uniformise P(n + 1), P_{n+1}, P n+1… → p(n+1)
    t = re.sub(r"\bp\s*[\(_{\[]{0,2}\s*n\s*\+\s*1\s*[\)}\]]{0,2}", "p(n+1)", t)
    t = re.sub(r"\bp\s*[\(_{\[]{1,2}\s*n\s*[\)}\]]{1,2}", "p(n)", t)
    return t.strip()


_DEFINITION = re.compile(r"(soit|notons|on note|appelons)\s+p\(n\)|p\(n\)\s*(:|designe|la propriete|est la propriete)")


def diagnostiquer_redaction(parties: Mapping[str, str], rang_initial: int, *,
                            exiger_propriete: bool = False) -> List[str]:
    """Renvoie la liste ordonnée des confusions détectées (vide = rédaction correcte).
    `exiger_propriete` : la propriété P(n) doit être énoncée (section « propriete » ou définition
    explicite « Soit P(n) : … » dans la rédaction)."""
    p = {k: _norm(parties.get(k, "")) for k in SECTIONS}
    out: List[str] = []
    if exiger_propriete:
        tout = " ".join([_norm(parties.get("propriete", "")), *p.values()])
        if not (_norm(parties.get("propriete", "")) and "p(n)" in tout) and not _DEFINITION.search(tout):
            out.append("PROP_NON_DEFINIE")

    init = p["initialisation"]
    if not init:
        out.append("INIT_ABSENTE")
    else:
        if re.search(r"\b(supposons|on suppose|admettons)\b", init):
            out.append("INIT_SUPPOSEE")
        rangs = [int(x) for grp in re.findall(r"p\s*\(\s*(\d+)\s*\)|\bn\s*=\s*(\d+)|\bu\s*_?\s*(\d+)", init)
                 for x in grp if x]
        if rangs and rang_initial not in rangs:
            out.append("INIT_MAUVAIS_RANG")
        if not rangs:
            out.append("INIT_ABSENTE")

    hyp = p["hypothese"]
    if not hyp:
        out.append("HYP_ABSENTE")
    elif re.search(r"pour tout (entier )?n\b", hyp) and not re.search(r"(un certain|fixe|donne)", hyp):
        out.append("HYP_POUR_TOUT_N")
    elif "p(n+1)" in hyp and "p(n)" not in hyp:
        out.append("HYP_SUR_P_N_PLUS_1")
    elif not re.search(r"(un certain|fixe|donne|quelconque|>=|a partir)", hyp):
        out.append("HYP_SANS_RANG")

    her = p["heredite"]
    if her:
        objectif = re.search(r"(montrons|demontrons|prouvons|objectif|on veut montrer|il faut montrer)[^.]*", her)
        cible = objectif.group(0) if objectif else ""
        if cible and "p(n)" in cible and "p(n+1)" not in cible:
            out.append("HER_OBJECTIF_P_N")
        if re.search(r"(d'apres|par|grace a|comme|on sait que|puisque)\s+(l'hypothese\s+)?p\(n\+1\)", her):
            out.append("HER_UTILISE_P_N_PLUS_1")
        if not re.search(r"(hypothese de recurrence|\bhr\b|d'apres p\(n\)|par p\(n\)|grace a p\(n\))", her):
            out.append("HER_SANS_HYPOTHESE")
        if re.search(r"p\(n\+1\)\s*(=>|⇒|implique|entraine)\s*p\(n\)(?!\+)|si p\(n\+1\)( est vraie)?,? alors p\(n\)(?!\+)", her):
            out.append("HER_IMPLICATION_INVERSEE")
    else:
        out.append("HER_OBJECTIF_P_N")

    concl = p["conclusion"]
    if not concl:
        out.append("CONCL_ABSENTE")
    elif re.search(r"il existe (un )?(entier )?n\b", concl):
        out.append("CONCL_QUANTIFICATEUR_EXISTENTIEL")
    else:
        if "p(n+1)" in concl and not re.search(r"pour tout", concl):
            out.append("CONCL_P_N_PLUS_1_SEULEMENT")
        elif not re.search(rf"(>=\s*{rang_initial}|a partir de\s+{rang_initial}|pour tout (entier )?(naturel )?n\b)", concl):
            out.append("CONCL_SANS_RANG")
    return out


def prochaine_question(confusions: List[str]) -> Optional[str]:
    """Une seule question à la fois, dans l'ordre de la démonstration."""
    return QUESTIONS_GUIDAGE[confusions[0]] if confusions else None


def analyser_redaction(parties: Mapping[str, str], rang_initial: int, *, exiger_propriete: bool = False) -> dict:
    """Ce dont Mika a besoin : l'ÉTAPE qui bloque (la première dans l'ordre de la démonstration),
    les étapes déjà valides, et UNE question de guidage qui ne donne pas la réponse."""
    conf = diagnostiquer_redaction(parties, rang_initial, exiger_propriete=exiger_propriete)
    ordre = {e: i for i, e in enumerate(ETAPES)}
    conf = sorted(conf, key=lambda c: ordre[ETAPE_DE[c]])  # tri STABLE : ordre interne conservé
    bloquees = {ETAPE_DE[c] for c in conf}
    etapes = [e for e in ETAPES if e != "propriete" or exiger_propriete]
    return {
        "etape_bloquante": ETAPE_DE[conf[0]] if conf else None,
        "confusions": conf,
        "etapes_valides": [e for e in etapes if e not in bloquees],
        "question": prochaine_question(conf),
        "complete": not conf,
    }


# --------------------------------------------------------------------------- #
# Vérification mathématique
# --------------------------------------------------------------------------- #
_n, _x = sympy.Symbol("n", integer=True), sympy.Symbol("x")


def _fonction(texte: str, var: str) -> sympy.Expr:
    expr = analyser(texte)
    autres = {str(s) for s in expr.free_symbols} - {var}
    if autres:
        raise EntreeRefusee("symbole_inattendu")
    return expr.subs(sympy.Symbol(var), _n if var == "n" else _x)


def verifier_formule_explicite(f_recurrence: str, u0: str, rang_initial: int, formule: str) -> Resultat:
    """
    u(n0) = u0 et u(n+1) = f(u(n)) (f écrite en x) ; l'élève propose u(n) = formule (en n).
    VALID si initialisation ET hérédité sont vérifiées symboliquement.
    """
    try:
        f = _fonction(f_recurrence, "x")
        g = _fonction(formule, "n")
        a = analyser(u0)
    except EntreeRefusee as exc:
        return revue(str(exc))
    if sympy.simplify(g.subs(_n, rang_initial) - a) != 0:
        return invalide("initialisation_fausse")
    if sympy.simplify(f.subs(_x, g) - g.subs(_n, _n + 1)) != 0:
        return invalide("heredite_fausse")
    return valide("formule_demontree")


def verifier_fonction_auxiliaire(f_recurrence: str, f_eleve: str) -> Resultat:
    """La fonction auxiliaire proposée par l'élève est-elle bien celle de la relation
    u(n+1) = f(u(n)) ? (équivalence symbolique démontrée ; sinon INVALID ou revue)."""
    try:
        f = _fonction(f_recurrence, "x")
        g = _fonction(f_eleve, "x")
    except EntreeRefusee as exc:
        return revue(str(exc))
    diff = sympy.simplify(f - g)
    if diff == 0:
        return valide("fonction_auxiliaire_correcte")
    if diff.is_number:
        return invalide("fonction_auxiliaire_incorrecte")
    return invalide("fonction_auxiliaire_incorrecte") if any(
        sympy.simplify(diff.subs(_x, v)) != 0 for v in (sympy.Rational(1, 3), 2, -sympy.Rational(5, 7))
    ) else revue("equivalence_indecidable")


def verifier_heredite_fonction_auxiliaire(f_texte: str, a: str, b: str) -> Resultat:
    """
    Hérédité « a ≤ u(n) ≤ b ⇒ a ≤ u(n+1) ≤ b » avec u(n+1) = f(u(n)) :
    suffisant si f est croissante sur [a, b], f(a) ≥ a et f(b) ≤ b.
    """
    try:
        f = _fonction(f_texte, "x")
        va, vb = analyser(a), analyser(b)
    except EntreeRefusee as exc:
        return revue(str(exc))
    if not (va.is_real and vb.is_real) or bool(va >= vb):
        return invalide("intervalle_invalide")
    try:
        croissante = is_increasing(f, sympy.Interval(va, vb), _x)
    except Exception:
        return revue("monotonie_indecidable")
    if croissante is not True:
        return invalide("fonction_non_croissante_sur_intervalle")
    if not bool(sympy.simplify(f.subs(_x, va) - va) >= 0):
        return invalide("f(a)_inferieur_a_a")
    if not bool(sympy.simplify(vb - f.subs(_x, vb)) >= 0):
        return invalide("f(b)_superieur_a_b")
    return valide("intervalle_stable_par_f_croissante")
