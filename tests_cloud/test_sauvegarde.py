"""Session 5 — tools.sauvegarde : sauvegarde en ligne, vérification, restauration atomique."""

import json
import sqlite3

import pytest

from tests_cloud.test_migrations_validation import _cli, _env

import subprocess
import sys

from tests_cloud.test_migrations_validation import RACINE


def _outil(tmp_path, *args):
    r = subprocess.run([sys.executable, "-m", "tools.sauvegarde", *args], cwd=RACINE, env=_env(tmp_path),
                       capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def _compter(p, table):
    con = sqlite3.connect(p)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608 (nom fixe)
    finally:
        con.close()


@pytest.fixture()
def bases(tmp_path):
    assert _cli(tmp_path, "upgrade")[0] == 0
    con = sqlite3.connect(tmp_path / "billing.db")
    con.execute("INSERT INTO comptes (id, email, mot_de_passe_hash, role, actif, email_verifie, cree_le, jeton_version) "
                "VALUES (1, 'sauve@example.com', 'x', 'parent', 1, 0, '2026-01-01 00:00:00', 0)")
    con.commit()
    con.close()
    return tmp_path


def test_sauvegarde_verification_restauration(bases):
    code, out, err = _outil(bases, "sauvegarder", "--dest", str(bases / "sv"))
    assert code == 0, err
    meta = json.loads(out)
    assert meta["bases"]["billing"]["revision"] == "b0004_verif_email_revocation"
    assert meta["bases"]["mika"]["revision"] == "m0003_tutorat"
    assert _outil(bases, "verifier", "--source", str(bases / "sv"))[0] == 0
    # Incident : la base billing est vidée après la sauvegarde.
    con = sqlite3.connect(bases / "billing.db")
    con.execute("DELETE FROM comptes")
    con.commit()
    con.close()
    assert _outil(bases, "restaurer", "--source", str(bases / "sv"))[0] == 2  # --confirmer exigé
    code, _, err = _outil(bases, "restaurer", "--source", str(bases / "sv"), "--confirmer")
    assert code == 0, err
    assert _compter(bases / "billing.db", "comptes") == 1
    assert list(bases.glob("billing.db.avant-restauration-*"))  # l'état d'avant est conservé
    assert _cli(bases, "status")[0] == 0


def test_sauvegarde_alteree_refusee(bases):
    assert _outil(bases, "sauvegarder", "--dest", str(bases / "sv"))[0] == 0
    with (bases / "sv" / "mika.db").open("ab") as f:
        f.write(b"x")
    assert _outil(bases, "verifier", "--source", str(bases / "sv"))[0] == 2
    assert _outil(bases, "restaurer", "--source", str(bases / "sv"), "--confirmer")[0] == 2


def test_refus_sans_ecrasement_ni_base_non_sqlite(bases, monkeypatch):
    assert _outil(bases, "sauvegarder", "--dest", str(bases / "sv"))[0] == 0
    assert _outil(bases, "sauvegarder", "--dest", str(bases / "sv"))[0] == 2  # jamais écraser
    from tools import sauvegarde

    monkeypatch.setenv("MIKA_DB_URL", "postgresql://hote/base")
    assert sauvegarde.main(["sauvegarder", "--dest", str(bases / "autre")]) == 2
