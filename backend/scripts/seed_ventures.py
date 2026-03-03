#!/usr/bin/env python3
"""
Seed the 4 core ventures into hub.organizations.

Idempotent — safe to run multiple times (INSERT ... ON CONFLICT DO NOTHING).

Neufin is assigned the static UUID 550e8400-e29b-41d4-a716-446655440000
so that frontend development can hard-code it.  The other three ventures
receive fixed UUIDs as well to keep staging environments reproducible.

Usage
-----
    cd fastapi-hub-spoke
    python scripts/seed_ventures.py

Requirements
------------
* hub.organizations table must exist (run Alembic migrations first).
* DATABASE_URL must be set in .env or the environment.
  The script connects directly — no RLS context is set, so it bypasses
  the venture_isolation policy on tables that enforce it.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# ── PYTHONPATH: shared_services ───────────────────────────────────────────────
_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "shared_services"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_root / ".env", override=False)

import uuid  # noqa: E402

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from core.config import settings  # noqa: E402

# ── Venture definitions ───────────────────────────────────────────────────────
# Static UUIDs — never change these after first deployment.

VENTURES: list[dict] = [
    {
        "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),  # Neufin — static for FE dev
        "name": "Neufin",
        "slug": "neufin",
        "description": (
            "Behavioural finance intelligence platform for wealth managers. "
            "Detects cognitive trading biases (FOMO, Disposition Effect, Sunk Cost) "
            "and generates personalised coach notes using AI-powered analysis of "
            "real-time market data and user trade history."
        ),
    },
    {
        "id": uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        "name": "Arisole",
        "slug": "arisole",
        "description": (
            "IoT gait analysis platform for biomechanics and sports science. "
            "Processes high-frequency sensor telemetry from wearables, identifies "
            "movement anomalies, and streams insights to clinicians and coaches."
        ),
    },
    {
        "id": uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8"),
        "name": "Neumas",
        "slug": "neumas",
        "description": (
            "Retail inventory intelligence and supply-chain optimisation. "
            "Forecasts demand, detects stock anomalies, and automates reorder "
            "workflows using time-series models and supplier integrations."
        ),
    },
    {
        "id": uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8"),
        "name": "Apex",
        "slug": "apex",
        "description": (
            "Event scheduling and course management platform for golf and leisure. "
            "Handles tee-time booking, tournament scheduling, membership management, "
            "and generates ical / calendar exports for participants."
        ),
    },
]

_INSERT_SQL = text("""
    INSERT INTO hub.organizations (id, name, slug, description)
    VALUES (:id, :name, :slug, :description)
    ON CONFLICT (id) DO NOTHING
""")


async def seed() -> None:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    async with engine.begin() as conn:
        for v in VENTURES:
            result = await conn.execute(
                _INSERT_SQL,
                {
                    "id": v["id"],
                    "name": v["name"],
                    "slug": v["slug"],
                    "description": v["description"],
                },
            )
            inserted = result.rowcount
            status = "inserted" if inserted else "already exists"
            print(f"  {v['slug']:10s}  {v['id']}  → {status}")

    await engine.dispose()


async def main() -> None:
    print("\nSeeding hub.organizations …\n")
    try:
        await seed()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print(
            "\nMake sure you have run 'alembic upgrade head' first "
            "so that hub.organizations exists."
        )
        sys.exit(1)
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
