"""
Validation des migrations (session 3, MIGRATION_VALIDATION_REPORT.md) : base neuve, base
historique, stamp-existant, upgrade pas à pas, downgrade, version incorrecte, migration
interrompue, rollback, données préservées. Chaque scénario : sous-processus + SQLite jetables.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


def _env(tmp_path):
    return {**os.environ, "MIKA_DB_URL": f"sqlite:///{tmp_path / 'mika.db'}",
            "BILLING_DB_URL": f"sqlite:///{tmp_path / 'billing.db'}",
            "MIKA_JWT_SECRET": "test-jwt-secret-not-for-prod-0123456789",
            "MIKA_PSEUDO_SECRET": "test-pseudo-secret-not-for-prod-0123456789"}


def _py(tmp_path, code):
    r = subprocess.run([sys.executable, "-c", PRELUDE + textwrap.dedent(code)], cwd=RACINE, env=_env(tmp_path),
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _cli(tmp_path, *args):
    r = subprocess.run([sys.executable, "-m", "tools.db", *args], cwd=RACINE, env=_env(tmp_path),
                       capture_output=True, text=True, timeout=180)
    return r.returncode, r.stdout, r.stderr


PRELUDE = """
import hashlib, json
from sqlalchemy import inspect, text
from app.db import migrations as m
from app.db.registre import engines

def tables(c):
    return sorted(t for t in inspect(engines()[c]).get_table_names() if t != "alembic_version")

def empreinte(c, noms):
    # Empreinte du CONTENU (toutes colonnes, ordre stable) : prouve la préservation des données.
    h = hashlib.sha256()
    with engines()[c].connect() as conn:
        for t in noms:
            for row in conn.execute(text(f"SELECT * FROM {t} ORDER BY 1, 2")).fetchall():
                h.update(repr(tuple(row)).encode())
    return h.hexdigest()

def remplir_mika():
    with engines()["mika"].begin() as conn:
        for i in range(50):
            conn.execute(text("INSERT INTO mika_tentatives (eleve_hmac, exercice_id, matiere, niveau, competence, "
                              "est_correct, avec_aide, ts) VALUES (:h, :x, 'maths', '5e', :c, :ok, 0, "
                              "'2026-01-01 00:00:00')"), {"h": f"h{i % 7}", "x": f"exo-{i}", "c": f"c{i % 5}", "ok": i % 2})
        conn.execute(text("INSERT INTO mika_etats (eleve_hmac, competence, etat, maj) "
                          "VALUES ('h1', 'c1', 'EN_COURS', '2026-01-01 00:00:00')"))
        conn.execute(text("INSERT INTO mika_session_states (session_id, eleve_hmac, is_active, last_activity_ts, "
                          "created_at, state_json) VALUES ('s1', 'h1', 1, '2026-01-01 00:00:00', "
                          "'2026-01-01 00:00:00', '{\\"ardoise\\": \\"é∑\\"}')"))

