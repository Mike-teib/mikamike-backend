"""
maths.py — Vérification SYMBOLIQUE déterministe des réponses de mathématiques (SymPy).

Sécurité : `sympy.parse_expr` repose sur `eval`. Toute entrée est donc :
  - bornée (longueur), filtrée par liste blanche de caractères ;
  - restreinte à des identifiants autorisés (lettres isolées, fonctions connues) ;
  - évaluée avec un espace de noms minimal SANS builtins ;
  - protégée contre les explosions de calcul (puissances imbriquées, exposants énormes).
Toute entrée refusée ⇒ NEEDS_HUMAN_REVIEW (jamais VALID par défaut).

Fonctions :
  equivalents(a, b)                      -> Resultat
  verifier_reponse(attendue, reponse, forme_requise=None) -> Resultat
Formes requises : "fraction_irreductible", "entier", "decimal", "developpee", "factorisee".
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    rationalize,
    standard_transformations,
)

from app.curriculum.verifiers.base import Resultat, ambigu, invalide, revue, valide

MAX_LONGUEUR = 200
MAX_EXPOSANT = 60
# Garde de complexité sur l'ARBRE (revue session 2, finding R2-03 : « 9^(59*59*59*59) »,
# « 10^(59)^(59) », « (x+y+z+1)^60 », « exp(exp(exp(59))) » bloquaient ou faisaient planter).
MAX_NOEUDS = 120
MAX_TERMES_DEVELOPPES = 2000
MAX_PROFONDEUR_FONCTIONS = 2
MAX_EXPOSANT_TRANSCENDANT = 8
MAX_OPS_SIMPLIFY = 60
_CARACTERES = re.compile(r"^[0-9a-zA-Z+\-*/^().,=\s²³√π×÷·−]*$")
_FONCTIONS: Dict[str, object] = {
    "sqrt": sympy.sqrt, "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "exp": sympy.exp, "ln": sympy.log, "log": sympy.log, "abs": sympy.Abs, "pi": sympy.pi,
}
_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor, rationalize)
_POINTS_TEST = (sympy.Rational(3, 7), sympy.Rational(-5, 3), sympy.Rational(11, 2), sympy.Rational(2, 13))


class EntreeRefusee(ValueError):
    pass


class ExpressionNonDefinie(ValueError):
    """Expression mathématiquement non définie (division par zéro, ln(0)…)."""


def normaliser(texte: str) -> str:
    """Écriture scolaire française → syntaxe SymPy (sans rien évaluer)."""
    t = (texte or "").strip()
    if not t:
        raise EntreeRefusee("reponse_vide")
    if len(t) > MAX_LONGUEUR:
        raise EntreeRefusee("reponse_trop_longue")
    if not _CARACTERES.match(t):
        raise EntreeRefusee("caractere_non_autorise")
    t = t.replace("−", "-").replace("×", "*").replace("·", "*").replace("÷", "/")
    t = t.replace("²", "^2").replace("³", "^3").replace("π", "pi")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)  # virgule décimale
    if "," in t:
        raise EntreeRefusee("virgule_ambigue")
    t = re.sub(r"√\s*\(", "sqrt(", t)
    t = re.sub(r"√\s*([0-9.]+|[a-zA-Z])", r"sqrt(\1)", t)
    if "√" in t:
        raise EntreeRefusee("racine_mal_formee")
    for mot in re.findall(r"[a-zA-Z]+", t):
        if mot not in _FONCTIONS and (len(mot) > 3):
            raise EntreeRefusee("identifiant_non_autorise")
    # Garde anti-explosion : pas de puissance de puissance, exposants bornés.
    if re.search(r"\^[^+\-*/=()]*\^|\^\s*\([^)]*\^", t):
        raise EntreeRefusee("puissances_imbriquees")
    for exp in re.findall(r"\^\s*\(?\s*-?\s*(\d+)", t):
        if int(exp) > MAX_EXPOSANT:
            raise EntreeRefusee("exposant_trop_grand")
    if re.search(r"\d{16,}", t):
        raise EntreeRefusee("nombre_trop_long")
    return t


def _espace_noms(texte: str) -> Tuple[Dict[str, object], Dict[str, object]]:
    glob: Dict[str, object] = {
        "__builtins__": {},
        "Integer": sympy.Integer, "Float": sympy.Float, "Rational": sympy.Rational,
        "Symbol": sympy.Symbol, "Function": sympy.Function,
        "Mul": sympy.Mul, "Add": sympy.Add, "Pow": sympy.Pow,
    }
    loc: Dict[str, object] = dict(_FONCTIONS)
    # Toute lettre est un symbole ordinaire (E, I, N, S, O, Q ne sont PAS les objets SymPy).
    for lettre in set(re.findall(r"[a-zA-Z]", texte)):
        loc.setdefault(lettre, sympy.Symbol(lettre))
    for mot in re.findall(r"[a-zA-Z]+", texte):
        if mot not in _FONCTIONS:
            for lettre in mot:
                loc[lettre] = sympy.Symbol(lettre)
    return glob, loc


_FONCTIONS_TRANSCENDANTES = (sympy.sin, sympy.cos, sympy.tan, sympy.exp, sympy.log)


def _valeur_exposant(e: sympy.Basic) -> float:
    """Valeur d'un exposant CONSTANT et simple ; toute puissance imbriquée est refusée."""
    if isinstance(e, (sympy.Integer, sympy.Rational, sympy.Float)):
        v = float(e)
        if abs(v) > MAX_EXPOSANT:
            raise EntreeRefusee("exposant_trop_grand")
        return v
    if isinstance(e, sympy.Pow) and e.exp == -1:  # division a/b écrite a*b^-1
        b = _valeur_exposant(e.base)
        if b == 0:
            raise ExpressionNonDefinie("expression_non_definie")
        return 1.0 / b
    if isinstance(e, sympy.Symbol):
        # Exposant symbolique (suites : 2^n, q^(n+1)) : aucun développement n'est déclenché.
        return 1.0
    if isinstance(e, (sympy.Mul, sympy.Add)) and len(e.args) <= 3:
        vals = [_valeur_exposant(a) for a in e.args]
        v = 1.0
        if isinstance(e, sympy.Mul):
            for x in vals:
                v *= x
        else:
            v = sum(vals)
        if abs(v) > MAX_EXPOSANT:
            raise EntreeRefusee("exposant_trop_grand")
        return v
    raise EntreeRefusee("exposant_non_litteral")


