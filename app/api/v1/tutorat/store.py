"""
store.py — Persistance de l'état de tutorat Mika (API /mika/session/*).

Deux tables, dans la base « mika » (pseudonymisée HMAC, jamais de PII) :
  - mika_tutorat_sessions : état explicite de la machine à états du tuteur,
    versionné (verrou optimiste : `version` incrémentée à chaque transition) ;
  - mika_tutorat_requetes : journal d'idempotence (une requête rejouée avec le
    même `requete_id` renvoie la MÊME réponse, sans nouvelle transition).
Les deux tables portent `eleve_hmac` : elles figurent dans le registre RGPD
(export + effacement), ce qu'un test vérifie.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

TutoratBase = declarative_base()


def _utcnow_naive() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


class TutoratSession(TutoratBase):
    __tablename__ = "mika_tutorat_sessions"

    id = Column(String(36), primary_key=True)  # uuid4 hex, généré par le SERVEUR
    eleve_hmac = Column(String(32), index=True, nullable=False)
    exercice_id = Column(String(128), nullable=False)
    etat_json = Column(Text, nullable=False)
    derniere_action = Column(String(32), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    termine = Column(Boolean, nullable=False, default=False)
    cree_le = Column(DateTime, nullable=False, default=_utcnow_naive)
    maj_le = Column(DateTime, nullable=False, default=_utcnow_naive, onupdate=_utcnow_naive)


class TutoratRequete(TutoratBase):
    __tablename__ = "mika_tutorat_requetes"

    tutorat_id = Column(String(36), primary_key=True)
    requete_id = Column(String(128), primary_key=True)
    eleve_hmac = Column(String(32), index=True, nullable=False)
    empreinte = Column(String(64), nullable=False)  # SHA-256 (type d'action + corps canonique)
    reponse_json = Column(Text, nullable=False)
    cree_le = Column(DateTime, nullable=False, default=_utcnow_naive)
