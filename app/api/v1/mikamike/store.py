"""
store.py — Persistance SQLite dédiée MikaMike.

Réécrit à partir de `database.py` + `models.py` du Drive en un module cohérent
et SYNCHRONE (SQLAlchemy ORM 2.x). Le `crud_student.py` du Drive était en
psycopg async et incompatible avec la session synchrone `get_db` : on repart sur
l'ORM, plus sûr et testable.

Base propre (`MikaBase`) : metadata distincte, isolée des autres modules.
"""

from __future__ import annotations

import datetime as _dt
import os

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

MikaBase = declarative_base()

# URL configurable ; SQLite fichier dédié par défaut.
MIKA_DB_URL = os.getenv("MIKA_DB_URL", "sqlite:///./mikamike_backend.db")

engine = create_engine(
    MIKA_DB_URL,
    connect_args={"check_same_thread": False} if MIKA_DB_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


class TentativeExercice(MikaBase):
    """Journal des tentatives (pseudonymisé HMAC, aucune PII)."""

    __tablename__ = "mika_tentatives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eleve_hmac = Column(String(32), index=True, nullable=False)  # HMAC-SHA256[:16]
    exercice_id = Column(String(64), nullable=False)
    matiere = Column(String(32), nullable=False, default="")
    niveau = Column(String(32), nullable=False, default="")
    competence = Column(String(64), nullable=False, default="")
    est_correct = Column(Boolean, nullable=False, default=False)
    avec_aide = Column(Boolean, nullable=False, default=False)
    ts = Column(DateTime, nullable=False, default=_utcnow)


class EtatCompetence(MikaBase):
    """État de maîtrise courant par (élève HMAC, compétence)."""

    __tablename__ = "mika_etats"

    eleve_hmac = Column(String(32), primary_key=True)
    competence = Column(String(64), primary_key=True)
    etat = Column(String(32), nullable=False, default="INCONNU")
    maj = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)


def init_db() -> None:
    """Crée les tables MikaMike si absentes (idempotent)."""
    MikaBase.metadata.create_all(bind=engine)


def get_db():
    """Dépendance FastAPI : session synchrone par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Création des tables au chargement (fichier SQLite local, effet de bord bénin).
init_db()
