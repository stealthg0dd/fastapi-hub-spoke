#!/usr/bin/env python3
"""
Neufin BiasDiscovery — smoke test
==================================

Exercises the full 4-node pipeline:
  DataCollector → ReasoningEngine → BiasLabeler → InterventionGenerator

The DataCollector is given two synthetic trades via a MockDB.
It then calls the Finance MCP for live AAPL and NVDA market data.
The ReasoningEngine analyses whether the user is Revenge Trading or Herding.

Usage
-----
    python test_bias_graph.py

Required
--------
    ANTHROPIC_API_KEY   (claude-opus-4-6 with extended thinking)

Optional — Finance MCP data (graceful fallback to N/A if absent)
--------
    FINNHUB_API_KEY
    ALPHA_VANTAGE_API_KEY
    NEWSAPI_KEY
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

# ── 1. PYTHONPATH bootstrap (before any project imports) ─────────────────────
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "shared_services"))
sys.path.insert(0, str(_ROOT / "spokes" / "neufin"))

# Load .env before settings initialise
from dotenv import load_dotenv  # noqa: E402
load_dotenv(_ROOT / ".env", override=False)

# ── 2. Project imports ────────────────────────────────────────────────────────
from langchain_core.runnables import RunnableConfig          # noqa: E402

from graph.bias_discovery import (                           # noqa: E402
    BiasDiscoveryState,
    bias_labeler,
    data_collector,
    intervention_generator,
    reasoning_engine,
)

# ── 3. Mock DB ────────────────────────────────────────────────────────────────
# We mock the AsyncSession so the DataCollector skips the real Postgres query
# but still calls Finance MCP for live prices and news.

_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

def _trade(tid: str, asset: str, iso: str, price: float, sentiment: float) -> SimpleNamespace:
    """Minimal object that satisfies NeufinTrade attribute access in DataCollector."""
    return SimpleNamespace(
        id=uuid.UUID(tid),
        asset=asset,
        traded_at=datetime.fromisoformat(iso),
        price=Decimal(str(price)),
        sentiment_score=sentiment,
        user_id=_USER_ID,
    )

# Ordered newest → oldest (matches ORDER BY traded_at DESC)
_MOCK_ROWS = [
    _trade(
        tid="aaaaaaaa-0000-0000-0000-000000000002",
        asset="NVDA",
        iso="2026-03-02T10:30:00+00:00",
        price=900.0,
        sentiment=+0.82,   # high excitement — classic FOMO / herding zone
    ),
    _trade(
        tid="aaaaaaaa-0000-0000-0000-000000000001",
        asset="AAPL",
        iso="2026-03-02T10:00:00+00:00",
        price=180.0,
        sentiment=-0.25,   # mild unease — sold under mild fear
    ),
]


class _MockResult:
    def __init__(self, rows: list): self._rows = rows
    def scalars(self) -> "_MockResult": return self
    def all(self) -> list: return self._rows


class MockDB:
    """Pretends to be an AsyncSession; returns the two synthetic trades."""
    async def execute(self, _stmt):
        return _MockResult(_MOCK_ROWS)


# ── 4. Helpers ────────────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 62) -> str:
    return char * width


def _print_market_context(ctx: dict[str, dict]) -> None:
    for sym, snap in ctx.items():
        price  = f"${snap['price']:.2f}"  if snap["price"]      is not None else "unavailable"
        change = f"({snap['change_pct']:+.2f}%)" if snap.get("change_pct") is not None else ""
        nheads = len(snap.get("headlines", []))
        print(f"        {sym:6s} {price:>12s} {change:>10s}  "
              f"source={snap['source']}  headlines={nheads}")
        for h in snap.get("headlines", [])[:2]:
            print(f"               ↳ {h[:72]}")


# ── 5. Main test runner ───────────────────────────────────────────────────────

async def run() -> None:
    # Preflight
    if not os.getenv("ANTHROPIC_API_KEY", ""):
        print("\n  ERROR: ANTHROPIC_API_KEY not set.\n"
              "  Add it to .env or export it before running this test.\n")
        sys.exit(1)

    print(f"\n{_divider('═')}")
    print("  Neufin BiasDiscovery — Smoke Test")
    print(_divider('═'))
    print()
    print("  Test input:")
    print("    Trade 1 │ SELL AAPL @ $180.00  │ 2026-03-02 10:00 UTC │ sentiment −0.25")
    print("    Trade 2 │ BUY  NVDA @ $900.00  │ 2026-03-02 10:30 UTC │ sentiment +0.82")
    print()
    print("  Hypothesis: AAPL sold under mild fear; NVDA bought 30 min later")
    print("              with high excitement.  Expected → Herding / Revenge Trading.")
    print()

    # Shared config — only db matters; nodes take user_id from state
    config = RunnableConfig(configurable={
        "db": MockDB(),
        "user_id": str(_USER_ID),
    })

    initial: BiasDiscoveryState = {
        "user_id": str(_USER_ID),
        "venture_id": "neufin-test",
        "trades": [],
        "market_context": {},
        "reasoning": "",
        "labeled_biases": [],
        "coach_note": "",
    }

    # ── Node 1: DataCollector ─────────────────────────────────────────────────
    print(_divider())
    print("  [1/4]  DataCollector")
    print(_divider())
    print("         Fetching live market data from Finance MCP …\n")

    dc_out = await data_collector(initial, config)

    print(f"         Trades extracted : {len(dc_out['trades'])}")
    print(f"         Symbols queried  : {list(dc_out['market_context'].keys())}\n")
    _print_market_context(dc_out["market_context"])

    state: BiasDiscoveryState = {**initial, **dc_out}

    # ── Node 2: ReasoningEngine ───────────────────────────────────────────────
    print()
    print(_divider())
    print("  [2/4]  ReasoningEngine  (claude-opus-4-6 + extended thinking)")
    print(_divider())
    print("         Comparing trade timing vs. market sentiment …")
    print("         This usually takes 20–60 s.\n")

    re_out = await reasoning_engine(state, config)
    reasoning_text: str = re_out["reasoning"]
    state = {**state, **re_out}

    print(f"         Reasoning length : {len(reasoning_text):,} chars\n")
    # Print a brief excerpt (first 600 chars)
    excerpt = reasoning_text[:600].replace("\n", "\n         ")
    print(f"         Excerpt ↓\n         {excerpt}…\n")

    # ── Node 3: BiasLabeler ───────────────────────────────────────────────────
    print(_divider())
    print("  [3/4]  BiasLabeler")
    print(_divider())

    bl_out = await bias_labeler(state, config)
    labels: list[str] = bl_out["labeled_biases"]
    state = {**state, **bl_out}

    print(f"         Canonical labels : {', '.join(labels)}\n")

    # ── Node 4: InterventionGenerator ────────────────────────────────────────
    print(_divider())
    print("  [4/4]  InterventionGenerator")
    print(_divider())
    print("         Drafting Advisor Note …\n")

    ig_out = await intervention_generator(state, config)
    note: str = ig_out["coach_note"]

    # ── Final output ──────────────────────────────────────────────────────────
    print()
    print(_divider('═'))
    print("  ADVISOR NOTE  (Wealth Manager → Client)")
    print(_divider('═'))
    print()
    # Word-wrap at 60 chars for clean terminal output
    import textwrap
    for para in note.split("\n"):
        if para.strip():
            print(textwrap.fill(para, width=60, initial_indent="  ",
                                subsequent_indent="  "))
        else:
            print()
    print()
    print(_divider('═'))
    print(f"  Detected biases : {', '.join(labels)}")
    print(_divider('═'))
    print()


if __name__ == "__main__":
    asyncio.run(run())
