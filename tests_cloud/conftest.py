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
# Bases JETABLES : schéma créé explicitement ci-dessous (pas de migration au démarrage).
os.environ.setdefault("MIKA_DB_INIT", "none")
# Anciens tests : contrat historique sans jeton (la couche d'autorisation est testée
# séparément en mode « enforce », cf. tests_cloud/test_auth.py).
os.environ.setdefault("MIKA_AUTH_MODE", "off")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from app.db.registre import creer_tables_pour_tests  # noqa: E402


creer_tables_pour_tests()


@pytest.fixture()
def client():
    # Isolation stricte : TOUTES les bases (mika + billing) neuves à chaque test.
    creer_tables_pour_tests(reinitialiser=True)
    with TestClient(app) as c:
        yield c
