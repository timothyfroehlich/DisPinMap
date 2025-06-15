"""
Unit tests for the monitor background tasks
Tests polling behavior, notification sending, and rate limiting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from src.monitor import MachineMonitor
from src.database import Database
import asyncio
from tests.utils.database import (
    setup_test_database,
    cleanup_test_database,
    verify_database_target,
    verify_channel_config
)
from tests.utils.generators import (
    generate_submission_data,
    generate_submission_sequence
)
from tests.utils.assertions import (
    assert_discord_message
)
from src.messages import Messages


@pytest.fixture
def mock_bot():
    """Create a mock bot with a mock channel"""
    bot = AsyncMock()
    channel = AsyncMock()
    channel.send.return_value = None
    bot.get_channel = MagicMock(return_value=channel)
    return bot


@pytest.fixture
def db():
    """Create test database"""
    test_db = setup_test_database()
    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def monitor(mock_bot, db):
    """Create a monitor instance with mocked dependencies"""
    return MachineMonitor(mock_bot, db)


@pytest.mark.asyncio
class TestMonitorTask:
    async def test_start_stop(self, monitor):
        """Test starting and stopping the monitor task"""
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitor_task is not None
        assert monitor.monitor_task.is_running()

        # Stop monitoring
        monitor.stop_monitoring()
        await asyncio.sleep(0.1)  # Give task time to stop
        assert not monitor.monitor_task.is_running()

    async def test_send_notifications_machines(self, monitor, mock_bot):
        """Test sending machine notifications"""
        # Setup test data
        submission = {
            'id': 1,
            'submission_type': 'new_lmx',
            'machine_name': 'Test Machine',
            'location_name': 'Test Location',
            'user_name': 'Test User'
        }

        # Send notification
        await monitor._send_notifications(123, [submission], 'machines')

        # Verify channel was retrieved and message was sent
        mock_bot.get_channel.assert_called_once_with(123)
        channel = mock_bot.get_channel.return_value
        channel.send.assert_awaited_once()
        assert Messages.Notification.Machine.ADDED.format(
            machine_name='Test Machine',
            location_name='Test Location',
            user_name='Test User'
        ) in channel.send.call_args[0][0]

    async def test_send_notifications_comments(self, monitor, mock_bot):
        """Test sending comment notifications"""
        # Setup test data
        submission = {
            'id': 1,
            'submission_type': 'new_condition',
            'machine_name': 'Test Machine',
            'location_name': 'Test Location',
            'user_name': 'Test User',
            'comment': 'Test Comment'
        }

        # Send notification
        await monitor._send_notifications(123, [submission], 'comments')

        # Verify channel was retrieved and message was sent
        mock_bot.get_channel.assert_called_once_with(123)
        channel = mock_bot.get_channel.return_value
        channel.send.assert_awaited_once()
        comment = submission.get('comment', '')
        comment_text = f"\n💬 {comment}" if comment else ""
        expected_message = Messages.Notification.Condition.UPDATED.format(
            machine_name='Test Machine',
            location_name='Test Location',
            comment_text=comment_text,
            user_name='Test User'
        )
        assert expected_message == channel.send.call_args[0][0]

    async def test_send_notifications_conditions(self, monitor, mock_bot):
        """Test sending condition notifications"""
        # Setup test data
        submission = {
            'id': 1,
            'submission_type': 'new_condition',
            'machine_name': 'Test Machine',
            'location_name': 'Test Location',
            'user_name': 'Test User'
        }

        # Send notification
        await monitor._send_notifications(123, [submission], 'all')

        # Verify channel was retrieved and message was sent
        mock_bot.get_channel.assert_called_once_with(123)
        channel = mock_bot.get_channel.return_value
        channel.send.assert_awaited_once()
        assert Messages.Notification.Condition.UPDATED.format(
            machine_name='Test Machine',
            location_name='Test Location',
            comment_text='',
            user_name='Test User'
        ) in channel.send.call_args[0][0]

    async def test_send_notifications_all_types(self, monitor):
        """Test sending notifications with all types setting"""
        channel_id = 12345
        submissions = [
            generate_submission_data(1, submission_type='new_lmx'),
            generate_submission_data(2, submission_type='new_condition', comment='Test Comment')
        ]

        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.send.return_value = None
        monitor.bot.get_channel.return_value = mock_channel

        # Send notifications
        await monitor._send_notifications(channel_id, submissions, 'all')

        # Verify both notifications were sent
        assert mock_channel.send.call_count == 2
        messages = [call[0][0] for call in mock_channel.send.call_args_list]
        assert any("Test Machine" in msg for msg in messages)
        assert any("Test Comment" in msg for msg in messages)

    async def test_send_notifications_multiple_machines(self, monitor, mock_bot):
        """Test sending notifications for multiple machines"""
        # Setup test data
        submissions = [
            {
                'id': i,
                'submission_type': 'new_lmx',
                'machine_name': f'Test Machine {i}',
                'location_name': f'Test Location {i}',
                'user_name': 'Test User'
            }
            for i in range(15)  # Create 15 submissions
        ]

        # Send notification
        await monitor._send_notifications(123, submissions, 'machines')

        # Verify channel was retrieved and message was sent
        mock_bot.get_channel.assert_called_once_with(123)
        channel = mock_bot.get_channel.return_value
        channel.send.assert_awaited_once()
        message = channel.send.call_args[0][0]
        assert Messages.Notification.Machine.MULTIPLE_ADDED.format(
            count=15,
            machines="\n".join(
                f"• **Test Machine {i}** at Test Location {i}"
                for i in range(10)
            ),
            remaining_text="\n... and 5 more machines"
        ) in message

    async def test_should_poll_channel(self, monitor):
        """Test channel polling decision logic"""
        # Test with default poll rate
        config = {'channel_id': 12345, 'poll_rate_minutes': 60}
        should_poll = await monitor._should_poll_channel(config)
        assert should_poll is True  # Currently always returns True

    async def test_poll_channel_no_targets(self, monitor):
        """Test polling channel with no targets"""
        config = {'channel_id': 12345}
        await monitor._poll_channel(config)
        # Should not raise any errors

    async def test_poll_channel_with_targets(self, monitor, mock_bot, db):
        """Test polling a channel with monitoring targets"""
        # Setup test data
        channel_id = 123
        guild_id = 456  # Required for update_channel_config
        target_type = 'location'
        target_name = 'Test Location'
        target_data = '1'

        # Add monitoring target
        db.add_monitoring_target(channel_id, target_type, target_name, target_data)
        db.update_channel_config(channel_id, guild_id, poll_rate_minutes=5, notification_types='machines')

        # Mock API response
        submission = {
            'id': 1,
            'submission_type': 'new_lmx',
            'machine_name': 'Test Machine',
            'location_name': 'Test Location',
            'user_name': 'Test User'
        }
        with patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [submission]

            # Poll channel
            await monitor._poll_channel({'channel_id': channel_id})

            # Verify API was called and notification was sent
            mock_fetch.assert_called_once_with(1)
            mock_bot.get_channel.assert_called_once_with(channel_id)
            channel = mock_bot.get_channel.return_value
            channel.send.assert_awaited_once()
            assert Messages.Notification.Machine.ADDED.format(
                machine_name='Test Machine',
                location_name='Test Location',
                user_name='Test User'
            ) in channel.send.call_args[0][0]

    async def test_send_notifications_machines_only(self, monitor):
        """Test sending notifications with machines only setting"""
        channel_id = 12345
        submissions = [
            generate_submission_data(1, submission_type='new_lmx'),
            generate_submission_data(2, submission_type='new_condition', comment='Test Comment')
        ]

        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.send.return_value = None
        monitor.bot.get_channel.return_value = mock_channel

        # Send notifications
        await monitor._send_notifications(channel_id, submissions, 'machines')

        # Verify only machine notification was sent
        mock_channel.send.assert_awaited_once()
        message = mock_channel.send.call_args[0][0]
        assert "Test Machine" in message
        assert "Test Comment" not in message

    async def test_send_notifications_comments_only(self, monitor):
        """Test sending notifications with comments only setting"""
        channel_id = 12345
        submissions = [
            generate_submission_data(1, submission_type='new_lmx'),
            generate_submission_data(2, submission_type='new_condition', comment='Test Comment')
        ]

        # Mock channel
        mock_channel = AsyncMock()
        mock_channel.send.return_value = None
        monitor.bot.get_channel.return_value = mock_channel

        # Send notifications
        await monitor._send_notifications(channel_id, submissions, 'comments')

        # Verify only comment notification was sent
        mock_channel.send.assert_awaited_once()
        message = mock_channel.send.call_args[0][0]
        assert "Test Machine" in message
        assert "Test Comment" in message

    async def test_send_notifications_channel_not_found(self, monitor):
        """Test handling of non-existent channel"""
        channel_id = 12345
        submissions = [generate_submission_data(1)]

        # Mock bot to return None for channel
        monitor.bot.get_channel.return_value = None

        # Send notifications - should not raise exception
        await monitor._send_notifications(channel_id, submissions, 'machines')

        # Verify channel was checked but no send was attempted
        monitor.bot.get_channel.assert_called_once_with(channel_id)

    async def test_poll_channel_api_error(self, monitor, db):
        """Test handling of API errors during polling"""
        channel_id = 12345
        guild_id = 67890

        # Set up channel config and targets
        db.update_channel_config(channel_id, guild_id, is_active=True)
        db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')

        # Mock API to raise exception
        with patch('src.monitor.fetch_submissions_for_coordinates', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            # Poll the channel - should not raise error
            await monitor._poll_channel({'channel_id': channel_id})

            # Verify API was called
            mock_fetch.assert_called_once()

            # Verify no notifications were sent
            assert not monitor.bot.get_channel.called
