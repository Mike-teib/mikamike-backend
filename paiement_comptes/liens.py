"""
liens.py — Autorisation compte ↔ élève (qui peut agir sur quel pseudo-id).

Un pseudo-id seul n'authentifie personne (revue session 2, R2-18). L'accès d'un
compte aux données d'un élève exige une ligne ici :
  relation = "parent" : compte parent autorisé pour cet enfant ;
  relation = "eleve"  : compte élève titulaire de ce pseudo-id.
L'élève est désigné par son HMAC (jamais le pseudo-id ni une PII en clair).

La CRÉATION des liens passe EXCLUSIVEMENT par une invitation à code unique (décision D8,
section « Invitations » ci-dessous, routes /liens/*). `lier` reste une fonction interne
(tests, outils), sans route publique.
"""

from __future__ import annotations

import base64 as _b64
import datetime as _dt
import hashlib as _hashlib
import hmac as _hmac
import os as _os
import re as _re
import secrets as _secrets
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, delete, select, update
from sqlalchemy.orm import Session

from paiement_comptes.database import Base

RELATIONS = ("parent", "eleve")


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


class LienCompteEleve(Base):
    __tablename__ = "liens_compte_eleve"
    __table_args__ = (UniqueConstraint("compte_id", "eleve_hmac", name="uq_lien_compte_eleve"),)

    id = Column(Integer, primary_key=True)
    compte_id = Column(Integer, ForeignKey("comptes.id", ondelete="CASCADE"), nullable=False, index=True)
    eleve_hmac = Column(String(32), nullable=False, index=True)
    relation = Column(String(16), nullable=False)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


def lier(db: Session, compte_id: int, eleve_hmac: str, relation: str) -> LienCompteEleve:
    if relation not in RELATIONS:
        raise ValueError("relation_inconnue")
    lien = LienCompteEleve(compte_id=compte_id, eleve_hmac=eleve_hmac, relation=relation)
    db.add(lien)
    db.commit()
    return lien


def relation(db: Session, compte_id: int, eleve_hmac: str) -> Optional[str]:
    return db.execute(
        select(LienCompteEleve.relation).where(
            LienCompteEleve.compte_id == compte_id, LienCompteEleve.eleve_hmac == eleve_hmac
        )
    ).scalar_one_or_none()


def supprimer_liens_eleve(db: Session, eleve_hmac: str) -> int:
    n = db.execute(delete(LienCompteEleve).where(LienCompteEleve.eleve_hmac == eleve_hmac)).rowcount or 0
    db.commit()
    return n


# --------------------------------------------------------------------------- #
# Invitations (décision D8) : SEUL moyen public de créer un lien compte ↔ élève.
#   - code à USAGE UNIQUE, EXPIRABLE, NON DEVINABLE (120 bits aléatoires, `secrets`) ;
#   - seule son empreinte HMAC est stockée (une fuite de la base ne livre aucun code) ;
#   - validation EXPLICITE par un compte connecté du bon rôle (parent), jamais par la seule
#     connaissance d'un pseudo-id ou d'un identifiant ;
#   - consommation atomique (UPDATE … WHERE utilise_le IS NULL AND expire_le > maintenant).
# --------------------------------------------------------------------------- #
TTL_INVITATION_DEFAUT_MIN = 48 * 60
TTL_INVITATION_BORNES = (10, 7 * 24 * 60)
MAX_INVITATIONS_ACTIVES = 5
_ALPHABET = _re.compile(r"^[A-Z2-7]{24}$")


def _maintenant() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


class InvitationLien(Base):
    __tablename__ = "invitations_lien"

    id = Column(Integer, primary_key=True)
    code_hash = Column(String(64), nullable=False, unique=True)
    eleve_hmac = Column(String(32), nullable=False, index=True)
    # Pseudo-id transmis au compte qui ACCEPTE (il en a besoin pour demander un jeton élève) ;
    # effacé dès l'acceptation (minimisation) et à la purge des invitations expirées.
    pseudo_id = Column(String(128), nullable=True)
    relation = Column(String(16), nullable=False)
    emis_par = Column(String(32), nullable=False)
    cree_le = Column(DateTime, nullable=False)
    expire_le = Column(DateTime, nullable=False)
    utilise_le = Column(DateTime, nullable=True)
    utilise_par = Column(Integer, nullable=True)


class InvitationInvalide(ValueError):
    """Code inconnu, déjà utilisé, expiré ou rôle incompatible : UNE seule erreur (pas d'oracle)."""


def ttl_invitation_min() -> int:
    try:
        ttl = int(_os.getenv("MIKA_INVITATION_TTL_MIN", str(TTL_INVITATION_DEFAUT_MIN)))
    except ValueError as exc:
        raise ValueError("MIKA_INVITATION_TTL_MIN non entier") from exc
    if not TTL_INVITATION_BORNES[0] <= ttl <= TTL_INVITATION_BORNES[1]:
        raise ValueError(f"MIKA_INVITATION_TTL_MIN hors {TTL_INVITATION_BORNES}")
    return ttl


