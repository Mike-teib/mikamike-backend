"""Session 5 — tools.smoke contre un VRAI serveur uvicorn (bases jetables migrées, enforce)."""

import os
import subprocess
import sys
import time
import urllib.request

import pytest

from tests_cloud.test_contrat_front import RACINE, _port_libre


@pytest.fixture()
def serveur(tmp_path):
    port = _port_libre()
    env = {**os.environ, "MIKA_DB_URL": f"sqlite:///{tmp_path / 'mika.db'}",
           "BILLING_DB_URL": f"sqlite:///{tmp_path / 'billing.db'}", "MIKA_DB_INIT": "migrate",
           "MIKA_AUTH_MODE": "enforce", "MIKA_RATE_LIMIT": "on", "MIKA_EMAIL_TRANSPORT": "faux", "MIKA_ENV": "staging"}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
                         cwd=RACINE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)  # nosec B310 (local)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("serveur non démarré")
        yield f"http://127.0.0.1:{port}"
    finally:
        p.terminate()
        p.wait(10)


def test_smoke_lecture_et_ecriture_vertes(serveur, capsys):
    from tools import smoke

    assert smoke.main(["--url", serveur]) == 0
    assert smoke.main(["--url", serveur, "--ecriture", "--email", "smoke.rc1@example.com"]) == 0
    sortie = capsys.readouterr().out
    assert "KO" not in sortie and "inscription_201" in sortie


def test_smoke_detecte_un_serveur_absent():
    from tools import smoke

    assert smoke.main(["--url", f"http://127.0.0.1:{_port_libre()}"]) == 1


def test_smoke_usage():
    from tools import smoke

    assert smoke.main(["--url", "http://x", "--ecriture"]) == 2
    assert smoke.main([]) == 2
