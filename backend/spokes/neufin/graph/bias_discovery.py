"""
BiasDiscovery — Neufin's 4-node LangGraph bias detection pipeline.

Graph topology
--------------

    START
      │
      ▼
  DataCollector       Queries last 5 trades from DB (RLS-scoped).
      │               Calls Finance MCP for real-time price + news
      │               for every unique ticker in those trades.
      ▼
  ReasoningEngine     Uses claude-opus-4-6 with extended thinking
      │               (budget: 8 000 tokens) to compare market
      │               sentiment and news at trade time vs. the
      │               user's actual trade decisions.
      ▼
  BiasLabeler         Uses tool-use to map the reasoning to exactly
      │               one or more of: FOMO, Disposition Effect,
      │               Sunk Cost.
      ▼
  InterventionGenerator  Drafts a 3-sentence Coach Note for the
      │               Wealth Manager to forward to their client.
      ▼
    END

State keys flow
---------------
    DataCollector  →  trades, market_context
    ReasoningEngine →  reasoning
    BiasLabeler    →  labeled_biases
    InterventionGenerator → coach_note

Config keys (via RunnableConfig["configurable"])
------------------------------------------------
    db : AsyncSession   — RLS-scoped session from get_db()
    user_id : str       — UUID of the user being analysed

Usage
-----
    from graph.bias_discovery import compiled_bias_graph
    from langchain_core.runnables import RunnableConfig

    result = await compiled_bias_graph.ainvoke(
        {
            "user_id": str(user_id),
            "venture_id": venture_id,
            "trades": [],
            "market_context": {},
            "reasoning": "",
            "labeled_biases": [],
            "coach_note": "",
        },
        config=RunnableConfig(configurable={"db": db, "user_id": str(user_id)}),
    )
    print(result["coach_note"])
"""

import asyncio
import logging
import uuid
from typing import TypedDict

import anthropic
import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from mcp.finance_mcp import MarketSnapshot, get_market_context_batch
from models.orm import NeufinTrade

logger = logging.getLogger(__name__)

_SONNET = "claude-sonnet-4-6"
_OPUS = "claude-opus-4-6"
_TRADE_LIMIT = 5


# ── State ────────────────────────────────────────────────────────────────────

class BiasDiscoveryState(TypedDict):
    user_id: str
    venture_id: str

    # DataCollector
    trades: list[dict]                  # serialised NeufinTrade rows
    market_context: dict[str, dict]     # symbol → MarketSnapshot.__dict__

    # ReasoningEngine
    reasoning: str

    # BiasLabeler
    labeled_biases: list[str]           # subset of _ALLOWED_LABELS

    # InterventionGenerator
    coach_note: str


_ALLOWED_LABELS: list[str] = ["FOMO", "Disposition Effect", "Sunk Cost"]


# ── Node 1: DataCollector ─────────────────────────────────────────────────────

async def data_collector(state: BiasDiscoveryState, config: RunnableConfig) -> dict:
    """
    Query the last 5 trades for the user (RLS-scoped) then enrich each
    ticker with real-time price and news via the Finance MCP.
    """
    db: AsyncSession = config["configurable"]["db"]
    user_id = uuid.UUID(state["user_id"])

    stmt = (
        select(NeufinTrade)
        .where(NeufinTrade.user_id == user_id)
        .order_by(NeufinTrade.traded_at.desc())
        .limit(_TRADE_LIMIT)
    )
    result = await db.execute(stmt)
    rows: list[NeufinTrade] = list(result.scalars().all())

    trades: list[dict] = [
        {
            "trade_id": str(t.id),
            "asset": t.asset,
            "traded_at": t.traded_at.isoformat(),
            "price": float(t.price),
            "sentiment_score": t.sentiment_score,
        }
        for t in rows
    ]

    symbols = list({t["asset"] for t in trades})
    logger.info(
        "data_collector: %d trades, %d unique symbols for user=%s",
        len(trades),
        len(symbols),
        state["user_id"],
    )

    market_context: dict[str, dict] = {}
    if symbols:
        async with httpx.AsyncClient(timeout=10.0) as http:
            snapshots: dict[str, MarketSnapshot] = await get_market_context_batch(
                symbols, http=http, fetch_history=False
            )
        for sym, snap in snapshots.items():
            market_context[sym] = {
                "symbol": snap.symbol,
                "price": snap.price,
                "source": snap.source,
                "change_pct": snap.change_pct,
                "headlines": snap.headlines,
            }

    return {"trades": trades, "market_context": market_context}


