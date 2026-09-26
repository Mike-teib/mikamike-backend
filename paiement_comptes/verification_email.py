"""
verification_email.py — Vérification de l'adresse e-mail d'un compte (R19).

Cycle : PARENT_CREATED → EMAIL_UNVERIFIED → VERIFICATION_TOKEN_CREATED → EMAIL_VERIFIED
        → INVITATION_ACCEPT_ALLOWED (liens.accepter_invitation exige email_verifie).

Jeton : 256 bits (`secrets.token_urlsafe(32)`), transmis UNIQUEMENT par courriel ; seule son
empreinte HMAC est stockée ; usage unique ; expiration (MIKA_EMAIL_VERIF_TTL_MIN, 24 h par
défaut) ; lié à l'ADRESSE ciblée (un changement d'adresse invalide les jetons en cours) ; tous
les jetons du compte sont invalidés dès qu'une vérification réussit.
Pas d'énumération : la confirmation ne prend que le jeton et répond de la même façon pour
inconnu / expiré / utilisé / adresse changée.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
import secrets
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, delete, select, update
from sqlalchemy.orm import Session

from paiement_comptes.database import Base

TTL_DEFAUT_MIN = 24 * 60
TTL_BORNES = (10, 7 * 24 * 60)
MAX_JETONS_ACTIFS = 3


def _maintenant() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


class VerificationEmail(Base):
    __tablename__ = "verifications_email"

    id = Column(Integer, primary_key=True)
    compte_id = Column(Integer, ForeignKey("comptes.id", ondelete="CASCADE"), nullable=False, index=True)
    jeton_hash = Column(String(64), nullable=False, unique=True)
    email_cible = Column(String(255), nullable=False)
    cree_le = Column(DateTime, nullable=False)
    expire_le = Column(DateTime, nullable=False)
    utilise_le = Column(DateTime, nullable=True)


class JetonVerificationInvalide(ValueError):
    """Inconnu, expiré, déjà utilisé, ou adresse modifiée depuis l'émission (réponse unique)."""


def verification_requise() -> bool:
    """MIKA_EMAIL_VERIFICATION = requise (défaut) | off (refusé en production)."""
    brut = (os.getenv("MIKA_EMAIL_VERIFICATION") or "requise").strip().lower()
    if brut not in ("requise", "off"):
        raise ValueError("MIKA_EMAIL_VERIFICATION invalide (requise | off)")
    if brut == "off" and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):
        raise ValueError("MIKA_EMAIL_VERIFICATION=off interdit en production")
    return brut == "requise"


def ttl_min() -> int:
    try:
        v = int(os.getenv("MIKA_EMAIL_VERIF_TTL_MIN", str(TTL_DEFAUT_MIN)))
    except ValueError as exc:
        raise ValueError("MIKA_EMAIL_VERIF_TTL_MIN non entier") from exc
    if not TTL_BORNES[0] <= v <= TTL_BORNES[1]:
        raise ValueError(f"MIKA_EMAIL_VERIF_TTL_MIN hors {TTL_BORNES}")
    return v


def _empreinte(jeton: str) -> str:
    from app.core.security_config import get_jwt_secret

    cle = hmac.new(get_jwt_secret().encode("utf-8"), b"mikamike/verification-email/v1", hashlib.sha256).digest()
    return hmac.new(cle, jeton.encode("utf-8"), hashlib.sha256).hexdigest()


def creer_jeton(db: Session, compte) -> str:
    """Nouveau jeton pour l'adresse ACTUELLE du compte ; renvoie le jeton en clair (à envoyer
    par courriel, jamais renvoyé dans une réponse HTTP). Au plus 3 jetons actifs par compte :
    le plus ancien est retiré."""
    now = _maintenant()
    db.execute(delete(VerificationEmail).where(VerificationEmail.compte_id == compte.id,
                                               VerificationEmail.utilise_le.is_(None),
                                               VerificationEmail.expire_le <= now))
    actifs = db.execute(select(VerificationEmail.id).where(
        VerificationEmail.compte_id == compte.id, VerificationEmail.utilise_le.is_(None))
        .order_by(VerificationEmail.id.asc())).scalars().all()
    for vid in actifs[:max(0, len(actifs) - MAX_JETONS_ACTIFS + 1)]:
        db.execute(delete(VerificationEmail).where(VerificationEmail.id == vid))
    jeton = secrets.token_urlsafe(32)
    db.add(VerificationEmail(compte_id=compte.id, jeton_hash=_empreinte(jeton), email_cible=compte.email,
                             cree_le=now, expire_le=now + _dt.timedelta(minutes=ttl_min())))
    db.commit()
    return jeton


def confirmer(db: Session, jeton: str) -> int:
    """Marque l'adresse vérifiée ; renvoie l'id du compte. Consommation ATOMIQUE (deux clics
    simultanés : un seul gagne ; l'autre reçoit la réponse générique)."""
    from paiement_comptes.models_billing import Compte

    if not jeton or len(jeton) > 128:
        raise JetonVerificationInvalide("jeton_invalide_ou_expire")
    now = _maintenant()
    v = db.execute(select(VerificationEmail).where(VerificationEmail.jeton_hash == _empreinte(jeton))).scalar_one_or_none()
    if v is None or v.utilise_le is not None or v.expire_le <= now:
        raise JetonVerificationInvalide("jeton_invalide_ou_expire")
    compte = db.get(Compte, v.compte_id)
    if compte is None or not compte.actif or compte.email != v.email_cible:
        raise JetonVerificationInvalide("jeton_invalide_ou_expire")
    res = db.execute(update(VerificationEmail).where(
        VerificationEmail.id == v.id, VerificationEmail.utilise_le.is_(None), VerificationEmail.expire_le > now,
    ).values(utilise_le=now))
    if res.rowcount != 1:
        db.rollback()
        raise JetonVerificationInvalide("jeton_invalide_ou_expire")
    compte.email_verifie = True
    # Tous les autres jetons du compte deviennent inutiles : invalidés.
    db.execute(delete(VerificationEmail).where(VerificationEmail.compte_id == compte.id,
                                               VerificationEmail.utilise_le.is_(None)))
    cid = compte.id
    db.commit()
    return cid


def invalider_jetons(db: Session, compte_id: int) -> int:
    """Changement d'adresse, suppression de compte : aucun jeton en cours ne survit."""
    n = db.execute(delete(VerificationEmail).where(VerificationEmail.compte_id == compte_id)).rowcount or 0
    return n


def etat(db: Session, compte) -> dict:
    en_attente = db.execute(select(VerificationEmail.id).where(
        VerificationEmail.compte_id == compte.id, VerificationEmail.utilise_le.is_(None),
        VerificationEmail.expire_le > _maintenant())).first() is not None
    statut = "EMAIL_VERIFIED" if compte.email_verifie else (
        "VERIFICATION_TOKEN_CREATED" if en_attente else "EMAIL_UNVERIFIED")
    return {"statut": statut, "email_verifie": bool(compte.email_verifie)}


def verification_ok_pour_invitation(compte) -> Optional[str]:
    """None si le compte peut valider une invitation, sinon le code d'erreur."""
    if verification_requise() and not compte.email_verifie:
        return "email_non_verifie"
    return None
