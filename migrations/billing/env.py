"""env.py Alembic — base « billing ». L'URL vient de la configuration (tools/db.py), jamais d'un secret en dur."""

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.migrations import ddl_transactionnel_sqlite
from app.db.registre import metadatas

config = context.config
target_metadata = metadatas("billing")


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is None:
        connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                         prefix="sqlalchemy.", poolclass=pool.NullPool)
        # SQLite : DDL réellement transactionnel (revue session 3, S3-03 — une migration
        # interrompue laissait des tables créées sans version, reprise impossible).
        ddl_transactionnel_sqlite(connectable)
        with connectable.connect() as connection:
            _executer(connection)
    else:
        _executer(connectable)


def _executer(connection) -> None:
    # render_as_batch : ALTER TABLE compatible SQLite (recopie de table transactionnelle).
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
