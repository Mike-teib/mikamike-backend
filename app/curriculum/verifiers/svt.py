"""
svt.py — Vérifications structurelles et règles déterministes pour les SVT.

Les contenus (termes attendus, chaînes causales, clés de classification) sont
FOURNIS par l'exercice validé — rien n'est codé en dur ici hormis l'échelle des
niveaux d'organisation du vivant, qui est une structure générale.

- vocabulaire scientifique (termes requis / erronés / hors niveau) ;
- relations causales et chaînes biologiques (présence et ORDRE des étapes) ;
- niveaux d'organisation (ordre croissant ou décroissant cohérent) ;
- classification (affectation de chaque élément au bon groupe) ;
- prudence : une notion marquée ambiguë n'accepte pas d'affirmation catégorique.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Mapping, Sequence, Set

from app.curriculum.verifiers.base import Resultat, ambigu, invalide, revue, valide

NIVEAUX_ORGANISATION = (
    "molecule", "organite", "cellule", "tissu", "organe", "appareil",
    "organisme", "population", "ecosysteme",
)
_SYNONYMES_NIVEAUX = {"systeme": "appareil", "individu": "organisme", "biosphere": None}

_CATEGORIQUES = re.compile(
    r"\b(toujours|jamais|forcement|certainement|obligatoirement|prouve definitivement|"
    r"sans aucun doute|100 ?%|tous les|aucun ne)\b"
)
_CONNECTEURS_CAUSAUX = re.compile(r"\b(donc|car|parce que|entraine|provoque|permet|aboutit a|conduit a|a cause de)\b")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").lower()
    # Les élisions (l'ADN, d'anticorps) sont des séparateurs de mots.
    return " ".join(re.sub(r"[^a-z0-9% ]", " ", t).split())


def _lemme(mot: str) -> str:
    for suf in ("aux", "s", "x"):
        if len(mot) > 3 and mot.endswith(suf):
            return mot[: -len(suf)] + ("al" if suf == "aux" else "")
    return mot


def _contient(texte_norm: str, terme: str) -> bool:
    mots_texte = [_lemme(m) for m in texte_norm.split()]
    mots_terme = [_lemme(m) for m in _norm(terme).split()]
    n = len(mots_terme)
    return any(mots_texte[i:i + n] == mots_terme for i in range(len(mots_texte) - n + 1)) if n else False


def verifier_vocabulaire(
    reponse: str,
    termes_requis: Iterable[str],
    *,
    termes_errones: Iterable[str] = (),
    termes_hors_niveau: Iterable[str] = (),
) -> Resultat:
    if not (reponse or "").strip():
        return invalide("reponse_vide")
    t = _norm(reponse)
    manquants = [x for x in termes_requis if not _contient(t, x)]
    errones = [x for x in termes_errones if _contient(t, x)]
    if errones:
        return invalide(*(f"terme_errone:{x}" for x in errones))
    if manquants:
        return invalide(*(f"terme_manquant:{x}" for x in manquants))
    hors = [x for x in termes_hors_niveau if _contient(t, x)]
    if hors:
        return ambigu(*(f"terme_hors_niveau:{x}" for x in hors))
    return valide("vocabulaire_correct")


def verifier_chaine_causale(etapes_eleve: Sequence[str], chaine_attendue: Sequence[str]) -> Resultat:
    """Chaque étape attendue doit apparaître, dans l'ordre (étapes supplémentaires tolérées)."""
    if not etapes_eleve:
        return invalide("reponse_vide")
    if not chaine_attendue:
        return revue("chaine_attendue_absente")
    eleve = [_norm(e) for e in etapes_eleve]
    positions: List[int] = []
    for etape in chaine_attendue:
        pos = next((i for i, e in enumerate(eleve) if _contient(e, etape)), None)
        if pos is None:
            return invalide(f"etape_manquante:{etape}")
        positions.append(pos)
    if positions != sorted(positions):
        return invalide("ordre_causal_incorrect")
    return valide("chaine_causale_correcte")


def verifier_explication_causale(reponse: str, cause: str, consequence: str) -> Resultat:
    """La cause doit précéder la conséquence et être reliée par un connecteur causal."""
    t = _norm(reponse)
    if not t:
        return invalide("reponse_vide")
    ic, ie = t.find(_norm(cause)), t.find(_norm(consequence))
    if ic < 0 or ie < 0:
        return invalide("cause_ou_consequence_absente")
    if not _CONNECTEURS_CAUSAUX.search(t):
        return invalide("lien_causal_non_explicite")
    # « B car A » est valide ; « A donc B » aussi : on vérifie la cohérence du connecteur.
    entre = t[min(ic, ie):max(ic, ie)]
    if ic > ie and not re.search(r"\b(car|parce que|a cause de)\b", entre):
        return invalide("sens_causal_inverse")
    return valide("explication_causale_correcte")


def verifier_niveaux_organisation(niveaux: Sequence[str]) -> Resultat:
    rangs: List[int] = []
    for n in niveaux:
        cle = _lemme(_norm(n))
        cle = _SYNONYMES_NIVEAUX.get(cle, cle)
        if cle not in NIVEAUX_ORGANISATION:
            return revue(f"niveau_inconnu:{n}")
        rangs.append(NIVEAUX_ORGANISATION.index(cle))
    if len(rangs) < 2:
        return invalide("au_moins_deux_niveaux")
    if len(set(rangs)) != len(rangs):
        return invalide("niveau_repete")
    if rangs == sorted(rangs) or rangs == sorted(rangs, reverse=True):
        return valide("ordre_coherent")
    return invalide("ordre_incoherent")


def verifier_classification(
    groupes_eleve: Mapping[str, Iterable[str]], cle: Mapping[str, Iterable[str]]
) -> Resultat:
    """Chaque élément de la clé doit être dans le même groupe chez l'élève."""
    attendu: Dict[str, str] = {_norm(e): g for g, elts in cle.items() for e in elts}
    vus: Set[str] = set()
    erreurs: List[str] = []
    for groupe, elts in groupes_eleve.items():
        for e in elts:
            ne = _norm(e)
            vus.add(ne)
            if ne not in attendu:
                return revue(f"element_hors_cle:{e}")
            if _norm(attendu[ne]) != _norm(groupe):
                erreurs.append(f"mal_classe:{e}")
    manquants = [e for e in attendu if e not in vus]
    if erreurs:
        return invalide(*erreurs)
    if manquants:
        return invalide(*(f"non_classe:{e}" for e in manquants))
    return valide("classification_correcte")


def verifier_prudence(reponse: str, *, notion_ambigue: bool) -> Resultat:
    """Sur une notion ambiguë / débattue, une affirmation catégorique part en revue humaine."""
    if notion_ambigue and _CATEGORIQUES.search(_norm(reponse)):
        return revue("affirmation_trop_categorique")
    return valide("prudence_respectee")
