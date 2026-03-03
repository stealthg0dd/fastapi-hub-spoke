"""
Neufin Billing Router — Stripe subscription management.

Business rules
--------------
Trial period  : 7 days from user.created_at (read from hub.users).
Post-trial    : user must subscribe via Stripe Checkout.
is_pro flag   : stored in spokes.neufin_subscriptions, toggled by webhook.

Endpoints
---------
POST /billing/create-checkout-session
    • If user is already is_pro → 200 {"status": "already_subscribed"}.
    • If trial still active → 200 {"status": "trial_active", "trial_ends_at": ...}.
    • If trial expired and not pro → creates Stripe Checkout Session and
      returns {"status": "checkout_required", "checkout_url": "..."}.

POST /billing/webhook
    Stripe sends signed POST events here.  Signature verified with
    STRIPE_WEBHOOK_SECRET before processing.
    Handles:
      invoice.paid                   → is_pro = True
      customer.subscription.deleted  → is_pro = False

Security
--------
The webhook endpoint is added to VentureIDMiddleware's exempt list because
Stripe cannot send X-Venture-ID or X-API-Key.  Payload authenticity is
guaranteed instead by Stripe's webhook signature (HMAC-SHA256).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.orm import NeufinSubscription

router = APIRouter(tags=["neufin-billing"])

_TRIAL_DAYS = 7


# ── Stripe helper ─────────────────────────────────────────────────────────────

def _stripe_client() -> stripe.StripeClient:
    return stripe.StripeClient(settings.stripe_secret_key)


# ── Request / Response models ─────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    user_id: uuid.UUID
    success_url: str = "https://app.neufin.io/billing/success"
    cancel_url:  str = "https://app.neufin.io/billing/cancel"


class CheckoutResponse(BaseModel):
    status: str                     # "already_subscribed" | "trial_active" | "checkout_required"
    trial_ends_at: str | None = None
    checkout_url:  str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_subscription(
    db: AsyncSession,
    venture_id: uuid.UUID,
    user_id: uuid.UUID,
    trial_ends_at: datetime,
) -> NeufinSubscription:
    """Fetch existing subscription row or create one."""
    result = await db.execute(
        select(NeufinSubscription).where(
            NeufinSubscription.venture_id == venture_id,
            NeufinSubscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = NeufinSubscription(
            venture_id=venture_id,
            user_id=user_id,
            is_pro=False,
            trial_ends_at=trial_ends_at,
        )
        db.add(sub)
        await db.flush()
    return sub


async def _get_user_created_at(db: AsyncSession, user_id: uuid.UUID) -> datetime | None:
    """Read hub.users.created_at for the given user (no RLS on hub schema)."""
    row = await db.execute(
        text("SELECT created_at FROM hub.users WHERE id = :uid"),
        {"uid": user_id},
    )
    result = row.fetchone()
    if result is None:
        return None
    ts = result[0]
    # Ensure timezone-aware
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _create_checkout_session_sync(
    customer_id: str | None,
    user_id: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Blocking Stripe call — runs in thread executor."""
    client = _stripe_client()

    # Create or reuse Stripe Customer
    if not customer_id:
        customer = client.customers.create(
            params={"metadata": {"neufin_user_id": user_id}}
        )
        customer_id = customer.id

    session = client.checkout.sessions.create(
        params={
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": settings.stripe_price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"neufin_user_id": user_id},
        }
    )
    return {"customer_id": customer_id, "checkout_url": session.url}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/create-checkout-session",
    response_model=CheckoutResponse,
    summary="Gate access via trial or Stripe Checkout",
    description=(
        "Checks the user's trial status (7 days from hub.users.created_at). "
        "Returns immediately if already subscribed or in trial. "
        "Otherwise creates a Stripe Checkout Session and returns the URL. "
        "Requires STRIPE_SECRET_KEY and STRIPE_PRICE_ID."
    ),
)
async def create_checkout_session(
    body: CheckoutRequest,
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe credentials are not configured on this server.",
        )

    try:
        v_id = uuid.UUID(x_venture_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Venture-ID")

    # Determine trial window from hub.users.created_at
    user_created_at = await _get_user_created_at(db, body.user_id)
    if user_created_at is None:
        # Unknown user — default trial starts now
        user_created_at = datetime.now(timezone.utc)

    trial_ends_at = user_created_at + timedelta(days=_TRIAL_DAYS)
    now = datetime.now(timezone.utc)

    sub = await _get_or_create_subscription(db, v_id, body.user_id, trial_ends_at)

    # ── Already subscribed ────────────────────────────────────────────────────
    if sub.is_pro:
        return CheckoutResponse(status="already_subscribed")

    # ── Trial still active ────────────────────────────────────────────────────
    if now < trial_ends_at:
        return CheckoutResponse(
            status="trial_active",
            trial_ends_at=trial_ends_at.isoformat(),
        )

    # ── Trial expired — create Checkout Session ───────────────────────────────
    try:
        result = await asyncio.to_thread(
            _create_checkout_session_sync,
            sub.stripe_customer_id,
            str(body.user_id),
            body.success_url,
            body.cancel_url,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {exc}",
        )

    # Persist customer_id for future calls
    if not sub.stripe_customer_id:
        sub.stripe_customer_id = result["customer_id"]

    return CheckoutResponse(
        status="checkout_required",
        checkout_url=result["checkout_url"],
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook receiver",
    description=(
        "Receives signed Stripe events.  Verifies the Stripe-Signature header "
        "before processing.  Handles invoice.paid (→ is_pro=True) and "
        "customer.subscription.deleted (→ is_pro=False). "
        "This endpoint is exempt from VentureIDMiddleware authentication."
    ),
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify signature in thread pool (blocking call)
    try:
        event = await asyncio.to_thread(
            stripe.WebhookSignature.verify_header,
            payload.decode("utf-8"),
            sig_header,
            settings.stripe_webhook_secret,
        )
        # construct_event returns the parsed event dict
        event = stripe.Event.construct_from(
            stripe.util.convert_to_stripe_object(
                stripe.WebhookSignature.verify_header(
                    payload.decode("utf-8"),
                    sig_header,
                    settings.stripe_webhook_secret,
                )
            ),
            stripe.api_key,
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook error: {exc}")

    event_type = event.get("type", "")
    data_obj   = event.get("data", {}).get("object", {})

    if event_type == "invoice.paid":
        await _handle_invoice_paid(db, data_obj)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data_obj)

    return {"received": True}


# ── Webhook sub-handlers ───────────────────────────────────────────────────────

async def _handle_invoice_paid(db: AsyncSession, invoice: dict) -> None:
    """Set is_pro=True for the customer associated with the paid invoice."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(NeufinSubscription).where(
            NeufinSubscription.stripe_customer_id == customer_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_pro = True
        subscription_id = invoice.get("subscription")
        if subscription_id:
            sub.stripe_subscription_id = subscription_id


async def _handle_subscription_deleted(db: AsyncSession, subscription: dict) -> None:
    """Set is_pro=False when a subscription is cancelled."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(NeufinSubscription).where(
            NeufinSubscription.stripe_customer_id == customer_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_pro = False
        sub.stripe_subscription_id = None
