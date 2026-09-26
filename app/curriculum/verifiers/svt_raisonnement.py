"""
svt_raisonnement.py — Validateurs SVT NON purement lexicaux (lot 15, session 4).

Principe : le raisonnement est évalué sur des réponses STRUCTURÉES (choix d'identifiants,
valeurs lues, champs de protocole) confrontées à des données FOURNIES par l'exercice validé.
Le texte libre n'est jamais validé sur la seule présence de mots : un terme en contexte négatif
est signalé, et toute détection heuristique aboutit à NEEDS_HUMAN_REVIEW, jamais à VALID.

- lecture de graphique : tendance sur un intervalle, valeur lue (interpolation entre mesures,
  jamais d'extrapolation), extremum ;
- démarche expérimentale : une seule variable testée, variables contrôlées, témoin, répétitions ;
- conclusion d'expérience : cohérente avec les résultats fournis, prudente si peu de répétitions ;
- corrélation / causalité : une étude observationnelle n'autorise qu'un lien de corrélation ;
- exploitation de documents : informations (identifiants) prélevées dans le bon document,
  mise en relation d'au moins deux documents ;
- définition : éléments essentiels (formulations admises fournies), définition circulaire refusée.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide

MAX_POINTS = 500
_COPULES = {"est", "designe", "correspond", "signifie", "represente", "definit"}
MAX_TEXTE = 2000
TENDANCES = ("augmente", "diminue", "stable", "non_monotone")
_NEGATIONS = {"ne", "n", "pas", "jamais", "aucun", "aucune", "non", "sans", "ni", "nullement"}
_SEP_PROPOSITIONS = re.compile(r"[.;:!?,]|\b(?:mais|cependant|alors que|tandis que|et|donc|car|or)\b")
_CAUSAL = re.compile(r"\b(provoque|provoquent|entraine|entrainent|cause|causent|est responsable|sont responsables|"
                     r"due a|dus a|dues a|du a|a cause de|explique|expliquent|agit sur|determine)\b")
_PRUDENT = re.compile(r"\b(correle|correlee|correles|correlation|associe|associee|associes|lien statistique|"
                      r"pourrait|pourraient|suggere|suggerent|semble|semblent|hypothese|possible)\b")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9% ]", " ", t).split())


def _mots(t: str) -> List[str]:
    return _norm(t).split()


def _contient(prop: List[str], terme: List[str]) -> bool:
    n = len(terme)
    return bool(n) and any(prop[i:i + n] == terme for i in range(len(prop) - n + 1))


def propositions(texte: str) -> List[List[str]]:
    """Découpe en propositions (ponctuation, coordination) — base de la détection de négation."""
    brut = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode("ascii").lower()
    return [p.split() for p in (_norm(x) for x in _SEP_PROPOSITIONS.split(brut) if x) if p]


def occurrences(texte: str, terme: str) -> Tuple[int, int]:
    """(occurrences affirmées, occurrences en proposition négative) du terme."""
    t = _mots(terme)
    aff = neg = 0
    for p in propositions(texte):
        if _contient(p, t):
            if _NEGATIONS & set(p):
                neg += 1
            else:
                aff += 1
    return aff, neg


# --------------------------------------------------------------------------- #
# Lecture de graphique (données fournies par l'exercice)
# --------------------------------------------------------------------------- #
def _points(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    pts = sorted((float(x), float(y)) for x, y in points)
    if not (2 <= len(pts) <= MAX_POINTS):
        raise ValueError("nombre_de_points_invalide")
    if len({x for x, _ in pts}) != len(pts):
        raise ValueError("abscisses_dupliquees")
    return pts


def tendance(points: Sequence[Tuple[float, float]], a: float, b: float, *, seuil: float = 0.0) -> str:
    """Tendance des MESURES comprises dans [a, b] ; variations ≤ seuil considérées nulles."""
    ys = [y for x, y in _points(points) if a <= x <= b]
    if len(ys) < 2:
        raise ValueError("pas_assez_de_mesures_sur_l_intervalle")
    d = [y2 - y1 for y1, y2 in zip(ys, ys[1:])]
    hausses = any(v > seuil for v in d)
    baisses = any(v < -seuil for v in d)
    if hausses and baisses:
        return "non_monotone"
    return "augmente" if hausses else "diminue" if baisses else "stable"


def verifier_tendance(points, a: float, b: float, reponse: str, *, seuil: float = 0.0) -> Resultat:
    if reponse not in TENDANCES:
        return revue("tendance_non_reconnue")
    try:
        t = tendance(points, a, b, seuil=seuil)
    except (ValueError, TypeError) as exc:
        return revue(f"donnees_{exc}")
    return valide("tendance_correcte") if reponse == t else invalide(f"tendance_incorrecte:{t}")


def verifier_lecture_valeur(points, x: float, reponse_y: Any, *, precision: float) -> Resultat:
    """Valeur lue en x (interpolation linéaire ENTRE deux mesures) à ± precision (graduation)."""
    if not (precision > 0):
        return revue("precision_de_lecture_invalide")
    try:
        pts = _points(points)
        y_rep = float(str(reponse_y).replace(",", "."))
    except (ValueError, TypeError):
        return revue("lecture_illisible")
    if not (pts[0][0] <= x <= pts[-1][0]):
        return revue("extrapolation_hors_mesures")
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= x <= x2:
            y = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
            break
    return valide("lecture_correcte") if abs(y_rep - y) <= precision else invalide("lecture_incorrecte")


def verifier_extremum(points, reponse: Mapping[str, Any], *, precision_x: float, precision_y: float) -> Resultat:
    """reponse = {"type": "max"|"min", "x": …, "y": …} ; plusieurs extrema égaux ⇒ revue."""
    try:
        pts = _points(points)
        typ = reponse["type"]
        xr, yr = float(reponse["x"]), float(reponse["y"])
    except (KeyError, ValueError, TypeError):
        return revue("reponse_structuree_invalide")
    if typ not in ("max", "min"):
        return revue("type_extremum_inconnu")
    cible = max(y for _, y in pts) if typ == "max" else min(y for _, y in pts)
    xs = [x for x, y in pts if y == cible]
    if len(xs) > 1:
        return revue("extremum_non_unique")
    if abs(yr - cible) > precision_y:
        return invalide("valeur_extremum_incorrecte")
    if abs(xr - xs[0]) > precision_x:
        return invalide("position_extremum_incorrecte")
    return valide("extremum_correct")


# --------------------------------------------------------------------------- #
# Démarche expérimentale
# --------------------------------------------------------------------------- #
def verifier_protocole(protocole: Mapping[str, Any], *, variable_attendue: str, repetitions_min: int = 3) -> Resultat:
    """
    protocole = {"hypothese": str, "variables_testees": [str], "variables_controlees": [str],
                 "temoin": bool, "mesure": str, "repetitions": int}
    """
    requis = ("hypothese", "variables_testees", "variables_controlees", "temoin", "mesure", "repetitions")
    if not isinstance(protocole, Mapping) or any(k not in protocole for k in requis):
        return invalide("protocole_incomplet")
    testees = [_norm(v) for v in protocole["variables_testees"] or []]
    controlees = {_norm(v) for v in protocole["variables_controlees"] or []}
    raisons: List[str] = []
    if not _norm(str(protocole["hypothese"])):
        raisons.append("hypothese_absente")
    if len(testees) != 1:
        raisons.append("une_seule_variable_doit_varier")
    elif testees[0] != _norm(variable_attendue):
        raisons.append("variable_testee_incorrecte")
    if set(testees) & controlees:
        raisons.append("variable_testee_aussi_controlee")
    if not controlees:
        raisons.append("aucune_variable_controlee")
    if protocole["temoin"] is not True:
        raisons.append("temoin_absent")
    if not _norm(str(protocole["mesure"])):
        raisons.append("mesure_absente")
    rep = protocole["repetitions"]
    if not isinstance(rep, int) or isinstance(rep, bool) or rep < repetitions_min:
        raisons.append("repetitions_insuffisantes")
    return invalide(*raisons) if raisons else valide("protocole_rigoureux")


def verifier_conclusion_experience(resultats: Mapping[str, Any], conclusion: Mapping[str, Any]) -> Resultat:
    """
    resultats (FOURNIS par l'exercice) : {"ecart_significatif": bool, "sens": "hausse"|"baisse"|None,
                                         "repetitions": int, "hypothese_predit": "hausse"|"baisse"}
    conclusion (élève) : {"hypothese": "validee"|"invalidee"|"non_conclusive"}
    """
    try:
        ecart, sens, n = resultats["ecart_significatif"], resultats.get("sens"), int(resultats["repetitions"])
        predit, c = resultats["hypothese_predit"], conclusion["hypothese"]
    except (KeyError, TypeError, ValueError):
        return revue("donnees_ou_reponse_incompletes")
    if c not in ("validee", "invalidee", "non_conclusive"):
        return revue("conclusion_non_reconnue")
    if n < 2:
        return valide("prudence_justifiee") if c == "non_conclusive" else invalide("conclusion_sur_mesure_unique")
    if not ecart:
        return valide("conclusion_correcte") if c == "non_conclusive" else invalide("ecart_non_significatif")
    attendu = "validee" if sens == predit else "invalidee"
    return valide("conclusion_correcte") if c == attendu else invalide(f"conclusion_incorrecte:{attendu}")


# --------------------------------------------------------------------------- #
# Corrélation / causalité
# --------------------------------------------------------------------------- #
def verifier_lien(type_etude: str, reponse: Mapping[str, Any]) -> Resultat:
    """
    type_etude (FOURNI) : "observationnelle" | "experimentale_controlee".
    reponse : {"lien": "correlation"|"causalite", "justification": str (optionnel)}.
    Étude observationnelle ⇒ seul un lien de corrélation est acceptable ; texte causal catégorique ⇒ refus.
    """
    lien = reponse.get("lien") if isinstance(reponse, Mapping) else None
    if type_etude not in ("observationnelle", "experimentale_controlee"):
        return revue("type_etude_inconnu")
    if lien not in ("correlation", "causalite"):
        return revue("lien_non_reconnu")
    justification = str(reponse.get("justification") or "")[:MAX_TEXTE]
    if type_etude == "observationnelle":
        if lien == "causalite":
            return invalide("causalite_affirmee_sur_correlation")
        props = propositions(justification)
        causales = [p for p in props if _CAUSAL.search(" ".join(p)) and not (_NEGATIONS & set(p))]
        if causales and not _PRUDENT.search(_norm(justification)):
            return revue("justification_formulee_causalement")
        return valide("lien_correct")
    return valide("lien_correct") if lien == "causalite" else invalide("lien_causal_sous_estime")


# --------------------------------------------------------------------------- #
# Exploitation de documents (informations = identifiants fournis par l'exercice)
# --------------------------------------------------------------------------- #
def verifier_exploitation_documents(
    prelevements: Mapping[str, Iterable[str]],
    informations: Mapping[str, str],
    infos_cles: Iterable[str],
    *,
    documents_min: int = 2,
) -> Resultat:
    """
    prelevements (élève) : {doc_id: [info_id, …]} ; informations (exercice) : {info_id: doc_id source} ;
    infos_cles : infos indispensables au raisonnement. Une info attribuée au mauvais document est une
    erreur de lecture ; au moins `documents_min` documents doivent être mis en relation.
    """
    cles = set(infos_cles)
    if not cles or not cles <= set(informations):
        return revue("infos_cles_non_definies")
    erreurs: List[str] = []
    vues: Set[str] = set()
    docs_utiles: Set[str] = set()
    for doc, infos in prelevements.items():
        for i in infos:
            if i not in informations:
                return revue(f"information_inconnue:{i}")
            if informations[i] != doc:
                erreurs.append(f"information_mal_attribuee:{i}")
            else:
                vues.add(i)
                docs_utiles.add(doc)
    if erreurs:
        return invalide(*sorted(erreurs))
    manquantes = sorted(cles - vues)
    if manquantes:
        return invalide(*(f"information_cle_manquante:{i}" for i in manquantes))
    if len(docs_utiles) < documents_min:
        return invalide("mise_en_relation_insuffisante")
    return valide("documents_exploites")


# --------------------------------------------------------------------------- #
# Définitions
# --------------------------------------------------------------------------- #
def verifier_definition(
    terme_defini: str,
    reponse: str,
    elements_essentiels: Sequence[Iterable[str]],
    *,
    confusions: Iterable[str] = (),
) -> Resultat:
    """
    elements_essentiels : pour chaque élément, les formulations ADMISES (fournies par l'exercice).
    Un élément présent uniquement en proposition négative ⇒ revue (jamais validé).
    Définition circulaire (le terme défini dans la définition, hors sujet grammatical initial) ⇒ invalide.
    """
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    if len(reponse) > MAX_TEXTE:
        return revue("reponse_trop_longue")
    if not elements_essentiels:
        return revue("elements_essentiels_absents")
    mots = _mots(reponse)
    terme = _mots(terme_defini)
    # Le sujet grammatical (« La photosynthèse est… ») n'est pas circulaire : on n'examine que ce
    # qui suit la première copule ; sans copule, le texte entier.
    copule = next((i for i, m in enumerate(mots) if m in _COPULES), None)
    corps = mots[copule + 1:] if copule is not None else mots
    if _contient(corps, terme):
        return invalide("definition_circulaire")
    for c in confusions:
        aff, neg = occurrences(reponse, c)
        if aff:
            return invalide(f"confusion:{c}")
    manquants: List[str] = []
    nies: List[str] = []
    for i, formulations in enumerate(elements_essentiels):
        formes = list(formulations)
        stats = [occurrences(reponse, f) for f in formes]
        if any(a for a, _ in stats):
            continue
        (nies if any(n for _, n in stats) else manquants).append(formes[0] if formes else str(i))
    if manquants:
        return invalide(*(f"element_manquant:{m}" for m in manquants))
    if nies:
        return revue(*(f"element_en_contexte_negatif:{m}" for m in nies))
    return valide("definition_correcte")


def resume_capacites() -> Dict[str, Optional[str]]:
    """Inventaire (documentation / rapports) des capacités SVT couvertes par ce module."""
    return {
        "lecture_graphique": "verifier_tendance, verifier_lecture_valeur, verifier_extremum",
        "experimentation": "verifier_protocole, verifier_conclusion_experience",
        "correlation_causalite": "verifier_lien",
        "documents": "verifier_exploitation_documents",
        "definitions": "verifier_definition",
    }
