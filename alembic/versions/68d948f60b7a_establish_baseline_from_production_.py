"""Establish baseline from production schema

Revision ID: 68d948f60b7a
Revises:
Create Date: 2025-06-27 21:20:45.836612

"""

from typing import Sequence, Union

# from alembic import op
# import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "68d948f60b7a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
