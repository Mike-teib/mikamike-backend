"""Invitations à usage unique pour créer un lien compte ↔ élève (décision D8)

Revision ID: b0003_invitations_lien
Revises: b0002_liens_compte_eleve
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'b0003_invitations_lien'
down_revision = 'b0002_liens_compte_eleve'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('invitations_lien',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('pseudo_id', sa.String(length=128), nullable=True),
    sa.Column('relation', sa.String(length=16), nullable=False),
    sa.Column('emis_par', sa.String(length=32), nullable=False),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.Column('expire_le', sa.DateTime(), nullable=False),
    sa.Column('utilise_le', sa.DateTime(), nullable=True),
    sa.Column('utilise_par', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_hash')
    )
    with op.batch_alter_table('invitations_lien', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invitations_lien_eleve_hmac'), ['eleve_hmac'], unique=False)


def downgrade() -> None:
    op.drop_table('invitations_lien')
