"""
quiz.py — Question de quiz (QCM à réponse unique) et contrôles.

Contrôles (codes) :
  NOTION_*                     mêmes verrous que les exercices (notion prouvée, cohérences)
  NIVEAU_INCOHERENT / MATIERE_INCOHERENTE
  INDEX_CORRECT_HORS_BORNES
  BONNE_REPONSE_INCORRECTE     le choix désigné n'est pas équivalent à la réponse de référence
  DOUBLE_BONNE_REPONSE         un distracteur est aussi jugé VALID (ex. « 1/2 » et « 0,5 »)
  DISTRACTEUR_INDECIDABLE      un distracteur est AMBIGUOUS / NEEDS_HUMAN_REVIEW
  CHOIX_DUPLIQUES              deux choix identiques après normalisation
  CHOIX_VIDE
  CHOIX_AMBIGU                 « toutes les réponses », « aucune des réponses »…
  DISTRACTEUR_NON_PLAUSIBLE    type différent de la bonne réponse (nombre vs texte)
  FUITE_REPONSE                la bonne réponse figure dans l'énoncé
  FUITE_LONGUEUR               la bonne réponse est nettement plus longue que les autres
  NON_EXPLICABLE               aucune explication fournie
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.curriculum import dedup
from app.curriculum.model import ID_CANONIQUE, IndexReferentiel, Matiere, Niveau
from app.curriculum.provenance import autorisation_generation
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import TYPES_VERIFICATION, verifier

_AMBIGUS = re.compile(r"\b(toutes? les r[ée]ponses|aucune (des|de ces) r[ée]ponses|les deux|je ne sais pas)\b", re.I)
_NUMERIQUE = re.compile(r"^[\s\d.,+\-−/×*^()²³√π]+[a-zA-Zµ°Ω/·.\s\d\-⁻¹²³]*$")


class QuestionQuiz(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_CANONIQUE)
    notion_id: str = Field(pattern=ID_CANONIQUE)
    matiere: Matiere
    niveau: Niveau
    enonce: str = Field(min_length=3, max_length=2000)
    choix: Tuple[str, ...] = Field(min_length=3, max_length=6)
    index_correct: int = Field(ge=0)
    # Réponse de référence INDÉPENDANTE des choix (clé de correction) : la bonne
    # réponse désignée doit lui être équivalente, et aucun distracteur ne doit l'être.
    reponse_reference: str = Field(min_length=1, max_length=500)
    type_verification: str
    parametres_verification: Dict[str, Any] = Field(default_factory=dict)
    explication: str = Field(default="", max_length=2000)


def _est_numerique(t: str) -> bool:
    return bool(_NUMERIQUE.match(t.strip()))


def verrous_notion(q, idx: IndexReferentiel, *, autoriser_fictif: bool = False) -> List[str]:
    """Verrous communs à tous les types de question (notion prouvée, niveau, matière)."""
    raisons: List[str] = []
    notion = idx.notions.get(q.notion_id)
    if notion is None:
        return ["NOTION_INCONNUE"]
    auto = autorisation_generation(notion, idx, autoriser_fictif=autoriser_fictif)
    if not auto.autorise:
        raisons.extend(f"NOTION_NON_AUTORISEE:{r}" for r in auto.raisons)
    if q.niveau != notion.niveau:
        raisons.append("NIVEAU_INCOHERENT")
    if q.matiere != notion.matiere:
        raisons.append("MATIERE_INCOHERENTE")
    return raisons


def valider_question(q: QuestionQuiz, idx: IndexReferentiel, *, autoriser_fictif: bool = False) -> List[str]:
    raisons = verrous_notion(q, idx, autoriser_fictif=autoriser_fictif)
    if raisons == ["NOTION_INCONNUE"]:
        return raisons

    if not 0 <= q.index_correct < len(q.choix):
        return raisons + ["INDEX_CORRECT_HORS_BORNES"]
    if q.type_verification not in TYPES_VERIFICATION:
        return raisons + ["TYPE_VERIFICATION_INCONNU"]

    bonne = q.choix[q.index_correct]
    norm = [dedup.normaliser(c) for c in q.choix]
    if any(not c for c in norm):
        raisons.append("CHOIX_VIDE")
    if len(set(norm)) != len(norm):
        raisons.append("CHOIX_DUPLIQUES")
    if any(_AMBIGUS.search(c) for c in q.choix):
        raisons.append("CHOIX_AMBIGU")

    ref = q.reponse_reference
    if verifier(q.type_verification, ref, bonne, q.parametres_verification).verdict != Verdict.VALID:
        raisons.append("BONNE_REPONSE_INCORRECTE")
    for i, c in enumerate(q.choix):
        if i == q.index_correct or not c.strip():
            continue
        v = verifier(q.type_verification, ref, c, q.parametres_verification).verdict
        if v == Verdict.VALID:
            raisons.append("DOUBLE_BONNE_REPONSE")
        elif v in (Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW):
            raisons.append("DISTRACTEUR_INDECIDABLE")
        if _est_numerique(c) != _est_numerique(bonne):
            raisons.append("DISTRACTEUR_NON_PLAUSIBLE")

    nb = dedup.normaliser(bonne)
    if len(nb) >= 2 and nb in dedup.normaliser(q.enonce):
        raisons.append("FUITE_REPONSE")
    autres = [len(c) for i, c in enumerate(q.choix) if i != q.index_correct]
    if autres and len(bonne) > 2 * max(autres) and len(bonne) > 20:
        raisons.append("FUITE_LONGUEUR")
    if not q.explication.strip():
        raisons.append("NON_EXPLICABLE")
    return sorted(set(raisons))
