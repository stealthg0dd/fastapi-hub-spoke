"""
Neufin Bias Profiler Agent

Analyses a user's last 10 trades and returns a structured JSON report
identifying the top 3 cognitive biases, each backed by citations to
specific trade records.

Design
------
- Uses Anthropic tool use (function calling) to force structured JSON output.
  The model cannot deviate from the schema — it must call `report_bias_analysis`
  and fill every required field.
- The system prompt is Neufin-specific and lives here (Rule 2: venture prompts
  stay in their spoke directory).
- The DB session is injected by the caller and must already have
  SET LOCAL app.current_venture_id applied (via get_db()) so that the
  NeufinTrade query is automatically RLS-scoped to the active venture.
- No imports from any other spoke.  Shared infrastructure (Anthropic key,
  async session pattern) is the only cross-cutting dependency.

Entry point
-----------
    result: BiasAnalysis = await analyze_user_biases(
        user_id=uuid.UUID("..."),
        venture_id="...",
        db=session,          # from get_db() — already RLS-configured
    )
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import anthropic
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from mcp.finance_mcp import NewsSentiment, get_news_sentiment
from models.orm import NeufinTrade

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048
_TRADE_LIMIT = 10

# ── Canonical bias taxonomy ──────────────────────────────────────────────────
# Bias slugs used in evidence citations and UserBehaviorProfile.detected_biases
_BIAS_TAXONOMY: frozenset[str] = frozenset(
    {
        "loss_aversion",
        "overconfidence",
        "recency_bias",
        "confirmation_bias",
        "disposition_effect",
        "anchoring",
        "herding",
        "sunk_cost_fallacy",
        "gambler_fallacy",
        "status_quo_bias",
    }
)

# ── Neufin-specific system prompt (stays in this spoke) ─────────────────────
_SYSTEM_PROMPT = """\
You are a quantitative behavioural finance analyst embedded in Neufin's
trading intelligence platform.  Your sole task is to identify the cognitive
biases that are costing this trader money.

BIAS TAXONOMY
You must evaluate the following biases only — do not invent new categories:

• loss_aversion       Holding losing positions too long; cutting winners early.
• overconfidence      Position sizing inconsistent with track record; ignoring
                      base rates; excessive trade frequency.
• recency_bias        Over-weighting the most recent price moves; chasing
                      momentum without fundamental justification.
• confirmation_bias   Trading in the direction of pre-existing views despite
                      clear contrary price signals.
• disposition_effect  Systematic pattern of selling winners and holding losers
                      across multiple trades (statistical, not one-off).
• anchoring           Entry/exit decisions disproportionately influenced by a
                      recent price high or low rather than current fundamentals.
• herding             Clustering trades around major news events or social
                      media sentiment spikes without independent analysis.
• sunk_cost_fallacy   Averaging down into a losing position solely because of
                      prior capital already committed.
• gambler_fallacy     Expecting a reversal after a run of losses/gains with
                      no structural reason for mean-reversion.
• status_quo_bias     Failing to close or resize a position despite changed
                      market conditions.

EVIDENCE REQUIREMENT
For EVERY bias you identify you MUST cite at least one specific trade by its
exact trade_id (UUID) from the data provided.  Generic observations such as
"the trader often buys at peaks" are not acceptable without a trade citation.

SENTIMENT SCORE INTERPRETATION
  -1.0 = extreme fear / panic selling
   0.0 = neutral / unemotional
  +1.0 = extreme greed / FOMO buying

Scores beyond ±0.5 at the time of trade are a strong signal that emotion
overrode analysis.

