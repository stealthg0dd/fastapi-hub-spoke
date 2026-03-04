import logging
import ssl
import certifi
import socket
from collections.abc import AsyncGenerator
from uuid import uuid4
from urllib.parse import urlparse

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

def _prepare_db_url(url: str) -> str:
    """
    1. Fixes the scheme for async compatibility.
    2. Forces IPv4 resolution to prevent [Errno 101] Network is unreachable.
    """
    if not url:
        return ""
    
    # Standardize scheme
    for prefix in ["postgres://", "postgresql://"]:
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    # Force IPv4 Resolution
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname:
            # Resolves to IPv4 to bypass Railway IPv6 routing issues
            ipv4_address = socket.gethostbyname(hostname)
            # Reconstruct netloc with IP but keep port/user/pass
            new_netloc = parsed.netloc.replace(hostname, ipv4_address)
            url = url.replace(parsed.netloc, new_netloc)
            logger.info("Resolving DB Host %s to IPv4 %s", hostname, ipv4_address)
    except Exception as e:
        logger.warning("IPv4 resolution failed, falling back to hostname: %s", e)
    
    return url

def _make_ssl_context() -> ssl.SSLContext:
    """
    SSL Fix: Disables verification to stop SSLCertVerificationError.
    Essential for Railway -> Supabase cross-cloud handshakes.
    """
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE 
    return ctx

# Prepare the final URL
_db_url = _prepare_db_url(settings.database_url)

# Engine configuration for Supabase Transaction Mode (Port 6543)
engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    poolclass=NullPool, # Critical for PgBouncer/Supabase
    connect_args={
        "ssl": _make_ssl_context(),
        "command_timeout": 60,
        # Prevents 'prepared statement already exists' errors in poolers
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    },
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- SESSION GENERATORS ---

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session with Row-Level Security context."""
    async with async_session_maker() as session:
        venture_id = current_venture_id.get()
        if venture_id:
            await session.execute(
                text("SELECT set_config('app.current_venture_id', :vid, true)"),
                {"vid": str(venture_id)},
            )
        yield session

async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session without RLS filters."""
    async with async_session_maker() as session:
        yield session

# --- LIFECYCLE HELPERS ---

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(3),
    retry=retry_if_exception_type((SQLAlchemyError, OSError, ConnectionError)),
    before_sleep=lambda retry_state: logger.warning(
        f"DB Connection failed. Retrying in 3s... (Attempt {retry_state.attempt_number}/5)"
    )
)
async def create_tables() -> None:
    """Resilient table creation with explicit ping."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database handshake successful: Tables verified/created.")
    except Exception as e:
        logger.error(f"❌ Critical Database Error: {e}")
        raise e