def _empreinte(code_normalise: str) -> str:
    from app.core.security_config import get_jwt_secret

    cle = _hmac.new(get_jwt_secret().encode("utf-8"), b"mikamike/invitation-lien/v1", _hashlib.sha256).digest()
    return _hmac.new(cle, code_normalise.encode("ascii"), _hashlib.sha256).hexdigest()


def normaliser_code(code: str) -> Optional[str]:
    """Tolère casse, espaces et tirets ; tout autre format ⇒ None (refus sans requête SQL)."""
    brut = _re.sub(r"[\s\-]", "", code or "").upper()
    return brut if _ALPHABET.fullmatch(brut) else None


def formater_code(code: str) -> str:
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def purger_invitations_expirees(db: Session) -> int:
    n = db.execute(delete(InvitationLien).where(InvitationLien.utilise_le.is_(None),
                                                InvitationLien.expire_le <= _maintenant())).rowcount or 0
    return n


def creer_invitation(db: Session, pseudo_id: str, eleve_hmac: str, *, relation: str = "parent",
                     emis_par: str) -> tuple[str, InvitationLien]:
    """Renvoie (code en clair, À AFFICHER UNE SEULE FOIS ; invitation). Rien d'autre ne le conserve."""
    if relation not in RELATIONS:
        raise ValueError("relation_inconnue")
    purger_invitations_expirees(db)
    actives = db.execute(select(InvitationLien.id).where(
        InvitationLien.eleve_hmac == eleve_hmac, InvitationLien.utilise_le.is_(None))).all()
    if len(actives) >= MAX_INVITATIONS_ACTIVES:
        db.rollback()
        raise ValueError("trop_d_invitations_actives")
    code = _b64.b32encode(_secrets.token_bytes(15)).decode("ascii")  # 120 bits, 24 caractères
    now = _maintenant()
    inv = InvitationLien(code_hash=_empreinte(code), eleve_hmac=eleve_hmac, pseudo_id=pseudo_id,
                         relation=relation, emis_par=emis_par[:32], cree_le=now,
                         expire_le=now + _dt.timedelta(minutes=ttl_invitation_min()))
    db.add(inv)
    db.commit()
    return formater_code(code), inv


def accepter_invitation(db: Session, code: str, compte) -> tuple[str, str]:
    """Validation par le compte connecté. Renvoie (pseudo_id, relation). Lève InvitationInvalide
    (message unique) ou ValueError("deja_lie") — un lien existant ne consomme pas le code."""
    from paiement_comptes.verification_email import verification_ok_pour_invitation

    norm = normaliser_code(code)
    if norm is None or compte is None or not compte.actif:
        raise InvitationInvalide("invitation_invalide")
    # R19 : rattachement sensible ⇒ adresse e-mail du compte VÉRIFIÉE (contrôle AVANT toute
    # lecture de l'invitation : le code n'est ni consommé ni révélé valide).
    if verification_ok_pour_invitation(compte):
        raise PermissionError("email_non_verifie")
    inv = db.execute(select(InvitationLien).where(InvitationLien.code_hash == _empreinte(norm))).scalar_one_or_none()
    now = _maintenant()
    if inv is None or inv.utilise_le is not None or inv.expire_le <= now or compte.role != inv.relation:
        raise InvitationInvalide("invitation_invalide")
    if relation(db, compte.id, inv.eleve_hmac) is not None:
        raise ValueError("deja_lie")
    pseudo, rel, eleve_hmac = inv.pseudo_id, inv.relation, inv.eleve_hmac
    # Consommation ATOMIQUE : deux acceptations concurrentes ⇒ une seule gagne.
    res = db.execute(update(InvitationLien).where(
        InvitationLien.id == inv.id, InvitationLien.utilise_le.is_(None), InvitationLien.expire_le > now,
    ).values(utilise_le=now, utilise_par=compte.id, pseudo_id=None))
    if res.rowcount != 1:
        db.rollback()
        raise InvitationInvalide("invitation_invalide")
    db.add(LienCompteEleve(compte_id=compte.id, eleve_hmac=eleve_hmac, relation=rel))
    db.commit()
    return pseudo, rel


def invitations_eleve(db: Session, eleve_hmac: str) -> list:
    return list(db.execute(select(InvitationLien).where(InvitationLien.eleve_hmac == eleve_hmac)
                           .order_by(InvitationLien.id.asc())).scalars())


def supprimer_invitations_eleve(db: Session, eleve_hmac: str) -> int:
    n = db.execute(delete(InvitationLien).where(InvitationLien.eleve_hmac == eleve_hmac)).rowcount or 0
    db.commit()
    return n
