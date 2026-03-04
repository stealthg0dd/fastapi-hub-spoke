from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from core.config import settings
from core.context import current_venture_id


def _asyncpg_url(url: str) -> str:
    """Ensure the URL uses the postgresql+asyncpg:// scheme.

    Railway (and many PaaS) inject DATABASE_URL as ``postgres://`` or
    ``postgresql://``.  SQLAlchemy's async engine requires the
    ``+asyncpg`` driver suffix; without it the engine silently uses
    the sync psycopg2 adapter and raises OSError on connection.
    """
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url  # already has +asyncpg or is a non-standard scheme


# NullPool: delegate all connection management to Supabase's PgBouncer
# (Transaction Pooler on port 6543). SQLAlchemy must not hold open connections
# between requests because PgBouncer recycles them on transaction end.
#
# statement_cache_size / prepared_statement_cache_size = 0: Transaction Pooler
# does not support PostgreSQL prepared statements — they are session-scoped
# and cannot survive connection recycling. Disabling prevents
# "prepared statement does not exist" errors under high concurrency.
engine = create_async_engine(
    _asyncpg_url(settings.database_url),
    echo=settings.debug,
    poolclass=NullPool,
    connect_args={
        "ssl": "require",           # Force SSL for Supabase
        "statement_cache_size": 0,  # Disable cache for Transaction Mode
    },
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session scoped to the current
    Venture ID via PostgreSQL Row-Level Security.

    The session is wrapped in an explicit transaction so that SET LOCAL takes
    effect immediately.  SET LOCAL is transaction-scoped: it is automatically
    rolled back when the transaction ends, which means we never leak one
    tenant's context to the next request even under connection-pool reuse.
    """
    async with async_session_maker() as session:
        async with session.begin():
            venture_id = current_venture_id.get()
            if venture_id:
                # set_config(setting, value, is_local=true) is the function form
                # of SET LOCAL.  It accepts a plain text argument so no casting
                # is required, and works correctly through PgBouncer because the
                # parameter is set within the current transaction scope.
                await session.execute(
                    text("SELECT set_config('app.current_venture_id', :vid, true)"),
                    {"vid": str(venture_id)},
                )
            yield session


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for admin/cross-venture queries.

    No RLS context is set — all ventures are visible.  Only use this for
    endpoints protected by the ``hub.admin_`` key bypass in VentureIDMiddleware.
    """
    async with async_session_maker() as session:
        async with session.begin():
            yield session


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
