"""Vérification d'adresse e-mail (R19) + version de jetons pour la révocation (session 4)

Revision ID: b0004_verif_email_revocation
Revises: b0003_invitations_lien
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'b0004_verif_email_revocation'
down_revision = 'b0003_invitations_lien'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('comptes', schema=None) as batch_op:
        # server_default : les comptes existants reçoivent 0 (aucune perte, aucun jeton révoqué).
        batch_op.add_column(sa.Column('jeton_version', sa.Integer(), nullable=False, server_default='0'))
    op.create_table('verifications_email',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('compte_id', sa.Integer(), nullable=False),
    sa.Column('jeton_hash', sa.String(length=64), nullable=False),
    sa.Column('email_cible', sa.String(length=255), nullable=False),
    sa.Column('cree_le', sa.DateTime(), nullable=False),
    sa.Column('expire_le', sa.DateTime(), nullable=False),
    sa.Column('utilise_le', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['compte_id'], ['comptes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('jeton_hash')
    )
    with op.batch_alter_table('verifications_email', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_verifications_email_compte_id'), ['compte_id'], unique=False)


def downgrade() -> None:
    op.drop_table('verifications_email')
    with op.batch_alter_table('comptes', schema=None) as batch_op:
        batch_op.drop_column('jeton_version')
