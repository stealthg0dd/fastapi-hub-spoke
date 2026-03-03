"""
Neufin Pydantic schemas.

These are the canonical data-transfer objects for trade events and user
behavior profiles.  They are used at API boundaries (request validation,
response serialisation) and as the input contract for the profiler agent.

They intentionally have no SQLAlchemy dependency — keeping validation logic
separate from persistence logic.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class TradeEvent(BaseModel):
    """
    A single executed trade submitted by or attributed to a user.

    Fields
    ------
    asset
        Ticker or trading pair symbol (e.g. "AAPL", "BTC/USD", "ETH-PERP").
        Max 30 characters to accommodate crypto pair formats.
    timestamp
        UTC execution timestamp of the trade.
    price
        Execution price.  Stored as Decimal to preserve precision for both
        equities (2 d.p.) and crypto assets (up to 8 d.p.).
    user_sentiment_score
        Self-reported or model-derived sentiment at the moment of the trade.
        Range: -1.0 (extreme fear / panic selling) to +1.0 (extreme greed /
        FOMO buying).  A score near 0.0 indicates neutral / unemotional
        decision-making.
    """

    asset: str = Field(..., min_length=1, max_length=30, examples=["AAPL", "BTC/USD"])
    timestamp: datetime
    price: Decimal = Field(..., gt=0, decimal_places=8)
    user_sentiment_score: float = Field(..., ge=-1.0, le=1.0)

    @field_validator("asset")
    @classmethod
    def asset_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    model_config = {"json_encoders": {Decimal: str}}


class UserBehaviorProfile(BaseModel):
    """
    Aggregated behavioral profile derived from a user's trading history.

    Produced by the profiler agent and persisted to
    spokes.neufin_behavior_profiles (RLS-scoped to the venture).

    Fields
    ------
    detected_biases
        Ordered list of bias identifiers ranked by severity, e.g.
        ["loss_aversion", "recency_bias", "overconfidence"].
        Values must be drawn from the canonical bias taxonomy defined
        in spokes/neufin/agents/profiler.py (_BIAS_TAXONOMY).
    risk_tolerance
        Inferred risk appetite on a 0.0–1.0 scale derived from position
        sizing relative to portfolio size and volatility of assets traded.
        0.0 = highly risk-averse, 1.0 = highly risk-seeking.
    historical_alpha_leak
        Estimated percentage-point return given up annually due to
        behavioral biases (e.g. 0.032 = 3.2 pp / year lost to biases).
        Negative values mean biases incidentally aided performance.
    """

    detected_biases: list[str] = Field(default_factory=list)
    risk_tolerance: float = Field(..., ge=0.0, le=1.0)
    historical_alpha_leak: float = Field(
        ...,
        description="Percentage-point annual return lost to behavioral biases",
    )

    @field_validator("detected_biases")
    @classmethod
    def biases_lowercase(cls, v: list[str]) -> list[str]:
        return [b.lower().strip() for b in v]
