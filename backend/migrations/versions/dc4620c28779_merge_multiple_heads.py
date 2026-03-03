"""merge multiple heads

Revision ID: dc4620c28779
Revises: 004_neufin_portfolio_billing, 005
Create Date: 2026-03-03 16:49:52.212940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc4620c28779'
down_revision: Union[str, None] = ('004_neufin_portfolio_billing', '005')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
