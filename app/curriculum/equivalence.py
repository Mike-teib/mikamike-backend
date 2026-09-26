"""
equivalence.py — R6 : audit de correction SYMBOLIQUE du catalogue historique (lecture seule).

Le catalogue historique (`app/api/v1/mikamike/catalogue.py`) corrige par COMPARAISON DE
CHAÎNES après normalisation (espaces, casse, virgule). Cet outil mesure, sans RIEN modifier,
ce qu'une correction symbolique changerait :

  - réponses équivalentes refusées aujourd'hui (faux négatifs : « 6/2 », « x = 3,0 ») ;
  - réponses NON équivalentes acceptées aujourd'hui (faux positifs) ;
  - équivalence de FOND mais pas de FORME (« 2/4 » pour « Simplifie 4/8 », « 0,5 » quand une
    fraction est demandée, « 1 m » pour « 100 cm ») ;
  - équations (« x = 3 », « 3 = x »), fractions, puissances (« x² », « x^2 », « x**2 »),
    expressions, unités mathématiques (longueurs, aires, volumes, angles, %).

Politique (fail-closed) : un verdict AUTOMATIQUE n'est rendu que si le fond ET la forme sont
certains. Tout le reste — forme différente, consigne dont la forme attendue est inconnue,
entrée non analysable, vérificateur indécis, unité différente — finit en NEEDS_HUMAN_REVIEW.
Aucune donnée officielle n'est modifiée : les décisions restent humaines (décision D5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Tuple

import sympy

from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.maths import EntreeRefusee, analyser, verifier_reponse


class Decision(str, Enum):
    ACCEPTER = "ACCEPTER"                      # équivalent, forme conforme
    REFUSER = "REFUSER"                        # non équivalent (certain)
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"  # tout cas ambigu


class Constat(str, Enum):
    CONCORDANT = "CONCORDANT"                              # historique et symbolique d'accord
    FAUX_NEGATIF_HISTORIQUE = "FAUX_NEGATIF_HISTORIQUE"    # équivalent (forme OK) refusé aujourd'hui
    FAUX_POSITIF_HISTORIQUE = "FAUX_POSITIF_HISTORIQUE"    # non équivalent accepté aujourd'hui
    FORME_DIFFERENTE = "FORME_DIFFERENTE"                  # fond équivalent, forme à trancher
    INDECIDABLE = "INDECIDABLE"                            # analyse impossible / vérificateur indécis


# --------------------------------------------------------------------------- #
# Unités mathématiques (facteur vers l'unité de base de la dimension)
# --------------------------------------------------------------------------- #
_UNITES: Dict[str, Tuple[str, Fraction]] = {
    "mm": ("longueur", Fraction(1, 1000)), "cm": ("longueur", Fraction(1, 100)),
    "dm": ("longueur", Fraction(1, 10)), "m": ("longueur", Fraction(1)), "km": ("longueur", Fraction(1000)),
    "mm²": ("aire", Fraction(1, 10**6)), "cm²": ("aire", Fraction(1, 10**4)), "dm²": ("aire", Fraction(1, 100)),
    "m²": ("aire", Fraction(1)), "km²": ("aire", Fraction(10**6)),
    "cm³": ("volume", Fraction(1, 10**6)), "dm³": ("volume", Fraction(1, 1000)), "m³": ("volume", Fraction(1)),
    "ml": ("volume", Fraction(1, 10**6)), "cl": ("volume", Fraction(1, 10**5)), "l": ("volume", Fraction(1, 1000)),
    "°": ("angle", Fraction(1)), "deg": ("angle", Fraction(1)),
    "%": ("pourcentage", Fraction(1)),
}
_RE_UNITE = re.compile(r"^\s*(?P<val>[-+]?[0-9]+(?:[.,][0-9]+)?(?:\s*/\s*[0-9]+)?)\s*(?P<u>[a-zA-Z°%]+[23²³]?)\s*$")
_ALIAS = {"m2": "m²", "cm2": "cm²", "mm2": "mm²", "dm2": "dm²", "km2": "km²", "m3": "m³", "cm3": "cm³",
          "dm3": "dm³", "degres": "°", "degrés": "°", "L": "l", "mL": "ml", "cL": "cl"}


def _avec_unite(texte: str) -> Optional[Tuple[Fraction, str]]:
    m = _RE_UNITE.match(texte or "")
    if not m:
        return None
    u = _ALIAS.get(m.group("u"), m.group("u"))
    if u not in _UNITES:
        return None
    brut = m.group("val").replace(",", ".").replace(" ", "")
    try:
        if "/" in brut:
            n, d = brut.split("/")
            val = Fraction(Fraction(n), Fraction(d))
        else:
            val = Fraction(brut)
    except (ValueError, ZeroDivisionError):
        return None
    return val, u


def comparer_unites(attendue: str, reponse: str) -> Optional[Tuple[Decision, str]]:
    """None si aucune des deux n'a d'unité. Sinon décision + raison."""
    a, r = _avec_unite(attendue), _avec_unite(reponse)
    if a is None and r is None:
        return None
    if a is None or r is None:
        return Decision.NEEDS_HUMAN_REVIEW, "unite_presente_d_un_seul_cote"
    (va, ua), (vr, ur) = a, r
    (da, fa), (dr, fr) = _UNITES[ua], _UNITES[ur]
    if da != dr:
        return Decision.REFUSER, f"dimension_differente:{da}/{dr}"
    if va * fa != vr * fr:
        return Decision.REFUSER, "valeur_differente"
    if ua != ur:
        return Decision.NEEDS_HUMAN_REVIEW, f"conversion_d_unite:{ua}->{ur}"
    return Decision.ACCEPTER, "meme_valeur_meme_unite"


# --------------------------------------------------------------------------- #
# Forme attendue, déduite de la consigne (sinon inconnue ⇒ revue humaine)
# --------------------------------------------------------------------------- #
_FORMES_CONSIGNE = (
    (re.compile(r"\bsimplifie", re.I), "fraction_irreductible"),
    (re.compile(r"\bréduis|\breduis|\bdéveloppe|\bdeveloppe", re.I), "developpee"),
    (re.compile(r"\bfactorise", re.I), "factorisee"),
    (re.compile(r"\bcalcule|\brésous|\bresous", re.I), "valeur_simplifiee"),
    (re.compile(r"sous forme décimale|forme decimale|en décimal", re.I), "decimal"),
)


def forme_de_la_consigne(enonce: str) -> Optional[str]:
    for motif, forme in _FORMES_CONSIGNE[::-1]:  # la mention la plus spécifique d'abord
        if motif.search(enonce or ""):
            return forme
    return None


def _valeur_simple(val: str) -> Optional[bool]:
    """Entier, décimal fini ou fraction irréductible à dénominateur > 1, écrit tel quel."""
    v = (val or "").strip().replace(" ", "").replace(",", ".")
    if re.fullmatch(r"[-+]?[0-9]+", v):
        return True
    if re.fullmatch(r"[-+]?[0-9]+\.[0-9]*[1-9]", v):
        return True
    if re.fullmatch(r"[-+]?[0-9]+\.[0-9]*0", v):
        return False  # « 3,0 », « 0,50 » : zéros superflus
    m = re.fullmatch(r"([-+]?[0-9]+)/([0-9]+)", v)
    if m:
        n, d = int(m.group(1)), int(m.group(2))
        return d > 1 and sympy.gcd(n, d) == 1
    return None  # expression : décidée par le vérificateur de forme


def _partie_valeur(reponse: str) -> str:
    return reponse.split("=", 1)[1] if "=" in reponse else reponse


def _forme_conforme(reponse: str, forme: str) -> Optional[bool]:
    """True/False si décidable, None sinon (⇒ revue humaine)."""
    solutions = re.split(r"\s+(?:ou|et)\s+|;", reponse)
    if len(solutions) > 1:
        verdicts = [_forme_conforme(x, forme) for x in solutions]
        return None if None in verdicts else all(verdicts)
    val = _partie_valeur(_normaliser_equation(reponse))
    if forme == "valeur_simplifiee":
        return _valeur_simple(val)
    if forme == "fraction_irreductible":
        s = _valeur_simple(val)
        return bool(s) and "/" in val if s is not None else None
    if forme == "decimal":
        s = _valeur_simple(val)
        return bool(s) and "/" not in val if s is not None else None
    if forme in ("developpee", "factorisee"):
        r = verifier_reponse(val, val, forme_requise=forme)
        if r.verdict == Verdict.VALID:
            return True
        if r.verdict == Verdict.INVALID:
            return False
        return None
    return None


def _normaliser_equation(texte: str) -> str:
    """« 3 = x » ⇒ « x = 3 » (variable isolée à droite) ; sinon inchangé."""
    t = (texte or "").strip()
    if t.count("=") == 1:
        g, d = (p.strip() for p in t.split("="))
        if re.fullmatch(r"[a-zA-Z]", d) and not re.fullmatch(r"[a-zA-Z]", g):
            return f"{d} = {g}"
    return t


def verdict_symbolique(attendues: Iterable[str], reponse: str) -> Tuple[Verdict, str]:
    """VALID si équivalente à l'une des réponses attendues ; indécis ⇒ NEEDS_HUMAN_REVIEW."""
    if _avec_unite(reponse) or any(_avec_unite(a) for a in attendues):
        for a in attendues:
            u = comparer_unites(a, reponse)
            if u and u[0] == Decision.ACCEPTER:
                return Verdict.VALID, u[1]
        u = comparer_unites(next(iter(attendues)), reponse)
        return (Verdict.NEEDS_HUMAN_REVIEW if u[0] == Decision.NEEDS_HUMAN_REVIEW else Verdict.INVALID), u[1]
    rep = _normaliser_equation(reponse)
    # Variable nommée par l'élève absente de toutes les réponses attendues (« y = 3 » pour x).
    vars_att = {m.group(1) for a in attendues for m in re.finditer(r"([a-zA-Z])\s*=", _normaliser_equation(a))}
    vars_rep = {m.group(1) for m in re.finditer(r"([a-zA-Z])\s*=", rep)}
    if vars_att and vars_rep - vars_att:
        return Verdict.INVALID, "variable_differente"
    indecis = None
    for a in attendues:
        try:
            r = verifier_reponse(_normaliser_equation(a), rep)
        except (EntreeRefusee, ValueError, TypeError) as exc:  # pragma: no cover - défensif
            indecis = f"analyse_impossible:{type(exc).__name__}"
            continue
        if r.verdict == Verdict.VALID:
            return Verdict.VALID, "equivalent"
        if r.verdict != Verdict.INVALID:
            indecis = ",".join(r.raisons) or r.verdict.value
    if indecis:
        return Verdict.NEEDS_HUMAN_REVIEW, indecis
    return Verdict.INVALID, "non_equivalent"


