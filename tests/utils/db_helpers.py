"""
Database helper functions for testing.

This module provides convenience functions to interact with the test
database, simplifying common setup and assertion steps in tests.
"""

# Import your SQLAlchemy models and session object
# from src.database import Database, Target
# from sqlalchemy.orm import Session


async def setup_monitoring_target(
    db_session, user_id: int, location_id: int, location_name: str
):
    """
    A helper to create and save a new monitoring target to the database.

    Args:
        db_session: The SQLAlchemy session fixture.
        user_id: The Discord user ID to associate with the target.
        location_id: The PinballMap location ID.
        location_name: The human-readable name of the location.

    Returns:
        The newly created Target object.
    """
    from src.models import ChannelConfig, MonitoringTarget

    session = db_session()

    # Create channel config if it doesn't exist
    channel_config = session.query(ChannelConfig).filter_by(channel_id=67890).first()
    if not channel_config:
        channel_config = ChannelConfig(
            channel_id=67890,  # Default mock channel ID
            guild_id=12345,  # Default mock guild ID
            is_active=True,
        )
        session.add(channel_config)
        session.commit()

    # Create monitoring target
    new_target = MonitoringTarget(
        channel_id=67890,  # Default mock channel ID
        target_type="location",
        target_name=location_name,
        location_id=location_id,
    )
    session.add(new_target)
    session.commit()
    session.refresh(new_target)

    return new_target


async def get_target_by_location_id(db_session, location_id: int):
    """
    Retrieves a target from the database by its location ID.

    Returns:
        The Target object or None if not found.
    """
    from src.models import MonitoringTarget

    session = db_session()
    return session.query(MonitoringTarget).filter_by(location_id=location_id).first()
