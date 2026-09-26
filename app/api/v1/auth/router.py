"""
router.py — POST /api/v1/auth/eleve/jeton : jeton de séance pour un élève.

Exige un jeton de COMPTE (parent ou élève titulaire) LIÉ au pseudo-id demandé,
quel que soit MIKA_AUTH_MODE. Le jeton émis est court (MIKA_ELEVE_TOKEN_TTL_MIN,
120 min par défaut, 720 max), typé `mika-eleve`, signé avec une clé dérivée.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core import auth
from app.core.validation import Identifiant

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class JetonEleveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_pseudo_id: Identifiant


class JetonEleveOut(BaseModel):
    token: str
    token_type: str = "Bearer"  # noqa: S105 (type de jeton, pas un secret)
    typ: str = auth.TYP_ELEVE
    expires_in: int


@auth_router.post("/eleve/jeton", response_model=JetonEleveOut)
def emettre_jeton_eleve(
    data: JetonEleveIn,
    authorization: str = Header(default=""),
    db: Session = Depends(auth._billing_db),
):
    jeton = auth._extraire(authorization)
    qui = auth.decoder(jeton) if jeton else None
    auth.compte_lie(qui, data.student_pseudo_id, db)
    token, ttl = auth.emettre_jeton_eleve(data.student_pseudo_id)
    return JetonEleveOut(token=token, expires_in=ttl)
