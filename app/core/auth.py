"""
auth.py — Authentification et autorisation des routes élève / parent / RGPD (AUTH_CONTRACT.md).

Principe : un pseudo-id seul n'est JAMAIS une preuve d'identité (revue session 2, R2-18).

Mode (lu à CHAQUE requête, variable MIKA_AUTH_MODE) :
  - absent ou « enforce » : jeton obligatoire, propriété vérifiée (fail-closed, défaut) ;
  - « off »               : contrat historique sans jeton (transition front, tests historiques) —
                            REFUSÉ si MIKA_ENV=production ;
  - toute autre valeur    : erreur de configuration ⇒ 500 (jamais d'ouverture silencieuse).

Deux types de jetons, jamais interchangeables :
  - jeton de COMPTE   (typ=compte, émis par /comptes/connexion, clé MIKA_JWT_SECRET) ;
  - jeton de SÉANCE ÉLÈVE (typ=mika-eleve, aud=mikamike-api, émis par /auth/eleve/jeton pour
    un compte lié à l'élève, signé avec une clé DÉRIVÉE : un jeton de compte ne peut pas
    être validé comme jeton élève même si le contrôle de `typ` était retiré).

Matrice (action × porteur) :
  apprentissage (exercices, parcours, escalier, mémoire, séance, tutorat) : jeton élève du même pseudo-id
  lecture (tableau de bord, export RGPD)  : jeton élève du même pseudo-id, ou compte lié (parent/élève)
  effacement RGPD                         : compte PARENT lié uniquement (décision D9)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security_config import get_jwt_secret

ALGO = "HS256"
ISSUER = "mikamike-backend"
AUDIENCE = "mikamike-api"
TYP_ELEVE = "mika-eleve"
TYP_COMPTE = "compte"
TTL_ELEVE_DEFAUT_MIN = 120
TTL_ELEVE_MAX_MIN = 720


class Action(str, Enum):
    APPRENTISSAGE = "apprentissage"
    LECTURE = "lecture"
    EFFACEMENT = "effacement"


@dataclass(frozen=True)
class Principal:
    typ: str                          # TYP_ELEVE | TYP_COMPTE
    role: str                         # eleve | parent | admin
    pseudo_id: Optional[str] = None   # jeton élève
    compte_id: Optional[int] = None   # jeton de compte ; jeton élève : compte émetteur (claim cid)


class ConfigAuthInvalide(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def mode_auth() -> str:
    brut = os.getenv("MIKA_AUTH_MODE")
    mode = "enforce" if brut is None or not brut.strip() else brut.strip().lower()
    if mode not in ("enforce", "off"):
        raise ConfigAuthInvalide("MIKA_AUTH_MODE invalide (attendu : enforce | off)")
    if mode == "off" and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):
        raise ConfigAuthInvalide("MIKA_AUTH_MODE=off interdit quand MIKA_ENV=production")
    return mode


def _ttl_eleve_min() -> int:
    try:
        ttl = int(os.getenv("MIKA_ELEVE_TOKEN_TTL_MIN", str(TTL_ELEVE_DEFAUT_MIN)))
    except ValueError as exc:
        raise ConfigAuthInvalide("MIKA_ELEVE_TOKEN_TTL_MIN non entier") from exc
    if not 1 <= ttl <= TTL_ELEVE_MAX_MIN:
        raise ConfigAuthInvalide(f"MIKA_ELEVE_TOKEN_TTL_MIN hors [1, {TTL_ELEVE_MAX_MIN}]")
    return ttl


def _cle_eleve() -> bytes:
    """Clé dérivée (HMAC) propre aux jetons élève : séparation cryptographique des types."""
    return hmac.new(get_jwt_secret().encode("utf-8"), b"mikamike/jeton-eleve/v1", hashlib.sha256).digest()


# --------------------------------------------------------------------------- #
# Jetons
# --------------------------------------------------------------------------- #
def emettre_jeton_eleve(pseudo_id: str, *, compte_id: int,
                        maintenant: Optional[_dt.datetime] = None) -> tuple[str, int]:
    """`compte_id` = compte (lié) qui a demandé le jeton : claim `cid`, revérifié à CHAQUE requête
    (revue session 3, S3-01 : sans lui, le jeton survivait à l'effacement RGPD, à la suppression
    du lien et à la désactivation du compte pendant toute sa durée de vie)."""
    if isinstance(compte_id, bool) or not isinstance(compte_id, int) or compte_id < 1:
        raise ValueError("compte_id invalide")
    now = maintenant or _dt.datetime.now(_dt.timezone.utc)
    ttl_s = _ttl_eleve_min() * 60
    claims = {
        "iss": ISSUER, "aud": AUDIENCE, "typ": TYP_ELEVE, "role": "eleve", "sub": pseudo_id,
        "cid": compte_id,
        "iat": int(now.timestamp()), "exp": int(now.timestamp()) + ttl_s, "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, _cle_eleve(), algorithm=ALGO), ttl_s


def _refus(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def interdit() -> HTTPException:
    # Même réponse pour « pas le propriétaire », « non lié » et « mauvais rôle » (pas d'oracle).
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acces_refuse")


def _extraire(authorization: str) -> Optional[str]:
    if not authorization:
        return None
    schema, _, jeton = authorization.partition(" ")
    if schema.lower() != "bearer" or not jeton.strip() or len(jeton) > 4096:
        raise _refus("jeton_invalide")
    return jeton.strip()


def decoder(jeton: str) -> Principal:
    """Décode un jeton élève OU compte ; toute autre forme ⇒ 401."""
    try:
        entete = jwt.get_unverified_header(jeton)
    except jwt.PyJWTError:
        raise _refus("jeton_invalide")
    if entete.get("alg") != ALGO:
        raise _refus("jeton_invalide")
    try:
        c = jwt.decode(jeton, _cle_eleve(), algorithms=[ALGO], audience=AUDIENCE, issuer=ISSUER,
                       options={"require": ["exp", "iat", "sub", "aud", "iss", "typ", "cid"]})
        cid = c.get("cid")
        if (c.get("typ") != TYP_ELEVE or c.get("role") != "eleve" or not isinstance(c.get("sub"), str)
                or isinstance(cid, bool) or not isinstance(cid, int) or cid < 1):
            raise _refus("jeton_invalide")
        return Principal(typ=TYP_ELEVE, role="eleve", pseudo_id=c["sub"], compte_id=cid)
    except jwt.ExpiredSignatureError:
        raise _refus("jeton_expire")
    except jwt.PyJWTError:
        pass
    try:
        c = jwt.decode(jeton, get_jwt_secret(), algorithms=[ALGO], options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise _refus("jeton_expire")
    except jwt.PyJWTError:
        raise _refus("jeton_invalide")
    # Jetons de compte historiques sans `typ` acceptés (compatibilité, cf. AUTH_CONTRACT §6).
    if c.get("typ", TYP_COMPTE) != TYP_COMPTE or "aud" in c:
        raise _refus("jeton_invalide")
    try:
        compte_id = int(c["sub"])
    except (TypeError, ValueError):
        raise _refus("jeton_invalide")
    return Principal(typ=TYP_COMPTE, role=str(c.get("role", "")), compte_id=compte_id)


# --------------------------------------------------------------------------- #
# Dépendances FastAPI
# --------------------------------------------------------------------------- #
def _billing_db():
    from paiement_comptes.database import get_db

    yield from get_db()


def principal(request: Request, authorization: str = Header(default="")) -> Optional[Principal]:
    """None en mode « off » ; sinon jeton obligatoire et valide."""
    from app.core import limitation

    try:
        mode = mode_auth()
    except ConfigAuthInvalide:
        raise HTTPException(status_code=500, detail="auth_mal_configuree")
    if mode == "off":
        return None
    # R7 : une source qui présente des jetons invalides en rafale est freinée (429).
    limitation.exiger_jeton_non_sonde(request)
    try:
        jeton = _extraire(authorization)
        if jeton is None:
            raise _refus("jeton_requis")
        return decoder(jeton)
    except HTTPException:
        limitation.jeton_invalide(request)
        raise


@dataclass(frozen=True)
class Garde:
    """Objet injecté dans les routes : `garde.exiger(pseudo_id, action)`."""

    qui: Optional[Principal]
    db: Session

    def exiger(self, pseudo_id: str, action: Action) -> None:
        if self.qui is None:  # mode off (contrat historique)
            return
        autoriser(self.qui, pseudo_id, action, self.db)


def garde(qui: Optional[Principal] = Depends(principal), db: Session = Depends(_billing_db)) -> Garde:
    return Garde(qui, db)


def autoriser(qui: Principal, pseudo_id: str, action: Action, db: Session) -> None:
    from app.core.pseudonymisation import hmac_eleve
    from paiement_comptes import crud_billing, liens

    if qui.typ == TYP_ELEVE:
        if not hmac.compare_digest(qui.pseudo_id or "", pseudo_id) or action == Action.EFFACEMENT:
            raise interdit()
        # Le compte émetteur doit être encore actif ET encore lié à l'élève (S3-01).
        emetteur = crud_billing.get_compte(db, qui.compte_id)
        if emetteur is None or not emetteur.actif:
            raise _refus("jeton_revoque")
        if liens.relation(db, emetteur.id, hmac_eleve(pseudo_id)) != emetteur.role:
            raise _refus("jeton_revoque")
        return
    # Jeton de compte : droits dérivés du lien compte ↔ élève (jamais du rôle seul).

    compte = crud_billing.get_compte(db, qui.compte_id)
    if compte is None or not compte.actif:
        raise _refus("compte_inconnu")
    rel = liens.relation(db, compte.id, hmac_eleve(pseudo_id))
    permis = {
        "parent": {Action.LECTURE, Action.EFFACEMENT},
        "eleve": {Action.LECTURE},
    }.get(rel or "", set())
    if action not in permis or compte.role != rel:
        raise interdit()


def compte_lie(qui: Optional[Principal], pseudo_id: str, db: Session) -> None:
    """Émission d'un jeton élève : exige un COMPTE lié (parent ou titulaire), dans tous les modes."""
    if qui is None or qui.typ != TYP_COMPTE:
        raise _refus("jeton_compte_requis")
    autoriser(qui, pseudo_id, Action.LECTURE, db)