OUTPUT
Rank the top 3 biases by (severity × confidence).  Use the tool provided.
Be precise and quantitative where possible.  Every evidence observation must
explain WHY that specific trade demonstrates the bias — not just describe it.\
"""

# ── Anthropic tool definition — forces structured JSON output ────────────────
_BIAS_REPORT_TOOL: anthropic.types.ToolParam = {
    "name": "report_bias_analysis",
    "description": (
        "Report the top 3 cognitive biases detected in the trader's "
        "recent trade history, with specific trade citations as evidence."
    ),
    "input_schema": {
        "type": "object",
        "required": ["top_biases", "overall_risk_assessment"],
        "properties": {
            "top_biases": {
                "type": "array",
                "description": "Top 3 biases ranked by severity × confidence.",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": [
                        "bias_name",
                        "confidence",
                        "severity",
                        "description",
                        "evidence",
                    ],
                    "properties": {
                        "bias_name": {
                            "type": "string",
                            "description": "Slug from the canonical bias taxonomy.",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Model's confidence that this bias is present.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Estimated impact on trading performance.",
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Plain-English explanation of how this bias "
                                "manifests in this specific trader's behaviour."
                            ),
                        },
                        "evidence": {
                            "type": "array",
                            "description": "Specific trades that demonstrate this bias.",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": [
                                    "trade_id",
                                    "asset",
                                    "traded_at",
                                    "price",
                                    "sentiment_score",
                                    "observation",
                                ],
                                "properties": {
                                    "trade_id": {
                                        "type": "string",
                                        "description": "Exact UUID of the cited trade.",
                                    },
                                    "asset": {"type": "string"},
                                    "traded_at": {
                                        "type": "string",
                                        "description": "ISO-8601 timestamp of the trade.",
                                    },
                                    "price": {"type": "number"},
                                    "sentiment_score": {"type": "number"},
                                    "observation": {
                                        "type": "string",
                                        "description": (
                                            "Precise explanation of why this "
                                            "trade evidences the named bias."
                                        ),
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "overall_risk_assessment": {
                "type": "string",
                "description": (
                    "Two-to-four sentence summary of the trader's overall "
                    "behavioural risk profile and the primary cost to their "
                    "performance."
                ),
            },
        },
    },
}

# ── Output models ────────────────────────────────────────────────────────────


class BiasEvidence(BaseModel):
    trade_id: str
    asset: str
    traded_at: str
    price: float
    sentiment_score: float
    observation: str


class DetectedBias(BaseModel):
    bias_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(..., pattern="^(low|medium|high)$")
    description: str
    evidence: list[BiasEvidence] = Field(..., min_length=1)


class BiasAnalysis(BaseModel):
    user_id: str
    venture_id: str
    analyzed_trades: int
    top_biases: list[DetectedBias] = Field(..., max_length=3)
    overall_risk_assessment: str
    analyzed_at: datetime


# ── Helpers ──────────────────────────────────────────────────────────────────


def _format_trade_table(trades: list[NeufinTrade]) -> str:
    """
    Render a markdown table of trades for the LLM prompt.
    Oldest trade first so the model can reason about temporal patterns.
    """
    header = (
        "| # | trade_id | asset | traded_at (UTC) | price | sentiment_score |\n"
        "|---|---|---|---|---|---|\n"
    )
    rows = []
    for i, t in enumerate(reversed(trades), start=1):  # oldest → newest
        price_str = f"{Decimal(str(t.price)):.8f}".rstrip("0").rstrip(".")
        rows.append(
            f"| {i} | {t.id} | {t.asset} "
            f"| {t.traded_at.strftime('%Y-%m-%d %H:%M')} "
            f"| {price_str} | {t.sentiment_score:+.2f} |"
        )
    return header + "\n".join(rows)


# ── Public entry point ───────────────────────────────────────────────────────


async def analyze_user_biases(
    *,
    user_id: uuid.UUID,
    venture_id: str,
    db: AsyncSession,
) -> BiasAnalysis:
    """
    Analyse the last 10 trades for *user_id* and return the top 3 cognitive
    biases with specific trade citations as evidence.

    Parameters
    ----------
    user_id:
        The user whose trades are being analysed.
    venture_id:
        The active venture UUID string (used for logging and output labelling).
        The *db* session must already have SET LOCAL app.current_venture_id
        applied — the NeufinTrade query is automatically RLS-scoped.
    db:
        An AsyncSession from get_db() with RLS context active.

    Returns
    -------
    BiasAnalysis
        Validated Pydantic model containing the top biases with evidence.

    Raises
    ------
    ValueError
        If the user has fewer than 2 trades (insufficient data for analysis).
    RuntimeError
        If the LLM does not return a tool_use block (unexpected API response).
    """
    # ── 1. Fetch last N trades (RLS already scoped to venture) ───────────────
    stmt = (
        select(NeufinTrade)
        .where(NeufinTrade.user_id == user_id)
        .order_by(NeufinTrade.traded_at.desc())
        .limit(_TRADE_LIMIT)
    )
    result = await db.execute(stmt)
    trades: list[NeufinTrade] = list(result.scalars().all())

    if len(trades) < 2:
        raise ValueError(
            f"Insufficient trade history for user {user_id}: "
            f"need at least 2 trades, found {len(trades)}."
        )

    logger.info(
        "profiler: analysing %d trades for user=%s venture=%s",
        len(trades),
        user_id,
        venture_id,
    )

    # ── 2. Build the user-turn content ───────────────────────────────────────
    trade_block = (
        f"## Trader Profile\n"
        f"User ID: {user_id}\n"
        f"Venture ID: {venture_id}\n"
        f"Trades provided: {len(trades)} most recent (newest listed last)\n\n"
        f"## Trade History\n\n"
        f"{_format_trade_table(trades)}\n\n"
        f"Identify the top 3 cognitive biases. "
        f"Cite specific trade_ids as evidence for each bias."
    )

    # ── 3. Call Claude with forced tool use ──────────────────────────────────
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        tools=[_BIAS_REPORT_TOOL],
        tool_choice={"type": "tool", "name": "report_bias_analysis"},
        messages=[{"role": "user", "content": trade_block}],
    )

    # ── 4. Extract tool_use block ─────────────────────────────────────────────
    tool_block = next(
        (b for b in message.content if b.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise RuntimeError(
            f"LLM did not return a tool_use block for user={user_id}. "
            f"Stop reason: {message.stop_reason}. "
            f"Content types: {[b.type for b in message.content]}"
        )

    raw: dict = tool_block.input  # type: ignore[union-attr]

    logger.info(
        "profiler: LLM identified %d bias(es) for user=%s",
        len(raw.get("top_biases", [])),
        user_id,
    )

    # ── 5. Validate and return ────────────────────────────────────────────────
    return BiasAnalysis(
        user_id=str(user_id),
        venture_id=venture_id,
        analyzed_trades=len(trades),
        top_biases=[DetectedBias(**b) for b in raw["top_biases"]],
        overall_risk_assessment=raw["overall_risk_assessment"],
        analyzed_at=datetime.now(UTC),
    )


# ── Behavioral Risk Assessment ────────────────────────────────────────────────
# Detects Revenge Trading and Herding over the last 20 trades and outputs
# a composite Behavioral Risk Score (0–10).

_BEHAVIORAL_RISK_LIMIT = 20
_REVENGE_WINDOW_HOURS = 4      # trade within N hours of a loss → candidate
_HERDING_SENTIMENT_THRESHOLD = 0.6  # sentiment_score above this → FOMO zone


class RevengeTrade(BaseModel):
    """A loss-trade immediately followed by another trade within the window."""
    loss_trade_id: str
    loss_asset: str
    loss_price: float
    loss_at: str                 # ISO-8601
    followup_trade_id: str
    followup_asset: str
    followup_price: float
    followup_at: str             # ISO-8601
    hours_apart: float


class HerdingSignal(BaseModel):
    """A buy made when news sentiment was at a 30-day peak (crowd-chasing)."""
    trade_id: str
    asset: str
    traded_at: str               # ISO-8601
    sentiment_score: float
    news_mood: str               # "bullish" | "bearish" | "neutral"
    consolidated_news: str


class TradingBehaviorRisk(BaseModel):
    user_id: str
    venture_id: str
    analyzed_trades: int
    behavioral_risk_score: float = Field(..., ge=0.0, le=10.0)
    revenge_trades: list[RevengeTrade]
    herding_signals: list[HerdingSignal]
    risk_summary: str
    assessed_at: datetime


def _detect_revenge_trades(trades: list[NeufinTrade]) -> list[RevengeTrade]:
    """
    Identify trades where a losing sentiment (score < 0) is followed by
    another trade within _REVENGE_WINDOW_HOURS — a classic revenge pattern.
    Trades must be sorted newest-first (as returned by the DB query).
    """
    # Reverse to chronological order for window comparison
    chron = list(reversed(trades))
    found: list[RevengeTrade] = []
    for i, t in enumerate(chron[:-1]):
        # A "loss trade" is one where the trader acted under negative sentiment
        if t.sentiment_score >= 0:
            continue
        followup = chron[i + 1]
        delta = followup.traded_at - t.traded_at
        hours = delta.total_seconds() / 3600
        if hours <= _REVENGE_WINDOW_HOURS:
            found.append(
                RevengeTrade(
                    loss_trade_id=str(t.id),
                    loss_asset=t.asset,
                    loss_price=float(t.price),
                    loss_at=t.traded_at.isoformat(),
                    followup_trade_id=str(followup.id),
                    followup_asset=followup.asset,
                    followup_price=float(followup.price),
                    followup_at=followup.traded_at.isoformat(),
                    hours_apart=round(hours, 2),
                )
            )
    return found


async def _detect_herding_signals(
    trades: list[NeufinTrade],
    http: httpx.AsyncClient,
) -> list[HerdingSignal]:
    """
    For every trade where sentiment_score >= _HERDING_SENTIMENT_THRESHOLD
    (FOMO zone), fetch current news sentiment for that asset and flag it
    as a potential herding signal.
    """
    fomo_trades = [t for t in trades if t.sentiment_score >= _HERDING_SENTIMENT_THRESHOLD]
    if not fomo_trades:
        return []

    # Deduplicate symbols to avoid redundant API calls
    unique_symbols = list({t.asset for t in fomo_trades})
    sentiments: dict[str, NewsSentiment] = {}
    for sym in unique_symbols:
        sentiments[sym] = await get_news_sentiment(sym, http=http)

    signals: list[HerdingSignal] = []
    for t in fomo_trades:
        snap = sentiments.get(t.asset)
        if snap and snap.mood == "bullish":
            signals.append(
                HerdingSignal(
                    trade_id=str(t.id),
                    asset=t.asset,
                    traded_at=t.traded_at.isoformat(),
                    sentiment_score=t.sentiment_score,
                    news_mood=snap.mood,
                    consolidated_news=snap.consolidated,
                )
            )
    return signals


def _compute_risk_score(
    trades: list[NeufinTrade],
    revenge: list[RevengeTrade],
    herding: list[HerdingSignal],
) -> float:
    """
    Composite Behavioral Risk Score (0–10).

    Component weights
    -----------------
    • Revenge trade frequency  (max 4 pts): each instance = 4 / max(1, N-1) pts
    • Herding signal frequency  (max 4 pts): each instance = 4 / max(1, N) pts
    • Avg absolute sentiment   (max 2 pts): mean(|score|) × 2
    """
    n = len(trades)
    if n < 2:
        return 0.0

    revenge_pts = min(4.0, len(revenge) * (4.0 / max(1, n - 1)))
    herding_pts = min(4.0, len(herding) * (4.0 / max(1, n)))
    avg_abs_sentiment = sum(abs(t.sentiment_score) for t in trades) / n
    sentiment_pts = min(2.0, avg_abs_sentiment * 2.0)

    return round(revenge_pts + herding_pts + sentiment_pts, 2)


async def assess_behavioral_risk(
    *,
    user_id: uuid.UUID,
    venture_id: str,
    db: AsyncSession,
) -> TradingBehaviorRisk:
    """
    Analyse the last 20 trades for *user_id* and return a Behavioral Risk
    Score together with detected Revenge Trading and Herding signals.

    Parameters
    ----------
    user_id:
        The user whose trades are being assessed.
    venture_id:
        Active venture UUID string (for logging and output labelling).
    db:
        AsyncSession from get_db() with RLS context active.

    Returns
    -------
    TradingBehaviorRisk
    """
    stmt = (
        select(NeufinTrade)
        .where(NeufinTrade.user_id == user_id)
        .order_by(NeufinTrade.traded_at.desc())
        .limit(_BEHAVIORAL_RISK_LIMIT)
    )
    result = await db.execute(stmt)
    trades: list[NeufinTrade] = list(result.scalars().all())

    logger.info(
        "behavioral_risk: assessing %d trades for user=%s venture=%s",
        len(trades),
        user_id,
        venture_id,
    )

    revenge: list[RevengeTrade] = _detect_revenge_trades(trades)

    async with httpx.AsyncClient(timeout=10.0) as http:
        herding: list[HerdingSignal] = await _detect_herding_signals(trades, http)

    score = _compute_risk_score(trades, revenge, herding)

    # Build a plain-English risk summary
    parts: list[str] = []
    if revenge:
        parts.append(
            f"{len(revenge)} revenge trade(s) detected "
            f"(trade within {_REVENGE_WINDOW_HOURS}h of a negative-sentiment entry)."
        )
    if herding:
        parts.append(
            f"{len(herding)} herding signal(s) detected "
            f"(high-FOMO trades during bullish news peaks)."
        )
    if not parts:
        parts.append("No significant revenge trading or herding patterns detected.")
    risk_summary = " ".join(parts) + f" Behavioral Risk Score: {score}/10."

    logger.info(
        "behavioral_risk: score=%.2f revenge=%d herding=%d for user=%s",
        score, len(revenge), len(herding), user_id,
    )

    return TradingBehaviorRisk(
        user_id=str(user_id),
        venture_id=venture_id,
        analyzed_trades=len(trades),
        behavioral_risk_score=score,
        revenge_trades=revenge,
        herding_signals=herding,
        risk_summary=risk_summary,
        assessed_at=datetime.now(UTC),
    )
