"""
physics.py — Vérification déterministe des grandeurs physiques (Physique-Chimie, SVT, ES).

Adapté de app/curriculum/verifiers/physique.py (branche session6-production-hardening), autonome.

- analyse d'une grandeur « valeur + unité » en écriture scolaire française :
  « 3,0 × 10^8 m/s », « 3,0.10⁸ m·s⁻¹ », « 2,5e-3 kg », « 12 km/h », « 0,10 mol/L »,
  « $1{,}5 \\times 10^{-3}$ kg » (LaTeX simple), « 1 200 m » (séparateur de milliers) ;
- analyse dimensionnelle (7 dimensions SI) et conversion vers le SI ;
- pas de résultat sans unité lorsque l'unité est requise ;
- chiffres significatifs, notation scientifique (1 ≤ |a| < 10) ;
- homogénéité d'une formule (« E = m*c^2 » avec E en J, m en kg, c en m/s) ;
- unités annoncées par un énoncé (« … en m/s », « (en km) », « exprimer en joules ») ;
- table de bornes physiques plausibles (PHYSICAL_BOUNDS).

Toute unité inconnue ou écriture non analysable ⇒ NEEDS_HUMAN_REVIEW.
"""

from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

from pedagogy.checks.math_notation import latex_to_plain
from pedagogy.checks.verdict import CheckResult, invalid, review, valid

Dim = Tuple[int, int, int, int, int, int, int]  # L, M, T, I, Θ, N, J
DIMENSIONLESS: Dim = (0, 0, 0, 0, 0, 0, 0)


def dim(L=0, M=0, T=0, I=0, K=0, N=0, J=0) -> Dim:  # noqa: E741
    return (L, M, T, I, K, N, J)


class Unit(NamedTuple):
    factor: float  # vers le SI
    dim: Dim


_BASE: Dict[str, Unit] = {
    "m": Unit(1.0, dim(L=1)),
    "g": Unit(1e-3, dim(M=1)),
    "t": Unit(1e3, dim(M=1)),
    "s": Unit(1.0, dim(T=1)),
    "A": Unit(1.0, dim(I=1)),
    "K": Unit(1.0, dim(K=1)),
    "mol": Unit(1.0, dim(N=1)),
    "cd": Unit(1.0, dim(J=1)),
    "N": Unit(1.0, dim(L=1, M=1, T=-2)),
    "J": Unit(1.0, dim(L=2, M=1, T=-2)),
    "W": Unit(1.0, dim(L=2, M=1, T=-3)),
    "Wh": Unit(3600.0, dim(L=2, M=1, T=-2)),
    "Pa": Unit(1.0, dim(L=-1, M=1, T=-2)),
    "bar": Unit(1e5, dim(L=-1, M=1, T=-2)),
    "V": Unit(1.0, dim(L=2, M=1, T=-3, I=-1)),
    "Ω": Unit(1.0, dim(L=2, M=1, T=-3, I=-2)),
    "ohm": Unit(1.0, dim(L=2, M=1, T=-3, I=-2)),
    "C": Unit(1.0, dim(T=1, I=1)),
    "Hz": Unit(1.0, dim(T=-1)),
    "L": Unit(1e-3, dim(L=3)),
    "l": Unit(1e-3, dim(L=3)),
    "min": Unit(60.0, dim(T=1)),
    "h": Unit(3600.0, dim(T=1)),
    "eV": Unit(1.602176634e-19, dim(L=2, M=1, T=-2)),
    "°C": Unit(1.0, dim(K=1)),  # valeurs absolues : cf. to_si
    "%": Unit(1e-2, DIMENSIONLESS),
    "rad": Unit(1.0, DIMENSIONLESS),
}
_PREFIXES = {
    "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2,
    "m": 1e-3, "µ": 1e-6, "μ": 1e-6, "u": 1e-6, "n": 1e-9, "p": 1e-12,
}
_NO_PREFIX = {"min", "h", "°C", "bar", "%", "t", "rad"}
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")

