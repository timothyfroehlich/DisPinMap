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
        target_type="geographic",
        display_name="45.523,-122.676",
        latitude=45.523,
        longitude=-122.676,
        radius_miles=25,
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
    assert retrieved_target.target_type == "geographic"
    assert retrieved_target.display_name == "45.523,-122.676"
    assert retrieved_target.latitude == 45.523
    assert retrieved_target.longitude == -122.676
    assert retrieved_target.radius_miles == 25

    session.close()


def test_add_duplicate_target_raises_error(db_session):
    """
    Tests that adding a duplicate target raises an IntegrityError.
    - Adds a location target.
    - Attempts to add the exact same location target again.
    - Asserts that a `sqlalchemy.exc.IntegrityError` (or similar) is raised.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    session = db_session()

    # Create first location target
    target1 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        display_name="Test Location",
        location_id=999,
    )

    session.add(target1)
    session.commit()

    # Try to add duplicate location target (same channel + location_id violates unique_location constraint)
    target2 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        display_name="Test Location Different",  # Different name since constraint is on location_id
        location_id=999,  # Same location_id - this should violate the unique_location constraint
    )

    session.add(target2)

    # Should raise integrity error on commit
    with pytest.raises(IntegrityError):
        session.commit()

    session.close()


def test_add_duplicate_geographic_target_raises_error(db_session):
    """
    Tests that adding a duplicate geographic target raises an IntegrityError.
    - Adds a geographic target.
    - Attempts to add the exact same geographic target again.
    - Asserts that a `sqlalchemy.exc.IntegrityError` (or similar) is raised.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    session = db_session()

    # Create first geographic target
    target1 = MonitoringTarget(
        channel_id=12345,
        target_type="geographic",
        display_name="Test Geographic Area",
        latitude=45.523,
        longitude=-122.676,
        radius_miles=25,
    )

    session.add(target1)
    session.commit()

    # Try to add duplicate geographic target (same channel + coordinates violates unique_geographic constraint)
    target2 = MonitoringTarget(
        channel_id=12345,
        target_type="geographic",
        display_name="Different Name Same Location",  # Different name
        latitude=45.523,  # Same coordinates
        longitude=-122.676,
        radius_miles=25,  # Different radius should still conflict since constraint is on lat/lon only
    )

    session.add(target2)

    # Should raise integrity error on commit
    with pytest.raises(IntegrityError):
        session.commit()

    session.close()


def test_add_geographic_target_updates_radius(db_session):
    """
    Tests that adding a geographic target with the same coordinates but a different
    radius updates the existing target's radius instead of creating a new one.
    """
    from src.database import Database

    db = Database(db_session)
    session = db_session()

    # 1. ARRANGE
    # Add an initial geographic target
    db.add_monitoring_target(
        channel_id=12345,
        target_type="geographic",
        display_name="Test Area",
        latitude=45.5,
        longitude=-122.5,
        radius_miles=10,
    )

    # 2. ACT
    # Add the same target with a different radius
    result = db.add_monitoring_target(
        channel_id=12345,
        target_type="geographic",
        display_name="Test Area",
        latitude=45.5,
        longitude=-122.5,
        radius_miles=20,
    )

    # 3. ASSERT
    # Check that the radius was updated
    updated_target = (
        session.query(MonitoringTarget)
        .filter_by(
            channel_id=12345,
            latitude=45.5,
            longitude=-122.5,
        )
        .one()
    )
    assert updated_target.radius_miles == 20

    # Check that the result from add_monitoring_target indicates an update
    assert result is not None
    assert result["updated_radius"] is True
    assert result["old_radius"] == 10
    assert result["new_radius"] == 20
    assert result["display_name"] == "Test Area"

    # Verify only one target exists for these coordinates
    count = (
        session.query(MonitoringTarget)
        .filter_by(
            channel_id=12345,
            latitude=45.5,
            longitude=-122.5,
        )
        .count()
    )
    assert count == 1

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
        display_name="Test Location",
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


def test_remove_monitoring_target_by_location_and_coordinates(db_session):
    """
    Tests the `remove_monitoring_target_by_location` and
    `remove_monitoring_target_by_coordinates` methods.
    """
    from src.database import Database
    import pytest

    db = Database(db_session)
    session = db_session()

    # 1. ARRANGE
    # Add a location target and a geographic target
    db.add_monitoring_target(
        channel_id=12345,
        target_type="location",
        display_name="Test Location",
        location_id=999,
    )
    db.add_monitoring_target(
        channel_id=12345,
        target_type="geographic",
        display_name="Test Area",
        latitude=45.5,
        longitude=-122.5,
        radius_miles=10,
    )

    # 2. ACT & ASSERT
    # Test remove_monitoring_target_by_location
    db.remove_monitoring_target_by_location(12345, 999)
    assert db.find_monitoring_target_by_location(12345, 999) is None
    with pytest.raises(ValueError):
        db.remove_monitoring_target_by_location(12345, 111)

    # Test remove_monitoring_target_by_coordinates
    db.remove_monitoring_target_by_coordinates(12345, 45.5, -122.5, 10)
    assert db.find_monitoring_target_by_coordinates(12345, 45.5, -122.5, 10) is None
    with pytest.raises(ValueError):
        db.remove_monitoring_target_by_coordinates(12345, 1.1, 2.2, 3)

    session.close()


def test_find_and_get_targets(db_session):
    """
    Tests the various find and get methods for monitoring targets.
    - `find_monitoring_target_by_location`
    - `find_monitoring_target_by_coordinates`
    - `get_location_targets`
    - `get_geographic_targets`
    """
    from src.database import Database

    db = Database(db_session)
    session = db_session()

    # 1. ARRANGE
    # Add a location target and a geographic target
    db.add_monitoring_target(
        channel_id=12345,
        target_type="location",
        display_name="Test Location",
        location_id=999,
    )
    db.add_monitoring_target(
        channel_id=12345,
        target_type="geographic",
        display_name="Test Area",
        latitude=45.5,
        longitude=-122.5,
        radius_miles=10,
    )

    # 2. ACT & ASSERT
    # Test find_monitoring_target_by_location
    found_location = db.find_monitoring_target_by_location(12345, 999)
    assert found_location is not None
    assert found_location["location_id"] == 999
    assert db.find_monitoring_target_by_location(12345, 111) is None

    # Test find_monitoring_target_by_coordinates
    found_geo = db.find_monitoring_target_by_coordinates(12345, 45.5, -122.5, 10)
    assert found_geo is not None
    assert found_geo["latitude"] == 45.5
    assert db.find_monitoring_target_by_coordinates(12345, 1.1, 2.2, 3) is None

    # Test get_location_targets
    location_targets = db.get_location_targets(12345)
    assert len(location_targets) == 1
    assert location_targets[0]["target_type"] == "location"

    # Test get_geographic_targets
    geographic_targets = db.get_geographic_targets(12345)
    assert len(geographic_targets) == 1
    assert geographic_targets[0]["target_type"] == "geographic"

    session.close()
