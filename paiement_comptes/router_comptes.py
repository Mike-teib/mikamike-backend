"""
router_comptes.py — Inscription / connexion self-service.

Fichier NEUF livré par CC. Aucune édition de main.py : Jules câble le routeur
(voir A_CABLER_DANS_MAIN.md).

Endpoints (préfixe /api/comptes) :
  POST /inscription   -> crée un compte
  POST /connexion     -> vérifie identifiants, renvoie un token de session
  GET  /moi           -> profil du compte courant (Bearer token)

Le token est un JWT signé HS256 avec MIKA_JWT_SECRET (env). Pas de secret en
dur. La dépendance `get_db` du projet est importée si disponible.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core import limitation
from paiement_comptes import crud_billing
from paiement_comptes.database import get_db
from paiement_comptes.models_billing import Compte

# --- JWT (PyJWT ; remplace python-jose, cf. CLOUD_SECURITY_REPORT.md) -------- #
try:
    import jwt  # PyJWT
except Exception:  # pragma: no cover
    jwt = None  # type: ignore

# Fail-closed, aucun repli : refus au chargement si MIKA_JWT_SECRET absent/invalide.
from app.core.security_config import get_jwt_secret as _get_jwt_secret

_JWT_SECRET = _get_jwt_secret()
_JWT_ALGO = "HS256"
_TOKEN_TTL_H = int(os.environ.get("MIKA_TOKEN_TTL_H", "168"))  # 7 jours


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def creer_token(compte: Compte) -> str:
    if jwt is None:
        raise HTTPException(status_code=500, detail="jwt_indisponible")
    if not _JWT_SECRET:
        raise HTTPException(status_code=500, detail="MIKA_JWT_SECRET_absent")
    now = _utcnow()
    payload = {
        "sub": str(compte.id),
        # Type de jeton explicite (anti-confusion avec les jetons de séance élève).
        "typ": "compte",
        "email": compte.email,
        "role": compte.role,
        # PyJWT sérialise en JSON : timestamps entiers (pas de datetime).
        "iat": int(now.timestamp()),
        "exp": int((now + _dt.timedelta(hours=_TOKEN_TTL_H)).timestamp()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


router = APIRouter(prefix="/comptes", tags=["comptes"])


# --- Schémas ----------------------------------------------------------------- #
class InscriptionIn(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=200)
    prenom: Optional[str] = Field(default=None, max_length=120)
    role: str = Field(default="parent")


class ConnexionIn(BaseModel):
    email: EmailStr
    mot_de_passe: str


class CompteOut(BaseModel):
    id: int
    email: str
    prenom: Optional[str] = None
    role: str
    statut_abonnement: str

    @classmethod
    def depuis(cls, compte: Compte) -> "CompteOut":
        ab = compte.abonnement
        statut = ab.statut.value if ab and ab.statut else "aucun"
        return cls(
            id=compte.id,
            email=compte.email,
            prenom=compte.prenom,
            role=compte.role,
            statut_abonnement=statut,
        )


class TokenOut(BaseModel):
    token: str
    compte: CompteOut


# --- Dépendance : compte courant depuis le Bearer token ---------------------- #
def compte_courant(
    request: Request,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> Compte:
    limitation.exiger_jeton_non_sonde(request)
    try:
        return _compte_courant(authorization, db)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            limitation.jeton_invalide(request)
        raise


def _compte_courant(authorization: str, db: Session) -> Compte:
    if jwt is None or not _JWT_SECRET:
        raise HTTPException(status_code=500, detail="auth_non_configuree")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_absent"
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO],
                             options={"require": ["exp", "sub"]})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalide"
        )
    # `sub` doit être l'id entier d'un compte : un jeton d'une autre nature (ex. jeton
    # de session élève dont `sub` est un pseudo-id) donnait auparavant une 500.
    # Jetons d'un autre type (séance élève « mika-eleve »…) refusés même si `sub` est numérique.
    if payload.get("typ", "compte") != "compte":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalide"
        )
    try:
        compte_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalide"
        )
    compte = crud_billing.get_compte(db, compte_id)
    if compte is None or not compte.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="compte_inconnu"
        )
    return compte


# --- Endpoints --------------------------------------------------------------- #
@router.post("/inscription", response_model=TokenOut, status_code=201)
def inscription(data: InscriptionIn, request: Request, db: Session = Depends(get_db)):
    quota = [(limitation.INSCRIPTION_IP, limitation.ip_client(request))]
    limitation.exiger(*quota)
    limitation.compter(quota)
    role = data.role if data.role in ("parent", "eleve") else "parent"
    try:
        compte = crud_billing.creer_compte(
            db,
            email=data.email,
            mot_de_passe=data.mot_de_passe,
            prenom=data.prenom,
            role=role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TokenOut(token=creer_token(compte), compte=CompteOut.depuis(compte))


@router.post("/connexion", response_model=TokenOut)
def connexion(data: ConnexionIn, request: Request, db: Session = Depends(get_db)):
    # R7 : refus AVANT bcrypt (le blocage ne coûte rien) ; jamais par l'e-mail seul (anti-DoS).
    paires = limitation.cles_connexion(request, data.email)
    limitation.exiger(*paires)
    compte = crud_billing.authentifier(db, data.email, data.mot_de_passe)
    limitation.enregistrer(paires, reussi=compte is not None)
    if compte is None:
        raise HTTPException(status_code=401, detail="identifiants_invalides")
    return TokenOut(token=creer_token(compte), compte=CompteOut.depuis(compte))


@router.get("/moi", response_model=CompteOut)
def moi(compte: Compte = Depends(compte_courant)):
    return CompteOut.depuis(compte)
