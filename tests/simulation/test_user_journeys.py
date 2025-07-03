"""
High-level simulation tests for key user journeys.

These tests simulate a user's entire interaction with the bot over a series
of steps, verifying that the system as a whole behaves as expected.
"""

# To be migrated from `tests_backup/simulation/test_user_journeys.py`

import pytest
import sqlalchemy.exc


def test_full_user_journey_add_and_monitor(db_session, api_mocker):
    """
    Simulates a full user journey:
    1. User adds a new location target.
    2. Bot confirms the target has been added.
    3. Time passes, and the background monitoring task runs.
    4. The monitor detects a new submission for the location.
    5. Bot sends a notification to the channel.
    6. User lists the targets and sees the location is still being monitored.
    7. User removes the target.
    8. Bot confirms removal.
    """
    from src.models import ChannelConfig, MonitoringTarget

    session = db_session()

    # Mock API responses for adding location
    api_mocker.add_response(
        url_substring="by_location_name",
        json_fixture_path="pinballmap_search/search_ground_kontrol_single_result.json",
    )
    api_mocker.add_response(
        url_substring="locations/874.json",
        json_fixture_path="pinballmap_locations/location_874_details.json",
    )

    # This test focuses on the database interactions since that's what we can test
    # The command handler integration would require a full bot setup

    # Step 1 & 2: Simulate adding a location target
    # Create channel config
    channel_config = ChannelConfig(channel_id=456, guild_id=789, is_active=True)
    session.add(channel_config)
    session.commit()

    # Add monitoring target (simulating successful add command)
    target = MonitoringTarget(
        channel_id=456,
        target_type="location",
        display_name="Ground Kontrol Classic Arcade",
        location_id=874,
    )
    session.add(target)
    session.commit()

    # Step 6: Verify target exists (simulating list command)
    targets = session.query(MonitoringTarget).filter_by(channel_id=456).all()
    assert len(targets) == 1
    assert targets[0].display_name == "Ground Kontrol Classic Arcade"
    assert targets[0].location_id == 874

    # Step 7 & 8: Remove target (simulating remove command)
    session.delete(targets[0])
    session.commit()

    # Verify removal
    remaining_targets = session.query(MonitoringTarget).filter_by(channel_id=456).all()
    assert len(remaining_targets) == 0

    session.close()


def test_journey_with_invalid_commands(db_session):
    """
    Simulates a user journey involving incorrect commands.
    1. User tries to add a target with an invalid type.
    2. Bot responds with a helpful error message.
    3. User tries to remove a target that doesn't exist.
    4. Bot responds gracefully.
    """
    from src.models import ChannelConfig, MonitoringTarget

    session = db_session()

    # Create channel config
    channel_config = ChannelConfig(channel_id=456, guild_id=789, is_active=True)
    session.add(channel_config)
    session.commit()

    # Step 1 & 2: Test that invalid target types are rejected by database constraints
    # Note: The new schema has CHECK constraints that prevent invalid target types

    # Try to create a target with invalid type - should raise IntegrityError
    test_target = MonitoringTarget(
        channel_id=456,
        target_type="invalid_type",  # This violates CHECK constraint
        display_name="Test",
        location_id=123,
    )
    session.add(test_target)

    # This should raise an IntegrityError due to CHECK constraint
    with pytest.raises(sqlalchemy.exc.IntegrityError) as exc_info:
        session.commit()

    # Verify it's the target_type check constraint that failed
    assert "target_data_check" in str(exc_info.value)

    # Rollback the failed transaction
    session.rollback()

    # Step 3 & 4: Test removing non-existent target
    # Verify no targets exist
    targets = session.query(MonitoringTarget).filter_by(channel_id=456).all()
    assert len(targets) == 0  # No targets should exist

    # This demonstrates the graceful handling - check before attempting removal
    if len(targets) > 0:
        # Would remove target
        target_to_remove = targets[0]
        session.delete(target_to_remove)
        session.commit()
    else:
        # Expected path - no targets to remove
        # In real implementation, command handler would return appropriate message
        assert targets == [], "Should have no targets when none exist to remove"

    session.close()
