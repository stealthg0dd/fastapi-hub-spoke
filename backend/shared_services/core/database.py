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
    1. Standardize scheme for async compatibility.
    2. Attempt IPv4 resolution for performance, with a graceful fallback.
    """
    if not url:
        return ""
    
    # Standardize scheme
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif "postgresql+asyncpg://" not in url:
        # Fallback for URLs already missing the driver part
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Attempt IPv4 Resolution
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname:
            # Resolve hostname to IP
            ipv4_address = socket.gethostbyname(hostname)
            # Reconstruct URL with IP to bypass potential DNS/IPv6 issues
            new_netloc = parsed.netloc.replace(hostname, ipv4_address)
            url = url.replace(parsed.netloc, new_netloc)
            logger.info("Database host resolved: %s -> %s", hostname, ipv4_address)
    except Exception as e:
        # DO NOT RAISE: Use original hostname if resolution fails
        logger.warning("DNS resolution info (using hostname instead): %s", e)
    
    return url

def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE 
    return ctx

_db_url = _prepare_db_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    poolclass=NullPool,
    connect_args={
        "ssl": _make_ssl_context(),
        "command_timeout": 60,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    },
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- SESSION GENERATORS ---

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        venture_id = current_venture_id.get()
        if venture_id:
            try:
                await session.execute(
                    text("SELECT set_config('app.current_venture_id', :vid, true)"),
                    {"vid": str(venture_id)},
                )
            except Exception as e:
                logger.error(f"Failed to set RLS context: {e}")
        else:
            logger.warning("get_db called without venture_id context.")
        yield session

async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# --- LIFECYCLE HELPERS ---

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(3),
    retry=retry_if_exception_type((SQLAlchemyError, OSError, ConnectionError)),
)
async def create_tables() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database handshake successful.")
    except Exception as e:
        logger.error(f"❌ Critical Database Error: {e}")
        raise e