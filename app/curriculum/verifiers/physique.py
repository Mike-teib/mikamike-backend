"""
physique.py — Vérification déterministe des grandeurs physiques (Physique-Chimie).

- analyse d'une grandeur « valeur + unité » en écriture scolaire française :
  « 3,0 × 10^8 m/s », « 3,0.10⁸ m·s⁻¹ », « 2,5e-3 kg », « 12 km/h », « 0,10 mol/L » ;
- analyse dimensionnelle (7 dimensions SI) et conversion vers le SI ;
- pas de résultat sans unité lorsque l'unité est requise ;
- chiffres significatifs, notation scientifique (1 ≤ |a| < 10) ;
- homogénéité d'une formule (« E = m*c^2 » avec E en J, m en kg, c en m/s).

Toute unité inconnue ou écriture non analysable ⇒ NEEDS_HUMAN_REVIEW.
"""

from __future__ import annotations

import re
from typing import Dict, NamedTuple, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide

Dim = Tuple[int, int, int, int, int, int, int]  # L, M, T, I, Θ, N, J
SANS_DIMENSION: Dim = (0, 0, 0, 0, 0, 0, 0)


def _d(L=0, M=0, T=0, I=0, K=0, N=0, J=0) -> Dim:  # noqa: E741
    return (L, M, T, I, K, N, J)


class Unite(NamedTuple):
    facteur: float  # vers le SI
    dim: Dim


_BASE: Dict[str, Unite] = {
    "m": Unite(1.0, _d(L=1)),
    "g": Unite(1e-3, _d(M=1)),
    "s": Unite(1.0, _d(T=1)),
    "A": Unite(1.0, _d(I=1)),
    "K": Unite(1.0, _d(K=1)),
    "mol": Unite(1.0, _d(N=1)),
    "cd": Unite(1.0, _d(J=1)),
    "N": Unite(1.0, _d(L=1, M=1, T=-2)),
    "J": Unite(1.0, _d(L=2, M=1, T=-2)),
    "W": Unite(1.0, _d(L=2, M=1, T=-3)),
    "Wh": Unite(3600.0, _d(L=2, M=1, T=-2)),
    "Pa": Unite(1.0, _d(L=-1, M=1, T=-2)),
    "bar": Unite(1e5, _d(L=-1, M=1, T=-2)),
    "V": Unite(1.0, _d(L=2, M=1, T=-3, I=-1)),
    "Ω": Unite(1.0, _d(L=2, M=1, T=-3, I=-2)),
    "ohm": Unite(1.0, _d(L=2, M=1, T=-3, I=-2)),
    "C": Unite(1.0, _d(T=1, I=1)),
    "Hz": Unite(1.0, _d(T=-1)),
    "L": Unite(1e-3, _d(L=3)),
    "l": Unite(1e-3, _d(L=3)),
    "min": Unite(60.0, _d(T=1)),
    "h": Unite(3600.0, _d(T=1)),
    "eV": Unite(1.602176634e-19, _d(L=2, M=1, T=-2)),
    "°C": Unite(1.0, _d(K=1)),  # écart de température ; valeurs absolues : cf. _vers_si
}
_PREFIXES = {
    "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1, "d": 1e-1, "c": 1e-2,
    "m": 1e-3, "µ": 1e-6, "μ": 1e-6, "u": 1e-6, "n": 1e-9, "p": 1e-12,
}
_SANS_PREFIXE = {"min", "h", "°C", "bar", "L", "l"}  # évite « mh », « kbar »… improbables
_EXPOSANTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


class GrandeurInvalide(ValueError):
    pass


def _unite_atomique(token: str) -> Unite:
    m = re.fullmatch(r"(°C|[A-Za-zµμΩ]+)\^?(-?\d+)?", token)
    if not m:
        raise GrandeurInvalide(f"unite_inconnue:{token}")
    sym, exp = m.group(1), int(m.group(2) or 1)
    if sym in _BASE:
        u = _BASE[sym]
    else:
        u = None
        for pre in sorted(_PREFIXES, key=len, reverse=True):
            reste = sym[len(pre):]
            if sym.startswith(pre) and reste in _BASE and reste not in _SANS_PREFIXE:
                base = _BASE[reste]
                u = Unite(_PREFIXES[pre] * base.facteur, base.dim)
                break
        if u is None:
            raise GrandeurInvalide(f"unite_inconnue:{sym}")
    return Unite(u.facteur ** exp, tuple(x * exp for x in u.dim))  # type: ignore[arg-type]


