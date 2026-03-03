"""Create spokes schema with neufin_trades and neufin_bias_scores + RLS

What it does
------------
1. Creates the 'spokes' PostgreSQL schema for all venture-specific tables.
2. Creates spokes.neufin_trades — immutable log of every executed trade
   with asset, price, timestamp, and sentiment score at time of trade.
3. Creates spokes.neufin_bias_scores — one row per bias analysis run.
   Stores the detected bias labels (JSON array), the composite behavioral
   risk score, and the AI-generated coach note ("nudge") for the client.
4. Enables Row-Level Security (RLS) + FORCE RLS on both tables.
5. Creates the venture_isolation RLS policy on each table using
   current_setting('app.current_venture_id', true) — the same pattern
   used by hub.knowledge_base.

Row-Level Security notes
------------------------
The SET LOCAL in get_db() writes app.current_venture_id at the start of
every transaction.  Postgres evaluates the USING clause on every row
access and filters out rows whose venture_id doesn't match.

FORCE ROW LEVEL SECURITY applies the policy even to the table owner so
that admin queries from superuser connections are not accidentally filtered
(they will be).  To bypass RLS in a migration/admin context either set
the parameter explicitly or use a BYPASSRLS role.

Revision ID: 003_neufin_spokes_schema
Revises:     002_hub_core_tables
Create Date: 2026-03-02
"""

from typing import Sequence, Union

from alembic import op

# ── Alembic metadata ──────────────────────────────────────────────────────────
revision: str = "003_neufin_spokes_schema"
down_revision: Union[str, None] = "002_hub_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared RLS policy template — parameterised by table name
_RLS_POLICY = """
    CREATE POLICY venture_isolation
        ON {table}
        USING (
            venture_id = current_setting('app.current_venture_id', true)::uuid
        )
        WITH CHECK (
            venture_id = current_setting('app.current_venture_id', true)::uuid
        )
"""


def upgrade() -> None:
    # ── spokes schema ─────────────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS spokes")

    # ── spokes.neufin_trades ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS spokes.neufin_trades (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            venture_id      UUID        NOT NULL,
            user_id         UUID        NOT NULL,
            asset           VARCHAR(30) NOT NULL,
            traded_at       TIMESTAMPTZ NOT NULL,
            price           NUMERIC(18, 8) NOT NULL,
            sentiment_score FLOAT       NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_neufin_trades_venture
            ON spokes.neufin_trades (venture_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_neufin_trades_user_traded_at
            ON spokes.neufin_trades (user_id, traded_at DESC)
    """)

    # Enable RLS
    op.execute("ALTER TABLE spokes.neufin_trades ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE spokes.neufin_trades FORCE ROW LEVEL SECURITY")
    op.execute(_RLS_POLICY.format(table="spokes.neufin_trades"))

    # ── spokes.neufin_bias_scores ─────────────────────────────────────────────
    # One row per analysis run — not upserted; each run appends a new row
    # so the dashboard can show a time-series of improving/worsening scores.
    op.execute("""
        CREATE TABLE IF NOT EXISTS spokes.neufin_bias_scores (
            id                     UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            venture_id             UUID    NOT NULL,
            user_id                UUID    NOT NULL,

            -- JSON array of bias slugs ordered by severity
            -- e.g. ["FOMO", "Disposition Effect", "Sunk Cost"]
            detected_biases        JSONB   NOT NULL DEFAULT '[]',

            -- Composite 0–10 score from the behavioral risk assessor
            behavioral_risk_score  FLOAT,

            -- AI-generated 3-sentence coach note ("nudge") from
            -- InterventionGenerator — forwarded verbatim by the Wealth Manager
            coach_note             TEXT,

            analyzed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_neufin_bias_scores_venture
            ON spokes.neufin_bias_scores (venture_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_neufin_bias_scores_user_analyzed
            ON spokes.neufin_bias_scores (user_id, analyzed_at DESC)
    """)

    op.execute("ALTER TABLE spokes.neufin_bias_scores ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE spokes.neufin_bias_scores FORCE ROW LEVEL SECURITY")
    op.execute(_RLS_POLICY.format(table="spokes.neufin_bias_scores"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS spokes.neufin_bias_scores")
    op.execute("DROP TABLE IF EXISTS spokes.neufin_trades")
    op.execute("DROP SCHEMA IF EXISTS spokes CASCADE")
