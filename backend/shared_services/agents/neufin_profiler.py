"""
Neufin Behavioral Profiler — background agent.

Integration flow
----------------
1. POST /spokes/neufin/trades  →  trade saved  →  BackgroundTasks fires profile_trade()
2. profile_trade() fetches real-time market context (Finnhub + AV + NewsAPI)
3. Calls Claude with force tool-use to extract structured bias JSON
4. Inserts one row into spokes.neufin_bias_scores

Bias taxonomy
-------------
FOMO            — buy when price is at or near the day's high after rapid upward move
Loss Aversion   — buying into a losing position near the day's low
Anchoring Bias  — price is anchored to a round number or the 52-week high
No Bias         — trade looks rational given market context

Output format (persisted to neufin_bias_scores)
------------------------------------------------
    detected_biases      : ["FOMO"]   (JSON list)
    behavioral_risk_score: 0.0–10.0
    coach_note           : reasoning + suggested action (3 sentences)
    analyzed_at          : UTC NOW()
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

import anthropic
import httpx
import openai
from google import genai as google_genai
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from core.config import settings
from core.database import async_session_maker
from mcp.finance_mcp import get_news_sentiment

logger = logging.getLogger(__name__)


# ── Market context ────────────────────────────────────────────────────────────

@dataclass
class _TradeContext:
    day_open: float | None
    day_high: float | None
    day_low: float | None
    week52_high: float | None      # derived from 100-day AV history
    news_mood: str                 # "bullish" | "bearish" | "neutral"
    news_consolidated: str         # paragraph for LLM


async def _finnhub_intraday(asset: str, http: httpx.AsyncClient) -> dict | None:
    """Return raw Finnhub /quote dict (h, l, o, c, pc) or None."""
    key = settings.finnhub_api_key
    if not key:
        return None
    try:
        r = await http.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": asset, "token": key},
        )
        r.raise_for_status()
        d = r.json()
        return d if d.get("c", 0) != 0 else None
    except Exception as exc:
        logger.warning("profiler finnhub %s: %s", asset, exc)
        return None


async def _av_highs(asset: str, http: httpx.AsyncClient) -> list[float]:
    """Return daily highs from AV TIME_SERIES_DAILY (≤100 bars for 52w proxy)."""
    key = settings.alpha_vantage_api_key
    if not key:
        return []
    try:
        r = await http.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": asset,
                "outputsize": "compact",   # 100 trading days ≈ 5 months
                "apikey": key,
            },
        )
        r.raise_for_status()
        ts = r.json().get("Time Series (Daily)", {})
        return [float(v["2. high"]) for v in ts.values()]
    except Exception as exc:
        logger.warning("profiler av %s: %s", asset, exc)
        return []


async def _fetch_context(asset: str) -> _TradeContext:
    """Fetch Finnhub quote, AV 52w-high, and news sentiment concurrently."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        fh_data, av_highs, sentiment = await asyncio.gather(
            asyncio.create_task(_finnhub_intraday(asset, http)),
            asyncio.create_task(_av_highs(asset, http)),
            asyncio.create_task(get_news_sentiment(asset, http=http)),
        )

    return _TradeContext(
        day_open=float(fh_data["o"]) if fh_data else None,
        day_high=float(fh_data["h"]) if fh_data else None,
        day_low=float(fh_data["l"]) if fh_data else None,
        week52_high=max(av_highs) if av_highs else None,
        news_mood=sentiment.mood,
        news_consolidated=sentiment.consolidated,
    )


# ── Claude bias analysis ──────────────────────────────────────────────────────

_BIAS_TOOL: dict = {
    "name": "analyze_bias",
    "description": "Record the dominant cognitive bias detected in this trade.",
    "input_schema": {
        "type": "object",
        "required": ["primary_bias", "confidence_score", "reasoning", "suggested_action"],
        "properties": {
            "primary_bias": {
                "type": "string",
                "enum": ["FOMO", "Loss Aversion", "Anchoring Bias", "No Bias Detected"],
                "description": "The single most dominant bias in this trade.",
            },
            "confidence_score": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "0.0 = no evidence, 1.0 = certainty.",
            },
            "reasoning": {
                "type": "string",
                "description": "Short punchy 1-2 sentence explanation of why this bias applies.",
            },
            "suggested_action": {
                "type": "string",
                "description": (
                    "Concrete intervention, e.g. 'Enforce a 24-hour cool-off period before "
                    "buying momentum stocks', 'Set a hard stop-loss at 8% below entry'."
                ),
            },
        },
    },
}


