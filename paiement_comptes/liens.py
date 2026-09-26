"""
liens.py — Autorisation compte ↔ élève (qui peut agir sur quel pseudo-id).

Un pseudo-id seul n'authentifie personne (revue session 2, R2-18). L'accès d'un
compte aux données d'un élève exige une ligne ici :
  relation = "parent" : compte parent autorisé pour cet enfant ;
  relation = "eleve"  : compte élève titulaire de ce pseudo-id.
L'élève est désigné par son HMAC (jamais le pseudo-id ni une PII en clair).

La CRÉATION des liens relève d'un parcours produit (vérification parentale,
invitation…) non encore décidé (décision D8, cf. AUTH_CONTRACT.md) : seule la
fonction `lier` existe, sans route publique.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, delete, select
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
