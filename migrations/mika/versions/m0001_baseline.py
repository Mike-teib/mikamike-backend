"""baseline : schéma historique (tables créées auparavant par create_all à l'import)

Une base créée par l'ancien code s'adopte avec `python -m tools.db stamp-existant mika`.

Revision ID: m0001_baseline
Revises: 
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'm0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mika_etats',
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('competence', sa.String(length=64), nullable=False),
    sa.Column('etat', sa.String(length=32), nullable=False),
    sa.Column('maj', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('eleve_hmac', 'competence')
    )
    op.create_table('mika_tentatives',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('exercice_id', sa.String(length=64), nullable=False),
    sa.Column('matiere', sa.String(length=32), nullable=False),
    sa.Column('niveau', sa.String(length=32), nullable=False),
    sa.Column('competence', sa.String(length=64), nullable=False),
    sa.Column('est_correct', sa.Boolean(), nullable=False),
    sa.Column('avec_aide', sa.Boolean(), nullable=False),
    sa.Column('ts', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mika_tentatives', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_tentatives_eleve_hmac'), ['eleve_hmac'], unique=False)
    op.create_table('mika_memory_schedules',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('notion_id', sa.String(length=64), nullable=False),
    sa.Column('statut_fragilite', sa.Boolean(), nullable=False),
    sa.Column('repetition_count', sa.Integer(), nullable=False),
    sa.Column('intervalle_jours', sa.Integer(), nullable=False),
    sa.Column('force_memoire_s', sa.Float(), nullable=False),
    sa.Column('derniers_succes_consecutifs', sa.Integer(), nullable=False),
    sa.Column('prochain_rappel_date', sa.DateTime(), nullable=False),
    sa.Column('derniere_mise_a_jour', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mika_memory_schedules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_memory_schedules_eleve_hmac'), ['eleve_hmac'], unique=False)
        batch_op.create_index(batch_op.f('ix_mika_memory_schedules_notion_id'), ['notion_id'], unique=False)
    op.create_table('mika_session_states',
    sa.Column('session_id', sa.String(length=64), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_activity_ts', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('state_json', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('session_id')
    )
    with op.batch_alter_table('mika_session_states', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_session_states_eleve_hmac'), ['eleve_hmac'], unique=False)


def downgrade() -> None:
    op.drop_table('mika_session_states')
    op.drop_table('mika_memory_schedules')
    op.drop_table('mika_tentatives')
    op.drop_table('mika_etats')
