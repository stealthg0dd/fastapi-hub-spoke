"""
POST /concierge/chat — Landing-page AI Concierge (no auth required).

This endpoint is exempt from VentureIDMiddleware because it serves
pre-signup visitors on the public landing page who do not yet hold
venture keys.  It uses the Anthropic API directly with a fixed
system prompt positioning the bot as the Neufin AI Concierge.

Rate-limiting is handled at the Vercel edge / NGINX level; this
handler trusts the proxy to enforce per-IP quotas.
"""
from __future__ import annotations

import logging

from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concierge", tags=["concierge"])

_client = AsyncAnthropic()

_SYSTEM = (
    "You are the Neufin AI Concierge. Your goal is to explain Neural Twin technology. "
    "You are sophisticated, witty, and professional. "
    "Neufin creates a digital mirror — a Neural Twin — of a user's financial behavior "
    "to detect cognitive biases like loss aversion, confirmation bias, and FOMO before "
    "they cost the user money. "
    "The platform offers a free 7-day trial with full access to the AI Behavioral Coach, "
    "real-time bias alerts, and the Emotional Breaker kill switch. "
    "Keep every response concise (2-4 sentences max). "
    "Be warm and confident, never pushy. "
    "Do not give specific financial advice or discuss competitor products."
)

_QUICK_ANSWERS: dict[str, str] = {
    "7-day trial": (
        "Your free 7-day trial gives you full access to the Neufin Neural Twin — "
        "real-time bias detection, the AI Behavioral Coach, and the Emotional Breaker. "
        "No credit card required to start. After 7 days, upgrade to Pro to keep your edge."
    ),
    "neural twin": (
        "A Neural Twin is a digital mirror of your financial behavior. "
        "It learns how you trade, detects the cognitive biases costing you alpha — "
        "like anchoring, loss aversion, or FOMO — and surfaces bias-free alternatives "
        "before you pull the trigger."
    ),
}


class ConciergeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ConciergeResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ConciergeResponse, summary="Neufin AI Concierge")
async def concierge_chat(body: ConciergeRequest) -> ConciergeResponse:
    """
    Public chat endpoint for the landing-page AI Concierge.
    Calls claude-sonnet-4-6 with the Neufin Concierge system prompt.
    No X-Venture-ID or X-API-Key required — exempt from VentureIDMiddleware.
    """
    # Fast-path for well-known quick-start questions (avoids LLM call)
    lower = body.message.lower()
    for keyword, answer in _QUICK_ANSWERS.items():
        if keyword in lower:
            return ConciergeResponse(reply=answer)

    try:
        msg = await _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": body.message}],
        )
        reply = msg.content[0].text if msg.content else "I'm unable to respond right now."
        return ConciergeResponse(reply=reply)
    except Exception as exc:
        logger.exception("concierge_chat error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable. Please try again.",
        )