@dataclass(frozen=True)
class Ligne:
    reponse: str
    historique_accepte: bool
    symbolique: str
    decision: Decision
    constat: Constat
    raison: str


def classer(enonce: str, attendues: List[str], reponse: str, historique_accepte: bool) -> Ligne:
    sym, raison = verdict_symbolique(attendues, reponse)
    if sym == Verdict.NEEDS_HUMAN_REVIEW or sym == Verdict.AMBIGUOUS:
        return Ligne(reponse, historique_accepte, sym.value, Decision.NEEDS_HUMAN_REVIEW, Constat.INDECIDABLE, raison)
    if sym == Verdict.INVALID:
        constat = Constat.FAUX_POSITIF_HISTORIQUE if historique_accepte else Constat.CONCORDANT
        return Ligne(reponse, historique_accepte, sym.value, Decision.REFUSER, constat, raison)
    # Fond équivalent : la FORME décide entre accepter et revue humaine.
    if _avec_unite(reponse):
        return Ligne(reponse, historique_accepte, sym.value, Decision.ACCEPTER,
                     Constat.CONCORDANT if historique_accepte else Constat.FAUX_NEGATIF_HISTORIQUE, raison)
    forme = forme_de_la_consigne(enonce)
    if forme is None:
        if historique_accepte:
            return Ligne(reponse, True, sym.value, Decision.ACCEPTER, Constat.CONCORDANT, "deja_acceptee")
        return Ligne(reponse, False, sym.value, Decision.NEEDS_HUMAN_REVIEW, Constat.FORME_DIFFERENTE,
                     "forme_attendue_inconnue")
    ok = _forme_conforme(reponse, forme)
    if ok is None:
        return Ligne(reponse, historique_accepte, sym.value, Decision.NEEDS_HUMAN_REVIEW, Constat.INDECIDABLE,
                     f"forme_{forme}_indecidable")
    if not ok:
        return Ligne(reponse, historique_accepte, sym.value, Decision.NEEDS_HUMAN_REVIEW, Constat.FORME_DIFFERENTE,
                     f"forme_{forme}_non_respectee")
    constat = Constat.CONCORDANT if historique_accepte else Constat.FAUX_NEGATIF_HISTORIQUE
    return Ligne(reponse, historique_accepte, sym.value, Decision.ACCEPTER, constat, f"forme_{forme}_respectee")


