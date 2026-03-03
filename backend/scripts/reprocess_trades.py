#!/usr/bin/env python3
"""
Reprocess unanalyzed trades through the Neufin Behavioral Profiler.

Finds all rows in spokes.neufin_trades that have NO corresponding row
in spokes.neufin_bias_scores (i.e. the background profiler hasn't run
yet or previously failed) and runs the profiler on each one.

Usage
-----
    cd fastapi-hub-spoke
    python scripts/reprocess_trades.py

    # Dry-run (list trades without running analysis):
    python scripts/reprocess_trades.py --dry-run

    # Limit to N trades (useful for testing):
    python scripts/reprocess_trades.py --limit 5

    # Target a specific trade by UUID:
    python scripts/reprocess_trades.py --trade-id <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path

# ── PYTHONPATH: shared_services must come before spokes/* ─────────────────────
_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "shared_services"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_root / ".env", override=False)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from agents.neufin_profiler import profile_trade  # noqa: E402
from core.config import settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reprocess_trades")


# ── SQL ───────────────────────────────────────────────────────────────────────

# Fetch trades that have no matching row in neufin_bias_scores.
# RLS is NOT set here — this is a superuser/admin script that runs without
# a venture context so we query across all ventures.
_UNANALYZED_SQL = text("""
    SELECT
        t.id,
        t.venture_id,
        t.user_id,
        t.asset,
        t.price::float        AS trade_price,
        t.sentiment_score,
        t.traded_at
    FROM spokes.neufin_trades t
    LEFT JOIN spokes.neufin_bias_scores b
           ON b.venture_id = t.venture_id
          AND b.user_id    = t.user_id
    WHERE b.id IS NULL
    ORDER BY t.traded_at ASC
    LIMIT :limit
""")

_SINGLE_TRADE_SQL = text("""
    SELECT
        t.id,
        t.venture_id,
        t.user_id,
        t.asset,
        t.price::float        AS trade_price,
        t.sentiment_score,
        t.traded_at
    FROM spokes.neufin_trades t
    WHERE t.id = :trade_id
""")


async def _fetch_trades(
    session: AsyncSession,
    *,
    trade_id: uuid.UUID | None,
    limit: int,
) -> list[dict]:
    """Return a list of trade dicts to process."""
    if trade_id:
        rows = (await session.execute(_SINGLE_TRADE_SQL, {"trade_id": trade_id})).mappings().all()
    else:
        rows = (await session.execute(_UNANALYZED_SQL, {"limit": limit})).mappings().all()
    return [dict(r) for r in rows]


async def reprocess(
    *,
    dry_run: bool = False,
    limit: int = 100,
    trade_id: uuid.UUID | None = None,
) -> None:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        trades = await _fetch_trades(session, trade_id=trade_id, limit=limit)

    await engine.dispose()

    if not trades:
        logger.info("No unanalyzed trades found — nothing to do.")
        return

    logger.info("Found %d trade(s) to process.", len(trades))

    if dry_run:
        for t in trades:
            logger.info(
                "  [DRY-RUN] trade_id=%-36s  asset=%-8s  price=%.4f",
                t["id"], t["asset"], t["trade_price"],
            )
        return

    for i, t in enumerate(trades, 1):
        trade_side = "BUY" if t["sentiment_score"] >= 0 else "SELL"
        logger.info(
            "[%d/%d] Profiling trade_id=%s  asset=%s  side=%s  price=%.4f",
            i, len(trades), t["id"], t["asset"], trade_side, t["trade_price"],
        )
        await profile_trade(
            trade_id=t["id"],
            venture_id=t["venture_id"],
            user_id=t["user_id"],
            asset=t["asset"],
            trade_price=t["trade_price"],
            trade_side=trade_side,
            sentiment_score=float(t["sentiment_score"]),
        )

    logger.info("Reprocessing complete.  %d trade(s) profiled.", len(trades))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List trades that would be processed without actually running the profiler.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of trades to process in one run (default: 100).",
    )
    parser.add_argument(
        "--trade-id",
        type=uuid.UUID,
        default=None,
        metavar="UUID",
        help="Re-analyze a specific trade by UUID (ignores --limit, reprocesses even if already analyzed).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        reprocess(
            dry_run=args.dry_run,
            limit=args.limit,
            trade_id=args.trade_id,
        )
    )
