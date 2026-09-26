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
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator
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
        # Version de révocation (session 4) : refusé dès que compte.jeton_version change.
        "ver": int(compte.jeton_version or 0),
        # PyJWT sérialise en JSON : timestamps entiers (pas de datetime).
        "iat": int(now.timestamp()),
        "exp": int((now + _dt.timedelta(hours=_TOKEN_TTL_H)).timestamp()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


router = APIRouter(prefix="/comptes", tags=["comptes"])


# --- Schémas ----------------------------------------------------------------- #
class InscriptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # lot 21 : pas d'affectation de masse
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=200)
    prenom: Optional[str] = Field(default=None, max_length=120)
    role: str = Field(default="parent")


class ConnexionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # lot 21 : pas d'affectation de masse
    email: EmailStr
    mot_de_passe: str


class CompteOut(BaseModel):
    id: int
    email: str
    prenom: Optional[str] = None
    role: str
    statut_abonnement: str
    email_verifie: bool = False

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
            email_verifie=bool(compte.email_verifie),
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
    # Révocation (session 4) : jeton émis avant une déconnexion / un changement de mot de
    # passe ou d'adresse. Jetons historiques sans `ver` : valables tant que la version est 0.
    ver = payload.get("ver", 0)
    if isinstance(ver, bool) or not isinstance(ver, int) or ver != (compte.jeton_version or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="jeton_revoque")
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
    # R19 : PARENT_CREATED → EMAIL_UNVERIFIED → VERIFICATION_TOKEN_CREATED (courriel).
    _envoyer_verification(db, compte)
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


# --------------------------------------------------------------------------- #
# Session 4 — vérification d'adresse (R19), révocation, cycle de vie du compte
# --------------------------------------------------------------------------- #
class ConfirmationEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jeton: str = Field(min_length=1, max_length=128)


class MotDePasseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ancien: str = Field(min_length=1, max_length=200)
    nouveau: str = Field(min_length=8, max_length=200)


class EmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nouvel_email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=200)


class SuppressionCompteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mot_de_passe: str = Field(min_length=1, max_length=200)
    confirmation: StrictBool

    @field_validator("confirmation")
    @classmethod
    def _vraie(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("confirmation_requise")
        return v


def _envoyer_verification(db: Session, compte: Compte) -> None:
    from app.core import courriel
    from paiement_comptes import verification_email as ve

    if compte.email_verifie:
        return
    jeton = ve.creer_jeton(db, compte)
    courriel.transport().envoyer(courriel.Message(
        destinataire=compte.email, sujet="MikaMike — vérifiez votre adresse",
        corps=f"Pour vérifier votre adresse, utilisez ce code : {jeton}\n(valable {ve.ttl_min() // 60} h, usage unique)",
        type="VERIFICATION_EMAIL", metadonnees={"jeton": jeton}))


def _exiger_mot_de_passe(request: Request, compte: Compte, mot_de_passe: str) -> None:
    """Action sensible : mot de passe actuel exigé, échecs limités par compte (anti force brute)."""
    paires = [(limitation.MDP_COMPTE, f"compte:{compte.id}")]
    limitation.exiger(*paires)
    if not crud_billing.verifier_mot_de_passe(mot_de_passe, compte.mot_de_passe_hash):
        limitation.enregistrer(paires, reussi=False)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mot_de_passe_incorrect")
    limitation.enregistrer(paires, reussi=True)


def _revoquer(compte: Compte) -> None:
    compte.jeton_version = int(compte.jeton_version or 0) + 1


@router.get("/verification-email")
def etat_verification(compte: Compte = Depends(compte_courant), db: Session = Depends(get_db)):
    from paiement_comptes import verification_email as ve

    return ve.etat(db, compte)


@router.post("/verification-email", status_code=status.HTTP_202_ACCEPTED)
def demander_verification(compte: Compte = Depends(compte_courant), db: Session = Depends(get_db)):
    """Renvoie un courriel de vérification. Le jeton n'apparaît JAMAIS dans la réponse HTTP."""
    if compte.email_verifie:
        return {"statut": "EMAIL_VERIFIED"}
    quota = [(limitation.VERIF_DEMANDE_COMPTE, f"compte:{compte.id}")]
    limitation.exiger(*quota)
    limitation.compter(quota)
    _envoyer_verification(db, compte)
    return {"statut": "VERIFICATION_TOKEN_CREATED"}


@router.post("/verification-email/confirmer")
def confirmer_verification(data: ConfirmationEmailIn, request: Request, db: Session = Depends(get_db)):
    """Sans authentification (lien reçu par courriel) : le jeton EST la preuve. Réponse unique
    pour inconnu / expiré / utilisé / adresse changée (aucune énumération)."""
    from paiement_comptes import verification_email as ve

    paires = [(limitation.VERIF_CONFIRMATION_IP, limitation.ip_client(request))]
    limitation.exiger(*paires)
    try:
        ve.confirmer(db, data.jeton)
    except ve.JetonVerificationInvalide:
        limitation.enregistrer(paires, reussi=False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="jeton_invalide_ou_expire")
    return {"statut": "EMAIL_VERIFIED"}


@router.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT)
def deconnexion(compte: Compte = Depends(compte_courant), db: Session = Depends(get_db)):
    """Déconnexion GLOBALE : tous les jetons du compte et tous les jetons élève qu'il a émis
    sont révoqués (jetons sans état : pas de révocation par appareil, cf. D11)."""
    _revoquer(compte)
    db.commit()