# Noms d'unités en toutes lettres (énoncés : « exprimer en joules »).
UNIT_NAMES: Dict[str, str] = {
    "metre": "m", "metres": "m", "mètre": "m", "mètres": "m", "kilometre": "km", "kilomètre": "km",
    "kilometres": "km", "kilomètres": "km", "centimetre": "cm", "centimètre": "cm", "centimètres": "cm",
    "millimetre": "mm", "millimètre": "mm", "millimètres": "mm",
    "seconde": "s", "secondes": "s", "minute": "min", "minutes": "min", "heure": "h", "heures": "h",
    "gramme": "g", "grammes": "g", "kilogramme": "kg", "kilogrammes": "kg", "tonne": "t", "tonnes": "t",
    "joule": "J", "joules": "J", "kilojoule": "kJ", "kilojoules": "kJ", "newton": "N", "newtons": "N",
    "watt": "W", "watts": "W", "volt": "V", "volts": "V", "ampere": "A", "ampère": "A", "amperes": "A",
    "ampères": "A", "ohms": "Ω", "pascal": "Pa", "pascals": "Pa", "hertz": "Hz", "litre": "L", "litres": "L",
    "millilitre": "mL", "millilitres": "mL", "kelvin": "K", "kelvins": "K", "mole": "mol", "moles": "mol",
    "coulomb": "C", "coulombs": "C",
}


class QuantityError(ValueError):
    pass


def _atomic_unit(token: str) -> Unit:
    m = re.fullmatch(r"(°C|%|[A-Za-zµμΩ]+)\^?(-?\d+)?", token)
    if not m:
        raise QuantityError(f"unite_inconnue:{token}")
    sym, exp = m.group(1), int(m.group(2) or 1)
    if abs(exp) > 6:
        raise QuantityError(f"exposant_d_unite_hors_bornes:{token}")
    if sym in _BASE:
        u = _BASE[sym]
    else:
        u = None
        for pre in sorted(_PREFIXES, key=len, reverse=True):
            rest = sym[len(pre):]
            if sym.startswith(pre) and rest in _BASE and rest not in _NO_PREFIX:
                base = _BASE[rest]
                u = Unit(_PREFIXES[pre] * base.factor, base.dim)
                break
        if u is None:
            raise QuantityError(f"unite_inconnue:{sym}")
    return Unit(u.factor ** exp, tuple(x * exp for x in u.dim))  # type: ignore[arg-type]


def parse_unit(text: str) -> Unit:
    """« m/s », « m.s-1 », « kg·m^-2 », « mol/L », « N.m », « km/h » → Unit."""
    t = latex_to_plain(text or "").strip().translate(_SUPERSCRIPTS)
    t = t.replace("·", ".").replace("*", ".").replace("⋅", ".").replace("(", "").replace(")", "")
    if not t:
        return Unit(1.0, DIMENSIONLESS)
    if len(t) > 40:
        raise QuantityError("unite_trop_longue")
    if t.lower() in UNIT_NAMES:
        t = UNIT_NAMES[t.lower()]
    factor, d = 1.0, [0] * 7
    for i, block in enumerate(t.split("/")):
        sign = 1 if i == 0 else -1
        for tok in [x for x in re.split(r"[.\s]+", block) if x]:
            u = _atomic_unit(tok)
            factor *= u.factor ** sign
            d = [a + sign * b for a, b in zip(d, u.dim)]
    return Unit(factor, tuple(d))  # type: ignore[arg-type]


class Quantity(NamedTuple):
    value: float
    mantissa: str
    exponent10: int
    unit_text: str
    unit: Unit
    scientific: bool


_NUMBER = re.compile(
    r"^\s*(?P<mant>[-+]?\d+(?:[.,]\d+)?)"
    r"(?:\s*(?:[×x*·.]\s*10\s*\^?\s*\(?(?P<e1>[-+]?\d+)\)?)|(?:[eE](?P<e2>[-+]?\d+)))?"
    r"\s*(?P<unit>.*)$"
)


def clean_quantity_text(text: str) -> str:
    t = latex_to_plain(text or "").strip().translate(_SUPERSCRIPTS)
    t = t.replace("−", "-").replace(" ", " ").replace(" ", " ")
    t = re.sub(r"(?<=\d)\s(?=\d{3}(?!\d))", "", t)  # 1 200 → 1200
    t = re.sub(r"(\d)\(,\)(\d)", r"\1,\2", t)          # 1{,}5 (LaTeX) → 1,5
    return t


def parse_quantity(text: str) -> Quantity:
    t = clean_quantity_text(text)
    if not t:
        raise QuantityError("grandeur_vide")
    if len(t) > 100:
        raise QuantityError("grandeur_trop_longue")
    m = _NUMBER.match(t)
    if not m:
        raise QuantityError("nombre_illisible")
    mant = m.group("mant")
    e = m.group("e1") or m.group("e2")
    exp = int(e) if e else 0
    if abs(exp) > 60:
        raise QuantityError("exposant_hors_bornes")
    value = float(mant.replace(",", ".")) * 10 ** exp
    unit_txt = m.group("unit").strip()
    return Quantity(value, mant, exp, unit_txt, parse_unit(unit_txt), e is not None)


