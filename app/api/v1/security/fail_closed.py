"""
fail_closed.py — Sécurité Fail-Closed & Garde de Session (Cahier §8).
=====================================================================
1. exiger_session_active : Dépendance FastAPI "Fail-Closed" qui refuse systématiquement
   tout accès sans jeton de session JWT valide et non expiré.
2. valider_payload_ocr : Contrôle strict et amont des payloads OCR (ardoise manuscrite)
   bloquant les données invalides ou > 2 Mo AVANT tout appel au moteur d'IA.
"""

from __future__ import annotations

import base64
import datetime as _dt
from typing import Dict, Any, Optional

from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field

# PyJWT (remplace python-jose : CVE sans correctif, cf. CLOUD_SECURITY_REPORT.md)
try:
    import jwt
    from jwt import PyJWTError as JWTError
except ImportError:  # pragma: no cover
    jwt = None

# Secret d'authentification pour JWT (fail-closed, aucun repli ; distinct du pseudo-secret)
from app.core.security_config import get_jwt_secret as _get_jwt_secret

_JWT_SECRET = _get_jwt_secret()
_JWT_ALGORITHM = "HS256"

# Seuil maximal strict pour payload OCR : 2 Mo (2 * 1024 * 1024 octets)
MAX_OCR_PAYLOAD_BYTES = 2 * 1024 * 1024


class OcrPayload(BaseModel):
    """Schéma du payload OCR / Ardoise manuscrite."""
    image_b64: str = Field(description="Données image de l'ardoise en base64 ou DataURL")
    exercice_id: Optional[str] = Field(default=None, description="Identifiant de l'exercice lié")


def exiger_session_active(authorization: str = Header(default="")) -> Dict[str, Any]:
    """
    Dépendance de Sécurité Fail-Closed (Cahier §8) :
    Exige un en-tête Authorization 'Bearer <token>' valide et non expiré.
    En cas de jeton absent, altéré ou expiré -> Refus strict 401 (Fail-Closed).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_requise",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_absent",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="module_jwt_indisponible"
        )

    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        pseudo_id: str = payload.get("sub") or payload.get("pseudo_id")
        
        if not pseudo_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="payload_token_invalide",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Vérification d'expiration explicite
        exp = payload.get("exp")
        if exp is not None:
            now_ts = int(_dt.datetime.now(_dt.timezone.utc).timestamp())
            if now_ts > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="session_expirer",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        return {
            "pseudo_id": pseudo_id,
            "role": payload.get("role", "eleve"),
            "exp": exp
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_expirer_ou_invalide",
            headers={"WWW-Authenticate": "Bearer"}
        )


def valider_payload_ocr(payload: OcrPayload) -> OcrPayload:
    """
    Validation préalable Fail-Closed des requêtes OCR / Ardoise (Cahier §8) :
    Rejette les requêtes trop volumineuses (> 2 Mo) ou au format corrompu
    STRICTEMENT AVANT de transmettre au service OCR / Moteur IA.
    """
    image_raw = payload.image_b64
    if not image_raw or not image_raw.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="donnees_ocr_vides"
        )

    # 1. Vérification de la taille du payload brut
    payload_size = len(image_raw.encode("utf-8"))
    if payload_size > MAX_OCR_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"payload_ocr_trop_volumineux: {payload_size} octets (max {MAX_OCR_PAYLOAD_BYTES} octets)"
        )

    # 2. Validation du format Base64 ou DataURL
    clean_b64 = image_raw
    if "," in image_raw:
        # Enlever l'en-tête DataURL type "data:image/png;base64,"
        header, clean_b64 = image_raw.split(",", 1)
        if "base64" not in header.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="format_dataurl_ocr_invalide"
            )

    clean_b64 = clean_b64.strip()
    try:
        # Tenter le décodage effectif base64 pour vérifier l'intégrité
        decoded_bytes = base64.b64decode(clean_b64, validate=True)
        if len(decoded_bytes) == 0:
            raise ValueError("Decoded bytes empty")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="encodage_base64_ocr_corrompu"
        )

    return payload
