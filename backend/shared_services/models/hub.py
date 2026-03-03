"""
Hub-level SQLAlchemy models.

These are shared resources visible to all spokes: organizations, users,
and an example embedding model demonstrating pgvector usage.
"""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "hub"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    # pgvector: semantic embedding of the organization description (e.g. 1536-dim OpenAI)
    description_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "hub"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hub.organizations.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="users"
    )


class KnowledgeBase(Base):
    """
    Venture-scoped knowledge articles with pgvector embeddings.

    Row-Level Security is enforced at the PostgreSQL level via the
    'venture_isolation' policy on this table.  The app sets
    app.current_venture_id at the start of every transaction (see
    core/database.py) so Postgres automatically filters rows.

    The ORM model mirrors the schema created by migration 001.
    """

    __tablename__ = "knowledge_base"
    __table_args__ = {"schema": "hub"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    venture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 1 536-dimensional OpenAI-compatible embedding; use None when not yet computed.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    # Arbitrary structured metadata (tags, source URL, author, etc.)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