def significant_figures(mantissa: str) -> int:
    digits = re.sub(r"[^\d]", "", mantissa.lstrip("+-"))
    return max(len(digits.lstrip("0")), 1)


def significant_figures_ambiguous(mantissa: str) -> bool:
    """« 1200 » : 2, 3 ou 4 chiffres significatifs selon l'intention ⇒ ambigu."""
    m = mantissa.lstrip("+-")
    return "," not in m and "." not in m and len(m.lstrip("0")) > 1 and m.endswith("0")


def to_si(q: Quantity) -> float:
    if q.unit_text == "°C":
        return q.value + 273.15
    return q.value * q.unit.factor


def check_quantity(
    expected: str,
    answer: str,
    *,
    unit_required: bool = True,
    tolerance_relative: float = 0.01,
    required_sig_figs: Optional[int] = None,
    scientific_notation: bool = False,
    unit_imposed: bool = False,
) -> CheckResult:
    """
    Une valeur numérique seule ne valide JAMAIS une grandeur dimensionnée : la dimension est
    comparée même si `unit_required=False`. `unit_imposed` : la réponse doit être exprimée
    dans l'unité de l'attendu (« exprimer en m/s »), pas seulement dans une unité équivalente.
    """
    if not (0 <= tolerance_relative <= 0.5):
        return review("tolerance_hors_bornes")
    tol = max(tolerance_relative, 1e-9)
    try:
        qe = parse_quantity(expected)
    except QuantityError as exc:
        return review(f"attendue_{exc}")
    if not (answer or "").strip():
        return invalid("reponse_vide")
    try:
        qa = parse_quantity(answer)
    except QuantityError as exc:
        return review(str(exc))

    if unit_required and qe.unit_text and not qa.unit_text:
        return invalid("unite_manquante")
    if qe.unit.dim != qa.unit.dim:
        return invalid("dimension_incorrecte")
    if unit_imposed and (abs(qe.unit.factor - qa.unit.factor) > 1e-12 * abs(qe.unit.factor)
                         or (qe.unit_text == "°C") != (qa.unit_text == "°C")):
        return invalid("unite_imposee_non_respectee")

    ve, va = to_si(qe), to_si(qa)
    if ve == 0:
        if abs(va) > 1e-12:
            return invalid("valeur_incorrecte")
    elif abs(va - ve) / abs(ve) > tol:
        return invalid("valeur_incorrecte")

    if required_sig_figs is not None and significant_figures(qa.mantissa) != required_sig_figs:
        if significant_figures_ambiguous(qa.mantissa) and \
                significant_figures(qa.mantissa.rstrip("0") or "0") <= required_sig_figs \
                < significant_figures(qa.mantissa):
            return review("chiffres_significatifs_ambigus")
        return invalid("chiffres_significatifs")
    if scientific_notation:
        a = abs(float(qa.mantissa.replace(",", ".")))
        if not qa.scientific or not (1 <= a < 10):
            return invalid("notation_scientifique_attendue")
    return valid("grandeur_correcte")


def format_significant(value: float, n: int) -> str:
    """Écrit `value` avec exactement n chiffres significatifs (virgule décimale française)."""
    if value == 0:
        return "0" if n == 1 else "0," + "0" * (n - 1)
    s = f"{value:.{n - 1}e}"
    mant, exp = s.split("e")
    e = int(exp)
    if -3 <= e < n:
        dec = max(n - 1 - e, 0)
        return f"{value:.{dec}f}".replace(".", ",")
    return f"{mant.replace('.', ',')} × 10^{e}"


# --------------------------------------------------------------------------- #
# Recherche d'une grandeur équivalente dans un texte
# --------------------------------------------------------------------------- #
_NUM_IN_TEXT = re.compile(
    r"(?<![\w.,])[-+]?\d+(?:[.,]\d+)?(?:\s*(?:[×x*·]\s*10\s*\^?\s*\(?[-+]?\d+\)?|[eE][-+]?\d+))?"
)


