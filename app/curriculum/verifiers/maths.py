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


def analyser(texte: str, *, evaluer: bool = True) -> sympy.Expr:
    t = normaliser(texte)
    if "=" in t:
        raise EntreeRefusee("egalite_non_attendue")
    glob, loc = _espace_noms(t)
    try:
        expr = parse_expr(t, local_dict=loc, global_dict=glob,
                          transformations=_TRANSFORMATIONS, evaluate=evaluer)
    except Exception as exc:  # syntaxe invalide, TokenError…
        raise EntreeRefusee("syntaxe_invalide") from exc
    if not isinstance(expr, sympy.Basic):
        raise EntreeRefusee("expression_invalide")
    if expr.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        raise ExpressionNonDefinie("expression_non_definie")
    return expr


def _difference_nulle(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
    """True : égales ; False : différentes ; None : indécidable."""
    d = sympy.simplify(a - b)
    if d == 0:
        return True
    if not d.free_symbols:
        val = complex(sympy.N(d, 30))
        return abs(val) < 1e-12 if not math.isnan(val.real) else None
    syms = sorted(d.free_symbols, key=str)
    for pt in _POINTS_TEST:
        try:
            v = complex(sympy.N(d.subs({s: pt + i for i, s in enumerate(syms)}), 30))
        except (TypeError, ValueError):
            return None
        if abs(v) > 1e-9:
            return False
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
