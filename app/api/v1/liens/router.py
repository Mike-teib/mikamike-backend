"""
router.py — Création des liens compte ↔ élève par INVITATION (décision D8).

  POST /api/v1/liens/invitations   émet un code à usage unique pour un élève
  POST /api/v1/liens/accepter      le compte connecté valide le code ⇒ lien créé

Jamais de lien par simple pseudo-id ou identifiant connu : il faut un code non devinable
(120 bits), à usage unique, expirable (48 h par défaut), accepté EXPLICITEMENT
(`confirmation: true`) par un compte connecté dont le rôle correspond à la relation.

Qui peut ÉMETTRE : l'élève lui-même (jeton de séance élève — son compte émetteur doit être
lié), ou un compte déjà lié à l'élève (parent, compte élève titulaire). Premier rattachement
d'un élève sans aucun lien : outil opérateur `python -m tools.liens inviter <pseudo>`.
Ces routes exigent un jeton QUEL QUE SOIT MIKA_AUTH_MODE.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.orm import Session

from app.core import auth, limitation
from app.core.pseudonymisation import hmac_eleve
from app.core.validation import Identifiant
from paiement_comptes import crud_billing, liens

liens_router = APIRouter(prefix="/liens", tags=["liens"])


class InvitationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_pseudo_id: Identifiant
    relation: Literal["parent", "eleve"] = "parent"


class AcceptationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    # Validation explicite : le compte confirme agir en tant que parent (ou titulaire) de l'élève.
    confirmation: StrictBool  # `1`, "true", "oui" refusés : le booléen JSON true est exigé

    @field_validator("confirmation")
    @classmethod
    def _vraie(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("confirmation_requise")
        return v


def principal_obligatoire(request: Request, authorization: str = Header(default="")) -> auth.Principal:
    """Dépendance : résolue AVANT la validation du corps (401 plutôt que 422 sans jeton)."""
    ip = limitation.ip_client(request)
    limitation.exiger((limitation.JETON_INVALIDE_IP, ip))
    try:
        jeton = auth._extraire(authorization)
        if jeton is None:
            raise auth._refus("jeton_requis")
        return auth.decoder(jeton)
    except HTTPException:
        limitation.jeton_invalide(request)
        raise


@liens_router.post("/invitations", status_code=status.HTTP_201_CREATED)
def emettre_invitation(data: InvitationIn, request: Request,
                       qui: auth.Principal = Depends(principal_obligatoire),
                       db: Session = Depends(auth._billing_db)):
    # Élève lui-même (jeton élève, lien du compte émetteur revérifié) ou compte déjà lié.
    auth.autoriser(qui, data.student_pseudo_id,
                   auth.Action.APPRENTISSAGE if qui.typ == auth.TYP_ELEVE else auth.Action.LECTURE, db)
    eleve_hmac = hmac_eleve(data.student_pseudo_id)
    quota = [(limitation.INVITATION_EMISSION, f"eleve:{eleve_hmac}"),
             (limitation.INVITATION_EMISSION, f"ip:{limitation.ip_client(request)}")]
    limitation.exiger(*quota)
    limitation.compter(quota)
    emis_par = "eleve" if qui.typ == auth.TYP_ELEVE else f"compte:{qui.compte_id}"
    try:
        code, inv = liens.creer_invitation(db, data.student_pseudo_id, eleve_hmac, relation=data.relation,
                                           emis_par=emis_par)
    except ValueError as exc:
        if str(exc) == "trop_d_invitations_actives":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="trop_d_invitations_actives")
        raise HTTPException(status_code=500, detail="invitation_mal_configuree")
    ttl_s = int((inv.expire_le - inv.cree_le).total_seconds())
    return {"code": code, "relation": inv.relation, "expires_in": ttl_s,
            "expire_le": inv.expire_le.isoformat() + "Z", "usage_unique": True}


@liens_router.post("/accepter", status_code=status.HTTP_201_CREATED)
def accepter_invitation(data: AcceptationIn, request: Request,
                        qui: auth.Principal = Depends(principal_obligatoire),
                        db: Session = Depends(auth._billing_db)):
    if qui.typ != auth.TYP_COMPTE:
        raise auth._refus("jeton_compte_requis")
    ip = limitation.ip_client(request)
    paires = [(limitation.INVITATION_ACCEPTATION_COMPTE, f"compte:{qui.compte_id}"),
              (limitation.INVITATION_ACCEPTATION_IP, ip)]
    limitation.exiger(*paires)
    compte = crud_billing.get_compte(db, qui.compte_id)
    if compte is None or not compte.actif:
        raise auth._refus("compte_inconnu")
    try:
        pseudo, rel = liens.accepter_invitation(db, data.code, compte)
    except liens.InvitationInvalide:
        limitation.enregistrer(paires, reussi=False)
        # Même réponse pour inconnu, utilisé, expiré, rôle incompatible (pas d'oracle).
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invitation_invalide")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="deja_lie")
    limitation.enregistrer([paires[0]], reussi=True)
    return {"statut": "lien_cree", "relation": rel, "student_pseudo_id": pseudo}