def find_quantity_in_text(expected: str, text: str, tolerance_relative: float = 0.01) -> bool:
    try:
        qe = parse_quantity(expected)
    except QuantityError:
        return False
    t = clean_quantity_text(text)
    for m in list(_NUM_IN_TEXT.finditer(t))[:80]:
        num = m.group(0)
        rest = t[m.end():].lstrip()
        toks = re.split(r"\s+", rest, maxsplit=2)[:2]
        first = toks[0].rstrip(".,;:!?)") if toks and toks[0] else ""
        candidates = [num + " " + first] if first else []
        if len(toks) > 1:
            candidates.append(num + " " + first + " " + toks[1].rstrip(".,;:!?)"))
        for c in candidates:
            if check_quantity(expected, c, tolerance_relative=tolerance_relative).ok:
                return True
        try:  # nombre seul exprimé dans l'unité de l'attendu
            v = float(re.sub(r"\s", "", num).replace(",", ".").replace("×10^", "e").replace("×10", "e")
                      .replace("x10^", "e").replace("*10^", "e").replace("·10^", "e"))
        except ValueError:
            continue
        ref = qe.value
        if (ref == 0 and abs(v) < 1e-12) or (ref != 0 and abs(v - ref) / abs(ref) <= max(tolerance_relative, 1e-9)):
            return True
    return False


# --------------------------------------------------------------------------- #
# Unités annoncées par un énoncé
# --------------------------------------------------------------------------- #
_UNIT_TOKEN = r"(?P<u>°C|[A-Za-zµμΩÀ-ÿ][A-Za-zµμΩÀ-ÿ0-9/.·⋅⁻¹²³\-^]*)(?![’'A-Za-zÀ-ÿ])"
_EN_UNIT = re.compile(r"(?<![A-Za-zÀ-ÿ])en\s+(?:unité\s+)?" + _UNIT_TOKEN)
_STOP_WORDS = frozenset({"a", "cas", "ce", "ces", "un", "une", "le", "la", "les", "des", "du", "de"})


def units_implied_by_text(text: str, *, ignore_single_capitals: bool = False) -> List[Tuple[str, Unit]]:
    """Unités demandées dans un énoncé : « … en m/s », « (en km) », « exprimer en joules ».

    `ignore_single_capitals` : en géométrie, « se coupent en A » désigne un point, pas des ampères.
    """
    out: List[Tuple[str, Unit]] = []
    for m in _EN_UNIT.finditer(latex_to_plain(text or "")):
        tok = m.group("u").rstrip(".,;:!?)")
        if not tok or tok.lower() in _STOP_WORDS:
            continue
        if ignore_single_capitals and re.fullmatch(r"[A-Z]", tok):
            continue
        try:
            out.append((tok, parse_unit(tok)))
        except QuantityError:
            continue
    return out


# --------------------------------------------------------------------------- #
# Bornes physiques plausibles
# --------------------------------------------------------------------------- #
SPEED_OF_LIGHT = 299_792_458.0


class PhysicalBound(NamedTuple):
    name: str
    dim: Dim
    min_si: Optional[float]
    max_si: Optional[float]
    min_strict: bool = False
    use_abs: bool = False
    keyword: Optional[str] = None  # regex : borne appliquée seulement si l'énoncé l'évoque


PHYSICAL_BOUNDS: Tuple[PhysicalBound, ...] = (
    PhysicalBound("vitesse_<=_c", dim(L=1, T=-1), None, SPEED_OF_LIGHT, use_abs=True),
    PhysicalBound("temperature_absolue_>=_0K", dim(K=1), 0.0, None),
    PhysicalBound("masse_>_0", dim(M=1), 0.0, None, min_strict=True),
    PhysicalBound("concentration_molaire_>=_0", dim(L=-3, N=1), 0.0, None),
    PhysicalBound("concentration_massique_>=_0", dim(L=-3, M=1), 0.0, None),
    PhysicalBound("quantite_de_matiere_>=_0", dim(N=1), 0.0, None),
    PhysicalBound("duree_>=_0", dim(T=1), 0.0, None, keyword=r"(?i)\b(dur[ée]e|temps de parcours)\b"),
    PhysicalBound("rendement_dans_[0,1]", DIMENSIONLESS, 0.0, 1.0, keyword=r"(?i)\brendement\b"),
    PhysicalBound("pH_dans_[0,14]_solution_aqueuse_diluee", DIMENSIONLESS, 0.0, 14.0, keyword=r"\bpH\b"),
)


def physical_bound_violations(value_si: float, d: Dim, context: str = "") -> List[str]:
    out: List[str] = []
    for b in PHYSICAL_BOUNDS:
        if b.dim != d:
            continue
        if b.keyword and not re.search(b.keyword, context or ""):
            continue
        v = abs(value_si) if b.use_abs else value_si
        if b.min_si is not None and (v < b.min_si or (b.min_strict and v <= b.min_si)):
            out.append(b.name)
        elif b.max_si is not None and v > b.max_si:
            out.append(b.name)
    return out


