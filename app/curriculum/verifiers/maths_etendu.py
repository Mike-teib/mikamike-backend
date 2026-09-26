"""
maths_etendu.py — Vérificateurs mathématiques spécialisés (lot 13, session 4).

Même doctrine que maths.py : VALID seulement si l'équivalence est DÉMONTRÉE ; INVALID si la
différence est démontrée ; tout le reste (entrée non analysable, calcul trop lourd, forme non
tranchée) ⇒ NEEDS_HUMAN_REVIEW. Toutes les entrées passent par `maths.analyser` (liste blanche,
bornes de longueur, garde de complexité sur l'arbre non évalué) : aucun `eval` libre.

  verifier_ensemble(attendu, reponse)            inéquations / intervalles / réunions
  verifier_derivee(fonction, reponse)            f'(x)
  verifier_limite(expression, point, reponse)    lim_{x→point} expression
  verifier_suite(nature, u0, raison, n0, formule)  suite arithmétique / géométrique explicite
  verifier_probabilite(attendue, reponse)        valeur dans [0, 1], fraction / décimal
  verifier_angle(attendu, reponse, unite)        degrés / radians
  verifier_valeur_approchee(exacte, reponse, decimales)
  racine_simplifiee(expression)                  forme « a√b » sans facteur carré dans b
"""

from __future__ import annotations

import re
from typing import Optional

import sympy

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide
from app.curriculum.verifiers.maths import EntreeRefusee, ExpressionNonDefinie, analyser, equivalents

_X = sympy.Symbol("x")
MAX_OPS_CALCUL = 30  # dérivées / limites : au-delà, revue humaine (temps de calcul non borné)
_INF = {"+inf": sympy.oo, "inf": sympy.oo, "+oo": sympy.oo, "oo": sympy.oo, "+∞": sympy.oo, "∞": sympy.oo,
        "-inf": -sympy.oo, "-oo": -sympy.oo, "-∞": -sympy.oo}


def _borne(t: str) -> sympy.Expr:
    t = t.strip().replace(" ", "")
    if t in _INF:
        return _INF[t]
    e = analyser(t)
    if e.free_symbols:
        raise EntreeRefusee("borne_non_numerique")
    return e


_INTERVALLE = re.compile(r"^\s*([\[\]])\s*([^;]+?)\s*;\s*([^;\[\]]+?)\s*([\[\]])\s*$")
_INEG = re.compile(r"^\s*(.+?)\s*(<=|>=|≤|≥|<|>)\s*(.+?)\s*(?:(<=|>=|≤|≥|<|>)\s*(.+?)\s*)?$")


