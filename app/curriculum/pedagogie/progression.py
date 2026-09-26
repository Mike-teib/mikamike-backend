"""
progression.py — Niveau de maîtrise d'une notion calculé sur l'HISTORIQUE (lot 18, session 4).

Niveaux : MAITRISEE / EN_COURS / FRAGILE / NON_ACQUISE, plus NON_EVALUEE tant que les
observations sont insuffisantes. Règles (toutes déterministes, documentées) :

  R1  jamais de diagnostic sur une seule réponse : moins de `MIN_OBSERVATIONS` tentatives
      ⇒ NON_EVALUEE (sauf l'état antérieur, conservé par l'appelant) ;
  R2  une réussite AVEC AIDE ne compte jamais comme réussite autonome (LE-06) ;
  R3  D14 : compréhension finale ratée ⇒ la tentative n'est PAS une réussite ;
  R4  MAITRISEE exige ≥ 3 réussites autonomes parmi les 4 dernières tentatives autonomes,
      dont la plus récente, réparties sur ≥ 2 jours distincts (retest espacé) ;
  R5  NON_ACQUISE : ≥ MIN_OBSERVATIONS tentatives récentes et aucune réussite (même aidée) ;
  R6  FRAGILE : moins de la moitié de réussites récentes, ou les 2 dernières tentatives
      autonomes échouées ;
  R7  une seule nouvelle réponse ne fait jamais passer de MAITRISEE à NON_ACQUISE, ni de
      NON_ACQUISE à MAITRISEE (au plus un cran de variation) — propriété testée.

Données manipulées : booléens et horodatages seulement (aucune donnée personnelle).
"""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import List, NamedTuple, Sequence, Tuple

MIN_OBSERVATIONS = 3
FENETRE = 6
HISTORIQUE_MAX = 60  # borne le coût (O(n·fenêtre)) : seules les réponses récentes comptent


class Niveau(str, Enum):
    NON_EVALUEE = "NON_EVALUEE"
    NON_ACQUISE = "NON_ACQUISE"
    FRAGILE = "FRAGILE"
    EN_COURS = "EN_COURS"
    MAITRISEE = "MAITRISEE"


ORDRE = (Niveau.NON_ACQUISE, Niveau.FRAGILE, Niveau.EN_COURS, Niveau.MAITRISEE)
PROCHAINE_ACTION = {
    Niveau.NON_EVALUEE: "observer_encore",
    Niveau.NON_ACQUISE: "reprendre_prerequis",
    Niveau.FRAGILE: "guidage_pas_a_pas",
    Niveau.EN_COURS: "entrainement_autonome",
    Niveau.MAITRISEE: "retest_espace",
}


class Tentative(NamedTuple):
    correcte: bool
    avec_aide: bool
    horodatage: float                   # secondes UTC
    comprehension_finale: bool = True   # D14


class Diagnostic(NamedTuple):
    niveau: Niveau
    raisons: Tuple[str, ...]
    prochaine_action: str
    observations: int


def _reussie(t: Tentative) -> bool:
    return t.correcte and t.comprehension_finale  # R3


def _jour(t: Tentative) -> _dt.date:
    return _dt.datetime.fromtimestamp(t.horodatage, _dt.timezone.utc).date()


def _brut(h: List[Tentative]) -> Tuple[Niveau, Tuple[str, ...]]:
    recentes = h[-FENETRE:]
    autonomes = [t for t in h if not t.avec_aide][-4:]
    reussites = [t for t in recentes if _reussie(t)]
    auto_ok = [t for t in autonomes if _reussie(t)]
    if len(autonomes) >= 3 and len(auto_ok) >= 3 and _reussie(autonomes[-1]) \
            and len({_jour(t) for t in auto_ok}) >= 2:
        return Niveau.MAITRISEE, ("R4_reussites_autonomes_espacees",)
    if not reussites:
        return Niveau.NON_ACQUISE, ("R5_aucune_reussite_recente",)
    if len(reussites) * 2 < len(recentes):
        return Niveau.FRAGILE, ("R6_moins_de_la_moitie_de_reussites",)
    if len(autonomes) >= 2 and not _reussie(autonomes[-1]) and not _reussie(autonomes[-2]):
        return Niveau.FRAGILE, ("R6_deux_echecs_autonomes_recents",)
    raisons = ["progression_en_cours"]
    if any(t.avec_aide and _reussie(t) for t in recentes):
        raisons.append("R2_reussites_aidees_non_comptees_comme_autonomes")
    if len({_jour(t) for t in auto_ok}) < 2 and len(auto_ok) >= 3:
        raisons.append("R4_retest_espace_requis")
    return Niveau.EN_COURS, tuple(raisons)


def diagnostiquer(historique: Sequence[Tentative]) -> Diagnostic:
    h = sorted(historique, key=lambda t: t.horodatage)[-HISTORIQUE_MAX:]
    if len(h) < MIN_OBSERVATIONS:
        return Diagnostic(Niveau.NON_EVALUEE, ("R1_observations_insuffisantes",),
                          PROCHAINE_ACTION[Niveau.NON_EVALUEE], len(h))
    # R7 : le niveau évolue réponse après réponse, d'au plus un cran à chaque nouvelle réponse.
    niveau, raisons = _brut(h[:MIN_OBSERVATIONS])
    for k in range(MIN_OBSERVATIONS + 1, len(h) + 1):
        cible, raisons = _brut(h[:k])
        ia, ib = ORDRE.index(niveau), ORDRE.index(cible)
        if abs(ib - ia) > 1:
            cible = ORDRE[ia + (1 if ib > ia else -1)]
            raisons = raisons + ("R7_variation_bornee_a_un_cran",)
        niveau = cible
    return Diagnostic(niveau, raisons, PROCHAINE_ACTION[niveau], len(h))
