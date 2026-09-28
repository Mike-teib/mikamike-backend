"""Serveur E2E jetable pour tester le vrai frontend contre le vrai backend MikaMike.

Données fictives uniquement. Ne doit jamais être utilisé en production.
"""
from __future__ import annotations

import os
import tempfile

_tmp = tempfile.gettempdir()
os.environ["MIKA_DB_URL"] = "sqlite:///" + os.path.join(_tmp, "mika_front_e2e.db")
os.environ["BILLING_DB_URL"] = "sqlite:///" + os.path.join(_tmp, "billing_front_e2e.db")
os.environ["MIKA_JWT_SECRET"] = "e2e-jwt-secret-not-for-prod-0123456789"
os.environ["MIKA_PSEUDO_SECRET"] = "e2e-pseudo-secret-not-for-prod-0123456789"
os.environ["MIKA_DB_INIT"] = "none"
os.environ["MIKA_AUTH_MODE"] = "enforce"
os.environ["MIKA_RATE_LIMIT"] = "on"
os.environ["MIKA_ENV"] = "test"
os.environ["MIKA_EMAIL_TRANSPORT"] = "faux"
os.environ["MIKA_EMAIL_VERIFICATION"] = "off"
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:4173"

from app.db.registre import creer_tables_pour_tests

creer_tables_pour_tests(reinitialiser=True)

from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
