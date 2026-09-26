"""R11 : index composite (eleve_hmac, competence, ts) sur mika_tentatives

Revision ID: m0002_index_tentatives
Revises: m0001_baseline
Create Date: 2026-09-26
"""
from alembic import context, op
import sqlalchemy as sa


revision = 'm0002_index_tentatives'
down_revision = 'm0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent : une base adoptée (stamp-existant) peut déjà porter l'index si elle a été
    # créée par un create_all postérieur à l'ajout de l'index au modèle.
    if not context.is_offline_mode():
        existants = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('mika_tentatives')}
        if 'ix_mika_tentatives_eleve_competence_ts' in existants:
            return
    with op.batch_alter_table('mika_tentatives', schema=None) as batch_op:
        batch_op.create_index('ix_mika_tentatives_eleve_competence_ts', ['eleve_hmac', 'competence', 'ts'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('mika_tentatives', schema=None) as batch_op:
        batch_op.drop_index('ix_mika_tentatives_eleve_competence_ts')
