"""
router_paiement.py — Stripe Checkout (abonnement mensuel) + webhook.

Fichier NEUF livré par CC. Aucune édition de main.py : Jules câble le routeur
(voir A_CABLER_DANS_MAIN.md).

Endpoints (préfixe /api/paiement) :
  POST /checkout          -> crée une session Stripe Checkout (mode subscription)
                             et renvoie l'URL de redirection. Auth Bearer.
  GET  /statut            -> statut d'abonnement du compte courant. Auth Bearer.
  POST /webhook           -> réception des événements Stripe (signature vérifiée).
                             PAS d'auth Bearer : sécurité = signature webhook.

Variables d'environnement attendues (aucun secret en dur) :
  STRIPE_SECRET_KEY        sk_...
  STRIPE_WEBHOOK_SECRET    whsec_...
  STRIPE_PRICE_ID          price_...   (prix récurrent mensuel)
  MIKA_APP_URL             https://app.mikamike.fr  (base des URLs succès/annulation)
"""

from __future__ import annotations

import datetime as _dt
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from paiement_comptes import crud_billing
from paiement_comptes.database import get_db
from paiement_comptes.models_billing import Compte, StatutAbonnement
from paiement_comptes.router_comptes import compte_courant

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None  # type: ignore


_STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
_APP_URL = os.environ.get("MIKA_APP_URL", "http://localhost:3012").rstrip("/")

if stripe is not None and _STRIPE_SECRET:
    stripe.api_key = _STRIPE_SECRET


router = APIRouter(prefix="/paiement", tags=["paiement"])


# Correspondance statut Stripe -> statut interne
_MAP_STATUT = {
    "trialing": StatutAbonnement.ESSAI,
    "active": StatutAbonnement.ACTIF,
    "past_due": StatutAbonnement.IMPAYE,
    "unpaid": StatutAbonnement.IMPAYE,
    "canceled": StatutAbonnement.ANNULE,
    "incomplete": StatutAbonnement.AUCUN,
    "incomplete_expired": StatutAbonnement.EXPIRE,
}


def _exiger_stripe() -> None:
    if stripe is None:
        raise HTTPException(status_code=500, detail="stripe_non_installe")
    if not _STRIPE_SECRET:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY_absent")


def _ts(epoch) -> _dt.datetime | None:
    if not epoch:
        return None
    return _dt.datetime.fromtimestamp(int(epoch), tz=_dt.timezone.utc)


# --- Schémas ----------------------------------------------------------------- #
class CheckoutOut(BaseModel):
    url: str


class StatutOut(BaseModel):
    statut: str
    acces_autorise: bool
    fin_periode_courante: str | None = None
    annulation_programmee: bool = False


# --- Endpoints --------------------------------------------------------------- #
@router.post("/checkout", response_model=CheckoutOut)
def creer_checkout(
    compte: Compte = Depends(compte_courant),
    db: Session = Depends(get_db),
):
    """Crée une session Checkout d'abonnement mensuel pour le compte courant."""
    _exiger_stripe()
    if not _PRICE_ID:
        raise HTTPException(status_code=500, detail="STRIPE_PRICE_ID_absent")

    ab = crud_billing.get_abonnement(db, compte.id)
    customer_id = ab.stripe_customer_id if ab else None

    # Réutilise le customer Stripe s'il existe, sinon Stripe en crée un.
    kwargs = dict(
        mode="subscription",
        line_items=[{"price": _PRICE_ID, "quantity": 1}],
        success_url=f"{_APP_URL}/paiement/succes?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{_APP_URL}/paiement/annule",
        client_reference_id=str(compte.id),
        metadata={"compte_id": str(compte.id)},
        subscription_data={"metadata": {"compte_id": str(compte.id)}},
    )
    if customer_id:
        kwargs["customer"] = customer_id
    else:
        kwargs["customer_email"] = compte.email

    try:
        session = stripe.checkout.Session.create(**kwargs)
    except Exception as exc:  # pragma: no cover - erreurs réseau/API Stripe
        raise HTTPException(status_code=502, detail=f"stripe_checkout: {exc}")

    return CheckoutOut(url=session.url)


@router.get("/statut", response_model=StatutOut)
def statut(
    compte: Compte = Depends(compte_courant),
    db: Session = Depends(get_db),
):
    ab = crud_billing.get_abonnement(db, compte.id)
    if ab is None:
        return StatutOut(statut="aucun", acces_autorise=False)
    return StatutOut(
        statut=ab.statut.value,
        acces_autorise=ab.acces_autorise,
        fin_periode_courante=(
            ab.fin_periode_courante.isoformat() if ab.fin_periode_courante else None
        ),
        annulation_programmee=ab.annulation_programmee,
    )


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Réceptionne les événements Stripe. Sécurité = signature, pas de Bearer."""
    _exiger_stripe()
    if not _WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET_absent")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, _WEBHOOK_SECRET)
    except Exception:
        # Signature invalide -> on refuse (ne jamais faire confiance au corps brut)
        raise HTTPException(status_code=400, detail="signature_invalide")

    type_ = event["type"]
    obj = event["data"]["object"]

    # 1) Checkout terminé : lier le customer au compte
    if type_ == "checkout.session.completed":
        compte_id = (obj.get("metadata") or {}).get("compte_id") or obj.get(
            "client_reference_id"
        )
        customer_id = obj.get("customer")
        if compte_id and customer_id:
            crud_billing.lier_customer(db, int(compte_id), customer_id)

    # 2) Cycle de vie de l'abonnement
    elif type_ in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        statut_stripe = obj.get("status", "")
        interne = _MAP_STATUT.get(statut_stripe, StatutAbonnement.AUCUN)
        if type_.endswith("deleted"):
            interne = StatutAbonnement.EXPIRE

        price_id = None
        try:
            items = obj["items"]["data"]
            if items:
                price_id = items[0]["price"]["id"]
        except Exception:
            price_id = None

        crud_billing.maj_statut_abonnement(
            db,
            stripe_subscription_id=obj.get("id", ""),
            statut=interne,
            stripe_customer_id=obj.get("customer"),
            stripe_price_id=price_id,
            fin_periode_courante=_ts(obj.get("current_period_end")),
            annulation_programmee=bool(obj.get("cancel_at_period_end")),
        )

    # 3) Paiement échoué -> impayé (relance)
    elif type_ == "invoice.payment_failed":
        sub_id = obj.get("subscription")
        if sub_id:
            crud_billing.maj_statut_abonnement(
                db,
                stripe_subscription_id=sub_id,
                statut=StatutAbonnement.IMPAYE,
                stripe_customer_id=obj.get("customer"),
            )

    # Les autres événements sont ignorés (accusé de réception 200)
    return {"recu": True}
