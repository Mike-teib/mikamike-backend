"""
maths.py — Vérification SYMBOLIQUE déterministe des réponses de mathématiques (SymPy).

Adapté de app/curriculum/verifiers/maths.py (branche session6-production-hardening),
rendu autonome (aucune dépendance à app/).

Sécurité : `sympy.parse_expr` repose sur `eval`. Toute entrée est donc :
  - bornée (longueur), filtrée par liste blanche de caractères ;
  - restreinte à des identifiants autorisés (lettres isolées, fonctions connues) ;
  - sans accès d'attribut (« x.n », « (1).evalf ») ;
  - évaluée avec un espace de noms minimal SANS builtins ;
  - protégée contre les explosions de calcul (puissances imbriquées, exposants énormes,
    développements trop grands, fonctions trop imbriquées) — contrôle de l'arbre NON
    évalué avant toute évaluation.
Toute entrée refusée ⇒ NEEDS_HUMAN_REVIEW (jamais VALID par défaut).

API :
  parse_math(texte)                                   -> sympy.Expr (lève MathInputRejected)
  equivalent(a, b)                                    -> CheckResult
  check_math_answer(attendue, reponse, required_form) -> CheckResult
  find_equivalent_in_text(attendue, texte)            -> bool
Formes requises (required_form) : "fraction_irreductible", "entier", "decimal",
"developpee", "factorisee". Forme inconnue ⇒ NEEDS_HUMAN_REVIEW.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    rationalize,
    standard_transformations,
)

from pedagogy.checks.math_notation import latex_to_plain
from pedagogy.checks.verdict import CheckResult, Verdict, ambiguous, invalid, review, valid

MAX_LENGTH = 200
MAX_EXPONENT = 60
MAX_NODES = 120
MAX_EXPANDED_TERMS = 2000
MAX_FUNCTION_DEPTH = 2
MAX_TRANSCENDENTAL_EXPONENT = 8
MAX_OPS_SIMPLIFY = 60
MAX_CANDIDATES = 80
KNOWN_FORMS = frozenset({"fraction_irreductible", "entier", "decimal", "developpee", "factorisee"})

_ALLOWED_CHARS = re.compile(r"^[0-9a-zA-Z+\-*/^().,=\s²³√π×÷·−]*$")
_FUNCTIONS: Dict[str, object] = {
    "sqrt": sympy.sqrt, "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "exp": sympy.exp, "ln": sympy.log, "log": sympy.log, "abs": sympy.Abs, "pi": sympy.pi,
}
_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor, rationalize)
_TEST_POINTS = (sympy.Rational(3, 7), sympy.Rational(-5, 3), sympy.Rational(11, 2), sympy.Rational(2, 13))
_TRANSCENDENTAL = (sympy.sin, sympy.cos, sympy.tan, sympy.exp, sympy.log)


class MathInputRejected(ValueError):
    """Entrée refusée par les gardes de sécurité ou illisible."""


class UndefinedExpression(ValueError):
    """Expression mathématiquement non définie (division par zéro, ln(0)…)."""


def value_to_text(value: Any) -> str:
    """Valeur attendue (int, float, Decimal, str) → texte sans notation « e » ambiguë."""
    if isinstance(value, bool):
        raise MathInputRejected("booleen_non_mathematique")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MathInputRejected("valeur_non_finie")
        s = format(Decimal(repr(value)), "f")
        return s.rstrip("0").rstrip(".") if "." in s else s
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, str):
        return value
    raise MathInputRejected("type_de_valeur_non_supporte")


def normalize_math(text: str) -> str:
    """Écriture scolaire française → syntaxe SymPy (sans rien évaluer)."""
    t = (text or "").strip()
    if not t:
        raise MathInputRejected("reponse_vide")
    if len(t) > MAX_LENGTH:
        raise MathInputRejected("reponse_trop_longue")
    if not _ALLOWED_CHARS.match(t):
        raise MathInputRejected("caractere_non_autorise")
    t = t.replace("−", "-").replace("×", "*").replace("·", "*").replace("÷", "/")
    t = t.replace("²", "^2").replace("³", "^3").replace("π", "pi")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)  # virgule décimale
    if "," in t:
        raise MathInputRejected("virgule_ambigue")
    if re.search(r"\.\s*[A-Za-z_(]|[A-Za-z)]\s*\.", t):
        raise MathInputRejected("acces_attribut_interdit")
    t = re.sub(r"√\s*\(", "sqrt(", t)
    t = re.sub(r"√\s*([0-9.]+|[a-zA-Z])", r"sqrt(\1)", t)
    if "√" in t:
        raise MathInputRejected("racine_mal_formee")
    for word in re.findall(r"[a-zA-Z]+", t):
        if word not in _FUNCTIONS and len(word) > 3:
            raise MathInputRejected("identifiant_non_autorise")
    if re.search(r"\^[^+\-*/=()]*\^|\^\s*\([^)]*\^", t):
        raise MathInputRejected("puissances_imbriquees")
    for exp in re.findall(r"\^\s*\(?\s*-?\s*(\d+)", t):
        if int(exp) > MAX_EXPONENT:
            raise MathInputRejected("exposant_trop_grand")
    if re.search(r"\d{16,}", t):
        raise MathInputRejected("nombre_trop_long")
    return t


def _namespace(text: str) -> Tuple[Dict[str, object], Dict[str, object]]:
    glob: Dict[str, object] = {
        "__builtins__": {},
        "Integer": sympy.Integer, "Float": sympy.Float, "Rational": sympy.Rational,
        "Symbol": sympy.Symbol, "Function": sympy.Function,
        "Mul": sympy.Mul, "Add": sympy.Add, "Pow": sympy.Pow,
    }
    loc: Dict[str, object] = dict(_FUNCTIONS)
    # Toute lettre est un symbole ordinaire (E, I, N, S, O, Q ne sont PAS les objets SymPy).
    for word in re.findall(r"[a-zA-Z]+", text):
        if word not in _FUNCTIONS:
            for letter in word:
                loc[letter] = sympy.Symbol(letter)
    return glob, loc


def _exponent_value(e: sympy.Basic) -> float:
    if isinstance(e, (sympy.Integer, sympy.Rational, sympy.Float)):
        v = float(e)
        if abs(v) > MAX_EXPONENT:
            raise MathInputRejected("exposant_trop_grand")
        return v
    if isinstance(e, sympy.Pow) and e.exp == -1:
        b = _exponent_value(e.base)
        if b == 0:
            raise UndefinedExpression("expression_non_definie")
        return 1.0 / b
    if isinstance(e, sympy.Symbol):
        return 1.0  # exposant symbolique (2^n) : aucun développement déclenché
    if isinstance(e, (sympy.Mul, sympy.Add)) and len(e.args) <= 3:
        vals = [_exponent_value(a) for a in e.args]
        if isinstance(e, sympy.Mul):
            v = 1.0
            for x in vals:
                v *= x
        else:
            v = sum(vals)
        if abs(v) > MAX_EXPONENT:
            raise MathInputRejected("exposant_trop_grand")
        return v
    raise MathInputRejected("exposant_non_litteral")


def _check_complexity(expr: sympy.Basic) -> None:
    """Refuse AVANT toute évaluation les arbres dont le calcul peut exploser."""
    nodes = 0
    stack = [(expr, 1.0, 0)]
    while stack:
        e, cumul, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            raise MathInputRejected("expression_trop_complexe")
        if isinstance(e, sympy.Pow):
            v = _exponent_value(e.exp) if e.exp != -1 else -1.0
            cumul *= max(1.0, abs(v))
            if cumul > MAX_EXPONENT:
                raise MathInputRejected("exposant_trop_grand")
            if isinstance(e.base, sympy.Add) and abs(v) > 1:
                k, n = len(e.base.args), int(abs(v))
                if math.comb(n + k - 1, k - 1) > MAX_EXPANDED_TERMS:
                    raise MathInputRejected("developpement_trop_grand")
            if abs(v) > MAX_TRANSCENDENTAL_EXPONENT and e.base.has(*_TRANSCENDENTAL):
                raise MathInputRejected("puissance_transcendante_trop_grande")
            stack.append((e.base, cumul, depth))
            continue
        if isinstance(e, sympy.Function):
            depth += 1
            if depth > MAX_FUNCTION_DEPTH:
                raise MathInputRejected("fonctions_trop_imbriquees")
        for a in e.args:
            stack.append((a, cumul, depth))


def parse_math(text: str, *, evaluate: bool = True) -> sympy.Expr:
    t = normalize_math(text)
    if "=" in t:
        raise MathInputRejected("egalite_non_attendue")
    glob, loc = _namespace(t)
    try:
        raw = parse_expr(t, local_dict=dict(loc), global_dict=dict(glob),
                         transformations=_TRANSFORMATIONS, evaluate=False)
    except Exception as exc:  # noqa: BLE001 — syntaxe invalide, TokenError…
        raise MathInputRejected("syntaxe_invalide") from exc
    if not isinstance(raw, sympy.Basic):
        raise MathInputRejected("expression_invalide")
    _check_complexity(raw)
    try:
        expr = parse_expr(t, local_dict=loc, global_dict=glob,
                          transformations=_TRANSFORMATIONS, evaluate=evaluate)
    except (OverflowError, RecursionError, MemoryError) as exc:
        raise MathInputRejected("calcul_trop_lourd") from exc
    except Exception as exc:  # noqa: BLE001
        raise MathInputRejected("syntaxe_invalide") from exc
    if not isinstance(expr, sympy.Basic):
        raise MathInputRejected("expression_invalide")
    if expr.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        raise UndefinedExpression("expression_non_definie")
    return expr


def _difference_is_zero(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
    """True : égales ; False : différentes ; None : indécidable (jamais d'exception)."""
    try:
        return _difference_is_zero_raw(a, b)
    except (OverflowError, RecursionError, MemoryError, ZeroDivisionError, TypeError, ValueError):
        return None


def _difference_is_zero_raw(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
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
        syms = sorted(d.free_symbols, key=str)
        for pt in _TEST_POINTS:
            v = complex(sympy.N(d.subs({s: pt + i for i, s in enumerate(syms)}), 30))
            if abs(v) > 1e-9:
                return False
    if sympy.count_ops(d) > MAX_OPS_SIMPLIFY:
        return None
    if sympy.simplify(d) == 0:
        return True
    if not d.free_symbols:
        return True  # |d| < 1e-12 à 30 chiffres significatifs
    return None


def equivalent(a: str, b: str) -> CheckResult:
    """a = attendue, b = proposée. Refus sur l'attendue ⇒ revue ; sur la proposée ⇒ revue."""
    try:
        ea = parse_math(a)
    except (MathInputRejected, UndefinedExpression) as exc:
        return review(f"attendue_{exc}")
    try:
        eb = parse_math(b)
    except MathInputRejected as exc:
        return review(str(exc))
    except UndefinedExpression as exc:
        return invalid(str(exc))
    res = _difference_is_zero(ea, eb)
    if res is True:
        return valid("equivalence_symbolique")
    if res is False:
        return invalid("non_equivalent")
    return ambiguous("equivalence_non_prouvee")


def _split_equality(t: str) -> Tuple[Optional[str], str]:
    parts = t.split("=")
    if len(parts) == 1:
        return None, t
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    raise MathInputRejected("egalite_mal_formee")


def _solutions(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"\s+ou\s+|;", text) if s.strip()]


def _form_gap(raw: str, form: str) -> Optional[str]:
    """None si la forme est respectée, sinon le code d'écart."""
    s = raw.replace(" ", "").replace("−", "-")
    if form == "entier":
        return None if re.fullmatch(r"-?\d+", s) else "forme_non_entiere"
    if form == "decimal":
        return None if re.fullmatch(r"-?\d+([.,]\d+)?", s) else "forme_non_decimale"
    if form == "fraction_irreductible":
        m = re.fullmatch(r"(-?\d+)/(\d+)", s)
        if not m:
            return None if re.fullmatch(r"-?\d+", s) else "forme_non_fractionnaire"
        p, q = int(m.group(1)), int(m.group(2))
        if q == 0:
            return "denominateur_nul"
        return None if math.gcd(p, q) == 1 and q != 1 else "fraction_non_irreductible"
    expr = parse_math(raw)
    if form == "developpee":
        return None if sympy.expand(expr) == expr and "(" not in s else "forme_non_developpee"
    if form == "factorisee":
        return None if isinstance(expr, (sympy.Mul, sympy.Pow)) else "forme_non_factorisee"
    raise MathInputRejected("forme_inconnue")


def check_math_answer(expected: Any, answer: str, required_form: Optional[str] = None) -> CheckResult:
    """
    Compare une réponse à la réponse attendue.

    - « x = 3 » attendu : « 3 », « x=3 », « x = 6/2 » sont équivalents ; « y = 3 » est INVALID ;
    - solutions multiples : « x = 2 ou x = -2 » (ordre indifférent) ;
    - `required_form` : impose en plus une écriture (ex. fraction irréductible).
    """
    try:
        expected_txt = latex_to_plain(value_to_text(expected))
    except MathInputRejected as exc:
        return review(f"attendue_{exc}")
    if required_form is not None and required_form not in KNOWN_FORMS:
        return review("forme_inconnue")
    if not (answer or "").strip():
        return invalid("reponse_vide")
    answer = latex_to_plain(answer)
    try:
        sol_exp = [_split_equality(normalize_math(s)) for s in _solutions(expected_txt)]
    except MathInputRejected as exc:
        return review(f"attendue_{exc}")
    try:
        sol_ans = [_split_equality(normalize_math(s)) for s in _solutions(answer)]
    except MathInputRejected as exc:
        return review(str(exc))
    if not sol_exp:
        return review("attendue_vide")
    if len(sol_exp) != len(sol_ans):
        return invalid("nombre_de_solutions_different")

    remaining = list(sol_ans)
    for var_e, val_e in sol_exp:
        found = False
        for i, (var_a, val_a) in enumerate(remaining):
            if var_a is not None and var_e is not None and var_a.replace(" ", "") != var_e.replace(" ", ""):
                continue
            r = equivalent(val_e, val_a)
            if r.undecided:
                return r
            if r.ok:
                remaining.pop(i)
                found = True
                break
        if not found:
            return invalid("valeur_incorrecte")

    if required_form:
        for s in _solutions(answer):
            try:
                _, val = _split_equality(s)
                gap = _form_gap(val, required_form)
            except (MathInputRejected, UndefinedExpression) as exc:
                return review(str(exc))
            if gap:
                return invalid(gap)
    return valid("reponse_equivalente")


# --------------------------------------------------------------------------- #
# Recherche d'une valeur équivalente dans un texte rédigé (solution, étape finale)
# --------------------------------------------------------------------------- #
_SPLIT_WORDS = re.compile(r"[A-Za-zÀ-ÿ]{2,}")
_CHUNK_SEP = re.compile(r"[:;!?\n]|,\s|\.(?=\s|$)|≈|⇔|⟺|⇒|→|≤|≥|<|>")


def math_candidates(text: str) -> List[str]:
    """Fragments « mathématiques » d'un texte : blocs séparés par les mots français."""
    t = latex_to_plain(text or "")
    out: List[str] = []

    def keep(word_match: re.Match) -> str:
        w = word_match.group(0)
        return w if w in _FUNCTIONS else "\n"

    t = _SPLIT_WORDS.sub(keep, t)
    for chunk in _CHUNK_SEP.split(t):
        chunk = chunk.strip(" .\t")
        if not chunk or not re.search(r"[0-9a-zA-Zπ√]", chunk):
            continue
        parts = [p.strip() for p in chunk.split("=")]
        if len(parts) > 1:
            out.extend(p for p in parts if p)
            out.append(chunk)
        else:
            out.append(chunk)
        if len(out) >= MAX_CANDIDATES:
            break
    return out[:MAX_CANDIDATES]


def find_equivalent_in_text(expected: Any, text: str) -> bool:
    """Vrai si CHAQUE solution attendue a un équivalent symbolique prouvé dans le texte."""
    try:
        expected_txt = latex_to_plain(value_to_text(expected))
        sols = [_split_equality(normalize_math(s)) for s in _solutions(expected_txt)]
    except MathInputRejected:
        return False
    cands = math_candidates(text)
    if not sols or not cands:
        return False
    for _, val in sols:
        if not any(equivalent(val, c).verdict == Verdict.VALID for c in cands):
            return False
    return True