def _controler_complexite(expr: sympy.Basic) -> None:
    """Refuse AVANT toute évaluation les arbres dont le calcul peut exploser."""
    noeuds = 0
    pile = [(expr, 1.0, 0)]  # (nœud, exposant cumulé, profondeur de fonctions)
    while pile:
        e, cumul, prof = pile.pop()
        noeuds += 1
        if noeuds > MAX_NOEUDS:
            raise EntreeRefusee("expression_trop_complexe")
        if isinstance(e, sympy.Pow):
            v = _valeur_exposant(e.exp) if not (e.exp == -1) else -1.0
            cumul *= max(1.0, abs(v))
            if cumul > MAX_EXPOSANT:
                raise EntreeRefusee("exposant_trop_grand")
            if isinstance(e.base, sympy.Add) and abs(v) > 1:
                k, n = len(e.base.args), int(abs(v))
                if math.comb(n + k - 1, k - 1) > MAX_TERMES_DEVELOPPES:
                    raise EntreeRefusee("developpement_trop_grand")
            if abs(v) > MAX_EXPOSANT_TRANSCENDANT and e.base.has(*_FONCTIONS_TRANSCENDANTES):
                raise EntreeRefusee("puissance_transcendante_trop_grande")
            pile.append((e.base, cumul, prof))
            continue
        if isinstance(e, sympy.Function):
            prof += 1
            if prof > MAX_PROFONDEUR_FONCTIONS:
                raise EntreeRefusee("fonctions_trop_imbriquees")
        for a in e.args:
            pile.append((a, cumul, prof))


def analyser(texte: str, *, evaluer: bool = True) -> sympy.Expr:
    t = normaliser(texte)
    if "=" in t:
        raise EntreeRefusee("egalite_non_attendue")
    glob, loc = _espace_noms(t)
    try:
        # 1) arbre NON évalué → contrôle de complexité ; 2) évaluation seulement si sûr.
        brut = parse_expr(t, local_dict=dict(loc), global_dict=dict(glob),
                          transformations=_TRANSFORMATIONS, evaluate=False)
    except Exception as exc:  # syntaxe invalide, TokenError…
        raise EntreeRefusee("syntaxe_invalide") from exc
    if not isinstance(brut, sympy.Basic):
        raise EntreeRefusee("expression_invalide")
    _controler_complexite(brut)
    try:
        expr = parse_expr(t, local_dict=loc, global_dict=glob,
                          transformations=_TRANSFORMATIONS, evaluate=evaluer)
    except (OverflowError, RecursionError, MemoryError) as exc:
        raise EntreeRefusee("calcul_trop_lourd") from exc
    except Exception as exc:
        raise EntreeRefusee("syntaxe_invalide") from exc
    if not isinstance(expr, sympy.Basic):
        raise EntreeRefusee("expression_invalide")
    if expr.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        raise ExpressionNonDefinie("expression_non_definie")
    return expr


