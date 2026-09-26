"""
legacy.py — Migration du référentiel historique (parcours/curriculum_dataset.py)
vers le modèle canonique, SANS rien inventer.

- Aucune source officielle n'accompagne l'existant ⇒ toutes les notions migrées
  sont NOT_EVIDENCED (preuve absente) et SOURCE_NOT_EVIDENCED (texte non prouvé).
- Aucun chapitre n'existe ⇒ chapitre_id = None (NOTION_SANS_CHAPITRE).
- Le niveau « primaire » ne permet pas de choisir entre CM1 et CM2 (et couvre
  aussi le cycle 2, hors périmètre) ⇒ ces notions NE SONT PAS migrées : elles
  sont listées dans `non_migrables` avec la raison.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Tuple

from app.api.v1.parcours.curriculum_dataset import CURRICULA_DATA
from app.curriculum.ids import slug
from app.curriculum.model import Matiere, Niveau, Notion, StatutTexte

_MATIERES: Dict[str, Matiere] = {
    "maths": Matiere.MATHEMATIQUES,
    "physique": Matiere.PHYSIQUE_CHIMIE,
    "chimie": Matiere.PHYSIQUE_CHIMIE,
    "svt": Matiere.SVT,
}
_NIVEAUX: Dict[str, Niveau] = {
    "6e": Niveau.SIXIEME, "5e": Niveau.CINQUIEME, "4e": Niveau.QUATRIEME,
    "3e": Niveau.TROISIEME, "2de": Niveau.SECONDE, "1re": Niveau.PREMIERE,
    "tle": Niveau.TERMINALE,
}


def id_notion_historique(id_hist: str) -> str:
    return f"notion:historique:{slug(id_hist)}"


def programme_non_source(matiere: Matiere, niveau: Niveau) -> str:
    """Identifiant de programme NON ENREGISTRÉ (aucune source) pour l'existant."""
    return f"prog:non-source:{matiere.value}:{slug(niveau.value)}"


class Migration(NamedTuple):
    notions: Tuple[Notion, ...]
    non_migrables: Tuple[Tuple[str, str], ...]  # (id historique, raison)


def migrer_existant() -> Migration:
    notions: List[Notion] = []
    rejets: List[Tuple[str, str]] = []
    migrables = {
        n.notion_id
        for (lvl, sub), groupe in CURRICULA_DATA.items()
        for n in groupe
        if lvl in _NIVEAUX and sub in _MATIERES
    }
    for (lvl, sub), groupe in sorted(CURRICULA_DATA.items()):
        for node in groupe:
            if lvl not in _NIVEAUX:
                rejets.append((node.notion_id, f"niveau_ambigu:{lvl}"))
                continue
            if sub not in _MATIERES:
                rejets.append((node.notion_id, f"matiere_inconnue:{sub}"))
                continue
            matiere, niveau = _MATIERES[sub], _NIVEAUX[lvl]
            notions.append(Notion(
                id=id_notion_historique(node.notion_id),
                programme_id=programme_non_source(matiere, niveau),
                chapitre_id=None,
                niveau=niveau,
                matiere=matiere,
                texte=node.titre,
                statut_texte=StatutTexte.SOURCE_NOT_EVIDENCED,
                preuve=None,
                # Prérequis vers des notions non migrées (primaire) : écartés, pas inventés.
                prerequis=tuple(id_notion_historique(p) for p in node.prerequisite_ids if p in migrables),
                id_historique=node.notion_id,
            ))
    return Migration(tuple(notions), tuple(rejets))