def _build_prompt(
    asset: str,
    trade_price: float,
    trade_side: str,
    sentiment_score: float,
    ctx: _TradeContext,
) -> str:
    def _fmt(v: float | None, prefix: str = "$") -> str:
        return f"{prefix}{v:,.2f}" if v is not None else "N/A"

    proximity_to_high = (
        f"{((trade_price - ctx.day_high) / ctx.day_high * 100):+.1f}% vs day high"
        if ctx.day_high else "N/A"
    )
    proximity_to_low = (
        f"{((trade_price - ctx.day_low) / ctx.day_low * 100):+.1f}% vs day low"
        if ctx.day_low else "N/A"
    )

    # Detect round-number anchoring heuristic for the prompt
    round_ref = round(trade_price / 50) * 50       # nearest $50 level
    anchor_diff = abs(trade_price - round_ref) / max(round_ref, 1) * 100

    return f"""You are the Neufin Behavioral Profiler. Analyze the following trade for cognitive bias.

TRADE
  Asset:           {asset}
  Side:            {trade_side}
  Executed Price:  {_fmt(trade_price)}
  Sentiment Score: {sentiment_score:+.2f}  (-1.0 fear … +1.0 greed)

MARKET CONTEXT
  Day Open:       {_fmt(ctx.day_open)}
  Day High:       {_fmt(ctx.day_high)}
  Day Low:        {_fmt(ctx.day_low)}
  52-week High:   {_fmt(ctx.week52_high)}
  vs Day High:    {proximity_to_high}
  vs Day Low:     {proximity_to_low}
  Nearest $50 level: {_fmt(round_ref)}  ({anchor_diff:.1f}% away)

NEWS SENTIMENT ({ctx.news_mood.upper()})
{ctx.news_consolidated}

BIAS CRITERIA — apply the FIRST that matches:
1. FOMO            — {trade_side} is BUY, price within 1.5% of day high, AND sentiment_score > 0.5
2. Loss Aversion   — {trade_side} is BUY, price within 1.5% of day low, AND sentiment_score < 0
3. Anchoring Bias  — price within 0.75% of a round $50 level OR within 0.5% of the 52-week high
4. No Bias Detected— none of the above apply

Call analyze_bias with your findings. Be punchy and specific in reasoning."""


@dataclass
class _BiasResult:
    primary_bias: str
    confidence_score: float
    reasoning: str
    suggested_action: str


async def _call_anthropic(prompt: str) -> _BiasResult:
    """Try Anthropic claude-haiku-4-5 with forced analyze_bias tool call."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        tools=[_BIAS_TOOL],
        tool_choice={"type": "tool", "name": "analyze_bias"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "analyze_bias":
            inp = block.input
            return _BiasResult(
                primary_bias=inp["primary_bias"],
                confidence_score=float(inp["confidence_score"]),
                reasoning=inp["reasoning"],
                suggested_action=inp["suggested_action"],
            )
    raise ValueError("Anthropic response contained no analyze_bias tool call")


# JSON schema passed as a function tool for OpenAI
_OPENAI_FUNCTION: dict = {
    "name": "analyze_bias",
    "description": _BIAS_TOOL["description"],
    "parameters": _BIAS_TOOL["input_schema"],
}


async def _call_openai(prompt: str) -> _BiasResult:
    """Try OpenAI gpt-4o-mini with forced function call."""
    import json

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=512,
        tools=[{"type": "function", "function": _OPENAI_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "analyze_bias"}},
        messages=[{"role": "user", "content": prompt}],
    )
    for choice in response.choices:
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                if tc.function.name == "analyze_bias":
                    inp = json.loads(tc.function.arguments)
                    return _BiasResult(
                        primary_bias=inp["primary_bias"],
                        confidence_score=float(inp["confidence_score"]),
                        reasoning=inp["reasoning"],
                        suggested_action=inp["suggested_action"],
                    )
    raise ValueError("OpenAI response contained no analyze_bias tool call")


# Gemini prompt template — instructs the model to reply with JSON only
_GEMINI_SYSTEM = (
    "You are the Neufin Behavioral Profiler. "
    "Always reply with a single JSON object containing exactly these keys: "
    "primary_bias (one of: FOMO, Loss Aversion, Anchoring Bias, No Bias Detected), "
    "confidence_score (0.0–1.0), reasoning (string), suggested_action (string). "
    "No extra text, no markdown fences."
)


async def _call_gemini(prompt: str) -> _BiasResult:
    """Try Gemini gemini-2.0-flash with JSON-mode output (google-genai SDK)."""
    import json

    client = google_genai.Client(api_key=settings.gemini_api_key)
    full_prompt = f"{_GEMINI_SYSTEM}\n\n{prompt}"
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=full_prompt,
        config=google_genai.types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    raw = response.text.strip()
    inp = json.loads(raw)
    return _BiasResult(
        primary_bias=inp["primary_bias"],
        confidence_score=float(inp["confidence_score"]),
        reasoning=inp["reasoning"],
        suggested_action=inp["suggested_action"],
    )


_FALLBACK_RESULT = _BiasResult(
    primary_bias="No Bias Detected",
    confidence_score=0.0,
    reasoning="All LLM providers failed; analysis unavailable.",
    suggested_action="Retry analysis when providers are reachable.",
)


async def _get_bias_analysis(prompt: str) -> _BiasResult:
    """
    LLM waterfall: Anthropic → OpenAI gpt-4o-mini → Gemini 1.5 Flash.

    Each provider is tried in order.  On any exception (API error, quota,
    missing key) the next provider is attempted.  If all three fail the
    hard-coded ``_FALLBACK_RESULT`` is returned so the trade flow is never
    blocked.
    """
    providers = [
        ("anthropic", _call_anthropic, settings.anthropic_api_key),
        ("openai",    _call_openai,    settings.openai_api_key),
        ("gemini",    _call_gemini,    settings.gemini_api_key),
    ]
    for name, fn, key in providers:
        if not key:
            logger.debug("profiler: skipping %s (no API key configured)", name)
            continue
        try:
            result = await fn(prompt)
            logger.info("profiler: bias analysis succeeded via %s", name)
            return result
        except Exception as exc:
            logger.warning("profiler: %s failed, trying next provider: %s", name, exc)

    logger.error("profiler: all LLM providers exhausted — returning fallback result")
    return _FALLBACK_RESULT


# ── DB persistence ────────────────────────────────────────────────────────────

# asyncpg parses ":param::type" as a positional placeholder collision, so we
# must not mix SQLAlchemy named params with PostgreSQL cast syntax (::).
# Instead, bind detected_biases with an explicit JSONB type so SQLAlchemy's
# asyncpg dialect serialises the Python list correctly before sending it.
_INSERT_BIAS_SQL = text("""
    INSERT INTO spokes.neufin_bias_scores
        (venture_id, user_id, detected_biases, behavioral_risk_score, coach_note)
    VALUES
        (:venture_id, :user_id, :detected_biases, :behavioral_risk_score, :coach_note)