def analyser_unite(texte: str) -> Unite:
    """« m/s », « m.s-1 », « kg·m^-2 », « mol/L », « N.m », « km/h » → Unite."""
    t = texte.strip().translate(_EXPOSANTS).replace("·", ".").replace("*", ".").replace("⋅", ".")
    if not t:
        return Unite(1.0, SANS_DIMENSION)
    facteur, dim = 1.0, [0] * 7
    for i, bloc in enumerate(t.split("/")):
        signe = 1 if i == 0 else -1
        for tok in [x for x in re.split(r"[.\s]+", bloc) if x]:
            u = _unite_atomique(tok)
            facteur *= u.facteur ** signe
            dim = [a + signe * b for a, b in zip(dim, u.dim)]
    return Unite(facteur, tuple(dim))  # type: ignore[arg-type]


class Grandeur(NamedTuple):
    valeur: float
    mantisse: str
    exposant10: int
    unite_texte: str
    unite: Unite
    scientifique: bool


_NOMBRE = re.compile(
    r"^\s*(?P<mant>[-+−]?\d+(?:[.,]\d+)?)"
    r"(?:\s*(?:[×x*·.]\s*10\s*\^?\s*(?P<e1>[-+−]?\d+))|(?:[eE](?P<e2>[-+−]?\d+)))?"
    r"\s*(?P<unite>.*)$"
)


def analyser_grandeur(texte: str) -> Grandeur:
    t = (texte or "").strip().translate(_EXPOSANTS).replace("−", "-")
    if not t:
        raise GrandeurInvalide("grandeur_vide")
    if len(t) > 100:
        raise GrandeurInvalide("grandeur_trop_longue")
    m = _NOMBRE.match(t)
    if not m:
        raise GrandeurInvalide("nombre_illisible")
    mant = m.group("mant").replace("−", "-")
    e = m.group("e1") or m.group("e2")
    exp = int(e.replace("−", "-")) if e else 0
    if abs(exp) > 60:
        raise GrandeurInvalide("exposant_hors_bornes")
    valeur = float(mant.replace(",", ".")) * 10 ** exp
    unite_txt = m.group("unite").strip()
    return Grandeur(valeur, mant, exp, unite_txt, analyser_unite(unite_txt), e is not None)


def chiffres_significatifs(mantisse: str) -> int:
    chiffres = re.sub(r"[^\d]", "", mantisse.lstrip("+-−"))
    return max(len(chiffres.lstrip("0")), 1)


def _vers_si(g: Grandeur) -> float:
    if g.unite_texte == "°C":
        return g.valeur + 273.15
    return g.valeur * g.unite.facteur


def verifier_grandeur(
    attendue: str,
    reponse: str,
    *,
    unite_requise: bool = True,
    tolerance_relative: float = 0.01,
    chiffres_significatifs_requis: Optional[int] = None,
    notation_scientifique: bool = False,
) -> Resultat:
    try:
        ga = analyser_grandeur(attendue)
    except GrandeurInvalide as exc:
        return revue(f"attendue_{exc}")
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    try:
        gr = analyser_grandeur(reponse)
    except GrandeurInvalide as exc:
        return revue(str(exc))

    if unite_requise and ga.unite_texte and not gr.unite_texte:
        return invalide("unite_manquante")
    if ga.unite.dim != gr.unite.dim:
        return invalide("dimension_incorrecte")

    va, vr = _vers_si(ga), _vers_si(gr)
    if va == 0:
        if abs(vr) > 1e-12:
            return invalide("valeur_incorrecte")
    elif abs(vr - va) / abs(va) > tolerance_relative:
        return invalide("valeur_incorrecte")

    if chiffres_significatifs_requis is not None and \
            chiffres_significatifs(gr.mantisse) != chiffres_significatifs_requis:
        return invalide("chiffres_significatifs")
    if notation_scientifique:
        a = abs(float(gr.mantisse.replace(",", ".")))
        if not gr.scientifique or not (1 <= a < 10):
            return invalide("notation_scientifique_attendue")
    return valide("grandeur_correcte")


