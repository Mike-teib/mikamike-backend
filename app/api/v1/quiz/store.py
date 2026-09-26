"""
store.py — Persistance des tentatives de quiz (API /quiz, contrat `mika-quiz/1`, session 6).

Base « mika » (pseudonymisée HMAC). Minimisation : la RÉPONSE de l'élève n'est jamais stockée
(seulement le verdict) ; la clé de correction reste dans le catalogue de contenu.
  - mika_quiz_tentatives : une tentative = une question, état EN_COURS → TERMINEE, versionnée ;
  - mika_quiz_requetes   : journal d'idempotence (même requete_id ⇒ même réponse).
Les deux tables portent `eleve_hmac` : registre RGPD (export + effacement).
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

QuizBase = declarative_base()


def _utcnow_naive() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


class QuizTentative(QuizBase):
    __tablename__ = "mika_quiz_tentatives"

    id = Column(String(32), primary_key=True)             # dérivé serveur (élève + requete_id)
    eleve_hmac = Column(String(32), index=True, nullable=False)
    question_id = Column(String(128), nullable=False)
    notion_id = Column(String(64), nullable=False)
    etat = Column(String(16), nullable=False, default="EN_COURS")   # EN_COURS | TERMINEE
    version = Column(Integer, nullable=False, default=1)
    avec_aide = Column(Boolean, nullable=False, default=False)      # monotone
    aides = Column(Integer, nullable=False, default=0)
    verdict = Column(String(16), nullable=True)                     # CORRECT | INCORRECT | A_REVOIR
    cree_le = Column(DateTime, nullable=False, default=_utcnow_naive)
    maj_le = Column(DateTime, nullable=False, default=_utcnow_naive, onupdate=_utcnow_naive)


class QuizRequete(QuizBase):
    __tablename__ = "mika_quiz_requetes"

    tentative_id = Column(String(32), primary_key=True)
    requete_id = Column(String(128), primary_key=True)
    eleve_hmac = Column(String(32), index=True, nullable=False)
    empreinte = Column(String(64), nullable=False)
    reponse_json = Column(Text, nullable=False)
    cree_le = Column(DateTime, nullable=False, default=_utcnow_naive)
