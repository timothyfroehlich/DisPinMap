"""Set is_active default to True on ChannelConfig

Revision ID: ea2a9d9df2f0
Revises: 5c8e4212f5ed
Create Date: 2025-06-30 06:43:43.298078

"""

from typing import Sequence, Union

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "ea2a9d9df2f0"
down_revision: Union[str, Sequence[str], None] = "5c8e4212f5ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "channel_configs",
        "is_active",
        server_default="true",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "channel_configs",
        "is_active",
        server_default="false",
    )