# ── Node 2: ReasoningEngine ───────────────────────────────────────────────────

_REASONING_SYSTEM = """\
You are a senior quantitative behavioural finance researcher at Neufin.
You will be given:
  1. A trader's last 5 executed trades (asset, timestamp, price, sentiment score).
  2. The current market context for each asset (real-time price, % change, recent headlines).

Your task: compare what the MARKET was signalling at the time of each trade against
what the trader actually did.  Look for divergence between market sentiment and the
trader's decision.  Think carefully and systematically — consider:

  • Were trades made into strongly negative news (fear override → possible FOMO)?
  • Did the trader hold an asset while it declined across multiple trades
    (disposition effect or sunk cost)?
  • Did sentiment scores spike abnormally on losing trades (emotional trading)?
  • Are there assets where the trader bought after significant run-ups
    (recency / herding)?

Be precise.  Reference specific trade timestamps and news headlines as evidence.
Do not diagnose biases yet — only reason through the evidence."""


async def reasoning_engine(state: BiasDiscoveryState, config: RunnableConfig) -> dict:  # noqa: ARG001
    """
    Extended-thinking reasoning pass: market context vs user trade timing.
    Uses claude-opus-4-6 with 8 000-token thinking budget.
    """
    trades_block = "\n".join(
        f"  {i+1}. {t['asset']} @ {t['price']} "
        f"on {t['traded_at']} | sentiment={t['sentiment_score']:+.2f}"
        for i, t in enumerate(state["trades"])
    )

    context_block = "\n".join(
        f"  {sym}: price={ctx.get('price', 'N/A')} "
        f"({ctx.get('change_pct', 0):+.1f}%), "
        f"headlines=[{', '.join(repr(h[:60]) for h in ctx.get('headlines', [])[:3])}]"
        for sym, ctx in state["market_context"].items()
    )

    user_content = (
        f"## Trader's Last {len(state['trades'])} Trades\n{trades_block}\n\n"
        f"## Current Market Context\n{context_block}\n\n"
        f"Reason carefully through the evidence above."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=_OPUS,
        max_tokens=10_000,
        thinking={"type": "enabled", "budget_tokens": 8_000},
        system=_REASONING_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    # Extract the visible text block (not the thinking block)
    reasoning_text = "\n\n".join(
        block.text
        for block in response.content
        if block.type == "text"
    )

    logger.info(
        "reasoning_engine: %d chars of reasoning for user=%s",
        len(reasoning_text),
        state["user_id"],
    )
    return {"reasoning": reasoning_text}


# ── Node 3: BiasLabeler ───────────────────────────────────────────────────────

_LABEL_TOOL: anthropic.types.ToolParam = {
    "name": "label_biases",
    "description": (
        "Map the reasoning analysis to the applicable high-level bias labels. "
        "Choose only from the three canonical labels. "
        "You may select more than one if the evidence supports it."
    ),
    "input_schema": {
        "type": "object",
        "required": ["labels", "rationale"],
        "properties": {
            "labels": {
                "type": "array",
                "description": "One to three bias labels that apply.",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "string",
                    "enum": ["FOMO", "Disposition Effect", "Sunk Cost"],
                },
            },
            "rationale": {
                "type": "string",
                "description": (
                    "One sentence per label explaining which trade evidence "
                    "triggered that label."
                ),
            },
        },
    },
}

