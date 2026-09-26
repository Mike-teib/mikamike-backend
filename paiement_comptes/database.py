"""
database.py — Persistance SQLite dédiée au module paiement/comptes.

Fournit la `Base`, l'`engine`, `SessionLocal` et `get_db`. Le schéma est appliqué par
les migrations (`python -m tools.db upgrade`), jamais à l'import.
Base séparée du module MikaMike : ses tables (comptes, abonnements)
ne collisionnent avec rien.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

BILLING_DB_URL = os.getenv("BILLING_DB_URL", "sqlite:///./billing.db")

engine = create_engine(
    BILLING_DB_URL,
    connect_args={"check_same_thread": False} if BILLING_DB_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    """Dépendance FastAPI : session synchrone par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
