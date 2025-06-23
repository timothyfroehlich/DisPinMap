"""
Migration script to add notification_types column to ChannelConfig and MonitoringTarget tables
"""

from sqlalchemy import create_engine, Column, String
from sqlalchemy.sql import text
import os
import logging

logger = logging.getLogger(__name__)


def run_migration(db_path: str = "pinball_bot.db"):
    """Run the migration to add notification_types column"""
    # Create engine
    engine = create_engine(f"sqlite:///{db_path}")

    # Add notification_types to ChannelConfig
    with engine.connect() as conn:
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE channel_configs
                ADD COLUMN notification_types VARCHAR DEFAULT 'machines'
            """
                )
            )
            logger.info("Added notification_types column to channel_configs")
        except Exception as e:
            logger.warning(f"Could not add notification_types to channel_configs: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE monitoring_targets
                ADD COLUMN notification_types VARCHAR DEFAULT 'machines'
            """
                )
            )
            logger.info("Added notification_types column to monitoring_targets")
        except Exception as e:
            logger.warning(
                f"Could not add notification_types to monitoring_targets: {e}"
            )

        conn.commit()


if __name__ == "__main__":
    run_migration()
