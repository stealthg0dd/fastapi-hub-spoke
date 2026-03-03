"""Add portfolio holdings, Plaid connections, and Stripe subscriptions

What it does
------------
1. spokes.neufin_portfolio_holdings — positions imported from Plaid or CSV.
   Each import run (re)populates positions for a (user_id, source) pair.

2. spokes.neufin_plaid_connections — Plaid Item per user; stores the
   access_token returned after public-token exchange.  One row per
   (venture_id, user_id) — re-linking upserts the row.

3. spokes.neufin_subscriptions — Stripe billing state.  One row per
   (venture_id, user_id).  is_pro is toggled by the Stripe webhook handler.

Row-Level Security
------------------
The same venture_isolation RLS policy used on neufin_trades is applied to
all three tables so they are automatically scoped by app.current_venture_id.

Revision ID: 004_neufin_portfolio_billing
Revises:     003_neufin_spokes_schema
Create Date: 2026-03-03
"""

from typing import Sequence, Union
from alembic import op

revision: str = "004_neufin_portfolio_billing"
down_revision: Union[str, None] = "003_neufin_spokes_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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
    # ── spokes.neufin_portfolio_holdings ──────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS spokes.neufin_portfolio_holdings (
            id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            venture_id  UUID            NOT NULL,
            user_id     UUID            NOT NULL,
            ticker      VARCHAR(30)     NOT NULL,
            quantity    NUMERIC(18, 8)  NOT NULL,
            avg_price   NUMERIC(18, 8)  NOT NULL,
            source      VARCHAR(20)     NOT NULL,   -- 'plaid' | 'csv'
            imported_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_neufin_holdings_user
            ON spokes.neufin_portfolio_holdings (venture_id, user_id)
    """)
    op.execute(
        "ALTER TABLE spokes.neufin_portfolio_holdings ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE spokes.neufin_portfolio_holdings FORCE ROW LEVEL SECURITY"
    )
    op.execute(_RLS_POLICY.format(table="spokes.neufin_portfolio_holdings"))

    # ── spokes.neufin_plaid_connections ───────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS spokes.neufin_plaid_connections (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            venture_id       UUID         NOT NULL,
            user_id          UUID         NOT NULL,
            access_token     TEXT         NOT NULL,
            item_id          VARCHAR(100) NOT NULL,
            institution_name VARCHAR(255),
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (venture_id, user_id)
        )
    """)
    op.execute(
        "ALTER TABLE spokes.neufin_plaid_connections ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE spokes.neufin_plaid_connections FORCE ROW LEVEL SECURITY"
    )
    op.execute(_RLS_POLICY.format(table="spokes.neufin_plaid_connections"))

    # ── spokes.neufin_subscriptions ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS spokes.neufin_subscriptions (
            id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            venture_id              UUID         NOT NULL,
            user_id                 UUID         NOT NULL,
            stripe_customer_id      VARCHAR(100),
            stripe_subscription_id  VARCHAR(100),
            is_pro                  BOOLEAN      NOT NULL DEFAULT FALSE,
            trial_ends_at           TIMESTAMPTZ,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (venture_id, user_id)
        )
    """)
    op.execute(
        "ALTER TABLE spokes.neufin_subscriptions ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE spokes.neufin_subscriptions FORCE ROW LEVEL SECURITY"
    )
    op.execute(_RLS_POLICY.format(table="spokes.neufin_subscriptions"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS spokes.neufin_subscriptions")
    op.execute("DROP TABLE IF EXISTS spokes.neufin_plaid_connections")
    op.execute("DROP TABLE IF EXISTS spokes.neufin_portfolio_holdings")
