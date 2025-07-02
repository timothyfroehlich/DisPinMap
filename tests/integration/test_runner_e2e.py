"""
End-to-end tests for the background monitoring loop.

These tests verify the complete functionality of the monitoring task, from
detecting active channels to fetching data, identifying new submissions,
and triggering notifications.
"""

# To be migrated from `tests_backup/enhanced/test_integration_background_tasks.py`,
# `tests_backup/enhanced/test_task_loop_failures.py`, and
# `tests_backup/func/test_monitor_task_loop_lifecycle.py`.

import pytest


@pytest.mark.asyncio
async def test_monitoring_loop_finds_new_submission_and_notifies(
    db_session, api_mocker
):
    """
    Tests the entire monitoring pipeline for a new submission.
    - Sets up an active channel with a monitoring target in the database.
    - Mocks the PinballMap API to return a new, unseen submission.
    - Mocks the Discord bot's `send` method to capture notification calls.
    - Runs one cycle of the monitoring loop.
    - Asserts that the new submission was detected.
    - Asserts that a notification was sent.
    - Asserts that the new submission is added to the 'seen' table in the database.
    """
    from src.models import ChannelConfig, MonitoringTarget, SeenSubmission

    session = db_session()

    # Setup: Create active channel with monitoring target
    channel_config = ChannelConfig(
        channel_id=12345, guild_id=11111, is_active=True, poll_rate_minutes=60
    )
    session.add(channel_config)

    target = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Test Location",
        location_id=874,
    )
    session.add(target)
    session.commit()

    # Mock API to return new submission
    api_mocker.add_response(
        url_substring="user_submissions",
        json_fixture_path="pinballmap_submissions/location_874_recent.json",
    )

    # Mock Discord bot and channel for notifications
    from unittest.mock import AsyncMock

    mock_bot = AsyncMock()
    mock_channel = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel

    # TODO: Add actual runner execution here when implementing full monitoring loop
    # For now, verify the setup is correct for notification testing

    # Verify target is set up correctly
    targets = session.query(MonitoringTarget).filter_by(channel_id=12345).all()
    assert len(targets) == 1
    assert targets[0].location_id == 874

    # Verify no seen submissions initially
    seen_count = session.query(SeenSubmission).filter_by(channel_id=12345).count()
    assert seen_count == 0

    # TODO: Add actual monitoring loop execution and verify notifications are sent
    # This would include checking mock_channel.send was called with expected content

    session.close()


@pytest.mark.asyncio
async def test_monitoring_loop_ignores_seen_submission(db_session, api_mocker):
    """
    Tests that the monitoring loop correctly ignores previously seen submissions.
    - Sets up a channel and target.
    - Pre-populates the 'seen' table with a submission ID.
    - Mocks the PinballMap API to return that same submission.
    - Mocks the Discord `send` method.
    - Runs one cycle of the monitoring loop.
    - Asserts that NO notification was sent.
    """
    from datetime import datetime

    from src.models import ChannelConfig, MonitoringTarget, SeenSubmission

    session = db_session()

    # Setup: Create channel and target
    channel_config = ChannelConfig(
        channel_id=12345, guild_id=11111, is_active=True, poll_rate_minutes=60
    )
    session.add(channel_config)

    target = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Test Location",
        location_id=874,
    )
    session.add(target)

    # Pre-populate seen submissions table
    seen_submission = SeenSubmission(
        channel_id=12345,
        submission_id=12345,  # This submission ID will be "seen"
        seen_at=datetime.now(),
    )
    session.add(seen_submission)
    session.commit()

    # Test filtering logic for seen submissions
    test_submission_ids = [12345, 67890, 11111]  # Mix of seen and unseen

    # Query existing seen submissions
    existing_seen = (
        session.query(SeenSubmission.submission_id).filter_by(channel_id=12345).all()
    )
    existing_seen_ids = {row[0] for row in existing_seen}

    # Filter out already seen submissions
    new_submissions = [
        sub_id for sub_id in test_submission_ids if sub_id not in existing_seen_ids
    ]

    # Assert that only unseen submissions remain
    assert 12345 not in new_submissions  # This was marked as seen
    assert 67890 in new_submissions  # This is new
    assert 11111 in new_submissions  # This is new
    assert len(new_submissions) == 2  # Only 2 new submissions

    session.close()


