"""
contenu.py — Catalogue des questions de quiz servies par HTTP (fail-closed, session 6).

Une question n'est servie que si elle franchit la validation de conception de son type
(`quiz.valider_question` pour le QCM, `quiz_types.valider` pour vrai/faux, réponse courte,
classement, association), dont les verrous de notion (notion PROVEN, matière, niveau).
Catalogue par défaut VIDE (aucun contenu réel publié) ⇒ 404 ; les tests installent un catalogue
FICTIF (`autoriser_fictif=True`, interdit en production). Seuls les contenus PUBLISHED doivent
y être chargés en production (garde de publication).
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Union

from app.curriculum import quiz as quiz_qcm
from app.curriculum import quiz_types
from app.curriculum.model import IndexReferentiel, Referentiel
from app.curriculum.quiz import QuestionQuiz

QuestionServie = Union[QuestionQuiz, quiz_types.Question]


class QuestionIndisponible(LookupError):
    pass


def type_de(q: QuestionServie) -> str:
    return "qcm" if isinstance(q, QuestionQuiz) else q.type


def raisons(q: QuestionServie, idx: IndexReferentiel, *, autoriser_fictif: bool) -> List[str]:
    if isinstance(q, QuestionQuiz):
        return quiz_qcm.valider_question(q, idx, autoriser_fictif=autoriser_fictif)
    return list(quiz_types.valider(q, idx, autoriser_fictif=autoriser_fictif))


class CatalogueQuiz:
    def __init__(self, referentiel: Referentiel, questions: Sequence[QuestionServie], *,
                 autoriser_fictif: bool = False):
        if autoriser_fictif and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):
            raise ValueError("contenu_fictif_interdit_en_production")
        self.idx = referentiel.index()
        self.autoriser_fictif = autoriser_fictif
        self.questions: Dict[str, QuestionServie] = {q.id: q for q in questions}

    def valide(self, q: QuestionServie) -> bool:
        return len(q.id) <= 128 and len(q.notion_id) <= 64 and not raisons(
            q, self.idx, autoriser_fictif=self.autoriser_fictif)

    def obtenir(self, question_id: str) -> QuestionServie:
        q = self.questions.get(question_id)
        if q is None or not self.valide(q):
            raise QuestionIndisponible(question_id)
        return q

    def pour_notion(self, notion_id: str) -> List[QuestionServie]:
        """Questions servables d'une notion, ordre déterministe (identifiant)."""
        return [q for _, q in sorted(self.questions.items()) if q.notion_id == notion_id and self.valide(q)]


_CATALOGUE: Optional[CatalogueQuiz] = None


def definir_catalogue(c: Optional[CatalogueQuiz]) -> None:
    global _CATALOGUE
    _CATALOGUE = c


def catalogue() -> CatalogueQuiz:
    return _CATALOGUE if _CATALOGUE is not None else CatalogueQuiz(Referentiel(), [])
