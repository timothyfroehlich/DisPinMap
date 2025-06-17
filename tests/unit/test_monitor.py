"""
Unit tests for the monitor background tasks
Tests polling behavior, notification sending, and rate limiting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from src.monitor import MachineMonitor
from src.database import Database
import asyncio
from tests.utils.database import (
    setup_test_database,
    cleanup_test_database,
)
from tests.utils.generators import (
    generate_submission_data,
)


@pytest.fixture
def mock_bot():
    """Create a mock bot with a mock channel"""
    bot = AsyncMock()
    channel = AsyncMock()
    channel.send.return_value = None
    bot.get_channel = MagicMock(return_value=channel)
    bot.database = setup_test_database()
    bot.notifier = AsyncMock()
    return bot


@pytest.fixture
def db(mock_bot):
    """Create test database"""
    yield mock_bot.database
    cleanup_test_database(mock_bot.database)


@pytest.fixture
def mock_notifier(mock_bot):
    return mock_bot.notifier


@pytest.fixture
def monitor(mock_bot, db, mock_notifier):
    """Create a monitor instance with mocked dependencies"""
    return MachineMonitor(mock_bot, db, mock_notifier)


@pytest.mark.asyncio
class TestMonitorTask:
    async def test_should_poll_channel(self, monitor):
        """Test channel polling decision logic"""
        channel_id = 123

        # Never polled before, should be true
        config = {'channel_id': channel_id, 'poll_rate_minutes': 60, 'last_poll_at': None}
        assert await monitor._should_poll_channel(config) is True

        # Polled recently, should be false
        config['last_poll_at'] = datetime.now(timezone.utc)
        assert await monitor._should_poll_channel(config) is False

        # Polled long ago, should be true
        config['last_poll_at'] = datetime.now(timezone.utc) - timedelta(minutes=61)
        assert await monitor._should_poll_channel(config) is True

    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_run_checks_for_channel_location(self, mock_fetch, monitor, db, mock_notifier):
        """Test running checks for a channel with a location target"""
        channel_id = 123
        guild_id = 456
        db.add_monitoring_target(channel_id, 'location', 'Test Location', '12345')
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        config['last_poll_at'] = None

        submission = generate_submission_data(1)
        mock_fetch.return_value = [submission]

        result = await monitor.run_checks_for_channel(channel_id, config)

        mock_fetch.assert_called_once_with(12345, use_min_date=True)
        mock_notifier.post_submissions.assert_called_once()
        db.filter_new_submissions(channel_id, [submission])
        # assert that submission is now marked as seen
        assert not db.filter_new_submissions(channel_id, [submission])
        # assert that new submissions were found
        assert result is True

    @patch('src.monitor.fetch_submissions_for_coordinates', new_callable=AsyncMock)
    async def test_run_checks_for_channel_coordinates(self, mock_fetch, monitor, db, mock_notifier):
        """Test running checks for a channel with a coordinate target"""
        channel_id = 123
        guild_id = 456
        db.add_monitoring_target(channel_id, 'latlong', '30.1,-97.2,10', '30.1,-97.2,10')
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        config['last_poll_at'] = None

        submission = generate_submission_data(2)
        mock_fetch.return_value = [submission]

        result = await monitor.run_checks_for_channel(channel_id, config)

        mock_fetch.assert_called_once_with(30.1, -97.2, 10, use_min_date=True)
        mock_notifier.post_submissions.assert_called_once()
        assert not db.filter_new_submissions(channel_id, [submission])
        # assert that new submissions were found
        assert result is True

    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_run_checks_no_new_submissions(self, mock_fetch, monitor, db, mock_notifier):
        """Test running checks when no new submissions are found"""
        channel_id = 123
        guild_id = 456
        db.add_monitoring_target(channel_id, 'location', 'Test Location', '12345')
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        config['last_poll_at'] = None

        mock_fetch.return_value = []

        result = await monitor.run_checks_for_channel(channel_id, config)

        mock_notifier.post_submissions.assert_not_called()
        # assert that no new submissions were found
        assert result is False

    async def test_run_checks_no_targets(self, monitor, db, mock_notifier):
        """Test running checks for a channel with no targets"""
        channel_id = 123
        config = {'channel_id': channel_id, 'last_poll_at': None}

        result = await monitor.run_checks_for_channel(channel_id, config)

        mock_notifier.post_submissions.assert_not_called()
        # Note: update_channel_last_poll_time should be called but we can't easily assert on real db
        # assert that no new submissions were found
        assert result is False

    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_no_new_submissions(self, mock_fetch, monitor, db, mock_notifier):
        """Test manual check when no new submissions are found"""
        channel_id = 123
        guild_id = 456
        db.add_monitoring_target(channel_id, 'location', 'Test Location', '12345')
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        # Set last poll time to 5 minutes ago
        config['last_poll_at'] = datetime.now(timezone.utc) - timedelta(minutes=5)

        mock_fetch.return_value = []

        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)

        mock_notifier.post_submissions.assert_not_called()
        # Should have sent a "Nothing new since X minutes ago" message
        mock_notifier.log_and_send.assert_called_once()
        args = mock_notifier.log_and_send.call_args[0]
        assert "Nothing new since" in args[1]
        assert "minutes ago" in args[1]
        # assert that no new submissions were found
        assert result is False

    @patch('src.monitor.MachineMonitor._should_poll_channel', new_callable=AsyncMock)
    @patch('src.monitor.MachineMonitor.run_checks_for_channel', new_callable=AsyncMock)
    async def test_monitor_task_loop(self, mock_run_checks, mock_should_poll, monitor, db):
        """Test the main monitor task loop"""
        channel_id = 123
        guild_id = 456
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        db.get_active_channels = MagicMock(return_value=[config])

        # Test when should_poll is true
        mock_should_poll.return_value = True
        await monitor.monitor_task_loop.coro(monitor)
        mock_should_poll.assert_called_once_with(config)
        mock_run_checks.assert_called_once_with(channel_id, config)

        mock_should_poll.reset_mock()
        mock_run_checks.reset_mock()

        # Test when should_poll is false
        mock_should_poll.return_value = False
        await monitor.monitor_task_loop.coro(monitor)
        mock_should_poll.assert_called_once_with(config)
        mock_run_checks.assert_not_called()

    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_run_checks_updates_last_checked_at(self, mock_fetch, monitor, db):
        """Test that run_checks_for_channel updates the last_checked_at timestamp."""
        channel_id = 123
        guild_id = 456
        db.add_monitoring_target(channel_id, 'location', 'Test Location', '12345')
        db.update_channel_config(channel_id, guild_id, is_active=True)
        config = db.get_channel_config(channel_id)
        target = db.get_monitoring_targets(channel_id)[0]
        assert target['last_checked_at'] is None

        mock_fetch.return_value = []
        await monitor.run_checks_for_channel(channel_id, config)

        updated_target = db.get_monitoring_targets(channel_id)[0]
        assert updated_target['last_checked_at'] is not None
        time_diff = datetime.now(timezone.utc) - updated_target['last_checked_at'].replace(tzinfo=timezone.utc)
        assert time_diff.total_seconds() < 5
