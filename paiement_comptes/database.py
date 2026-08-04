"""
database.py — Persistance SQLite dédiée au module paiement/comptes.

Fournit la `Base`, l'`engine`, `SessionLocal`, `get_db` et `init_db`.
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


def init_db() -> None:
    """Crée les tables (idempotent).

    À appeler APRÈS que les modèles aient été définis. C'est `models_billing`
    qui l'invoque à la fin de son propre import : ainsi `Compte`/`Abonnement`
    sont déjà enregistrés sur `Base.metadata` quand `create_all` s'exécute.
    On NE l'appelle PAS ici (au chargement de database.py) : ça s'exécuterait
    pendant l'import de models_billing (déclenché par la ligne `from ... import
    Base`), donc AVANT la définition des classes -> tables jamais créées.
    """
    Base.metadata.create_all(bind=engine)
