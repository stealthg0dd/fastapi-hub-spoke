"""
Public concierge endpoints — no auth required.

  POST /concierge/chat     → AI Concierge (landing-page chatbot)
  POST /concierge/waitlist → Early-access waitlist (emails info@neufin.ai)

Both are exempt from VentureIDMiddleware (added to _EXEMPT_PREFIXES in
shared_services/middleware/venture_id.py).
"""
from __future__ import annotations

import logging
import os
from email.mime.text import MIMEText

import aiosmtplib
from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concierge", tags=["concierge"])

_client = AsyncAnthropic()

# ── Chatbot system prompt with full FAQ context ──────────────────────────────

_SYSTEM = """
You are the Neufin AI Concierge — sophisticated, warm, and concise.
Your sole purpose is to help visitors on the Neufin landing page understand
the product and get started. Keep every response to 2-4 sentences maximum.
Never give specific financial advice or discuss competitors.

=== NEUFIN PRODUCT KNOWLEDGE BASE ===

WHAT IS NEUFIN / NEURAL TWIN
- Neufin creates a Neural Twin — a digital mirror of a user's investment strategy, without cognitive biases.
- It analyses historical trading patterns, identifies bias-driven decisions (loss aversion, confirmation bias, FOMO, herding), and simulates what a perfectly rational version of the user would have done.
- The Neural Twin stress-tests decisions against 10,000 Monte Carlo scenarios before making a recommendation.
- It continuously learns and adapts to market conditions.

BIAS DETECTION
- Tracks 47 distinct cognitive biases using behavioural finance algorithms.
- Analyses transaction history, holding periods, entry/exit points vs. optimal decision points.
- Quantifies each bias with an exact dollar impact (e.g. "loss aversion cost you $4,200 last year").
- Provides scores: Loss Aversion (0-100), Disposition Effect %, Confirmation Bias frequency, Herding instances.

SIGNAL ACCURACY
- Sentiment signals: 73% directional accuracy over rolling 6-month periods.
- Alpha predictions: 89% correlation with actual outcomes.
- Bias interventions: 82% success rate when acted on within suggested timeframe.
- Neural Twin simulator: 18% average outperformance vs baseline in crash scenarios.

PRICING
- Individual: $49/month or $470/year — up to 20 positions, bias detection, sentiment analysis, Alpha Score, mobile app.
- Professional Trader: $149/month or $1,490/year — unlimited positions, advanced backtesting, API access, priority support.
- Enterprise: Custom pricing — multi-user, white-label, dedicated account manager, SLA.
- All plans: 7-day free trial (no credit card for early-access registrants).
- Early bird waitlist members: 50% off first 3 months (save up to $223).

TRIAL & EARLY BIRD
- 7-day free trial with full access to all features; no credit card required for waitlist members.
- Early bird benefits: 50% discount all plans for first 3 months, priority onboarding (30-min 1-on-1 session), lifetime Early Adopter badge, guaranteed price lock for 12 months.
- Limited to first 500 registrants; discount code valid for 90 days.

DATA SECURITY
- SOC 2 Type II certified; 256-bit AES at rest, TLS 1.3 in transit.
- Zero-knowledge architecture — brokerage passwords never stored; read-only OAuth tokens via Plaid.
- GDPR and CCPA compliant; regular penetration testing.
- Neufin is NOT a financial institution and does NOT hold custody of assets.

TRADE EXECUTION
- Neufin is a decision-intelligence platform, NOT a trading bot.
- Plaid integration is read-only by default; users maintain full control.
- Any trade execution (Professional plan) requires explicit two-factor approval per trade.

DATA PORTABILITY / CANCELLATION
- 30-day grace period after cancellation with read-only access for export (CSV, PDF, JSON).
- Permanent deletion within 7 business days upon request (GDPR Right to be Forgotten).
- Anonymised aggregate data may be retained for ML research per privacy policy.

INTEGRATIONS
- 12,000+ financial institutions via Plaid: Robinhood, Schwab, Fidelity, TD Ameritrade, IBKR, Webull, M1 Finance, Vanguard, and more.
- Asset classes: US equities, options, crypto (Coinbase/Kraken, 50+ alts), forex, futures.
- Manual CSV upload supported for unsupported brokerages.

INTERNATIONAL SUPPORT
- Primary focus is US markets (NYSE, NASDAQ).
- Manual entry supported for any global exchange.
- UK and Canadian broker integrations planned Q2 2025; full multi-currency Q3 2025.

MOBILE APP
- Native iOS (15+) and Android (10+) apps on App Store and Google Play.
- Features: real-time push alerts, Alpha Score dashboard, bias alerts, sentiment heatmap, biometric sync.
- PWA also available for any modern browser.

PERFORMANCE EXPECTATIONS
- Beta data (500+ users, 6 months): avg Alpha improvement +3.2% annualised; Sharpe ratio +0.34.
- 68% of users following debiasing recommendations outperformed their previous 12-month baseline.
- Results vary; past performance does not guarantee future results.

TIMELINE TO RESULTS
- Day 1: Instant Alpha Score analysis showing historical missed returns.
- Month 1-3: Measurable behaviour change; avg +1.8% Alpha improvement.
- Month 3-6: Neural Twin fully personalised; avg +3.2% annualised.
- 6+ months: Users develop proactive bias awareness.

CONTACT
- Email: info@neufin.ai
- Join waitlist: use the "Join Waitlist" button on the landing page.
""".strip()

