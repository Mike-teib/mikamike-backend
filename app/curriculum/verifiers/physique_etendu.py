"""
physique_etendu.py — Validateurs Physique-Chimie complémentaires (lot 14, session 4).

- incertitudes : « (3,02 ± 0,05) m », « 3,02 ± 0,05 m », « (2,998 ± 0,004) × 10^8 m/s » ;
  incertitude écrite avec 1 ou 2 chiffres significatifs, valeur arrondie à la même décimale ;
- ordre de grandeur : « 10^8 m/s » ; zone où les conventions scolaires divergent
  (mantisse entre √10 et 5) ⇒ NEEDS_HUMAN_REVIEW ;
- conversions : la réponse doit être exprimée dans l'unité CIBLE (pas seulement équivalente) ;
- constantes : table fermée (valeurs exactes du SI 2019 ou valeurs conventionnelles déclarées).

Règle commune : une valeur numérique seule ne valide jamais une grandeur dimensionnée.
Toute écriture non analysable ⇒ NEEDS_HUMAN_REVIEW. Calcul décimal exact (pas de flottant
pour les arrondis).
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Dict, NamedTuple, Optional, Tuple

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide
from app.curriculum.verifiers.physique import (
    SANS_DIMENSION,
    GrandeurInvalide,
    Unite,
    analyser_grandeur,
    analyser_unite,
    chiffres_significatifs,
)

_EXPOSANTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_NB = r"[-+]?\d+(?:[.,]\d+)?"
_PUISS = r"(?:\s*[×x*·.]\s*10\s*\^?\s*(?P<exp>[-+]?\d+))?"
_INCERTITUDE = [
    re.compile(rf"^\(\s*(?P<x>{_NB})\s*(?:±|\+/-|\+-)\s*(?P<u>{_NB})\s*\){_PUISS}\s*(?P<unite>.*)$"),
    # Sans parenthèses, « x ± u × 10^n » est ambigu (la puissance porte-t-elle sur x ?) ⇒ non accepté.
    re.compile(rf"^(?P<x>{_NB})\s*(?:±|\+/-|\+-)\s*(?P<u>{_NB})\s*(?P<unite>.*)$"),
]
LONGUEUR_MAX = 120


def _normaliser(t: str) -> str:
    return (t or "").strip().translate(_EXPOSANTS).replace("−", "-")


def _dec(t: str) -> Decimal:
    return Decimal(t.replace(",", "."))


def _decimales(t: str) -> int:
    t = t.replace(",", ".")
    return len(t.split(".")[1]) if "." in t else 0


class Mesure(NamedTuple):
    x: Decimal          # dans l'unité et la puissance de 10 écrites
    u: Decimal
    x_txt: str
    u_txt: str
    exposant10: int
    unite_texte: str
    unite: Unite


def analyser_mesure(texte: str) -> Mesure:
    t = _normaliser(texte)
    if not t:
        raise GrandeurInvalide("mesure_vide")
    if len(t) > LONGUEUR_MAX:
        raise GrandeurInvalide("mesure_trop_longue")
    for motif in _INCERTITUDE:
        m = motif.match(t)
        if m:
            break
    else:
        raise GrandeurInvalide("ecriture_incertitude_illisible")
    exp = int(m.groupdict().get("exp") or 0)
    if abs(exp) > 60:
        raise GrandeurInvalide("exposant_hors_bornes")
    unite_txt = m.group("unite").strip()
    if unite_txt == "°C":
        raise GrandeurInvalide("temperature_celsius_non_supportee")
    return Mesure(_dec(m.group("x")), _dec(m.group("u")), m.group("x"), m.group("u"), exp,
                  unite_txt, analyser_unite(unite_txt))


def _si(v: Decimal, exp: int, unite: Unite) -> Decimal:
    return v * (Decimal(10) ** exp) * Decimal(repr(unite.facteur))


def _arrondi_cs(v: Decimal, cs: int, mode) -> Decimal:
    if v == 0:
        return v
    pos = v.adjusted() - cs + 1  # exposant du dernier chiffre conservé
    return v.quantize(Decimal(1).scaleb(pos), rounding=mode)


def verifier_incertitude(attendue: str, reponse: str) -> Resultat:
    """
    `attendue` : « x ± u unité » (valeurs de référence, u non arrondie acceptée).
    Réponse VALIDE si : unité présente et de même dimension ; u > 0 écrite avec 1 ou 2 chiffres
    significatifs et égale à u de référence arrondie (au plus proche OU par excès, les deux
    conventions scolaires) ; x écrit avec la même décimale que u et égal à x de référence
    arrondi à cette décimale.
    """
    try:
        ma = analyser_mesure(attendue)
    except (GrandeurInvalide, InvalidOperation) as exc:
        return revue(f"attendue_{exc}")
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    try:
        mr = analyser_mesure(reponse)
    except GrandeurInvalide as exc:
        # Valeur sans incertitude (« 3,02 m ») : lisible mais incomplète.
        try:
            analyser_grandeur(reponse)
            return invalide("incertitude_manquante")
        except GrandeurInvalide:
            return revue(str(exc))
    except InvalidOperation:
        return revue("nombre_illisible")
    if ma.u <= 0:
        return revue("attendue_incertitude_non_positive")
    if ma.unite.dim != SANS_DIMENSION and not mr.unite_texte:
        return invalide("unite_manquante")
    if ma.unite.dim != mr.unite.dim:
        return invalide("dimension_incorrecte")
    if mr.u <= 0:
        return invalide("incertitude_non_positive")
    cs_u = chiffres_significatifs(mr.u_txt)
    if cs_u > 2:
        return invalide("incertitude_trop_de_chiffres_significatifs")
    if _decimales(mr.x_txt) != _decimales(mr.u_txt):
        return invalide("valeur_et_incertitude_incoherentes")

    # Tout est ramené dans l'écriture de la RÉPONSE (même unité, même puissance de 10).
    echelle_rep = _si(Decimal(1), mr.exposant10, mr.unite)
    u_ref = _si(ma.u, ma.exposant10, ma.unite) / echelle_rep
    x_ref = _si(ma.x, ma.exposant10, ma.unite) / echelle_rep
    admises = {_arrondi_cs(u_ref, cs_u, ROUND_HALF_UP), _arrondi_cs(u_ref, cs_u, ROUND_CEILING)}
    if mr.u not in admises:
        return invalide("incertitude_incorrecte")
    pas = Decimal(1).scaleb(-_decimales(mr.u_txt))
    if mr.x != x_ref.quantize(pas, rounding=ROUND_HALF_UP):
        return invalide("valeur_incorrecte")
    return valide("mesure_correcte")


# --------------------------------------------------------------------------- #
# Ordre de grandeur
# --------------------------------------------------------------------------- #
_ODG = re.compile(r"^(?:1\s*[×x*·.]\s*)?10\s*\^?\s*(?P<e1>[-+]?\d+)\s*(?P<u1>.*)$|^1?[eE](?P<e2>[-+]?\d+)\s*(?P<u2>.*)$")
_RACINE_10 = math.sqrt(10)


def verifier_ordre_de_grandeur(attendue: str, reponse: str) -> Resultat:
    """
    `attendue` : grandeur (« 3,0e8 m/s ») ; `reponse` : puissance de dix (« 10^8 m/s »).
    Mantisse a de l'attendue (dans l'unité de la réponse) : a < √10 ⇒ 10^n ; a ≥ 5 ⇒ 10^(n+1) ;
    √10 ≤ a < 5 : les deux conventions en usage divergent ⇒ revue humaine.
    """
    try:
        ga = analyser_grandeur(attendue)
    except GrandeurInvalide as exc:
        return revue(f"attendue_{exc}")
    t = _normaliser(reponse)
    if not t:
        return invalide("reponse_vide")
    if len(t) > LONGUEUR_MAX:
        return revue("reponse_trop_longue")
    m = _ODG.match(t)
    if not m:
        try:
            analyser_grandeur(t)
            return invalide("puissance_de_dix_attendue")
        except GrandeurInvalide as exc:
            return revue(str(exc))
    n = int(m.group("e1") or m.group("e2"))
    unite_txt = (m.group("u1") if m.group("e1") is not None else m.group("u2")) or ""
    unite_txt = unite_txt.strip()
    if "°C" in (ga.unite_texte, unite_txt):
        return revue("temperature_celsius_non_supportee")
    try:
        ur = analyser_unite(unite_txt)
    except GrandeurInvalide as exc:
        return revue(str(exc))
    if ga.unite.dim != SANS_DIMENSION and not unite_txt:
        return invalide("unite_manquante")
    if ga.unite.dim != ur.dim:
        return invalide("dimension_incorrecte")
    v = abs(ga.valeur * ga.unite.facteur / ur.facteur)
    if v == 0:
        return revue("ordre_de_grandeur_de_zero")
    e = math.floor(math.log10(v))
    a = v / 10 ** e
    if a < _RACINE_10:
        return valide("ordre_de_grandeur_correct") if n == e else invalide("ordre_de_grandeur_incorrect")
    if a >= 5:
        return valide("ordre_de_grandeur_correct") if n == e + 1 else invalide("ordre_de_grandeur_incorrect")
    return revue("convention_ordre_de_grandeur_ambigue") if n in (e, e + 1) else invalide("ordre_de_grandeur_incorrect")


# --------------------------------------------------------------------------- #
# Conversions
# --------------------------------------------------------------------------- #
def verifier_conversion(depart: str, unite_cible: str, reponse: str, *, tolerance_relative: float = 1e-6) -> Resultat:
    """« 72 km/h » → « m/s » : la réponse doit être dans l'unité cible (facteur ET dimension)."""
    if not (0 < tolerance_relative <= 0.1):
        return revue("tolerance_hors_bornes")
    try:
        gd = analyser_grandeur(depart)
        uc = analyser_unite(unite_cible)
    except GrandeurInvalide as exc:
        return revue(f"attendue_{exc}")
    if "°C" in (gd.unite_texte, unite_cible.strip()):
        return revue("temperature_celsius_non_supportee")
    if gd.unite.dim != uc.dim:
        return revue("conversion_impossible_dimensions_differentes")
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    try:
        gr = analyser_grandeur(reponse)
    except GrandeurInvalide as exc:
        return revue(str(exc))
    if gd.unite.dim != SANS_DIMENSION and not gr.unite_texte:
        return invalide("unite_manquante")
    if gr.unite.dim != uc.dim:
        return invalide("dimension_incorrecte")
    if gr.unite.facteur != uc.facteur:
        return invalide("unite_cible_non_respectee")
    attendu = gd.valeur * gd.unite.facteur / uc.facteur
    if attendu == 0:
        return valide("conversion_correcte") if gr.valeur == 0 else invalide("valeur_incorrecte")
    if abs(gr.valeur - attendu) / abs(attendu) > tolerance_relative:
        return invalide("valeur_incorrecte")
    return valide("conversion_correcte")


# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #
class Constante(NamedTuple):
    valeur: str
    unite: str
    exacte: bool
    origine: str


CONSTANTES: Dict[str, Constante] = {
    "c": Constante("299792458", "m/s", True, "SI 2019 (valeur exacte)"),
    "h": Constante("6.62607015e-34", "J.s", True, "SI 2019 (valeur exacte)"),
    "e": Constante("1.602176634e-19", "C", True, "SI 2019 (valeur exacte)"),
    "N_A": Constante("6.02214076e23", "mol-1", True, "SI 2019 (valeur exacte)"),
    "k_B": Constante("1.380649e-23", "J.K-1", True, "SI 2019 (valeur exacte)"),
    "R": Constante("8.31446261815324", "J.mol-1.K-1", True, "N_A × k_B (exacte)"),
    "G": Constante("6.67430e-11", "N.m2.kg-2", False, "CODATA 2018 (mesurée)"),
    "g": Constante("9.80665", "m.s-2", False, "pesanteur normale conventionnelle ; valeur locale variable"),
}


def verifier_constante(nom: str, reponse: str, *, chiffres_min: int = 3) -> Resultat:
    """
    La réponse doit porter l'unité (dimension) de la constante et être égale à sa valeur arrondie
    au nombre de chiffres significatifs ÉCRITS (au moins `chiffres_min`).
    `g` : valeur locale ⇒ tolérance de 0,5 % puis revue au-delà si écart < 1 %.
    """
    k = CONSTANTES.get(nom)
    if k is None:
        return revue(f"constante_inconnue:{nom}")
    if not (1 <= chiffres_min <= 10):
        return revue("parametres_de_verification_invalides")
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    try:
        gr = analyser_grandeur(reponse)
        uk = analyser_unite(k.unite)
    except GrandeurInvalide as exc:
        return revue(str(exc))
    if not gr.unite_texte:
        return invalide("unite_manquante")
    if gr.unite.dim != uk.dim:
        return invalide("dimension_incorrecte")
    cs = chiffres_significatifs(gr.mantisse)
    if cs < chiffres_min:
        return invalide("precision_insuffisante")
    ref = Decimal(k.valeur) * Decimal(repr(uk.facteur)) / Decimal(repr(gr.unite.facteur)) / (Decimal(10) ** gr.exposant10)
    ecrite = _dec(gr.mantisse)
    if nom == "g":
        ecart = abs(ecrite - ref) / ref
        if ecart <= Decimal("0.005"):
            return valide("constante_correcte")
        return revue("valeur_locale_de_g_a_verifier") if ecart <= Decimal("0.01") else invalide("valeur_incorrecte")
    if ecrite != _arrondi_cs(ref, cs, ROUND_HALF_UP):
        return invalide("valeur_incorrecte")
    return valide("constante_correcte")


def valeur_constante(nom: str) -> Optional[Tuple[float, str]]:
    k = CONSTANTES.get(nom)
    return (float(k.valeur), k.unite) if k else None
