"""
Neufin SQLAlchemy ORM models — spokes.neufin_* tables.

All tables live in the 'spokes' PostgreSQL schema and carry a venture_id
column so that the standard 'venture_isolation' Row-Level Security policy
(SET LOCAL app.current_venture_id) scopes every query to the active venture.

RLS policies for these tables are applied by the Neufin Alembic migration
chain (spokes/neufin/migrations/), not by the hub migration chain.

Base
----
Defined locally so this module is self-contained and can be imported whether
the spoke runs as a standalone service or within the hub's PYTHONPATH.  The
spoke's migration env.py imports this Base to discover table metadata.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, JSON, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NeufinTrade(Base):
    """
    One executed trade attributed to a user within a venture.

    venture_id  — RLS discriminator; automatically filtered by Postgres policy.
    user_id     — FK-by-convention to hub.users (no FK constraint to keep the
                  spoke decoupled from hub schema migrations).
    asset       — Ticker / trading pair, e.g. "AAPL", "BTC/USD", "ETH-PERP".
    traded_at   — UTC execution timestamp.
    price       — Numeric(18,8) to handle both equities (2 d.p.) and crypto.
    sentiment_score — Sentiment at trade time: -1.0 fear … +1.0 greed.
    """

    __tablename__ = "neufin_trades"
    __table_args__ = (
        Index("ix_neufin_trades_user_traded_at", "user_id", "traded_at"),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    asset: Mapped[str] = mapped_column(String(30), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Numeric(18, 8): handles BTC at $100k+ with 8 decimal places for sats
    price: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NeufinBehaviorProfile(Base):
    """
    Aggregated behavioral profile for one user, updated after each profiler run.

    One row per (venture_id, user_id) pair.  The profiler agent upserts this
    row after analyzing the user's recent trades.

    venture_id           — RLS discriminator.
    user_id              — One profile per user per venture (unique constraint).
    detected_biases      — JSON list of bias slugs ranked by severity,
                           e.g. ["loss_aversion", "recency_bias"].
    risk_tolerance       — Inferred 0.0–1.0 risk appetite score.
    historical_alpha_leak — Estimated pp/year of return lost to biases.
    last_analyzed_at     — Timestamp of the most recent profiler run.
    """

    __tablename__ = "neufin_behavior_profiles"
    __table_args__ = (
        Index(
            "uq_neufin_profile_venture_user",
            "venture_id",
            "user_id",
            unique=True,
        ),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    detected_biases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    risk_tolerance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    historical_alpha_leak: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NeufinBiasScore(Base):
    """
    One bias-analysis result appended after each profiler / BiasDiscovery run.

    Unlike NeufinBehaviorProfile (rolling upsert), this table is append-only:
    every run adds a new row so the dashboard can show temporal drift in a
    user's bias pattern.

    venture_id            — RLS discriminator; automatically filtered by Postgres.
    user_id               — The user whose trades were analysed.
    detected_biases       — Ordered JSON array of canonical bias labels from the
                            BiasLabeler node, e.g. ["FOMO", "Sunk Cost"].
    behavioral_risk_score — Composite 0–10 score from assess_behavioral_risk().
                            NULL if only the bias profiler (not risk assessor) ran.
    coach_note            — AI-generated 3-sentence advisor nudge from
                            InterventionGenerator.  Forwarded verbatim to client.
    analyzed_at           — UTC timestamp of the analysis run.
    """

    __tablename__ = "neufin_bias_scores"
    __table_args__ = (
        Index("ix_neufin_bias_scores_user_analyzed", "user_id", "analyzed_at"),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    detected_biases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    behavioral_risk_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    coach_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NeufinPortfolioHolding(Base):
    """
    One portfolio position imported from Plaid or CSV.

    Append-only per import run — re-importing replaces holdings for that
    (user_id, source) pair by deleting then re-inserting in one transaction.

    venture_id — RLS discriminator.
    source     — "plaid" | "csv" (provenance of the data).
    """

    __tablename__ = "neufin_portfolio_holdings"
    __table_args__ = (
        Index("ix_neufin_holdings_user", "user_id", "venture_id"),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    avg_price: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "plaid" | "csv"
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NeufinPlaidConnection(Base):
    """
    Plaid Item for one user — stores the encrypted access token.

    One row per (venture_id, user_id) — a new exchange_token call replaces
    the existing row (upsert on unique constraint).
    """

    __tablename__ = "neufin_plaid_connections"
    __table_args__ = (
        Index(
            "uq_neufin_plaid_venture_user", "venture_id", "user_id", unique=True
        ),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NeufinSubscription(Base):
    """
    Stripe billing state for one user within a venture.

    One row per (venture_id, user_id).  Created on first billing check.
    is_pro is toggled by the Stripe webhook handler.
    """

    __tablename__ = "neufin_subscriptions"
    __table_args__ = (
        Index(
            "uq_neufin_subscription_venture_user",
            "venture_id",
            "user_id",
            unique=True,
        ),
        {"schema": "spokes"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_pro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
