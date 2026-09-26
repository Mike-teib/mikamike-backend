"""
registre.py — Registre UNIQUE des schémas (metadata SQLAlchemy) par base.

Deux bases physiques :
  - « mika »    (MIKA_DB_URL)    : données d'apprentissage pseudonymisées (HMAC) ;
  - « billing » (BILLING_DB_URL) : comptes, abonnements, liens compte ↔ élève.

Aucun module applicatif ne crée de table à l'import (revue session 2, R2-07) :
le schéma est appliqué par les migrations (`python -m tools.db upgrade`).
`creer_tables_pour_tests` n'existe que pour les bases jetables des tests.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine

CIBLES = ("mika", "billing")


def metadatas(cible: str) -> List[MetaData]:
    """Metadata des modèles d'une base (import paresseux : aucun effet de bord)."""
    if cible == "mika":
        from app.api.v1.memory.spaced_repetition import MemoryBase
        from app.api.v1.mikamike.store import MikaBase
        from app.api.v1.session.session_manager import SessionBase
        from app.api.v1.tutorat.store import TutoratBase

        return [MikaBase.metadata, MemoryBase.metadata, SessionBase.metadata, TutoratBase.metadata]
    if cible == "billing":
        import paiement_comptes.liens  # noqa: F401  (enregistre la table des liens)
        import paiement_comptes.models_billing  # noqa: F401
        from paiement_comptes.database import Base

        return [Base.metadata]
    raise ValueError(f"cible_inconnue:{cible}")


def engines() -> Dict[str, Engine]:
    from app.api.v1.mikamike.store import engine as mika_engine
    from paiement_comptes.database import engine as billing_engine

    return {"mika": mika_engine, "billing": billing_engine}


def creer_tables_pour_tests(*, reinitialiser: bool = False) -> None:
    """Bases JETABLES de test uniquement : (re)crée toutes les tables sans migration."""
    for cible, eng in engines().items():
        for md in metadatas(cible):
            if reinitialiser:
                md.drop_all(bind=eng)
            md.create_all(bind=eng)