def remplir_billing():
    with engines()["billing"].begin() as conn:
        conn.execute(text("INSERT INTO comptes (id, email, mot_de_passe_hash, role, actif, email_verifie, cree_le) "
                          "VALUES (1, 'fictif@example.com', 'x', 'parent', 1, 0, '2026-01-01 00:00:00')"))
        conn.execute(text("INSERT INTO abonnements (compte_id, statut, annulation_programmee, cree_le, maj_le) "
                          "VALUES (1, 'AUCUN', 0, '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))

HIST_MIKA = ["mika_etats", "mika_memory_schedules", "mika_session_states", "mika_tentatives"]
"""


# --------------------------------------------------------------------------- #
# Base neuve
# --------------------------------------------------------------------------- #
def test_base_neuve_cli_upgrade_status(tmp_path):
    assert _cli(tmp_path, "status")[0] == 1  # aucune révision : en retard
    code, out, _ = _cli(tmp_path, "upgrade")
    assert code == 0 and "mika: m0003_tutorat" in out and "billing: b0003_invitations_lien" in out
    code, out, _ = _cli(tmp_path, "status")
    assert code == 0 and out.count(" OK") == 2
    assert _cli(tmp_path, "upgrade")[0] == 0  # idempotent : relancer ne change rien


def test_upgrade_pas_a_pas_chaque_revision(tmp_path):
    out = _py(tmp_path, """
        vus = []
        for rev in ("m0001_baseline", "m0002_index_tentatives", "m0003_tutorat"):
            m.upgrade("mika", rev)
            vus.append([m.courante("mika"), tables("mika")])
        print(json.dumps(vus))
    """)
    assert [v[0] for v in out] == ["m0001_baseline", "m0002_index_tentatives", "m0003_tutorat"]
    assert "mika_tutorat_sessions" not in out[1][1] and "mika_tutorat_sessions" in out[2][1]


# --------------------------------------------------------------------------- #
# Base historique + stamp-existant (données préservées)
# --------------------------------------------------------------------------- #
def test_base_historique_adoptee_donnees_preservees(tmp_path):
    out = _py(tmp_path, """
        from app.api.v1.mikamike.store import MikaBase
        from app.api.v1.memory.spaced_repetition import MemoryBase
        from app.api.v1.session.session_manager import SessionBase
        import paiement_comptes.models_billing
        from paiement_comptes.database import Base
        for md in (MikaBase.metadata, MemoryBase.metadata, SessionBase.metadata):
            md.create_all(bind=engines()["mika"])
        Base.metadata.tables["comptes"].create(bind=engines()["billing"])
        Base.metadata.tables["abonnements"].create(bind=engines()["billing"])
        remplir_mika(); remplir_billing()
        avant = (empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"]))
        print(json.dumps({"avant": avant}))
    """)
    code, sortie, err = _cli(tmp_path, "stamp-existant", "mika")
    assert code == 0, err
    assert _cli(tmp_path, "stamp-existant", "billing")[0] == 0
    assert _cli(tmp_path, "stamp-existant", "mika")[0] == 1  # déjà versionnée : refus propre
    assert _cli(tmp_path, "upgrade")[0] == 0
    apres = _py(tmp_path, """
        print(json.dumps({"apres": (empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"])),
                          "etat": m.etat()}))
    """)
    assert apres["apres"] == out["avant"]
    assert all(e["courante"] == e["head"] for e in apres["etat"].values())


# --------------------------------------------------------------------------- #
# Downgrade / rollback de schéma : données des tables conservées préservées
# --------------------------------------------------------------------------- #
def test_downgrade_puis_upgrade_preserve_les_donnees_conservees(tmp_path):
    out = _py(tmp_path, """
        m.upgrade("mika"); m.upgrade("billing")
        remplir_mika(); remplir_billing()
        ref = (empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"]))
        m.downgrade("mika", "m0001_baseline"); m.downgrade("billing", "b0001_baseline")
        mi = (empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"]),
              tables("mika"), tables("billing"))
        m.upgrade("mika"); m.upgrade("billing")
        fin = (empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"]))
        print(json.dumps({"ref": ref, "mi": mi, "fin": fin, "etat": m.etat()}))
    """)
    assert out["mi"][:2] == out["ref"] and out["fin"] == out["ref"]
    assert "mika_tutorat_sessions" not in out["mi"][2] and "liens_compte_eleve" not in out["mi"][3]
    assert all(e["courante"] == e["head"] for e in out["etat"].values())


def test_downgrade_documente_la_perte_des_tables_retirees(tmp_path):
    out = _py(tmp_path, """
        m.upgrade("mika")
        with engines()["mika"].begin() as conn:
            conn.execute(text("INSERT INTO mika_tutorat_sessions (id, eleve_hmac, exercice_id, etat_json, "
                              "derniere_action, version, termine, cree_le, maj_le) VALUES ('t', 'h', 'x', '{}', "
                              "'A', 1, 0, '2026-01-01', '2026-01-01')"))
        m.downgrade("mika", "m0002_index_tentatives"); m.upgrade("mika")
        with engines()["mika"].connect() as conn:
            n = conn.execute(text("SELECT count(*) FROM mika_tutorat_sessions")).scalar()
        print(json.dumps({"n": n}))
    """)
    assert out["n"] == 0  # CLOUD_DB_MIGRATION_PLAN §6 : restaurer la sauvegarde si nécessaire


# --------------------------------------------------------------------------- #
# Version incorrecte
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", ["zzz_inconnue", "m9999_futur"])
def test_version_incorrecte_refus_propre(tmp_path, version):
    _py(tmp_path, f"""
        m.upgrade("mika"); m.upgrade("billing")
        with engines()["mika"].begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '{version}'"))
        print(json.dumps({{}}))
    """)
    code, out, err = _cli(tmp_path, "status")
    assert code == 1 and "EN RETARD" in out
    code, out, err = _cli(tmp_path, "upgrade", "mika")
    assert code == 1 and err.startswith("erreur:") and "Traceback" not in err
    out = _py(tmp_path, """
        try:
            m.initialiser_au_demarrage("check"); r = "demarre"
        except m.SchemaNonAJour as exc:
            r = str(exc)
        print(json.dumps({"r": r}))
    """)
    assert version in out["r"]  # le démarrage est refusé, message explicite


def test_cli_cible_inconnue_et_commande_inconnue(tmp_path):
    assert _cli(tmp_path, "upgrade", "compta")[0] == 1
    assert _cli(tmp_path, "nimportequoi")[0] == 2
    assert _cli(tmp_path)[0] == 2


# --------------------------------------------------------------------------- #
# Migration interrompue / rollback transactionnel
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cible,depart,table_coupee,table_creee_avant", [
    ("mika", "m0002_index_tentatives", "mika_tutorat_requetes", "mika_tutorat_sessions"),
    ("billing", "b0001_baseline", "liens_compte_eleve", None),
    ("mika", None, "mika_session_states", "mika_tentatives"),
])
def test_migration_interrompue_rollback_et_reprise(tmp_path, cible, depart, table_coupee, table_creee_avant):
    out = _py(tmp_path, f"""
        from alembic.operations import Operations
        if {depart!r}:
            m.upgrade({cible!r}, {depart!r})
            remplir_mika() if {cible!r} == "mika" else remplir_billing()
        cles = HIST_MIKA if {cible!r} == "mika" else ["comptes", "abonnements"]
        ref = empreinte({cible!r}, [t for t in cles if t in tables({cible!r})])
        version_ref, tables_ref = m.courante({cible!r}), tables({cible!r})
        orig = Operations.create_table
        def coupure(self, nom, *a, **k):
            if nom == {table_coupee!r}:
                raise RuntimeError("coupure simulee")
            return orig(self, nom, *a, **k)
        Operations.create_table = coupure
        try:
            m.upgrade({cible!r})
            coupe = False
        except RuntimeError:
            coupe = True
        Operations.create_table = orig
        apres = (m.courante({cible!r}), tables({cible!r}),
                 empreinte({cible!r}, [t for t in cles if t in tables({cible!r})]))
        m.upgrade({cible!r})
        print(json.dumps({{"coupe": coupe, "ref": [version_ref, tables_ref, ref], "apres": apres,
                           "reprise": m.courante({cible!r}), "head": m.head({cible!r})}}))
    """)
    assert out["coupe"]
    assert out["apres"][0] == out["ref"][0]  # version inchangée
    # Seules subsistent les révisions entièrement appliquées (m0001 pour la coupure en m0001,
    # rien du tout) : aucune table de la révision coupée.
    if table_creee_avant and out["ref"][0] is not None:
        assert table_creee_avant not in out["apres"][1]
    assert out["apres"][1] == out["ref"][1]
    assert out["apres"][2] == out["ref"][2]  # données préservées
    assert out["reprise"] == out["head"]


def test_downgrade_interrompu_atomique(tmp_path):
    out = _py(tmp_path, """
        from alembic.operations import Operations
        m.upgrade("mika")
        orig = Operations.drop_table
        def coupure(self, nom, *a, **k):
            if nom == "mika_tutorat_sessions":
                raise RuntimeError("coupure simulee")
            return orig(self, nom, *a, **k)
        Operations.drop_table = coupure
        try:
            m.downgrade("mika", "m0002_index_tentatives")
        except RuntimeError:
            pass
        Operations.drop_table = orig
        print(json.dumps({"v": m.courante("mika"), "t": tables("mika")}))
    """)
    assert out["v"] == "m0003_tutorat"
    assert {"mika_tutorat_sessions", "mika_tutorat_requetes"} <= set(out["t"])  # rien de défait à moitié
