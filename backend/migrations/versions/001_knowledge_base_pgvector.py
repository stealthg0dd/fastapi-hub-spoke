"""Create hub.knowledge_base table with pgvector and Row-Level Security

This is the foundational migration for multi-tenant knowledge storage.

What it does
------------
1. Ensures the pgvector extension and hub schema exist (idempotent).
2. Creates hub.knowledge_base with:
   - venture_id  — tenant discriminator column, used by RLS.
   - embedding   — 1 536-dim vector column (OpenAI-compatible).
   - metadata    — JSONB for arbitrary structured data (tags, source, etc.)
3. Creates a B-tree index on venture_id for fast tenant-scoped reads.
4. Creates an IVFFlat index on the embedding column for approximate
   nearest-neighbour vector search (cosine distance).
5. Enables Row-Level Security and forces it even for the table owner.
6. Creates a single RLS policy (venture_isolation) that uses
   current_setting('app.current_venture_id', true) — the session
   parameter set by the application's get_db() dependency — to
   restrict SELECT / INSERT / UPDATE / DELETE to the active venture.

Row-Level Security notes
------------------------
* The second arg to current_setting(..., true) means "return NULL instead
  of raising an error if the setting is not defined".  This allows admin
  scripts running outside the app to bypass the policy gracefully by not
  setting the parameter.
* FORCE ROW LEVEL SECURITY applies the policy even to the table owner
  (usually the postgres superuser role used by migrations).  Remove it if
  you prefer a separate app role that is not a superuser.
* To bypass RLS for a migration-only session:
      SET app.current_venture_id = '';   -- policy evaluates to false → no rows
  Or run as a BYPASSRLS role.

Revision ID: 001_knowledge_base_pgvector
Revises:
Create Date: 2026-03-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001_knowledge_base_pgvector"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Prerequisites (idempotent — safe to run on an existing database)
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS hub")

    # ------------------------------------------------------------------
    # Create the table
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_base",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Tenant discriminator — every row belongs to exactly one venture.
        sa.Column("venture_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        # 1 536-dim embedding (OpenAI text-embedding-ada-002 / text-embedding-3-small).
        # NULL is allowed so rows can be inserted before embeddings are computed.
        sa.Column("embedding", Vector(1536), nullable=True),
        # Arbitrary structured metadata: tags, source URL, author, chunk index, etc.
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="hub",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    # B-tree index: fast equality lookups on venture_id (used by every query
    # after the RLS policy is applied).
    op.create_index(
        "ix_kb_venture_id",
        "knowledge_base",
        ["venture_id"],
        schema="hub",
    )

    # IVFFlat index for approximate nearest-neighbour vector search.
    # lists=100 is a reasonable default for up to ~1 M rows per venture;
    # increase for larger datasets.  Requires at least `lists` rows before
    # the index is useful — for small datasets a sequential scan is fine.
    op.execute(
        """
        CREATE INDEX ix_kb_embedding_ivfflat
        ON hub.knowledge_base
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # ------------------------------------------------------------------
    # Row-Level Security
    # ------------------------------------------------------------------

    # Enable RLS on the table.
    op.execute("ALTER TABLE hub.knowledge_base ENABLE ROW LEVEL SECURITY")

    # Force RLS even for the table owner / superuser so no role can
    # accidentally read cross-tenant data.
    op.execute("ALTER TABLE hub.knowledge_base FORCE ROW LEVEL SECURITY")

    # Single policy covering all statement types (SELECT, INSERT, UPDATE, DELETE).
    #
    # USING      — applied to existing rows (SELECT / UPDATE / DELETE).
    # WITH CHECK — applied to new/modified rows (INSERT / UPDATE).
    #
    # current_setting('app.current_venture_id', true):
    #   The app sets this via "SET LOCAL app.current_venture_id = '<id>'"
    #   inside each transaction (see shared_services/core/database.py).
    #   Returning NULL (true = missing_ok) means unset sessions see no rows.
    op.execute(
        """
        CREATE POLICY venture_isolation
        ON hub.knowledge_base
        AS PERMISSIVE
        FOR ALL
        USING (
            venture_id::text = current_setting('app.current_venture_id', true)
        )
        WITH CHECK (
            venture_id::text = current_setting('app.current_venture_id', true)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS venture_isolation ON hub.knowledge_base"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_kb_embedding_ivfflat"
    )
    op.drop_index("ix_kb_venture_id", table_name="knowledge_base", schema="hub")
    op.drop_table("knowledge_base", schema="hub")
