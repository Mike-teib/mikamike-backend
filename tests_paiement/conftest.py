"""
conftest.py — Fixtures paiement/comptes sur l'app autonome (main:app).

Même préambule que tests_mika (posé avant tout import applicatif).
"""

import os
import tempfile

os.environ.setdefault(
    "MIKA_DB_URL", "sqlite:///" + os.path.join(tempfile.gettempdir(), "mika_backend_test.db")
)
os.environ.setdefault(
    "BILLING_DB_URL", "sqlite:///" + os.path.join(tempfile.gettempdir(), "billing_backend_test.db")
)
os.environ.setdefault("MIKA_JWT_SECRET", "test-jwt-secret-autonome")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from app.api.v1.mikamike.store import MikaBase, engine as mika_engine  # noqa: E402
from paiement_comptes.database import Base as BillingBase, engine as billing_engine  # noqa: E402


@pytest.fixture()
def client():
    for base, eng in ((MikaBase, mika_engine), (BillingBase, billing_engine)):
        base.metadata.drop_all(bind=eng)
        base.metadata.create_all(bind=eng)
    with TestClient(app) as c:
        yield c