def _vers_ensemble(texte: str) -> sympy.Set:
    """« x > 3 », « -1 ≤ x < 2 », « ]3 ; +∞[ », « [0;1] ∪ [2;3] », « S = … », « ∅ », « R »."""
    t = (texte or "").strip()
    t = re.sub(r"^\s*S\s*=\s*", "", t)
    if len(t) > 200:
        raise EntreeRefusee("reponse_trop_longue")
    if t in ("∅", "{}", "ensemble vide"):
        return sympy.S.EmptySet
    if t in ("R", "ℝ", "]-inf;+inf[", "]-∞;+∞["):
        return sympy.S.Reals
    morceaux = re.split(r"\s*(?:∪|\bU\b|\bou\b)\s*", t)
    if len(morceaux) > 1:
        return sympy.Union(*(_vers_ensemble(m) for m in morceaux))
    m = _INTERVALLE.match(t)
    if m:
        g, a, b, d = m.groups()
        va, vb = _borne(a), _borne(b)
        return sympy.Interval(va, vb, left_open=(g == "]" or va == -sympy.oo), right_open=(d == "[" or vb == sympy.oo))
    m = _INEG.match(t)
    if m:
        a, op1, b, op2, c = m.groups()
        ops = {"≤": "<=", "≥": ">="}
        op1, op2 = ops.get(op1, op1), ops.get(op2, op2) if op2 else None
        if op2:  # a op1 x op2 c (double inégalité)
            if b.strip() != "x":
                raise EntreeRefusee("double_inegalite_mal_formee")
            gauche = _borne(a)
            droite = _borne(c)
            if op1 in ("<", "<=") and op2 in ("<", "<="):
                return sympy.Interval(gauche, droite, left_open=op1 == "<", right_open=op2 == "<")
            raise EntreeRefusee("double_inegalite_non_ordonnee")
        g, d = a.strip(), b.strip()
        if g == "x" and d != "x":
            v = _borne(d)
            return {"<": sympy.Interval.open(-sympy.oo, v), "<=": sympy.Interval(-sympy.oo, v, left_open=True),
                    ">": sympy.Interval.open(v, sympy.oo), ">=": sympy.Interval(v, sympy.oo, right_open=True)}[op1]
        if d == "x" and g != "x":
            v = _borne(g)
            return {"<": sympy.Interval.open(v, sympy.oo), "<=": sympy.Interval(v, sympy.oo, right_open=True),
                    ">": sympy.Interval.open(-sympy.oo, v), ">=": sympy.Interval(-sympy.oo, v, left_open=True)}[op1]
        # Inéquation non résolue (« 2x - 6 > 0 ») : résolue si polynomiale de degré ≤ 2.
        expr = analyser(g) - analyser(d)
        if expr.free_symbols - {_X} or not expr.is_polynomial(_X) or sympy.degree(expr, _X) > 2:
            raise EntreeRefusee("inequation_non_traitee")
        rel = {"<": sympy.StrictLessThan, "<=": sympy.LessThan, ">": sympy.StrictGreaterThan,
               ">=": sympy.GreaterThan}[op1](expr, 0)
        return sympy.solveset(rel, _X, domain=sympy.S.Reals)
    raise EntreeRefusee("ensemble_non_reconnu")


def verifier_ensemble(attendu: str, reponse: str) -> Resultat:
    try:
        ea = _vers_ensemble(attendu)
    except (EntreeRefusee, ExpressionNonDefinie, ValueError, TypeError) as exc:
        return revue(f"attendu_{exc}")
    try:
        er = _vers_ensemble(reponse)
    except (EntreeRefusee, ExpressionNonDefinie, ValueError, TypeError) as exc:
        return revue(str(exc))
    try:
        egaux = sympy.Complement(ea, er) == sympy.S.EmptySet and sympy.Complement(er, ea) == sympy.S.EmptySet
    except (TypeError, ValueError, RecursionError):
        return revue("comparaison_indecidable")
    return valide("ensembles_egaux") if egaux else invalide("ensembles_differents")


def _petite(e: sympy.Expr) -> bool:
    return sympy.count_ops(e) <= MAX_OPS_CALCUL


def verifier_derivee(fonction: str, reponse: str) -> Resultat:
    try:
        f = analyser(fonction)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(f"fonction_{exc}")
    if f.free_symbols - {_X} or not _petite(f):
        return revue("fonction_hors_perimetre")
    rep = re.sub(r"^\s*f\s*'\s*\(\s*x\s*\)\s*=\s*", "", reponse or "")
    try:
        derivee = sympy.diff(f, _X)
    except (ValueError, TypeError, RecursionError):
        return revue("derivation_impossible")
    return equivalents(str(derivee).replace("**", "^"), rep)


def verifier_limite(expression: str, point: str, reponse: str) -> Resultat:
    try:
        f = analyser(expression)
        p = _borne(point)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(str(exc))
    if f.free_symbols - {_X} or not _petite(f):
        return revue("expression_hors_perimetre")
    try:
        # Point fini : limite BILATÉRALE (sympy.limit est unilatérale à droite par défaut ;
        # « lim 1/x en 0 = +∞ » serait accepté à tort).
        lim = sympy.limit(f, _X, p) if p in (sympy.oo, -sympy.oo) else sympy.limit(f, _X, p, dir="+-")
    except (NotImplementedError, ValueError, TypeError, RecursionError):
        return revue("limite_indecidable")
    if lim.has(sympy.AccumBounds) or isinstance(lim, sympy.Limit) or lim == sympy.zoo:
        return revue("limite_non_determinee")
    r = (reponse or "").strip().replace(" ", "")
    if r in _INF or lim in (sympy.oo, -sympy.oo):
        return valide("limite_infinie") if _INF.get(r) == lim else invalide("limite_differente")
    return equivalents(str(lim).replace("**", "^"), r)


