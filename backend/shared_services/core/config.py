from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at <service_root>/core/config.py
# Walk up from the service root to find a .env file.
# On Railway, there is no .env — env vars are injected as OS env vars,
# so _locate_env_file() returns None and no file loading is attempted.
_SERVICE_ROOT = Path(__file__).resolve().parent.parent  # core/ → service_root/


def _locate_env_file(start: Path) -> Optional[str]:
    """Walk up the directory tree to find the nearest .env file."""
    current = start
    for _ in range(5):
        candidate = current / ".env"
        if candidate.is_file():
            return str(candidate)
        parent = current.parent
        if parent == current:  # reached filesystem root
            break
        current = parent
    return None


_ENV_FILE = _locate_env_file(_SERVICE_ROOT)


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,  # None on Railway (no crash); path to .env locally
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

    # Frontend URL — used by stripe_service.py to build success/cancel URLs.
    # Dev default:  http://localhost:3001/portal
    # Production:   set FRONTEND_URL=https://neufin.vercel.app/portal in Railway
    frontend_url: str = "http://localhost:3001/portal"

    # CORS — extra allowed origins beyond the static list in main.py.
    # Set as a comma-separated string in Railway's environment variables:
    #   ALLOWED_ORIGINS=https://neufin-preview-abc.vercel.app,https://staging.neufin.ai
    allowed_origins: str = ""


settings = Settings()
