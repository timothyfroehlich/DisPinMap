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


def test_monitoring_loop_finds_new_submission_and_notifies(db_session, api_mocker):
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
    pass


def test_monitoring_loop_ignores_seen_submission(db_session, api_mocker):
    """
    Tests that the monitoring loop correctly ignores previously seen submissions.
    - Sets up a channel and target.
    - Pre-populates the 'seen' table with a submission ID.
    - Mocks the PinballMap API to return that same submission.
    - Mocks the Discord `send` method.
    - Runs one cycle of the monitoring loop.
    - Asserts that NO notification was sent.
    """
    pass


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
        assert True, "Successfully handled location_id field without KeyError"
    except KeyError as e:
        if "target_data" in str(e):
            pytest.fail(
                f"KeyError accessing target_data field: {e}. Field should be location_id"
            )
        else:
            # Re-raise if it's a different KeyError
            raise


def test_monitoring_loop_handles_api_errors_gracefully(db_session, api_mocker):
    """
    Tests that the monitoring loop continues running even if one target's API call fails.
    - Sets up multiple active targets.
    - Mocks the API to return an error for one target but a success for another.
    - Runs the monitoring loop.
    - Asserts that the loop completes without crashing and that the successful target is processed.
    """
    pass
