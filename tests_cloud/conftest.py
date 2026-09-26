"""
conftest.py — Tests de non-régression de la mission cloud.

Même préambule que tests_mika : secrets de TEST factices et bases SQLite
jetables posés AVANT tout import applicatif. Aucune donnée réelle, aucun réseau.
"""

import os
import tempfile

os.environ.setdefault(
    "MIKA_DB_URL", "sqlite:///" + os.path.join(tempfile.gettempdir(), "mika_backend_test.db")
)
os.environ.setdefault(
    "BILLING_DB_URL", "sqlite:///" + os.path.join(tempfile.gettempdir(), "billing_backend_test.db")
)
os.environ.setdefault("MIKA_JWT_SECRET", "test-jwt-secret-not-for-prod-0123456789")
os.environ.setdefault("MIKA_PSEUDO_SECRET", "test-pseudo-secret-not-for-prod-0123456789")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1.memory.spaced_repetition import MemoryBase  # noqa: E402
from app.api.v1.mikamike.store import MikaBase, engine as mika_engine  # noqa: E402
from app.api.v1.session.session_manager import SessionBase  # noqa: E402
from main import app  # noqa: E402
from paiement_comptes.database import Base as BillingBase, engine as billing_engine  # noqa: E402


@pytest.fixture()
def client():
    # Isolation stricte : TOUTES les bases élève et billing neuves à chaque test.
    for base, eng in (
        (MikaBase, mika_engine),
        (MemoryBase, mika_engine),
        (SessionBase, mika_engine),
        (BillingBase, billing_engine),
    ):
        base.metadata.drop_all(bind=eng)
        base.metadata.create_all(bind=eng)
    with TestClient(app) as c:
        yield c