# ── Fast-path local answers (no LLM call) ────────────────────────────────────

_QUICK_ANSWERS: dict[str, str] = {
    "7-day trial": (
        "Your free 7-day trial gives full access to the Neufin Neural Twin — "
        "real-time bias detection, the AI Behavioural Coach, sentiment analysis, and the Emotional Breaker. "
        "No credit card required for early-access registrants. After 7 days, upgrade to Pro to keep your edge."
    ),
    "neural twin": (
        "A Neural Twin is a digital mirror of your financial behaviour. "
        "It learns how you trade, detects the 47 cognitive biases costing you alpha — "
        "like anchoring, loss aversion, or FOMO — and surfaces bias-free alternatives "
        "before you pull the trigger."
    ),
    "pricing": (
        "Neufin offers three plans: Individual ($49/mo), Professional Trader ($149/mo), and Enterprise (custom). "
        "All include a 7-day free trial. Early bird waitlist members get 50% off for the first 3 months."
    ),
    "early bird": (
        "Early bird waitlist members receive 50% off all plans for the first 3 months (up to $223 savings), "
        "a dedicated onboarding session, and a lifetime Early Adopter badge. "
        "Limited to the first 500 registrants."
    ),
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ConciergeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ConciergeResponse(BaseModel):
    reply: str


class WaitlistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=1, max_length=50)
    company: str = Field(default="", max_length=200)
    portfolio_size: str = Field(default="", max_length=100)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ConciergeResponse, summary="Neufin AI Concierge chat")
async def concierge_chat(body: ConciergeRequest) -> ConciergeResponse:
    """
    Public chat endpoint for the landing-page AI Concierge.
    Calls claude-sonnet-4-6 with the Neufin system prompt + full FAQ knowledge base.
    """
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


@router.post("/waitlist", summary="Early-access waitlist submission")
async def submit_waitlist(body: WaitlistRequest) -> dict[str, str]:
    """
    Public endpoint — stores waitlist submissions and emails info@neufin.ai.
    Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars for email delivery.
    Submissions are always logged regardless of email success.
    """
    logger.info(
        "Waitlist submission: name=%r email=%r phone=%r company=%r portfolio=%r",
        body.name, body.email, body.phone, body.company, body.portfolio_size,
    )

    email_body = f"""\
New Early Access Registration — Neufin AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name:           {body.name}
Email:          {body.email}
Phone:          {body.phone}
Company:        {body.company or 'Not provided'}
Portfolio Size: {body.portfolio_size or 'Not provided'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated notification from the Neufin AI waitlist form.
"""

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_addr   = os.getenv("WAITLIST_TO_EMAIL", "info@neufin.ai")

    if smtp_host and smtp_user and smtp_pass:
        try:
            mime_msg = MIMEText(email_body, "plain", "utf-8")
            mime_msg["Subject"] = f"New Waitlist Registration — {body.name}"
            mime_msg["From"]    = smtp_user
            mime_msg["To"]      = to_addr

            await aiosmtplib.send(
                mime_msg,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_pass,
                start_tls=True,
            )
            logger.info("Waitlist email sent to %s", to_addr)
        except Exception as exc:
            # Email failure is non-fatal — submission is always logged above
            logger.warning("Failed to send waitlist email: %s", exc)
    else:
        logger.warning(
            "SMTP_HOST/SMTP_USER/SMTP_PASS not configured — "
            "waitlist submission logged only (not emailed)."
        )

    return {"status": "ok", "message": "Thank you for joining the Neufin AI waitlist!"}
