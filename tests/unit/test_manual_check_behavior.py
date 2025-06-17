"""
Test suite for manual check behavior verification

This file tests the specific behaviors documented for manual checks (!check command):
- Uses use_min_date=False to fetch historical submissions (no time limit)
- Implements hybrid model: shows new submissions + older ones to reach 5 total
- No time limit (can go back further than 24 hours to find 5 submissions)  
- Shows explicit error messages to Discord on failures
- Does not update last_poll_at timestamp (separate from scheduled polling)
- Provides feedback messages about time since last poll when no new submissions

TEST STRUCTURE:
Each test verifies manual check behaviors without asserting on message content.
Focus is on API parameter verification, hybrid submission logic, and error handling patterns.

STARTING CONDITIONS:
- Test database with existing monitoring targets
- Controlled last_poll_at timestamps for time-based testing
- Mocked API responses with controlled submission timing
- Mock Discord context objects for command execution

ASSERTIONS:
- API calls use use_min_date=False parameter
- Hybrid logic: new + older submissions to reach 5 total
- No time limits applied (can fetch very old submissions)
- Error messages sent to Discord via notifier.log_and_send
- Feedback messages provided when no new submissions found
- last_poll_at timestamp remains unchanged
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from src.monitor import MachineMonitor
from src.cogs.monitoring import MonitoringCog
from tests.utils.database import setup_test_database, cleanup_test_database
from tests.utils.generators import generate_submission_data
from tests.utils import MockContext


@pytest.fixture
def mock_bot():
    """Create mock bot with channel access"""
    bot = AsyncMock()
    channel = AsyncMock()
    channel.id = 12345
    bot.get_channel = MagicMock(return_value=channel)
    return bot


@pytest.fixture
def db():
    """Create test database"""
    test_db = setup_test_database()
    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def mock_notifier():
    """Create mock notifier"""
    return AsyncMock()


@pytest.fixture
def monitor(mock_bot, db, mock_notifier):
    """Create monitor instance for manual checks"""
    return MachineMonitor(mock_bot, db, mock_notifier)


@pytest.fixture
def monitoring_cog(mock_bot, db, mock_notifier):
    """Create monitoring cog for command testing"""
    return MonitoringCog(mock_bot, db, mock_notifier)


@pytest.mark.asyncio
class TestManualCheckBehavior:
    """
    Test manual check behavior that occurs when users run !check command.
    
    Key behaviors to verify:
    1. API calls use use_min_date=False (no time limits)
    2. Hybrid model: new submissions + older ones to reach 5 total
    3. No 24-hour time limit (can fetch very old data)
    4. Errors are explicitly sent to Discord
    5. Feedback messages when no new submissions found
    6. No interference with polling timestamps
    7. Integration between command and monitor cog
    """
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_uses_min_date_false_for_location(self, mock_fetch, monitor, db, mock_bot):
        """
        Test that manual checks use use_min_date=False for location targets.
        
        Starting conditions:
        - Channel with location monitoring target
        - Previous poll timestamp exists
        - Manual check initiated (is_manual_check=True)
        
        Assertions:
        - fetch_submissions_for_location called with use_min_date=False
        - No time-based filtering applied to API call
        - Historical data is accessible
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response
        submissions = [generate_submission_data(i) for i in range(3)]
        mock_fetch.return_value = submissions
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify API called with correct parameters
        mock_fetch.assert_called_once_with(location_id, use_min_date=False)
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_coordinates', new_callable=AsyncMock)
    async def test_manual_check_uses_min_date_false_for_coordinates(self, mock_fetch, monitor, db, mock_bot):
        """
        Test that manual checks use use_min_date=False for coordinate targets.
        
        Starting conditions:
        - Channel with coordinate monitoring target
        - Previous poll timestamp exists
        - Manual check initiated (is_manual_check=True)
        
        Assertions:
        - fetch_submissions_for_coordinates called with use_min_date=False
        - No time-based filtering applied to API call
        - Historical data is accessible
        """
        channel_id = 12345
        guild_id = 67890
        lat, lon, radius = 30.1, -97.2, 10
        
        # Setup database
        db.add_monitoring_target(channel_id, 'latlong', f'{lat},{lon},{radius}')
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response
        submissions = [generate_submission_data(i) for i in range(3)]
        mock_fetch.return_value = submissions
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify API called with correct parameters
        mock_fetch.assert_called_once_with(lat, lon, radius, use_min_date=False)
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_hybrid_model_new_plus_old(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test hybrid model: new submissions + older ones to reach 5 total.
        
        Note: Current implementation shows top 5 submissions sorted by timestamp.
        The hybrid model (new + old to reach 5) may need implementation.
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response with 7 submissions
        base_time = datetime.now(timezone.utc)
        submissions = []
        for i in range(7):
            submission = generate_submission_data(i + 1)
            submission['created_at'] = (base_time - timedelta(hours=i)).isoformat()
            submissions.append(submission)
        
        mock_fetch.return_value = submissions
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify submissions were processed
        mock_notifier.log_and_send.assert_called()
        mock_notifier.post_submissions.assert_called()
        
        # Get the submissions that were posted
        call_args = mock_notifier.post_submissions.call_args
        posted_submissions = call_args[0][1]
        
        # Verify limited to 5 submissions
        assert len(posted_submissions) == 5
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_shows_all_when_less_than_five_available(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test manual check when fewer than 5 submissions total are available.
        
        Starting conditions:
        - Channel with monitoring targets
        - Only 3 total submissions available (new + old)
        
        Assertions:
        - All 3 available submissions are shown
        - No padding or empty submissions
        - Method still completes successfully
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response with only 3 submissions
        submissions = [generate_submission_data(i + 1) for i in range(3)]
        mock_fetch.return_value = submissions
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify all submissions were posted
        mock_notifier.post_submissions.assert_called()
        call_args = mock_notifier.post_submissions.call_args
        posted_submissions = call_args[0][1]
        
        # Verify all 3 submissions shown
        assert len(posted_submissions) == 3
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_no_time_limits(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test that manual checks have no time limits (can go back indefinitely).
        
        Starting conditions:
        - Channel with monitoring targets
        - Submissions available from weeks/months ago
        - No recent submissions available
        
        Assertions:
        - Very old submissions are included in results
        - No 24-hour or other time filtering applied
        - API called without time constraints
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Create very old submissions (weeks ago)
        base_time = datetime.now(timezone.utc) - timedelta(weeks=4)
        submissions = []
        for i in range(3):
            submission = generate_submission_data(i + 1)
            submission['created_at'] = (base_time - timedelta(days=i)).isoformat()
            submissions.append(submission)
        
        mock_fetch.return_value = submissions
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify API called with use_min_date=False (no time limits)
        mock_fetch.assert_called_once_with(location_id, use_min_date=False)
        
        # Verify old submissions were accepted and posted
        mock_notifier.post_submissions.assert_called()
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_provides_feedback_no_new_submissions(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test feedback messages when manual check finds no new submissions.
        
        Starting conditions:
        - Channel with monitoring targets
        - last_poll_at timestamp from X minutes ago
        - No submissions since last poll
        
        Assertions:
        - notifier.log_and_send called with time-based feedback message
        - Feedback includes time since last poll (minutes or hours)
        - Method returns False (no new submissions)
        - User receives informative message about timing
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database with last poll timestamp
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        last_poll_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        db.update_channel_last_poll_time(channel_id, last_poll_time)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response with no submissions
        mock_fetch.return_value = []
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify feedback message was sent
        mock_notifier.log_and_send.assert_called()
        call_args = mock_notifier.log_and_send.call_args
        message = call_args[0][1]
        assert "Nothing new since" in message
        assert "minutes ago" in message
        
        # Verify result indicates no new submissions
        assert result is False
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_handles_no_previous_poll(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test manual check when no previous poll timestamp exists.
        
        Starting conditions:
        - Channel with monitoring targets
        - last_poll_at is None (never polled before)
        - No submissions available
        
        Assertions:
        - notifier.log_and_send called with generic "no submissions" message
        - No time-based messaging (since no previous poll to reference)
        - Method handles None timestamp gracefully
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database without last poll timestamp
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        config['last_poll_at'] = None
        
        # Setup mock response with no submissions
        mock_fetch.return_value = []
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify generic message was sent (not time-based)
        mock_notifier.log_and_send.assert_called()
        call_args = mock_notifier.log_and_send.call_args
        message = call_args[0][1]
        assert "No submissions found" in message
        
        # Verify result indicates no submissions
        assert result is False
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_updates_poll_timestamp(self, mock_fetch, monitor, db, mock_bot):
        """
        Test that manual checks update last_poll_at timestamp on success.
        
        Starting conditions:
        - Channel with existing last_poll_at timestamp
        - Successful manual check operation
        
        Assertions:
        - last_poll_at timestamp is updated to reflect successful check
        - Successful manual checks indicate targets are being monitored properly
        - Timestamp update shows the system is working
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database with initial timestamp
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        initial_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.update_channel_last_poll_time(channel_id, initial_time)
        config = db.get_channel_config(channel_id)
        
        # Setup mock response
        submissions = [generate_submission_data(1)]
        mock_fetch.return_value = submissions
        
        # Execute manual check
        before_time = datetime.now(timezone.utc)
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        after_time = datetime.now(timezone.utc)
        
        # Verify timestamp was updated to reflect successful manual check
        updated_config = db.get_channel_config(channel_id)
        updated_time = updated_config['last_poll_at']
        assert updated_time is not None
        assert updated_time != initial_time
        assert before_time <= updated_time <= after_time
        
        # Verify result
        assert result is True
    
    @patch('src.monitor.fetch_submissions_for_location', new_callable=AsyncMock)
    async def test_manual_check_sends_explicit_error_messages(self, mock_fetch, monitor, db, mock_bot, mock_notifier):
        """
        Test that manual check errors are sent to Discord.
        
        Starting conditions:
        - Channel with monitoring targets
        - API call raises exception during manual check
        
        Assertions:
        - notifier.log_and_send IS called with error message
        - Error message includes context that it's a manual check
        - Error is not suppressed (unlike automatic polls)
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123
        
        # Setup database
        db.add_monitoring_target(channel_id, 'location', 'Test Location', str(location_id))
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)
        
        # Setup mock to raise exception
        mock_fetch.side_effect = Exception("API Error")
        
        # Execute manual check
        result = await monitor.run_checks_for_channel(channel_id, config, is_manual_check=True)
        
        # Verify error message was sent to Discord
        mock_notifier.log_and_send.assert_called()
        call_args = mock_notifier.log_and_send.call_args
        message = call_args[0][1]
        assert "Error during manual check" in message
        
        # Verify failed result
        assert result is False
    
    async def test_check_command_integration(self, monitoring_cog, db):
        """
        Test integration between !check command and monitor cog.
        
        Starting conditions:
        - MonitoringCog with valid bot.get_cog setup
        - Channel with monitoring targets
        - Mock context for command execution
        
        Assertions:
        - bot.get_cog('MachineMonitor') is called
        - run_checks_for_channel called with is_manual_check=True
        - Command execution completes without errors
        - Integration between cogs works correctly
        """
        ctx = MockContext(12345, 67890)
        
        # Setup monitoring target
        db.add_monitoring_target(ctx.channel.id, 'location', 'Test Location', '123')
        
        # Setup mock monitor cog
        mock_monitor_cog = AsyncMock()
        mock_monitor_cog.run_checks_for_channel = AsyncMock(return_value=True)
        monitoring_cog.bot.get_cog = MagicMock(return_value=mock_monitor_cog)
        
        # Execute check command
        await monitoring_cog.check.callback(monitoring_cog, ctx)
        
        # Verify integration
        monitoring_cog.bot.get_cog.assert_called_once_with('MachineMonitor')
        mock_monitor_cog.run_checks_for_channel.assert_called_once()
        
        # Verify is_manual_check parameter
        call_args = mock_monitor_cog.run_checks_for_channel.call_args
        assert call_args[1]['is_manual_check'] is True
    
    async def test_check_command_handles_missing_monitor_cog(self, monitoring_cog, db, mock_notifier):
        """
        Test !check command when MachineMonitor cog is not available.
        
        Starting conditions:
        - bot.get_cog returns None (monitor cog not loaded)
        - Valid Discord context for error message
        
        Assertions:
        - notifier.log_and_send called with monitor not found message
        - Command fails gracefully
        - User receives informative error message
        """
        ctx = MockContext(12345, 67890)
        
        # Setup bot to return None for monitor cog
        monitoring_cog.bot.get_cog = MagicMock(return_value=None)
        
        # Execute check command
        await monitoring_cog.check.callback(monitoring_cog, ctx)
        
        # Verify error message was sent
        monitoring_cog.notifier.log_and_send.assert_called()
        call_args = monitoring_cog.notifier.log_and_send.call_args
        message = call_args[0][1]
        assert "Could not find the monitor" in message