"""
Migrations Alembic (lot B, CLOUD_DB_MIGRATION_PLAN.md).

Chaque scénario tourne dans un sous-processus avec ses PROPRES bases SQLite jetables
(les engines sont liés à l'import) : aucune base réelle n'est touchée.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path, code: str, **env_extra) -> dict:
    env = {
        **os.environ,
        "MIKA_DB_URL": f"sqlite:///{tmp_path / 'mika.db'}",
        "BILLING_DB_URL": f"sqlite:///{tmp_path / 'billing.db'}",
        "MIKA_JWT_SECRET": "test-jwt-secret-not-for-prod-0123456789",
        "MIKA_PSEUDO_SECRET": "test-pseudo-secret-not-for-prod-0123456789",
        **env_extra,
    }
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=RACINE, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


TABLES = """
from sqlalchemy import inspect
from app.db.registre import engines
def tables():
    return {c: sorted(t for t in inspect(e).get_table_names() if t != "alembic_version")
            for c, e in engines().items()}
"""


def test_import_de_l_application_ne_cree_aucune_table(tmp_path):
    out = _run(tmp_path, TABLES + """
import json, main  # noqa
print(json.dumps(tables()))
""")
    assert out == {"mika": [], "billing": []}


def test_upgrade_head_egal_aux_modeles(tmp_path):
    out = _run(tmp_path, TABLES + """
import json
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData
from app.db import migrations as m
from app.db.registre import engines, metadatas
diffs = {}
for c in ("mika", "billing"):
    m.upgrade(c)
    md = MetaData()
    for x in metadatas(c):
        for t in x.tables.values():
            t.to_metadata(md)
    with engines()[c].connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diffs[c] = [str(d) for d in compare_metadata(ctx, md)]
print(json.dumps({"diffs": diffs, "etat": m.etat(), "tables": tables()}))
""")
    assert out["diffs"] == {"mika": [], "billing": []}
    for c in ("mika", "billing"):
        assert out["etat"][c]["courante"] == out["etat"][c]["head"]
    assert "mika_tutorat_sessions" in out["tables"]["mika"]
    assert "liens_compte_eleve" in out["tables"]["billing"]


def test_downgrade_jusqu_a_base_puis_reupgrade(tmp_path):
    out = _run(tmp_path, TABLES + """
import json
from app.db import migrations as m
for c in ("mika", "billing"):
    m.upgrade(c)
    m.downgrade(c, "base")
vide = tables()
for c in ("mika", "billing"):
    m.upgrade(c)
print(json.dumps({"vide": vide, "plein": tables()}))
""")
    assert out["vide"] == {"mika": [], "billing": []}
    assert len(out["plein"]["mika"]) == 6 and len(out["plein"]["billing"]) == 3


def test_demarrage_refuse_si_schema_absent(tmp_path):
    out = _run(tmp_path, """
import json
from fastapi.testclient import TestClient
from app.db.migrations import SchemaNonAJour
import main
try:
    with TestClient(main.app):
        pass
    print(json.dumps({"refuse": False}))
except SchemaNonAJour as exc:
    print(json.dumps({"refuse": True, "msg": str(exc)}))
""", MIKA_DB_INIT="check")
    assert out["refuse"] and "tools.db upgrade" in out["msg"]


def test_demarrage_migrate_puis_check(tmp_path):
    out = _run(tmp_path, """
import json
from fastapi.testclient import TestClient
import main
with TestClient(main.app) as c:
    code = c.get("/health").status_code
from app.db.migrations import initialiser_au_demarrage
print(json.dumps({"code": code, "mode": initialiser_au_demarrage("check")}))
""", MIKA_DB_INIT="migrate")
    assert out == {"code": 200, "mode": "check"}


def test_mode_init_invalide_refuse(tmp_path):
    out = _run(tmp_path, """
import json
from app.db.migrations import SchemaNonAJour, initialiser_au_demarrage
try:
    initialiser_au_demarrage("create_all")
    print(json.dumps({"refuse": False}))
except SchemaNonAJour:
    print(json.dumps({"refuse": True}))
""")
    assert out["refuse"]


def test_adoption_base_historique_conserve_les_donnees(tmp_path):
    out = _run(tmp_path, TABLES + """
import json
from sqlalchemy import text
from app.db import migrations as m
from app.db.registre import engines
# Base « historique » : exactement ce que créait l'ancien create_all (sans les tables récentes).
from app.api.v1.mikamike.store import MikaBase
from app.api.v1.memory.spaced_repetition import MemoryBase
from app.api.v1.session.session_manager import SessionBase
e = engines()["mika"]
for md in (MikaBase.metadata, MemoryBase.metadata, SessionBase.metadata):
    md.create_all(bind=e)
with e.begin() as conn:
    conn.execute(text("INSERT INTO mika_etats (eleve_hmac, competence, etat, maj) "
                      "VALUES ('h', 'c', 'EN_COURS', '2026-01-01 00:00:00')"))
m.adopter_base_existante("mika", m.BASELINE_REVISION["mika"])
m.upgrade("mika")
with e.connect() as conn:
    n = conn.execute(text("SELECT count(*) FROM mika_etats")).scalar()
print(json.dumps({"n": n, "etat": m.etat()["mika"], "tables": tables()["mika"]}))
""")
    assert out["n"] == 1
    assert out["etat"]["courante"] == out["etat"]["head"]
    assert "mika_tutorat_sessions" in out["tables"]


@pytest.mark.parametrize("prep,attendu", [
    ("", "vide"),
    ("m.upgrade('mika')", "déjà versionnée"),
    ("from app.api.v1.mikamike.store import MikaBase; MikaBase.metadata.create_all(bind=engines()['mika'])",
     "tables manquantes"),
])
def test_adoption_refusee_si_base_non_conforme(tmp_path, prep, attendu):
    out = _run(tmp_path, f"""
import json
from app.db import migrations as m
from app.db.registre import engines
{prep}
try:
    m.adopter_base_existante("mika", m.BASELINE_REVISION["mika"])
    print(json.dumps({{"msg": "adoptee"}}))
except m.SchemaNonAJour as exc:
    print(json.dumps({{"msg": str(exc)}}))
""")
    assert attendu in out["msg"]


def test_sql_hors_ligne_pour_revue(tmp_path):
    env = {**os.environ, "MIKA_DB_URL": f"sqlite:///{tmp_path / 'm.db'}",
           "BILLING_DB_URL": f"sqlite:///{tmp_path / 'b.db'}"}
    r = subprocess.run([sys.executable, "-m", "tools.db", "sql", "mika"], cwd=RACINE, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "CREATE TABLE mika_tutorat_sessions" in r.stdout
    assert not (tmp_path / "m.db").exists() or (tmp_path / "m.db").stat().st_size == 0
