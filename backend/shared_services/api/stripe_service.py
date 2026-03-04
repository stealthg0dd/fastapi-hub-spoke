from __future__ import annotations

import uuid
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_admin_db
from models.hub import User

logger = logging.getLogger(__name__)

router = APIRouter()


class CheckoutRequest(BaseModel):
    user_id: str
    price_id: str | None = None


@router.post("/create-checkout-session")
async def create_checkout_session(body: CheckoutRequest):
    """
    Create a Stripe Checkout Session for the Pro subscription.

    Returns a redirect URL — the frontend navigates to it so Stripe
    handles payment collection on its hosted page.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    stripe.api_key = settings.stripe_secret_key

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": body.price_id or settings.stripe_price_id,
                "quantity": 1,
            }],
            metadata={"user_id": body.user_id},
            success_url=(
                f"{settings.frontend_url.rstrip('/')}"
                "/?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{settings.frontend_url.rstrip('/')}/",
        )
    except stripe.error.InvalidRequestError as exc:
        logger.error("Stripe checkout creation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_admin_db),
):
    """
    Receive Stripe webhook events.

    Verifies the signature, then on `checkout.session.completed`:
      - Finds the hub.users record by user_id stored in metadata.
      - Sets is_premium = True so subsequent API calls recognise the subscription.
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]
        user_id_str: str | None = checkout_session.get("metadata", {}).get("user_id")

        if user_id_str:
            try:
                user_uuid = uuid.UUID(user_id_str)
            except ValueError:
                logger.warning("stripe webhook: invalid user_id in metadata: %s", user_id_str)
                return {"received": True}

            result = await db.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            if user:
                user.is_premium = True
                user.trial_ends_at = None
                logger.info("stripe webhook: user %s upgraded to premium", user_uuid)
            else:
                logger.warning(
                    "stripe webhook: user %s not found in hub.users (may be Supabase-only)",
                    user_uuid,
                )

    return {"received": True}
