"""Tutorat Mika : état de séance versionné + journal d'idempotence (API /mika/session)

Revision ID: m0003_tutorat
Revises: m0002_index_tentatives
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'm0003_tutorat'
down_revision = 'm0002_index_tentatives'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mika_tutorat_sessions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('exercice_id', sa.String(length=128), nullable=False),
    sa.Column('etat_json', sa.Text(), nullable=False),
    sa.Column('derniere_action', sa.String(length=32), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('termine', sa.Boolean(), nullable=False),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.Column('maj_le', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mika_tutorat_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_tutorat_sessions_eleve_hmac'), ['eleve_hmac'], unique=False)
    op.create_table('mika_tutorat_requetes',
    sa.Column('tutorat_id', sa.String(length=36), nullable=False),
    sa.Column('requete_id', sa.String(length=128), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('empreinte', sa.String(length=64), nullable=False),
    sa.Column('reponse_json', sa.Text(), nullable=False),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('tutorat_id', 'requete_id')
    )
    with op.batch_alter_table('mika_tutorat_requetes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_tutorat_requetes_eleve_hmac'), ['eleve_hmac'], unique=False)


def downgrade() -> None:
    op.drop_table('mika_tutorat_requetes')
    op.drop_table('mika_tutorat_sessions')
