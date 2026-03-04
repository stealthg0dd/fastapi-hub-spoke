from collections.abc import AsyncGenerator
import logging
import ssl
import certifi
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from core.config import settings
from core.context import current_venture_id

logger = logging.getLogger(__name__)

def _asyncpg_url(url: str) -> str:
    """Fixes the scheme for async compatibility."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url

def _make_ssl_context() -> ssl.SSLContext:
    """SSL context backed by certifi — works in Nix containers where system CAs are absent."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    return ctx

# Log the DB host at startup to aid Railway debugging (password masked)
_db_url = _asyncpg_url(settings.database_url)
try:
    from urllib.parse import urlparse
    _parsed = urlparse(_db_url)
    logger.info("DB target: %s@%s:%s/%s", _parsed.username, _parsed.hostname, _parsed.port, _parsed.path.lstrip("/"))
except Exception:
    pass

# Engine configuration optimized for Supabase PgBouncer (Port 6543)
engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    poolclass=NullPool,
    connect_args={
        "ssl": _make_ssl_context(),
        "statement_cache_size": 0,  # Required for Transaction Mode
    },
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session with Row-Level Security context."""
    async with async_session_maker() as session:
        async with session.begin():
            venture_id = current_venture_id.get()
            if venture_id:
                await session.execute(
                    text("SELECT set_config('app.current_venture_id', :vid, true)"),
                    {"vid": str(venture_id)},
                )
            yield session

async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session without RLS filters for admin tasks."""
    async with async_session_maker() as session:
        async with session.begin():
            yield session

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(3),
    retry=retry_if_exception_type((SQLAlchemyError, OSError)),
    before_sleep=lambda retry_state: logger.warning(
        f"DB Connection failed. Retrying in 3s... (Attempt {retry_state.attempt_number}/5)"
    )
)
async def create_tables() -> None:
    """Resilient table creation with retry logic for cloud networking stability."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database handshake successful: Tables verified/created.")