def check_physical_plausibility(quantity_text: str, context: str = "") -> List[str]:
    """Bornes violées par une grandeur écrite (liste vide si plausible ou non analysable)."""
    try:
        q = parse_quantity(quantity_text)
    except QuantityError:
        return []
    return physical_bound_violations(to_si(q), q.unit.dim, context)


# --------------------------------------------------------------------------- #
# Homogénéité d'une formule
# --------------------------------------------------------------------------- #
_VAR_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,7}")
_DIMLESS_FUNCS = {"sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
                  "exp": sympy.exp, "ln": sympy.log, "log": sympy.log, "sqrt": sympy.sqrt}


class NotHomogeneous(ValueError):
    pass


def _dim_expr(e: sympy.Expr, dims: Dict[sympy.Symbol, Dim]) -> Dim:
    if e.is_Number or e in (sympy.pi, sympy.E):
        return DIMENSIONLESS
    if isinstance(e, sympy.Symbol):
        return dims[e]
    if isinstance(e, sympy.Add):
        ds = {_dim_expr(a, dims) for a in e.args}
        if len(ds) != 1:
            raise NotHomogeneous("somme_non_homogene")
        return ds.pop()
    if isinstance(e, sympy.Mul):
        tot = [0] * 7
        for a in e.args:
            tot = [x + y for x, y in zip(tot, _dim_expr(a, dims))]
        return tuple(tot)  # type: ignore[return-value]
    if isinstance(e, sympy.Pow):
        base, exp = e.args
        if _dim_expr(exp, dims) != DIMENSIONLESS or not exp.is_Rational:
            if _dim_expr(base, dims) == DIMENSIONLESS:
                return DIMENSIONLESS
            raise NotHomogeneous("exposant_non_rationnel")
        if abs(exp) > 12:
            raise NotHomogeneous("exposant_hors_bornes")
        db = _dim_expr(base, dims)
        prod = [x * exp for x in db]
        if any(not sympy.Rational(p).is_integer for p in prod):
            raise NotHomogeneous("dimension_fractionnaire")
        return tuple(int(p) for p in prod)  # type: ignore[return-value]
    if isinstance(e, sympy.Function):
        for a in e.args:
            if _dim_expr(a, dims) != DIMENSIONLESS:
                raise NotHomogeneous("argument_de_fonction_dimensionne")
        return DIMENSIONLESS
    raise NotHomogeneous("expression_non_supportee")


def check_homogeneity(formula: str, variable_units: Dict[str, str]) -> CheckResult:
    """
    Vérifie qu'une formule « A = expr » est homogène.
    `variable_units` : {"E": "J", "m": "kg", "c": "m/s"} — tout symbole doit être déclaré.
    """
    if len(formula) > 200 or "__" in formula or formula.count("=") != 1:
        return review("formule_refusee")
    if not re.fullmatch(r"[A-Za-z0-9_+\-*/^().=\s]+", formula):
        return review("caractere_non_autorise")
    if re.search(r"\.\s*[A-Za-z_(]", formula):
        return review("acces_attribut_interdit")
    names = set(_VAR_NAME.findall(formula)) - set(_DIMLESS_FUNCS) - {"pi"}
    unknown = names - set(variable_units)
    if unknown:
        return review("variable_non_declaree:" + ",".join(sorted(unknown)))
    if any(not _VAR_NAME.fullmatch(n) for n in variable_units):
        return review("nom_de_variable_invalide")
    try:
        dims = {sympy.Symbol(n): parse_unit(u).dim for n, u in variable_units.items()}
    except QuantityError as exc:
        return review(str(exc))
    loc: Dict[str, object] = {n: sympy.Symbol(n) for n in variable_units}
    loc.update(_DIMLESS_FUNCS)
    loc["pi"] = sympy.pi
    glob = {"__builtins__": {}, "Integer": sympy.Integer, "Float": sympy.Float,
            "Rational": sympy.Rational, "Symbol": sympy.Symbol,
            "Mul": sympy.Mul, "Add": sympy.Add, "Pow": sympy.Pow}
    left, right = formula.split("=")
    try:
        el = parse_expr(left, local_dict=dict(loc), global_dict=dict(glob),
                        transformations=standard_transformations + (convert_xor,), evaluate=False)
        er = parse_expr(right, local_dict=dict(loc), global_dict=dict(glob),
                        transformations=standard_transformations + (convert_xor,), evaluate=False)
        if _dim_expr(el, dims) != _dim_expr(er, dims):
            return invalid("membres_de_dimensions_differentes")
    except NotHomogeneous as exc:
        return invalid(str(exc))
    except Exception:  # noqa: BLE001
        return review("formule_illisible")
    return valid("formule_homogene")
