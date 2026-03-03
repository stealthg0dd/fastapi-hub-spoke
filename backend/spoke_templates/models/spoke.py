"""
Spoke-level SQLAlchemy models (template).

Replace / extend these with domain models specific to each startup.
All spoke tables live under the 'spokes' schema by default, keeping them
isolated from hub tables while sharing the same Postgres instance.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SpokeResource(Base):
    """
    Generic placeholder model — rename and reshape this for your startup's
    primary domain object (e.g. Product, Listing, Project, etc.).
    """

    __tablename__ = "resources"
    __table_args__ = {"schema": "spokes"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Tenant / organization reference (FK lives in hub schema)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
