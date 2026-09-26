"""Quiz HTTP : tentatives versionnées + journal d'idempotence (API /quiz, session 6)

Revision ID: m0004_quiz
Revises: m0003_tutorat
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'm0004_quiz'
down_revision = 'm0003_tutorat'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mika_quiz_tentatives',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('question_id', sa.String(length=128), nullable=False),
    sa.Column('notion_id', sa.String(length=64), nullable=False),
    sa.Column('etat', sa.String(length=16), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('avec_aide', sa.Boolean(), nullable=False),
    sa.Column('aides', sa.Integer(), nullable=False),
    sa.Column('verdict', sa.String(length=16), nullable=True),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.Column('maj_le', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mika_quiz_tentatives', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_quiz_tentatives_eleve_hmac'), ['eleve_hmac'], unique=False)
    op.create_table('mika_quiz_requetes',
    sa.Column('tentative_id', sa.String(length=32), nullable=False),
    sa.Column('requete_id', sa.String(length=128), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('empreinte', sa.String(length=64), nullable=False),
    sa.Column('reponse_json', sa.Text(), nullable=False),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('tentative_id', 'requete_id')
    )
    with op.batch_alter_table('mika_quiz_requetes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mika_quiz_requetes_eleve_hmac'), ['eleve_hmac'], unique=False)


def downgrade() -> None:
    op.drop_table('mika_quiz_requetes')
    op.drop_table('mika_quiz_tentatives')
