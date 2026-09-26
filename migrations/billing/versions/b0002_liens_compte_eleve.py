"""Liens compte ↔ élève (autorisation parent/élève, AUTH_CONTRACT.md)

Revision ID: b0002_liens_compte_eleve
Revises: b0001_baseline
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'b0002_liens_compte_eleve'
down_revision = 'b0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('liens_compte_eleve',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('compte_id', sa.Integer(), nullable=False),
    sa.Column('eleve_hmac', sa.String(length=32), nullable=False),
    sa.Column('relation', sa.String(length=16), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['compte_id'], ['comptes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('compte_id', 'eleve_hmac', name='uq_lien_compte_eleve')
    )
    with op.batch_alter_table('liens_compte_eleve', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_liens_compte_eleve_compte_id'), ['compte_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_liens_compte_eleve_eleve_hmac'), ['eleve_hmac'], unique=False)


def downgrade() -> None:
    op.drop_table('liens_compte_eleve')