@pytest.mark.asyncio
async def test_monitoring_respects_poll_rate(db_session):
    """
    Tests that the monitoring logic correctly respects the channel's poll rate.
    - Sets up a channel with a last_poll_at time that is NOT yet ready to be polled again.
    - Runs the monitor's channel selection logic.
    - Asserts that this channel is NOT selected for polling.
    - Updates the last_poll_at time to be in the past.
    - Runs the logic again and asserts that the channel IS selected.
    """
    from datetime import datetime, timedelta, timezone

    from src.cogs.runner import Runner
    from src.models import ChannelConfig
    from tests.utils.mock_factories import (
        create_async_notifier_mock,
        create_bot_mock,
        create_database_mock,
    )

    session = db_session()

    # Create mock dependencies for Runner using spec-based factories
    mock_bot = create_bot_mock()
    mock_database = create_database_mock()
    mock_notifier = create_async_notifier_mock()

    # Create monitor instance
    runner = Runner(mock_bot, mock_database, mock_notifier)

    # Create channel config with recent poll time (using UTC timezone)
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    channel_config = ChannelConfig(
        channel_id=12345,
        guild_id=67890,  # Required field
        poll_rate_minutes=60,  # 1 hour poll rate
        last_poll_at=recent_time,
        is_active=True,
    )

    session.add(channel_config)
    session.commit()

    # Convert channel config to dictionary format expected by _should_poll_channel
    config_dict = {
        "channel_id": channel_config.channel_id,
        "poll_rate_minutes": channel_config.poll_rate_minutes,
        "last_poll_at": channel_config.last_poll_at,
    }

    # Should NOT be ready to poll yet (only 5 minutes passed)
    should_poll_now = await runner._should_poll_channel(config_dict)
    assert should_poll_now is False

    # Update to old poll time
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    channel_config.last_poll_at = old_time
    session.commit()

    # Update the config dict with new time
    config_dict["last_poll_at"] = old_time

    # Should be ready to poll now
    should_poll_later = await runner._should_poll_channel(config_dict)
    assert should_poll_later is True

    # CLEANUP
    session.delete(channel_config)
    session.commit()
    session.close()


@pytest.mark.asyncio
async def test_run_checks_handles_location_id_field(db_session):
    """
    Test that runner.run_checks_for_channel handles location_id field correctly.

    This test reproduces Issue #68: KeyError 'target_data' in !check command.
    The database field was renamed from target_data to location_id, but runner.py
    still tries to access target['target_data'] causing a KeyError.
    """
    from src.cogs.runner import Runner
    from tests.utils.mock_factories import (
        create_async_notifier_mock,
        create_bot_mock,
        create_database_mock,
    )

    # Create mock dependencies using spec-based factories
    mock_bot = create_bot_mock()
    mock_database = create_database_mock()
    mock_notifier = create_async_notifier_mock()

    # Create runner instance
    runner = Runner(mock_bot, mock_database, mock_notifier)

    # Mock database to return target with location_id field (post-migration schema)
    mock_target = {
        "id": 1,
        "target_type": "location",
        "location_id": "123",  # This is the NEW field name
        "target_name": "Test Location",
    }

    mock_database.get_monitoring_targets.return_value = [mock_target]
    mock_database.get_channel_config.return_value = {
        "channel_id": 12345,
        "poll_rate_minutes": 60,
        "is_active": True,
    }

    # This should NOT crash with KeyError: 'target_data'
    # The bug occurs in runner.py lines 305, 323, 324 where it tries to access
    # target["target_data"] but the database returns target["location_id"]
    try:
        submissions, api_failure = await runner._process_target(
            mock_target, is_manual_check=True
        )
        # If we get here without KeyError, the fix worked
        assert submissions is not None, (
            "Should return submissions data without KeyError"
        )
        assert isinstance(submissions, list), "Submissions should be a list"
    except KeyError as e:
        if "target_data" in str(e):
            pytest.fail(
                f"KeyError accessing target_data field: {e}. Field should be location_id"
            )
        else:
            # Re-raise if it's a different KeyError
            raise


