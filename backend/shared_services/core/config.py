from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is 3 levels up from backend/shared_services/core/config.py
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        extra="ignore",
    )

    # Database
    # DATABASE_URL  → Transaction Pooler (port 6543) — used by the app at runtime.
    # DIRECT_URL    → Direct connection (port 5432) — used only by Alembic migrations
    #                  because DDL statements and advisory locks need a real session.
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/hubdb"
    direct_url: str = ""  # falls back to database_url when not set

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Application
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Hub identity
    hub_name: str = "Hub"
    api_prefix: str = "/api/v1"

    # LLM providers — waterfall order: Anthropic → OpenAI → Gemini
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Finance MCP data providers (all optional — fallback logic applies)
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    newsapi_key: str = ""

    # Plaid (brokerage account linking)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"          # "sandbox" | "development" | "production"

    # Stripe (subscription billing)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""           # recurring Price ID for the Pro plan


settings = Settings()