@router.post("/mot-de-passe", response_model=TokenOut)
def changer_mot_de_passe(data: MotDePasseIn, request: Request, compte: Compte = Depends(compte_courant),
                         db: Session = Depends(get_db)):
    _exiger_mot_de_passe(request, compte, data.ancien)
    compte.mot_de_passe_hash = crud_billing.hacher_mot_de_passe(data.nouveau)
    _revoquer(compte)  # un jeton volé avant le changement ne vaut plus rien
    db.commit()
    db.refresh(compte)
    return TokenOut(token=creer_token(compte), compte=CompteOut.depuis(compte))


@router.post("/email", response_model=TokenOut)
def changer_email(data: EmailIn, request: Request, compte: Compte = Depends(compte_courant),
                  db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError

    from paiement_comptes import verification_email as ve

    _exiger_mot_de_passe(request, compte, data.mot_de_passe)
    nouvel = str(data.nouvel_email).strip().lower()
    if nouvel == compte.email:
        raise HTTPException(status_code=400, detail="email_identique")
    if crud_billing.get_compte_par_email(db, nouvel) is not None:
        raise HTTPException(status_code=400, detail="email_indisponible")
    ve.invalider_jetons(db, compte.id)  # un jeton envoyé à l'ancienne adresse ne vaut plus
    compte.email = nouvel
    compte.email_verifie = False
    _revoquer(compte)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="email_indisponible")
    db.refresh(compte)
    _envoyer_verification(db, compte)
    return TokenOut(token=creer_token(compte), compte=CompteOut.depuis(compte))


@router.get("/moi/export")
def exporter_compte(compte: Compte = Depends(compte_courant), db: Session = Depends(get_db)):
    """Droit d'accès RGPD du TITULAIRE du compte (les données d'apprentissage d'un élève
    s'exportent par /rgpd/export/{pseudo}). Jamais : hash de mot de passe, jetons, codes."""
    from paiement_comptes import verification_email as ve
    from paiement_comptes.liens import InvitationLien, LienCompteEleve

    liens_ = db.query(LienCompteEleve).filter(LienCompteEleve.compte_id == compte.id).all()
    acceptees = db.query(InvitationLien).filter(InvitationLien.utilise_par == compte.id).count()
    ab = compte.abonnement
    return {
        "contexte_rgpd": "Export des données du compte",
        "compte": {"id": compte.id, "email": compte.email, "prenom": compte.prenom, "role": compte.role,
                   "actif": compte.actif, "cree_le": compte.cree_le.isoformat() if compte.cree_le else None,
                   "derniere_connexion": compte.derniere_connexion.isoformat() if compte.derniere_connexion else None},
        "verification_email": ve.etat(db, compte),
        "abonnement": {"statut": ab.statut.value if ab and ab.statut else "aucun"},
        "liens_eleves": [{"relation": lien.relation, "cree_le": lien.cree_le.isoformat() if lien.cree_le else None}
                         for lien in liens_],
        "invitations_acceptees": acceptees,
    }


@router.delete("/moi")
def supprimer_compte(data: SuppressionCompteIn, request: Request, compte: Compte = Depends(compte_courant),
                     db: Session = Depends(get_db)):
    """Suppression du compte par son titulaire. SQLite n'applique pas les ON DELETE CASCADE sans
    PRAGMA : chaque table dépendante est purgée EXPLICITEMENT. Les données d'apprentissage des
    élèves ne sont pas touchées (elles appartiennent à l'élève : /rgpd/effacer). Les jetons
    élève émis par ce compte deviennent invalides (compte émetteur inexistant)."""
    from paiement_comptes import verification_email as ve
    from paiement_comptes.liens import InvitationLien, LienCompteEleve
    from paiement_comptes.models_billing import StatutAbonnement

    _exiger_mot_de_passe(request, compte, data.mot_de_passe)
    ab = compte.abonnement
    if ab is not None and ab.statut in (StatutAbonnement.ACTIF, StatutAbonnement.ESSAI, StatutAbonnement.IMPAYE):
        raise HTTPException(status_code=409, detail="abonnement_en_cours")  # résilier d'abord (Stripe)
    cid = compte.id
    n_liens = db.query(LienCompteEleve).filter(LienCompteEleve.compte_id == cid).delete()
    ve.invalider_jetons(db, cid)
    db.query(InvitationLien).filter(InvitationLien.utilise_par == cid).update({"utilise_par": None})
    db.query(InvitationLien).filter(InvitationLien.emis_par == f"compte:{cid}",
                                    InvitationLien.utilise_le.is_(None)).delete()
    db.delete(compte)  # l'abonnement suit par la cascade ORM (relationship « all, delete-orphan »)
    db.commit()
    return {"statut": "compte_supprime", "liens_supprimes": n_liens}