# --------------------------------------------------------------------------- #
# Homogénéité d'une formule
# --------------------------------------------------------------------------- #
_NOM_VAR = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,7}")
_FONCTIONS_SANS_DIM = {"sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
                       "exp": sympy.exp, "ln": sympy.log, "log": sympy.log, "sqrt": sympy.sqrt}


class NonHomogene(ValueError):
    pass


def _dim_expr(e: sympy.Expr, dims: Dict[sympy.Symbol, Dim]) -> Dim:
    if e.is_Number or e in (sympy.pi, sympy.E):
        return SANS_DIMENSION
    if isinstance(e, sympy.Symbol):
        return dims[e]
    if isinstance(e, sympy.Add):
        ds = {_dim_expr(a, dims) for a in e.args}
        if len(ds) != 1:
            raise NonHomogene("somme_non_homogene")
        return ds.pop()
    if isinstance(e, sympy.Mul):
        tot = [0] * 7
        for a in e.args:
            tot = [x + y for x, y in zip(tot, _dim_expr(a, dims))]
        return tuple(tot)  # type: ignore[return-value]
    if isinstance(e, sympy.Pow):
        base, exp = e.args
        if _dim_expr(exp, dims) != SANS_DIMENSION or not exp.is_Rational:
            if _dim_expr(base, dims) == SANS_DIMENSION:
                return SANS_DIMENSION
            raise NonHomogene("exposant_non_rationnel")
        db = _dim_expr(base, dims)
        prod = [x * exp for x in db]
        if any(not sympy.Rational(p).is_integer for p in prod):
            raise NonHomogene("dimension_fractionnaire")
        return tuple(int(p) for p in prod)  # type: ignore[return-value]
    if isinstance(e, sympy.Function):
        for a in e.args:
            if _dim_expr(a, dims) != SANS_DIMENSION:
                raise NonHomogene("argument_de_fonction_dimensionne")
        return SANS_DIMENSION
    raise NonHomogene("expression_non_supportee")


def verifier_homogeneite(formule: str, unites_variables: Dict[str, str]) -> Resultat:
    """
    Vérifie qu'une formule « A = expr » est homogène.
    `unites_variables` : {"E": "J", "m": "kg", "c": "m/s"} — tout symbole doit être déclaré.
    """
    if len(formule) > 200 or "__" in formule or formule.count("=") != 1:
        return revue("formule_refusee")
    if not re.fullmatch(r"[A-Za-z0-9_+\-*/^().=\s]+", formule):
        return revue("caractere_non_autorise")
    noms = set(_NOM_VAR.findall(formule)) - set(_FONCTIONS_SANS_DIM) - {"pi"}
    inconnus = noms - set(unites_variables)
    if inconnus:
        return revue("variable_non_declaree:" + ",".join(sorted(inconnus)))
    try:
        dims = {sympy.Symbol(n): analyser_unite(u).dim for n, u in unites_variables.items()}
    except GrandeurInvalide as exc:
        return revue(str(exc))
    loc = {n: sympy.Symbol(n) for n in unites_variables}
    loc.update(_FONCTIONS_SANS_DIM)
    loc["pi"] = sympy.pi
    glob = {"__builtins__": {}, "Integer": sympy.Integer, "Float": sympy.Float,
            "Rational": sympy.Rational, "Symbol": sympy.Symbol,
            "Mul": sympy.Mul, "Add": sympy.Add, "Pow": sympy.Pow}
    gauche, droite = formule.split("=")
    try:
        eg = parse_expr(gauche, local_dict=loc, global_dict=glob,
                        transformations=standard_transformations + (convert_xor,), evaluate=False)
        ed = parse_expr(droite, local_dict=loc, global_dict=glob,
                        transformations=standard_transformations + (convert_xor,), evaluate=False)
        if _dim_expr(eg, dims) != _dim_expr(ed, dims):
            return invalide("membres_de_dimensions_differentes")
    except NonHomogene as exc:
        return invalide(str(exc))
    except Exception:
        return revue("formule_illisible")
    return valide("formule_homogene")
