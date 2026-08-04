"""
models_billing.py — Modèles SQLAlchemy pour les comptes self-service et
l'abonnement MikaMike.

Fichier NEUF livré par CC. Ne modifie aucun modèle existant.
À importer depuis main.py / la base commune (voir A_CABLER_DANS_MAIN.md).

On réutilise la `Base` déclarative du projet si elle est déjà exposée
(``from database import Base``). Sinon on retombe sur une Base locale afin que
le module reste importable seul (tests unitaires, création de tables isolée).
"""

from __future__ import annotations

import datetime as _dt
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from paiement_comptes.database import Base


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


class StatutAbonnement(str, enum.Enum):
    """Cycle de vie d'un abonnement, calqué sur les états Stripe utiles."""

    AUCUN = "aucun"            # jamais abonné
    ESSAI = "essai"           # période d'essai / trialing
    ACTIF = "actif"           # active — accès complet
    IMPAYE = "impaye"         # past_due / unpaid — relance
    ANNULE = "annule"         # canceled — accès jusqu'à fin de période
    EXPIRE = "expire"         # période terminée, accès coupé


class Compte(Base):
    """Compte parent/élève créé en self-service (remplace les comptes en dur)."""

    __tablename__ = "comptes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String(255), nullable=False)
    prenom = Column(String(120), nullable=True)          # prénom élève (mineur) — minimisation
    role = Column(String(20), nullable=False, default="parent")  # parent | eleve | admin
    actif = Column(Boolean, nullable=False, default=True)
    email_verifie = Column(Boolean, nullable=False, default=False)

    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    derniere_connexion = Column(DateTime(timezone=True), nullable=True)

    abonnement = relationship(
        "Abonnement",
        back_populates="compte",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Abonnement(Base):
    """Abonnement mensuel Stripe rattaché à un compte."""

    __tablename__ = "abonnements"

    id = Column(Integer, primary_key=True, index=True)
    compte_id = Column(
        Integer, ForeignKey("comptes.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    statut = Column(
        Enum(StatutAbonnement), nullable=False, default=StatutAbonnement.AUCUN
    )

    # Identifiants Stripe (jamais de données carte stockées côté MikaMike)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    fin_periode_courante = Column(DateTime(timezone=True), nullable=True)
    annulation_programmee = Column(Boolean, nullable=False, default=False)

    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    maj_le = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    compte = relationship("Compte", back_populates="abonnement")

    @property
    def acces_autorise(self) -> bool:
        """True si l'abonnement ouvre l'accès payant (essai ou actif)."""
        return self.statut in (StatutAbonnement.ESSAI, StatutAbonnement.ACTIF)


# Les classes ci-dessus sont maintenant enregistrées sur Base.metadata :
# on crée les tables MAINTENANT (et pas au chargement de database.py, qui
# s'exécute trop tôt dans la chaîne d'import — cf. commentaire de init_db()).
from paiement_comptes.database import init_db as _init_db  # noqa: E402

_init_db()
