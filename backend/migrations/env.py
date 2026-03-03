"""
Alembic environment for fastapi-hub-spoke.

Supports async SQLAlchemy (asyncpg driver).  The database URL is read from
core.config.settings so it honours environment variables / .env files just
like the running application does.

Usage
-----
    cd /path/to/fastapi-hub-spoke
    alembic upgrade head
    alembic downgrade -1
    alembic revision --autogenerate -m "describe change"
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

# ---------------------------------------------------------------------------
# Make shared_services importable (alembic.ini sets prepend_sys_path, but
# we guard here as well for direct script execution).
# ---------------------------------------------------------------------------
_shared = Path(__file__).parent.parent / "shared_services"
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

# Import settings before models so the DB URL is available.
from core.config import settings  # noqa: E402
from core.database import Base  # noqa: E402

# Import all model modules so their tables are registered with Base.metadata.
import models.hub  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Standard Alembic boilerplate
# ---------------------------------------------------------------------------
config = context.config

# Override the URL from the application's settings (reads .env / env vars).
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout without a live DB connection.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas so hub.* tables are auto-detected.
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connect to the live database and apply migrations.
# ---------------------------------------------------------------------------
def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    # Migrations use the DIRECT_URL (port 5432 — real PostgreSQL session) rather
    # than the Transaction Pooler (port 6543) because:
    #   - DDL statements (CREATE TABLE, ALTER TABLE) must run in the same
    #     session that holds Alembic's advisory lock.
    #   - The Transaction Pooler (PgBouncer transaction mode) can recycle the
    #     underlying connection mid-migration, breaking the lock and causing
    #     partial migrations.
    # Fall back to DATABASE_URL if DIRECT_URL is not configured.
    migration_url = settings.direct_url or settings.database_url
    connectable = create_async_engine(
        migration_url,
        poolclass=pool.NullPool,
        connect_args={
            "ssl": "require",
            "statement_cache_size": 0,
        },
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
