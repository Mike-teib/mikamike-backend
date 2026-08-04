"""
crud_billing.py — Accès données pour comptes + abonnements.

Fichier NEUF livré par CC. Aucune écriture destructive, aucune modification de
schéma existant. Toutes les fonctions prennent une `Session` SQLAlchemy fournie
par l'appelant (dépendance `get_db` du projet).

Hash de mot de passe : passlib/bcrypt si présent, sinon fallback PBKDF2-HMAC de
la stdlib pour rester importable sans dépendance supplémentaire.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
from typing import Optional

from sqlalchemy.orm import Session

from paiement_comptes.models_billing import Abonnement, Compte, StatutAbonnement

# --------------------------------------------------------------------------- #
# Hachage mot de passe
# --------------------------------------------------------------------------- #
# On utilise bcrypt DIRECTEMENT (comme le reste du repo) : passlib a un bug avec
# bcrypt >= 4.1 (lecture de version) et 5.x. Repli PBKDF2 stdlib si bcrypt absent.
try:
    import bcrypt as _bcrypt

    def hacher_mot_de_passe(mot_de_passe: str) -> str:
        # bcrypt ignore/rejette au-delà de 72 octets : on tronque explicitement.
        pw = mot_de_passe.encode("utf-8")[:72]
        return _bcrypt.hashpw(pw, _bcrypt.gensalt()).decode("utf-8")

    def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
        try:
            return _bcrypt.checkpw(
                mot_de_passe.encode("utf-8")[:72], hash_stocke.encode("utf-8")
            )
        except Exception:
            return False

except Exception:  # pragma: no cover - fallback stdlib
    _ITER = 240_000

    def hacher_mot_de_passe(mot_de_passe: str) -> str:
        sel = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), sel, _ITER)
        return f"pbkdf2_sha256${_ITER}${sel.hex()}${dk.hex()}"

    def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
        try:
            algo, iters, sel_hex, dk_hex = hash_stocke.split("$")
            if algo != "pbkdf2_sha256":
                return False
            dk = hashlib.pbkdf2_hmac(
                "sha256", mot_de_passe.encode(), bytes.fromhex(sel_hex), int(iters)
            )
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


# --------------------------------------------------------------------------- #
# Comptes
# --------------------------------------------------------------------------- #
def get_compte_par_email(db: Session, email: str) -> Optional[Compte]:
    email = (email or "").strip().lower()
    return db.query(Compte).filter(Compte.email == email).first()


def get_compte(db: Session, compte_id: int) -> Optional[Compte]:
    return db.query(Compte).filter(Compte.id == compte_id).first()


def creer_compte(
    db: Session,
    email: str,
    mot_de_passe: str,
    prenom: Optional[str] = None,
    role: str = "parent",
) -> Compte:
    """Crée un compte. Lève ValueError si l'email existe déjà."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("email_invalide")
    if len(mot_de_passe or "") < 8:
        raise ValueError("mot_de_passe_trop_court")
    if get_compte_par_email(db, email) is not None:
        raise ValueError("email_deja_utilise")

    compte = Compte(
        email=email,
        mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
        prenom=(prenom or None),
        role=role,
    )
    db.add(compte)
    db.flush()  # obtient l'id sans committer (l'appelant gère la transaction)

    # Abonnement vierge rattaché d'office
    db.add(Abonnement(compte_id=compte.id, statut=StatutAbonnement.AUCUN))
    db.commit()
    db.refresh(compte)
    return compte


def authentifier(db: Session, email: str, mot_de_passe: str) -> Optional[Compte]:
    compte = get_compte_par_email(db, email)
    if compte is None or not compte.actif:
        return None
    if not verifier_mot_de_passe(mot_de_passe, compte.mot_de_passe_hash):
        return None
    compte.derniere_connexion = _utcnow()
    db.commit()
    return compte


# --------------------------------------------------------------------------- #
# Abonnements
# --------------------------------------------------------------------------- #
def get_abonnement(db: Session, compte_id: int) -> Optional[Abonnement]:
    return (
        db.query(Abonnement).filter(Abonnement.compte_id == compte_id).first()
    )


def get_abonnement_par_customer(
    db: Session, stripe_customer_id: str
) -> Optional[Abonnement]:
    return (
        db.query(Abonnement)
        .filter(Abonnement.stripe_customer_id == stripe_customer_id)
        .first()
    )


def get_abonnement_par_subscription(
    db: Session, stripe_subscription_id: str
) -> Optional[Abonnement]:
    return (
        db.query(Abonnement)
        .filter(Abonnement.stripe_subscription_id == stripe_subscription_id)
        .first()
    )


def lier_customer(db: Session, compte_id: int, stripe_customer_id: str) -> Abonnement:
    ab = get_abonnement(db, compte_id)
    if ab is None:
        ab = Abonnement(compte_id=compte_id, statut=StatutAbonnement.AUCUN)
        db.add(ab)
    ab.stripe_customer_id = stripe_customer_id
    db.commit()
    db.refresh(ab)
    return ab


def maj_statut_abonnement(
    db: Session,
    *,
    stripe_subscription_id: str,
    statut: StatutAbonnement,
    stripe_customer_id: Optional[str] = None,
    stripe_price_id: Optional[str] = None,
    fin_periode_courante: Optional[_dt.datetime] = None,
    annulation_programmee: Optional[bool] = None,
) -> Optional[Abonnement]:
    """Met à jour l'abonnement depuis un événement webhook Stripe.

    Recherche par subscription_id puis par customer_id. Retourne None si aucun
    abonnement local ne correspond (événement à ignorer).
    """
    ab = get_abonnement_par_subscription(db, stripe_subscription_id)
    if ab is None and stripe_customer_id:
        ab = get_abonnement_par_customer(db, stripe_customer_id)
    if ab is None:
        return None

    ab.stripe_subscription_id = stripe_subscription_id
    ab.statut = statut
    if stripe_customer_id:
        ab.stripe_customer_id = stripe_customer_id
    if stripe_price_id:
        ab.stripe_price_id = stripe_price_id
    if fin_periode_courante is not None:
        ab.fin_periode_courante = fin_periode_courante
    if annulation_programmee is not None:
        ab.annulation_programmee = annulation_programmee

    db.commit()
    db.refresh(ab)
    return ab