def _difference_nulle(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
    """True : égales ; False : différentes ; None : indécidable (jamais d'exception)."""
    try:
        return _difference_nulle_brute(a, b)
    except (OverflowError, RecursionError, MemoryError, ZeroDivisionError, TypeError, ValueError):
        return None


def _difference_nulle_brute(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
    d = a - b
    if d == 0:
        return True
    if not d.free_symbols:
        val = complex(sympy.N(d, 30))
        if math.isnan(val.real) or math.isnan(val.imag):
            return None
        if abs(val) >= 1e-12:
            return False
    else:
        # Test NUMÉRIQUE d'abord (rapide) : une seule valeur non nulle prouve la différence.
        syms = sorted(d.free_symbols, key=str)
        for pt in _POINTS_TEST:
            v = complex(sympy.N(d.subs({s: pt + i for i, s in enumerate(syms)}), 30))
            if abs(v) > 1e-9:
                return False
    # Candidats égaux : preuve symbolique seulement si l'expression reste petite.
    if sympy.count_ops(d) > MAX_OPS_SIMPLIFY:
        return None
    if sympy.simplify(d) == 0:
        return True
    if not d.free_symbols:
        return True  # |d| < 1e-12 à 30 chiffres significatifs
    return None  # nul en tous les points testés sans preuve symbolique


def equivalents(a: str, b: str) -> Resultat:
    try:
        ea = analyser(a)
    except (EntreeRefusee, ExpressionNonDefinie) as exc:
        return revue(f"attendue_{exc}")
    try:
        eb = analyser(b)
    except EntreeRefusee as exc:
        return revue(str(exc))
    except ExpressionNonDefinie as exc:
        return invalide(str(exc))
    res = _difference_nulle(ea, eb)
    if res is True:
        return valide("equivalence_symbolique")
    if res is False:
        return invalide("non_equivalent")
    return ambigu("equivalence_non_prouvee")


def _separer_egalite(t: str) -> Tuple[Optional[str], str]:
    parts = t.split("=")
    if len(parts) == 1:
        return None, t
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    raise EntreeRefusee("egalite_mal_formee")


def _solutions(texte: str) -> List[str]:
    return [s.strip() for s in re.split(r"\s+ou\s+|;", texte) if s.strip()]


def _forme_ok(brut: str, forme: str) -> Optional[str]:
    """None si la forme est respectée, sinon le code d'écart."""
    s = brut.replace(" ", "").replace("−", "-")
    if forme == "entier":
        return None if re.fullmatch(r"-?\d+", s) else "forme_non_entiere"
    if forme == "decimal":
        return None if re.fullmatch(r"-?\d+([.,]\d+)?", s) else "forme_non_decimale"
    if forme == "fraction_irreductible":
        m = re.fullmatch(r"(-?\d+)/(\d+)", s)
        if not m:
            return None if re.fullmatch(r"-?\d+", s) else "forme_non_fractionnaire"
        p, q = int(m.group(1)), int(m.group(2))
        if q == 0:
            return "denominateur_nul"
        return None if math.gcd(p, q) == 1 and q != 1 else "fraction_non_irreductible"
    expr = analyser(brut)
    if forme == "developpee":
        return None if sympy.expand(expr) == expr and "(" not in s else "forme_non_developpee"
    if forme == "factorisee":
        return None if isinstance(expr, (sympy.Mul, sympy.Pow)) else "forme_non_factorisee"
    return "forme_inconnue"


def verifier_reponse(attendue: str, reponse: str, forme_requise: Optional[str] = None) -> Resultat:
    """
    Compare une réponse d'élève à la réponse attendue.

    - « x = 3 » attendu : « 3 », « x=3 », « x = 6/2 » sont équivalents ;
      une autre variable (« y = 3 ») est INVALID.
    - solutions multiples : « x = 2 ou x = -2 » (ordre indifférent).
    - `forme_requise` : impose en plus une écriture (ex. fraction irréductible).
    """
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    try:
        sol_att = [_separer_egalite(normaliser(s)) for s in _solutions(attendue)]
        sol_rep = [_separer_egalite(normaliser(s)) for s in _solutions(reponse)]
    except EntreeRefusee as exc:
        return revue(str(exc))

    if len(sol_att) != len(sol_rep):
        return invalide("nombre_de_solutions_different")

    restantes = list(sol_rep)
    for var_a, val_a in sol_att:
        trouve = False
        for i, (var_r, val_r) in enumerate(restantes):
            if var_r is not None and var_a is not None and var_r.replace(" ", "") != var_a.replace(" ", ""):
                continue
            r = equivalents(val_a, val_r)
            if r.verdict.value in ("NEEDS_HUMAN_REVIEW", "AMBIGUOUS"):
                return r
            if r.valide:
                restantes.pop(i)
                trouve = True
                break
        if not trouve:
            return invalide("valeur_incorrecte")

    if forme_requise:
        for s in _solutions(reponse):
            _, val = _separer_egalite(s)
            try:
                ecart = _forme_ok(val, forme_requise)
            except EntreeRefusee as exc:
                return revue(str(exc))
            if ecart:
                return invalide(ecart)
    return valide("reponse_equivalente")
