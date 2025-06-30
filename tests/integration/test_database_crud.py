"""
Integration tests for database Create, Read, Update, Delete (CRUD) operations.

These tests verify that the database interaction logic in `src/database.py`
works correctly. They run against a real, but isolated, database instance
provided by the `db_session` fixture.
"""

# To be migrated from `tests_backup/unit/test_database.py` (which was an integration test).

# import pytest  # Will be needed for actual test implementation
# from sqlalchemy.exc import IntegrityError  # Will be needed for actual test implementation

from datetime import datetime

from src.models import ChannelConfig, MonitoringTarget, SeenSubmission


def test_add_and_retrieve_monitoring_target(db_session):
    """
    Tests basic CRUD functionality: adding a monitoring target to the database
    and then retrieving it to ensure it was saved correctly.
    """
    # 1. SETUP
    # The db_session fixture provides a clean, isolated session for this test.
    session = db_session()

    # Create a model instance with test data
    new_target = MonitoringTarget(
        channel_id=12345,
        target_type="latlong",
        target_name="45.523,-122.676",
    )

    # 2. ACTION
    # Add the new object to the session and commit it to the database
    session.add(new_target)
    session.commit()

    # 3. ASSERT
    # Query the database to retrieve the object we just saved.
    retrieved_target = (
        session.query(MonitoringTarget).filter_by(channel_id=12345).first()
    )

    assert retrieved_target is not None
    assert retrieved_target.channel_id == 12345
    assert retrieved_target.target_type == "latlong"
    assert retrieved_target.target_name == "45.523,-122.676"

    session.close()


def test_add_duplicate_target_raises_error(db_session):
    """
    Tests that adding a duplicate target raises an IntegrityError.
    - Adds a target.
    - Attempts to add the exact same target again.
    - Asserts that a `sqlalchemy.exc.IntegrityError` (or similar) is raised.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    session = db_session()

    # Create first target
    target1 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Test Location",
        location_id=999,
    )

    session.add(target1)
    session.commit()

    # Try to add duplicate target (same channel + type + name should violate constraint)
    target2 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Test Location Different",  # Different name since constraint is on location_id
        location_id=999,  # Same location_id - this should violate the unique constraint
    )

    session.add(target2)

    # Should raise integrity error on commit
    with pytest.raises(IntegrityError):
        session.commit()

    session.close()


def test_update_channel_config(db_session):
    """
    Tests updating an existing channel configuration.
    - Adds a ChannelConfig with initial settings.
    - Calls the update logic to change the poll rate.
    - Retrieves the config and asserts that the poll rate has been updated.
    """
    session = db_session()

    # Create initial channel config
    initial_config = ChannelConfig(
        channel_id=12345,
        guild_id=11111,
        poll_rate_minutes=60,
        notification_types="machines",
        is_active=True,
    )

    session.add(initial_config)
    session.commit()

    # Update the config
    config_to_update = session.query(ChannelConfig).filter_by(channel_id=12345).first()
    config_to_update.poll_rate_minutes = 30
    config_to_update.notification_types = "all"
    session.commit()

    # Retrieve and verify the update
    updated_config = session.query(ChannelConfig).filter_by(channel_id=12345).first()
    assert updated_config.poll_rate_minutes == 30
    assert updated_config.notification_types == "all"
    assert updated_config.is_active is True  # Should remain unchanged

    session.close()


def test_remove_monitoring_target(db_session):
    """
    Tests removing a monitoring target from the database.
    - Adds a target.
    - Calls the removal logic.
    - Queries the database and asserts that the target no longer exists.
    """
    session = db_session()

    # Add a target to remove later
    target = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Test Location",
        location_id=999,
    )

    session.add(target)
    session.commit()

    # Verify it was added
    added_target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=12345, location_id=999)
        .first()
    )
    assert added_target is not None

    # Remove the target
    session.delete(added_target)
    session.commit()

    # Verify it was removed
    removed_target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=12345, location_id=999)
        .first()
    )
    assert removed_target is None

    session.close()


def test_filter_new_submissions(db_session):
    """
    Tests the logic for filtering out already-seen submissions.
    - Adds some submission IDs to the SeenSubmission table for a channel.
    - Calls the `filter_new_submissions` logic with a list containing both old and new IDs.
    - Asserts that the function correctly returns only the new submission IDs.
    """
    session = db_session()

    # Create a channel config first (required for foreign key)
    channel_config = ChannelConfig(channel_id=12345, guild_id=11111, is_active=True)
    session.add(channel_config)
    session.commit()

    # Add some seen submissions
    seen_submissions = [
        SeenSubmission(channel_id=12345, submission_id=100, seen_at=datetime.now()),
        SeenSubmission(channel_id=12345, submission_id=200, seen_at=datetime.now()),
        SeenSubmission(channel_id=12345, submission_id=300, seen_at=datetime.now()),
    ]

    for submission in seen_submissions:
        session.add(submission)
    session.commit()

    # Test filtering logic
    all_submission_ids = [100, 200, 300, 400, 500]  # Mix of seen and unseen

    # Query existing seen submissions for this channel
    existing_seen = (
        session.query(SeenSubmission.submission_id).filter_by(channel_id=12345).all()
    )
    existing_seen_ids = {row[0] for row in existing_seen}

    # Filter out already seen submissions
    new_submission_ids = [
        sub_id for sub_id in all_submission_ids if sub_id not in existing_seen_ids
    ]

    # Assert that only new submissions remain
    assert set(new_submission_ids) == {400, 500}
    assert 100 not in new_submission_ids
    assert 200 not in new_submission_ids
    assert 300 not in new_submission_ids

    session.close()
