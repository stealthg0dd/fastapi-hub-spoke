#!/usr/bin/env python3
"""
Connectivity smoke test using explicit asyncpg arguments.

Usage:
    cd fastapi-hub-spoke
    python3 db_smoke_test.py
"""
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def test_explicit():
    credentials = {
        "host": "db.gpczchjipalfgkfqamcu.supabase.co",
        "port": 5432,
        "user": "postgres",
        "password": "OP2K6TUJ8zeSp4mQ",
        "database": "postgres",
        "ssl": "require",
        "statement_cache_size": 0,
    }

    print(f"Testing connection to {credentials['host']}:{credentials['port']} ...")
    try:
        conn = await asyncpg.connect(**credentials, timeout=15)
        version = await conn.fetchval("SELECT version();")
        db = await conn.fetchval("SELECT current_database();")
        usr = await conn.fetchval("SELECT current_user;")
        ext = await conn.fetchval(
            "SELECT extname FROM pg_extension WHERE extname='vector'"
        )
        await conn.close()
        print(f"  SUCCESS  db={db}  user={usr}")
        print(f"  {version[:72]}")
        print(f"  pgvector: {'enabled' if ext else 'NOT installed — run: CREATE EXTENSION vector'}")
        return True
    except Exception as e:
        print(f"  FAIL: {type(e).__name__} — {e}")
        return False


if __name__ == "__main__":
    ok = asyncio.run(test_explicit())
    raise SystemExit(0 if ok else 1)