""").bindparams(bindparam("detected_biases", type_=JSONB()))


async def _save_result(
    venture_id: uuid.UUID,
    user_id: uuid.UUID,
    result: _BiasResult,
) -> None:
    """Persist the bias result to spokes.neufin_bias_scores."""
    coach_note = f"{result.reasoning} {result.suggested_action}"
    behavioral_risk = round(result.confidence_score * 10, 2)
    # Pass a Python list — SQLAlchemy's JSONB bindparam serialises it correctly.
    detected = [result.primary_bias]

    async with async_session_maker() as session:
        async with session.begin():
            # Set RLS context so the WITH CHECK policy on neufin_bias_scores passes
            await session.execute(
                text("SELECT set_config('app.current_venture_id', :vid, true)"),
                {"vid": str(venture_id)},
            )
            await session.execute(
                _INSERT_BIAS_SQL,
                {
                    "venture_id": venture_id,
                    "user_id": user_id,
                    "detected_biases": detected,
                    "behavioral_risk_score": behavioral_risk,
                    "coach_note": coach_note,
                },
            )

    logger.info(
        "profiler: %s | bias=%s (%.2f) | risk=%.1f",
        venture_id, result.primary_bias, result.confidence_score, behavioral_risk,
    )


# ── Public entry point ────────────────────────────────────────────────────────

async def profile_trade(
    *,
    trade_id: uuid.UUID,
    venture_id: uuid.UUID,
    user_id: uuid.UUID,
    asset: str,
    trade_price: float,
    trade_side: str,        # "BUY" | "SELL"
    sentiment_score: float,
) -> None:
    """
    Background task: analyze one trade for cognitive biases.

    Called by FastAPI BackgroundTasks after the trade is committed.
    Creates its own DB session — the request session is already closed.

    Parameters mirror NeufinTrade fields so callers don't need to import
    the ORM model; they just pass scalars extracted from the saved row.
    """
    logger.info(
        "profiler: starting analysis trade_id=%s asset=%s price=%.4f",
        trade_id, asset, trade_price,
    )
    try:
        ctx = await _fetch_context(asset)
        prompt = _build_prompt(asset, trade_price, trade_side, sentiment_score, ctx)
        result = await _get_bias_analysis(prompt)
        await _save_result(venture_id, user_id, result)
    except Exception as exc:
        # Profiling is non-critical — log and continue, never break the trade flow
        logger.error(
            "profiler: failed for trade_id=%s: %s", trade_id, exc, exc_info=True
        )