_LABELER_SYSTEM = """\
You are a behavioural finance classifier.  You receive a detailed reasoning
analysis of a trader's recent behaviour.  Map the evidence to the following
canonical labels only:

  • FOMO (Fear Of Missing Out): Trader chased momentum or bought into euphoria,
    driven by fear of being left out of a rally.

  • Disposition Effect: Trader systematically sold winners early and/or held
    losers too long across multiple trades.

  • Sunk Cost: Trader averaged down or held a losing position purely because
    of prior capital committed, not because the outlook improved.

Select every label that the evidence clearly supports.  Use the tool provided."""


async def bias_labeler(state: BiasDiscoveryState, config: RunnableConfig) -> dict:  # noqa: ARG001
    """Map the ReasoningEngine output to one or more of the 3 canonical labels."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=_SONNET,
        max_tokens=512,
        system=_LABELER_SYSTEM,
        tools=[_LABEL_TOOL],
        tool_choice={"type": "tool", "name": "label_biases"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"## Reasoning Analysis\n\n{state['reasoning']}\n\n"
                    "Apply the appropriate bias label(s)."
                ),
            }
        ],
    )

    tool_block = next(
        (b for b in response.content if b.type == "tool_use"), None
    )
    if tool_block is None:
        logger.warning("bias_labeler: no tool_use block returned, defaulting to FOMO")
        return {"labeled_biases": ["FOMO"]}

    labels: list[str] = tool_block.input.get("labels", ["FOMO"])  # type: ignore[union-attr]
    valid = [l for l in labels if l in _ALLOWED_LABELS]
    logger.info(
        "bias_labeler: labels=%s for user=%s", valid, state["user_id"]
    )
    return {"labeled_biases": valid or ["FOMO"]}


# ── Node 4: InterventionGenerator ────────────────────────────────────────────

_INTERVENTION_SYSTEM = """\
You are a Wealth Manager coach writing a brief, empathetic message that the
Wealth Manager will forward verbatim to their client.

Rules:
  • Exactly 3 sentences.
  • Sentence 1: Acknowledge what the data shows about the client's recent trading
    pattern — be specific but not accusatory.
  • Sentence 2: Name the cognitive bias in plain English and explain the financial
    cost it creates (no jargon like "disposition effect" — say "selling winners
    too early").
  • Sentence 3: Offer one concrete, actionable change the client can make before
    their next trade.

Tone: warm, professional, forward-looking.  Never use "you failed" or "you made
a mistake".  The client is intelligent — treat them accordingly."""


async def intervention_generator(
    state: BiasDiscoveryState, config: RunnableConfig  # noqa: ARG001
) -> dict:
    """
    Draft a 3-sentence Coach Note based on the labeled biases and reasoning.
    This is what the Wealth Manager sends to their client.
    """
    bias_str = " and ".join(state["labeled_biases"])
    user_content = (
        f"## Detected Biases\n{bias_str}\n\n"
        f"## Supporting Analysis\n{state['reasoning'][:1500]}\n\n"
        f"## Trades\n"
        + "\n".join(
            f"  {t['asset']} @ {t['price']} on {t['traded_at']}"
            for t in state["trades"]
        )
        + "\n\nWrite the 3-sentence Coach Note now."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=_SONNET,
        max_tokens=300,
        system=_INTERVENTION_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    note = response.content[0].text.strip()  # type: ignore[index]
    logger.info(
        "intervention_generator: coach note drafted for user=%s (%d chars)",
        state["user_id"],
        len(note),
    )
    return {"coach_note": note}


# ── Graph assembly ────────────────────────────────────────────────────────────

_builder = StateGraph(BiasDiscoveryState)

_builder.add_node("DataCollector", data_collector)
_builder.add_node("ReasoningEngine", reasoning_engine)
_builder.add_node("BiasLabeler", bias_labeler)
_builder.add_node("InterventionGenerator", intervention_generator)

_builder.add_edge(START, "DataCollector")
_builder.add_edge("DataCollector", "ReasoningEngine")
_builder.add_edge("ReasoningEngine", "BiasLabeler")
_builder.add_edge("BiasLabeler", "InterventionGenerator")
_builder.add_edge("InterventionGenerator", END)

compiled_bias_graph = _builder.compile()
