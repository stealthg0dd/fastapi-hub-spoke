"""Create hub.organizations and hub.users

What it does
------------
1. Ensures the hub schema exists (idempotent — 001 may have created it).
2. Creates hub.organizations — one row per venture, stores the venture's
   name, slug, description, and an optional pgvector description_embedding.
3. Creates hub.users — platform users scoped to an organization.
4. No RLS on these tables: the application uses the hub schema for
   cross-cutting identity; RLS on spoke tables provides the data isolation.

Revision ID: 002_hub_core_tables
Revises:     001_knowledge_base_pgvector
Create Date: 2026-03-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# ── Alembic metadata ──────────────────────────────────────────────────────────
revision: str = "002_hub_core_tables"
down_revision: Union[str, None] = "001_knowledge_base_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # hub schema created by 001 — CREATE IF NOT EXISTS is safe here too
    op.execute("CREATE SCHEMA IF NOT EXISTS hub")

    # ── hub.organizations ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS hub.organizations (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL UNIQUE,
            slug        VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_hub_organizations_slug
            ON hub.organizations (slug)
    """)

    # ── hub.users ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS hub.users (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email            VARCHAR(320) NOT NULL UNIQUE,
            hashed_password  VARCHAR(255) NOT NULL,
            full_name        VARCHAR(255),
            is_active        BOOLEAN NOT NULL DEFAULT TRUE,
            organization_id  UUID REFERENCES hub.organizations(id) ON DELETE SET NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_hub_users_email
            ON hub.users (email)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_hub_users_org
            ON hub.users (organization_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hub.users")
    op.execute("DROP TABLE IF EXISTS hub.organizations")