def verifier_suite(nature: str, u0: str, raison: str, n0: int, formule: str) -> Resultat:
    """Formule explicite de u(n) pour une suite arithmétique (u(n) = u0 + (n-n0)r) ou géométrique."""
    n = sympy.Symbol("n")
    try:
        a, q = analyser(u0), analyser(raison)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(str(exc))
    if nature == "arithmetique":
        attendu = a + (n - n0) * q
    elif nature == "geometrique":
        attendu = a * q ** (n - n0)
    else:
        return revue("nature_inconnue")
    rep = re.sub(r"^\s*u\s*\(?\s*n\s*\)?\s*=\s*", "", formule or "")
    return equivalents(str(attendu).replace("**", "^"), rep)


def verifier_probabilite(attendue: str, reponse: str) -> Resultat:
    r = (reponse or "").strip()
    if r.endswith("%"):
        return revue("pourcentage_forme_a_trancher")
    try:
        v = analyser(r)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(str(exc))
    if v.free_symbols:
        return revue("probabilite_non_numerique")
    if not (0 <= v <= 1):
        return invalide("hors_intervalle_probabilite")
    return equivalents(attendue, r)


_DEG = re.compile(r"^\s*(.+?)\s*(°|deg|degres|degrés)\s*$")


def verifier_angle(attendu: str, reponse: str, unite: str) -> Resultat:
    """`unite` : unité DEMANDÉE (« deg » ou « rad »). Même angle dans l'autre unité ⇒ revue."""
    def valeur_rad(t: str):
        m = _DEG.match(t or "")
        if m:
            return analyser(m.group(1)) * sympy.pi / 180, "deg"
        e = analyser(t)
        return e, ("rad" if e.has(sympy.pi) else None)
    try:
        a, ua = valeur_rad(attendu)
        r, ur = valeur_rad(reponse)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(str(exc))
    if ua is None:
        ua = unite
    if ur is None:  # nombre nu : interprété dans l'unité DEMANDÉE
        r = r * sympy.pi / 180 if unite == "deg" else r
        ur = unite
    if sympy.simplify(a - r) != 0:
        return invalide("angle_different")
    return valide("angle_egal") if ur == unite else revue("unite_d_angle_differente")


def verifier_valeur_approchee(exacte: str, reponse: str, decimales: int) -> Resultat:
    """Arrondi demandé à `decimales` chiffres : l'écriture exacte est acceptée ; une valeur
    décimale doit avoir EXACTEMENT ce nombre de décimales et être l'arrondi correct."""
    r = (reponse or "").strip().replace(",", ".")
    if not re.fullmatch(r"-?\d+(\.\d+)?", r):
        res = equivalents(exacte, reponse)
        return res if res.verdict.value != "INVALID" else invalide("ni_exacte_ni_arrondie")
    try:
        v = analyser(exacte)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(str(exc))
    if v.free_symbols:
        return revue("valeur_non_numerique")
    nb = len(r.split(".")[1]) if "." in r else 0
    if nb != decimales:
        return invalide("nombre_de_decimales_incorrect")
    # Arrondi au plus proche, calculé en rationnels exacts (aucune erreur binaire).
    echelle = sympy.Integer(10) ** decimales
    exacte_num = sympy.Rational(str(sympy.N(v, 40)))
    signe = -1 if exacte_num < 0 else 1  # arrondi « au plus proche, moitié loin de zéro »
    attendu = signe * sympy.floor(abs(exacte_num) * echelle + sympy.Rational(1, 2)) / echelle
    return valide("arrondi_correct") if sympy.Rational(r) == attendu else invalide("arrondi_incorrect")


def racine_simplifiee(expression: str) -> Optional[bool]:
    """True si aucune racine carrée n'a de facteur carré parfait (> 1) ; None si non analysable."""
    try:
        e = analyser(expression, evaluer=False)
    except (EntreeRefusee, ExpressionNonDefinie):
        return None
    for p in e.atoms(sympy.Pow):
        if p.exp == sympy.Rational(1, 2) and p.base.is_Integer:
            b = int(p.base)
            if any(b % (k * k) == 0 for k in range(2, int(b ** 0.5) + 1)):
                return False
    return True