# --------------------------------------------------------------------------- #
# Génération de candidats (variantes équivalentes + erreurs typiques)
# --------------------------------------------------------------------------- #
def _variantes_valeur(val: str) -> List[str]:
    v = val.strip()
    out = [v, v.replace(".", ","), f" {v} "]
    try:
        e = analyser(v)
    except (EntreeRefusee, ValueError):
        return out
    if e.is_Rational:
        q = sympy.Rational(e)
        for k in (2, 3):
            out.append(f"{q.p * k}/{q.q * k}")
        if q.q != 1:
            out.append(f"{q.p}/{q.q}")
            d = sympy.Rational(q.p, q.q)
            if (10 ** 6 * d).is_integer:
                out.append(str(float(d)).replace(".", ","))
                out.append(f"{float(d) * 100:g} %")
        else:
            out += [f"{q.p},0", f"{q.p}.00", f"{q.p * 2}/2"]
        # Erreurs typiques (doivent être REFUSÉES) : ±1, opposé, inverse.
        out += [str(q + 1), str(q - 1), str(-q)]
        if q != 0:
            out.append(str(1 / q))
    else:
        s = str(e).replace("**", "^")
        out += [s, s.replace("^2", "²"), str(sympy.expand(e)).replace("**", "^"),
                str(sympy.factor(e)).replace("**", "^"), s.replace("*", "")]
        out.append(str(e + 1).replace("**", "^"))
    return out


