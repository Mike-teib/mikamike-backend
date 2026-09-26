"""baseline : comptes + abonnements (schéma historique)

Une base créée par l'ancien code s'adopte avec `python -m tools.db stamp-existant billing`.

Revision ID: b0001_baseline
Revises: 
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'b0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('comptes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('mot_de_passe_hash', sa.String(length=255), nullable=False),
    sa.Column('prenom', sa.String(length=120), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('actif', sa.Boolean(), nullable=False),
    sa.Column('email_verifie', sa.Boolean(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('derniere_connexion', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('comptes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_comptes_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_comptes_id'), ['id'], unique=False)
    op.create_table('abonnements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('compte_id', sa.Integer(), nullable=False),
    sa.Column('statut', sa.Enum('AUCUN', 'ESSAI', 'ACTIF', 'IMPAYE', 'ANNULE', 'EXPIRE', name='statutabonnement'), nullable=False),
    sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
    sa.Column('fin_periode_courante', sa.DateTime(timezone=True), nullable=True),
    sa.Column('annulation_programmee', sa.Boolean(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('maj_le', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['compte_id'], ['comptes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('compte_id')
    )
    with op.batch_alter_table('abonnements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_abonnements_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_abonnements_stripe_customer_id'), ['stripe_customer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_abonnements_stripe_subscription_id'), ['stripe_subscription_id'], unique=False)


def downgrade() -> None:
    op.drop_table('abonnements')
    op.drop_table('comptes')
