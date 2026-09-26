"""
migrations.py — Application et contrôle des migrations Alembic (bases « mika » et « billing »).

Utilisé par `tools/db.py` (CLI) et par le démarrage de l'application :
  MIKA_DB_INIT=check   (défaut) refuse de démarrer si une base n'est pas à la révision head ;
  MIKA_DB_INIT=migrate applique les migrations au démarrage (dev / conteneur éphémère) ;
  MIKA_DB_INIT=none    aucune action (bases jetables de test, schéma créé par la fixture).
Aucune URL ni secret n'est écrit ici : les URL viennent de MIKA_DB_URL / BILLING_DB_URL.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine

from app.db.registre import CIBLES, engines

RACINE = Path(__file__).resolve().parents[2]
MODES_INIT = ("check", "migrate", "none")


class SchemaNonAJour(RuntimeError):
    """Base absente de l'historique de migration ou en retard sur head (fail-closed)."""


def config(cible: str) -> Config:
    if cible not in CIBLES:
        raise ValueError(f"cible_inconnue:{cible}")
    cfg = Config()
    cfg.set_main_option("script_location", str(RACINE / "migrations" / cible))
    cfg.set_main_option("version_table", "alembic_version")
    # `%` doublé : ConfigParser interpole les valeurs ; une URL dont le mot de passe est
    # encodé (`p%40ss`) faisait planter toutes les commandes (revue session 3, S3-02).
    url = engines()[cible].url.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def ddl_transactionnel_sqlite(engine: Engine) -> None:
    """pysqlite valide implicitement avant chaque DDL : une migration interrompue laissait des
    tables sans version. On passe le pilote en mode autocommit et on émet BEGIN nous-mêmes :
    la révision entière (DDL + mise à jour d'alembic_version) devient atomique."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _connect(dbapi_connection, _record):  # pragma: no cover - trivial
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(conn):  # pragma: no cover - trivial
        conn.exec_driver_sql("BEGIN")


def head(cible: str) -> str:
    return ScriptDirectory.from_config(config(cible)).get_current_head()


def courante(cible: str) -> Optional[str]:
    with engines()[cible].connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def upgrade(cible: str, revision: str = "head") -> None:
    command.upgrade(config(cible), revision)


def downgrade(cible: str, revision: str) -> None:
    command.downgrade(config(cible), revision)


def etat() -> Dict[str, Dict[str, Optional[str]]]:
    return {c: {"courante": courante(c), "head": head(c)} for c in CIBLES}


def verifier_a_jour() -> None:
    for c, e in etat().items():
        if e["courante"] != e["head"]:
            raise SchemaNonAJour(
                f"base {c} : révision {e['courante'] or 'aucune'} ≠ head {e['head']} — "
                f"exécuter `python -m tools.db upgrade` (ou `stamp-existant` pour une base créée "
                f"avant les migrations, cf. CLOUD_DB_MIGRATION_PLAN.md)"
            )


def adopter_base_existante(cible: str, baseline: str) -> str:
    """
    Base créée AVANT les migrations (create_all historique) : vérifie que les tables du
    baseline sont présentes, puis marque la base à la révision `baseline` (sans DDL).
    Refuse une base vide (utiliser upgrade) ou une base déjà versionnée.
    """
    if courante(cible) is not None:
        raise SchemaNonAJour(f"base {cible} déjà versionnée")
    attendues = BASELINE_TABLES[cible]
    presentes = set(inspect(engines()[cible]).get_table_names())
    if not presentes:
        raise SchemaNonAJour(f"base {cible} vide : utiliser upgrade")
    manquantes = sorted(set(attendues) - presentes)
    if manquantes:
        raise SchemaNonAJour(f"base {cible} incomplète, tables manquantes : {','.join(manquantes)}")
    command.stamp(config(cible), baseline)
    return baseline


def initialiser_au_demarrage(mode: Optional[str] = None) -> str:
    mode = (mode or os.getenv("MIKA_DB_INIT", "check")).strip().lower()
    if mode not in MODES_INIT:
        raise SchemaNonAJour(f"MIKA_DB_INIT invalide : {mode!r} (attendu : {', '.join(MODES_INIT)})")
    if mode == "migrate":
        for c in CIBLES:
            upgrade(c)
    if mode in ("migrate", "check"):
        verifier_a_jour()
    return mode


# Tables présentes dans les bases créées par le code historique (create_all à l'import).
BASELINE_TABLES = {
    "mika": ("mika_tentatives", "mika_etats", "mika_memory_schedules", "mika_session_states"),
    "billing": ("comptes", "abonnements"),
}
BASELINE_REVISION = {"mika": "m0001_baseline", "billing": "b0001_baseline"}
