"""
Contrat front exécutable (FRONT_IMPLEMENTATION_PACK.md) :
  1. l'API n'a pas dérivé de `contrat_front/contrat.json` (régénéré en processus isolé) ;
  2. le vérificateur Node du front passe contre un VRAI serveur uvicorn (bases jetables,
     schéma appliqué par les migrations, mode enforce).
"""

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


def test_api_conforme_au_contrat_front():
    r = subprocess.run([sys.executable, "-m", "tools.contrat_front", "--verifier"], cwd=RACINE,
                       capture_output=True, text=True, timeout=300, env={**os.environ, "MIKA_ENV": ""})
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node absent")
def test_verificateur_node_contre_un_serveur_reel(tmp_path):
    port = _port_libre()
    env = {**os.environ, "MIKA_DB_URL": f"sqlite:///{tmp_path / 'mika.db'}",
           "BILLING_DB_URL": f"sqlite:///{tmp_path / 'billing.db'}", "MIKA_DB_INIT": "migrate",
           "MIKA_AUTH_MODE": "enforce", "MIKA_RATE_LIMIT": "on", "MIKA_EMAIL_TRANSPORT": "faux", "MIKA_ENV": ""}
    serveur = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level",
                                "warning"], cwd=RACINE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)  # nosec B310 (local)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("serveur non démarré")
        r = subprocess.run(["node", "contrat_front/verifier_contrat.mjs", f"http://127.0.0.1:{port}"], cwd=RACINE,
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
        assert "contrat respecté" in r.stdout
    finally:
        serveur.terminate()
        serveur.wait(10)