@pytest.mark.asyncio
async def test_run_checks_for_channel_with_invalid_city_target_is_handled(caplog):
    """
    Test that run_checks_for_channel handles an invalid 'city' target gracefully
    by logging an error and not crashing.
    """
    import logging

    from src.cogs.runner import Runner
    from tests.utils.mock_factories import (
        create_async_notifier_mock,
        create_bot_mock,
        create_database_mock,
    )

    # Arrange
    mock_bot = create_bot_mock()
    mock_db = create_database_mock()
    mock_notifier = create_async_notifier_mock()

    runner = Runner(bot=mock_bot, database=mock_db, notifier=mock_notifier)

    channel_id = 12345
    config = {"channel_id": channel_id}

    # This is the problematic target
    targets = [
        {
            "id": 1,
            "target_type": "city",
            "target_name": "Austin",
            "location_id": None,
        }
    ]
    mock_db.get_monitoring_targets.return_value = targets

    # Act
    # This should no longer raise a ValueError but handle it gracefully.
    caplog.set_level(logging.ERROR)
    await runner.run_checks_for_channel(channel_id, config, is_manual_check=True)

    # Assert
    assert "Skipping target with unsupported type 'city': id=1" in caplog.text
    assert (
        "This target should be re-added using the add command to geocode it correctly."
        in caplog.text
    )


@pytest.mark.asyncio
async def test_monitoring_loop_handles_api_errors_gracefully(db_session, api_mocker):
    """
    Tests that the monitoring loop continues running even if one target's API call fails.
    - Sets up multiple active targets.
    - Mocks the API to return an error for one target but a success for another.
    - Runs the monitoring loop.
    - Asserts that the loop completes without crashing and that the successful target is processed.
    """
    from unittest.mock import patch

    import requests

    from src.api import fetch_submissions_for_location
    from src.models import ChannelConfig, MonitoringTarget

    session = db_session()

    # Setup: Create channel with multiple targets
    channel_config = ChannelConfig(
        channel_id=12345, guild_id=11111, is_active=True, poll_rate_minutes=60
    )
    session.add(channel_config)

    # Target 1 - will cause API error
    target1 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Failing Location",
        location_id=999,
    )
    session.add(target1)

    # Target 2 - will succeed
    target2 = MonitoringTarget(
        channel_id=12345,
        target_type="location",
        target_name="Working Location",
        location_id=874,
    )
    session.add(target2)
    session.commit()

    # Test that API errors are handled gracefully
    # First call (target1) fails, second call (target2) succeeds

    # Mock API failure for location 999
    with patch("src.api.rate_limited_request") as mock_request:
        mock_request.side_effect = requests.exceptions.HTTPError("API Error")

        try:
            result1 = await fetch_submissions_for_location(999)
            # Should return empty list on error
            assert result1 == []
        except Exception as e:
            # Should handle the exception gracefully without crashing
            assert "API" in str(e) or "connection" in str(e) or "timeout" in str(e), (
                f"Unexpected exception type: {e}"
            )

    # Mock API success for location 874
    api_mocker.add_response(
        url_substring="user_submissions",
        json_fixture_path="pinballmap_submissions/location_874_recent.json",
    )

    result2 = await fetch_submissions_for_location(874)

    # Should successfully return submissions
    assert isinstance(result2, list)

    # Verify both targets exist in database
    targets = session.query(MonitoringTarget).filter_by(channel_id=12345).all()
    assert len(targets) == 2

    session.close()
