"""
enseignement_scientifique.py — Rattachement des contenus pluridisciplinaires.

L'Enseignement scientifique (tronc commun de 1re / Tle) mobilise plusieurs
disciplines. Règle : on ne force JAMAIS une notion dans une seule matière si la
source ne le justifie pas, et on ne déclare pas de disciplines que la source
n'indique pas.
"""

from __future__ import annotations

from typing import Iterable, Optional

from app.curriculum.model import Matiere, Notion
from app.curriculum.verifiers.base import Resultat, invalide, revue, valide

DISCIPLINES_MOBILISABLES = frozenset({
    Matiere.MATHEMATIQUES, Matiere.PHYSIQUE_CHIMIE, Matiere.SVT,
})


def verifier_rattachement(
    matiere_proposee: Matiere,
    disciplines_source: Optional[Iterable[Matiere]],
) -> Resultat:
    """
    `disciplines_source` : disciplines explicitement indiquées par la source officielle.
    None ⇒ la source n'a pas été consultée : revue humaine.
    """
    if disciplines_source is None:
        return revue("disciplines_source_inconnues")
    ds = set(disciplines_source)
    if not ds <= DISCIPLINES_MOBILISABLES | {Matiere.ENSEIGNEMENT_SCIENTIFIQUE}:
        return invalide("discipline_non_mobilisable")
    ds.discard(Matiere.ENSEIGNEMENT_SCIENTIFIQUE)
    if len(ds) > 1 and matiere_proposee != Matiere.ENSEIGNEMENT_SCIENTIFIQUE:
        return invalide("contenu_pluridisciplinaire_force_dans_une_matiere")
    if len(ds) == 1 and matiere_proposee not in (Matiere.ENSEIGNEMENT_SCIENTIFIQUE, *ds):
        return invalide("matiere_non_justifiee_par_la_source")
    return valide("rattachement_justifie")


def verifier_notion_es(notion: Notion, disciplines_source: Optional[Iterable[Matiere]]) -> Resultat:
    """Une notion d'ES doit déclarer exactement les disciplines indiquées par la source."""
    if notion.matiere != Matiere.ENSEIGNEMENT_SCIENTIFIQUE:
        return verifier_rattachement(notion.matiere, disciplines_source)
    if disciplines_source is None:
        return revue("disciplines_source_inconnues")
    attendu = set(disciplines_source) - {Matiere.ENSEIGNEMENT_SCIENTIFIQUE}
    declare = set(notion.disciplines_mobilisees)
    if declare != attendu:
        manquantes = sorted(d.value for d in attendu - declare)
        inventees = sorted(d.value for d in declare - attendu)
        return invalide(*[f"discipline_manquante:{d}" for d in manquantes],
                        *[f"discipline_non_justifiee:{d}" for d in inventees])
    return valide("disciplines_conformes_a_la_source")