def candidats(attendues: Iterable[str]) -> List[str]:
    vus, out = set(), []
    for a in attendues:
        var, val = (a.split("=", 1) + [""])[:2] if "=" in a else (None, a)
        for v in _variantes_valeur(val):
            for c in ([v] if var is None else [v, f"{var.strip()} = {v.strip()}", f"{v.strip()} = {var.strip()}"]):
                if c not in vus:
                    vus.add(c)
                    out.append(c)
    return out


@dataclass
class RapportExercice:
    exercice_id: str
    enonce: str
    forme_consigne: Optional[str]
    attendues: List[str]
    coherence_attendues: str
    lignes: List[Ligne] = field(default_factory=list)


def auditer_catalogue(exercices: Dict[str, dict], est_correct) -> List[RapportExercice]:
    """`est_correct(exercice_id, reponse)` = correcteur HISTORIQUE (lecture seule)."""
    rapports = []
    for exo_id in sorted(exercices):
        meta = exercices[exo_id]
        att = list(meta.get("reponses_acceptees", []))
        coherence = "COHERENTES"
        for a in att[1:]:
            if verdict_symbolique([att[0]], a)[0] != Verdict.VALID:
                coherence = "NEEDS_HUMAN_REVIEW:reponses_acceptees_non_equivalentes"
        rap = RapportExercice(exo_id, meta.get("enonce", ""), forme_de_la_consigne(meta.get("enonce", "")),
                              att, coherence)
        for c in candidats(att):
            rap.lignes.append(classer(rap.enonce, att, c, bool(est_correct(exo_id, c))))
        rapports.append(rap)
    return rapports


def synthese(rapports: List[RapportExercice]) -> Dict[str, int]:
    compte: Dict[str, int] = {}
    for r in rapports:
        for ligne in r.lignes:
            for cle in (f"decision:{ligne.decision.value}", f"constat:{ligne.constat.value}"):
                compte[cle] = compte.get(cle, 0) + 1
        if r.coherence_attendues != "COHERENTES":
            compte["exercices_incoherents"] = compte.get("exercices_incoherents", 0) + 1
    compte["exercices"] = len(rapports)
    return dict(sorted(compte.items()))
