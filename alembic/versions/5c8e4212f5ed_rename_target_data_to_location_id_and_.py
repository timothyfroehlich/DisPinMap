"""Rename target_data to location_id and update constraint

Revision ID: 5c8e4212f5ed
Revises: 68d948f60b7a
Create Date: 2025-06-27 21:21:20.796111

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "5c8e4212f5ed"
down_revision: Union[str, Sequence[str], None] = "68d948f60b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("monitoring_targets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("location_id", sa.Integer(), nullable=True))

    # Data migration: Copy from target_data to location_id
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
        UPDATE monitoring_targets
        SET location_id = CAST(target_data AS INTEGER)
        WHERE target_type = 'location' AND target_data IS NOT NULL
    """
        )
    )

    with op.batch_alter_table("monitoring_targets", schema=None) as batch_op:
        batch_op.drop_constraint("unique_channel_target", type_="unique")
        batch_op.create_unique_constraint(
            "unique_channel_location", ["channel_id", "target_type", "location_id"]
        )
        batch_op.drop_column("target_data")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("monitoring_targets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("target_data", sa.VARCHAR(), nullable=True))

    # Data migration: Copy from location_id back to target_data
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
        UPDATE monitoring_targets
        SET target_data = CAST(location_id AS VARCHAR)
        WHERE target_type = 'location' AND location_id IS NOT NULL
    """
        )
    )

    with op.batch_alter_table("monitoring_targets", schema=None) as batch_op:
        batch_op.drop_constraint("unique_channel_location", type_="unique")
        batch_op.create_unique_constraint(
            "unique_channel_target", ["channel_id", "target_type", "target_name"]
        )
        batch_op.drop_column("location_id")
    # ### end Alembic commands ###
