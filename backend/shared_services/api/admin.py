"""
Hub Admin API — cross-venture analytics.

Endpoints here are protected by the ``hub.admin_`` key bypass in
VentureIDMiddleware (no X-Venture-ID required, no RLS context set).
Never mount these routes under a venture-scoped prefix.

Endpoints
---------
GET /admin/venture-risk-leaderboard
    Returns all ventures ordered by average behavioral risk score (desc),
    together with their total trade volume.  Ventures with no trades are
    included with zeros.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_admin_db

router = APIRouter(tags=["admin"])


# ── Response model ─────────────────────────────────────────────────────────────

class VentureRiskEntry(BaseModel):
    venture: str
    avg_risk: float
    total_trades: int


# ── SQL ────────────────────────────────────────────────────────────────────────

# Join hub.organizations against trade counts and average risk scores from the
# spokes schema.  Because RLS is not active for admin sessions, this query
# sees all rows across every venture partition.
#
# Ventures with no trades appear with zeros (LEFT JOIN + COALESCE).
# Ordered by avg_risk DESC so the riskiest venture is always first.

_LEADERBOARD_SQL = text("""
    SELECT
        o.slug                                          AS venture,
        COALESCE(t.total_trades, 0)::int               AS total_trades,
        ROUND(COALESCE(b.avg_risk, 0.0)::numeric, 2)   AS avg_risk
    FROM hub.organizations o

    LEFT JOIN (
        SELECT venture_id, COUNT(*) AS total_trades
        FROM   spokes.neufin_trades
        GROUP  BY venture_id
    ) t ON t.venture_id = o.id

    LEFT JOIN (
        SELECT venture_id, AVG(behavioral_risk_score) AS avg_risk
        FROM   spokes.neufin_bias_scores
        GROUP  BY venture_id
    ) b ON b.venture_id = o.id

    ORDER BY avg_risk DESC, total_trades DESC
""")


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get(
    "/venture-risk-leaderboard",
    response_model=list[VentureRiskEntry],
    summary="Cross-venture behavioral risk leaderboard",
    description=(
        "Returns every venture ordered by average behavioral risk score "
        "(highest first). Requires a Global Admin key (X-API-Key: hub.admin_…). "
        "No X-Venture-ID header needed — RLS is not applied."
    ),
)
async def venture_risk_leaderboard(
    db: AsyncSession = Depends(get_admin_db),
) -> list[VentureRiskEntry]:
    rows = (await db.execute(_LEADERBOARD_SQL)).mappings().all()
    return [
        VentureRiskEntry(
            venture=r["venture"],
            avg_risk=float(r["avg_risk"]),
            total_trades=int(r["total_trades"]),
        )
        for r in rows
    ]
