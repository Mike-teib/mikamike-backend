"""
Package front `frontend-contract/` (types, client fetch, machines d'état, tests contractuels) :
  1. `tsc --noEmit` passe (TypeScript strict, syntaxe effaçable uniquement) ;
  2. `node --test` passe (machines d'état + chaque appel de contrat_front/contrat.json) ;
  3. chaque `nom` de contrat.json est couvert par une méthode du client ;
  4. le test d'intégration Node passe contre un VRAI serveur uvicorn (mode enforce, courriel faux).

Le jeton de vérification d'adresse n'est jamais renvoyé par HTTP et le premier code d'invitation est
émis par l'opérateur : ce fichier sert aussi de HARNAIS côté serveur pour le test Node
(`python tests_cloud/test_frontend_contract_pkg.py --harnais jeton-verification <email>` |
`... --harnais invitation <pseudo>`), sur la même base que le serveur (BILLING_DB_URL).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
PKG = RACINE / "frontend-contract"


# --------------------------------------------------------------------------------------------- #
# Harnais (exécuté par le test Node via MIKA_CONTRACT_HELPER, jamais par pytest directement)
# --------------------------------------------------------------------------------------------- #
def _harnais(argv: list[str]) -> int:
    sys.path.insert(0, str(RACINE))
    from app.core.pseudonymisation import hmac_eleve
    from paiement_comptes import crud_billing, liens
    from paiement_comptes import verification_email as ve
    from paiement_comptes.database import SessionLocal

    commande, valeur = argv
    db = SessionLocal()
    try:
        if commande == "jeton-verification":
            compte = crud_billing.get_compte_par_email(db, valeur)
            if compte is None:
                print("compte inconnu", file=sys.stderr)
                return 1
            print(ve.creer_jeton(db, compte))  # équivalent du lien reçu par courriel
        elif commande == "invitation":
            code, _ = liens.creer_invitation(db, valeur, hmac_eleve(valeur), emis_par="operateur")
            print(code)
        else:
            print(f"commande inconnue : {commande}", file=sys.stderr)
            return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__" and sys.argv[1:2] == ["--harnais"]:
    sys.exit(_harnais(sys.argv[2:]))


# --------------------------------------------------------------------------------------------- #
# Tests pytest
# --------------------------------------------------------------------------------------------- #
import pytest  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None or shutil.which("npm") is None,
                                reason="Node/npm absents")


def _env_node(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIKA_CONTRACT_")}
    env.update(extra)
    return env


@pytest.fixture(scope="module")
def paquet() -> Path:
    if not (PKG / "node_modules" / "typescript").is_dir():
        r = subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=PKG, capture_output=True, text=True,
                           timeout=300)
        if r.returncode != 0:
            pytest.skip(f"npm ci impossible (réseau ?) : {r.stderr[-500:]}")
    return PKG


def _node_test(fichiers: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["node", "--test", *fichiers], cwd=PKG, capture_output=True, text=True, timeout=300,
                          env=env)


def _compteur(sortie: str, nom: str) -> int:
    for ligne in sortie.splitlines():
        if ligne.startswith(f"# {nom} "):
            return int(ligne.split()[-1])
    raise AssertionError(f"compteur « {nom} » absent de la sortie node --test")


def test_typescript_strict(paquet):
    tsc = paquet / "node_modules" / ".bin" / "tsc"
    r = subprocess.run([str(tsc), "--noEmit", "-p", "tsconfig.json"], cwd=paquet, capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


def test_version_typescript_epinglee(paquet):
    pkg = json.loads((paquet / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "@mikamike/frontend-contract" and pkg["private"] is True and pkg["type"] == "module"
    assert list(pkg["devDependencies"]) == ["typescript"]
    version = pkg["devDependencies"]["typescript"]
    assert version.startswith("5.") and version.replace(".", "").isdigit(), "version exacte 5.x attendue"
    verrou = json.loads((paquet / "package-lock.json").read_text(encoding="utf-8"))
    assert verrou["packages"]["node_modules/typescript"]["version"] == version
    assert "dependencies" not in pkg, "aucune dépendance d'exécution"


def test_node_test_machines_et_contrat(paquet):
    r = _node_test(["contract-tests/*.test.ts"], _env_node())
    sortie = r.stdout + r.stderr
    assert r.returncode == 0, sortie[-4000:]
    assert _compteur(r.stdout, "fail") == 0
    assert _compteur(r.stdout, "pass") >= 250
    assert "MIKA_CONTRACT_BASE_URL non définie" in r.stdout  # intégration ignorée EXPLICITEMENT


def test_chaque_appel_du_contrat_couvert_par_le_client(paquet):
    script = (
        "const m = await import('./client.ts');"
        "const proto = Object.getOwnPropertyNames(m.MikaClient.prototype);"
        "console.log(JSON.stringify({couverture: m.COUVERTURE_CONTRAT, routes: m.ROUTES, proto}));"
    )
    r = subprocess.run(["node", "--input-type=module", "-e", script], cwd=paquet, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stderr[-2000:]
    info = json.loads(r.stdout)
    contrat = json.loads((RACINE / "contrat_front" / "contrat.json").read_text(encoding="utf-8"))
    noms = [a["nom"] for a in contrat["appels"]]
    assert sorted(noms) == sorted(info["couverture"]), "contrat.json et COUVERTURE_CONTRAT divergent"
    for appel in contrat["appels"]:
        op = info["couverture"][appel["nom"]]
        assert op in info["proto"], f"{appel['nom']} : méthode {op} absente du client"
        route = info["routes"][op]
        assert route["methode"] == appel["methode"], appel["nom"]
        assert contrat["base"] + route["chemin"] == appel["chemin"], appel["nom"]


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_integration_node_contre_un_serveur_reel(paquet, tmp_path):
    port = _port_libre()
    env_serveur = {**os.environ, "MIKA_DB_URL": f"sqlite:///{tmp_path / 'mika.db'}",
                   "BILLING_DB_URL": f"sqlite:///{tmp_path / 'billing.db'}", "MIKA_DB_INIT": "migrate",
                   "MIKA_AUTH_MODE": "enforce", "MIKA_RATE_LIMIT": "on", "MIKA_EMAIL_TRANSPORT": "faux",
                   "MIKA_ENV": ""}
    serveur = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level",
                                "warning"], cwd=RACINE, env=env_serveur, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)  # nosec B310 (local)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("serveur non démarré")
        harnais = [sys.executable, str(Path(__file__).resolve()), "--harnais"]
        env = _env_node(**{k: v for k, v in env_serveur.items() if k.startswith(("MIKA_", "BILLING_"))},
                        MIKA_CONTRACT_BASE_URL=f"http://127.0.0.1:{port}",
                        MIKA_CONTRACT_HELPER=json.dumps(harnais))
        r = _node_test(["contract-tests/integration.test.ts"], env)
        sortie = r.stdout + r.stderr
        assert r.returncode == 0, sortie[-5000:]
        assert _compteur(r.stdout, "fail") == 0
        assert _compteur(r.stdout, "skipped") == 0, "aucune étape ne doit être ignorée avec serveur + harnais"
        assert _compteur(r.stdout, "pass") >= 12
    finally:
        serveur.terminate()
        serveur.wait(10)
