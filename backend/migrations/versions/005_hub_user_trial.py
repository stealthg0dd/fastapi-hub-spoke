"""Add trial_ends_at and is_premium to hub.users.

Revision ID: 005
Revises: 004
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"),
        schema="hub",
    )
    op.add_column(
        "users",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        schema="hub",
    )
    # Back-fill existing users: trial started at created_at, ends 7 days later
    op.execute("""
        UPDATE hub.users
        SET trial_ends_at = created_at + INTERVAL '7 days'
        WHERE trial_ends_at IS NULL
    """)


def downgrade() -> None:
    op.drop_column("users", "trial_ends_at", schema="hub")
    op.drop_column("users", "is_premium", schema="hub")
