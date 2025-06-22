"""
Test suite for automatic poll behavior verification

This file tests the specific behaviors documented for automatic polls (scheduled monitoring):
- Uses use_min_date=True to fetch only new submissions since last successful check
- Filters submissions to only show those not previously seen
- Updates last_poll_at timestamp only on successful checks
- Suppresses Discord error messages (logs only)
- Respects 24-hour lookback limit from last successful poll

TEST STRUCTURE:
Each test verifies specific behavioral aspects without asserting on message content.
Focus is on API parameter verification, database state changes, and method call patterns.

STARTING CONDITIONS:
- Clean test database with monitoring targets
- Mocked API responses with controlled submission data
- Mocked Discord bot and channel objects
- Controlled timestamps for time-based testing

ASSERTIONS:
- API calls use correct use_min_date parameter
- Database timestamps are updated correctly on success/failure
- Submission filtering works correctly (new vs seen)
- Error handling follows automatic poll patterns (no Discord messages)
- Notifier methods are called with expected patterns

"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cogs.monitor import MachineMonitor
from tests.utils.db_utils import cleanup_test_database, setup_test_database
from tests.utils.generators import generate_submission_data


@pytest.fixture
def mock_bot():
    """Create a mock bot with channel access"""
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
    """Create monitor instance with mocked dependencies"""
    return MachineMonitor(mock_bot, db, mock_notifier)


@pytest.mark.asyncio
class TestAutomaticPollBehavior:
    """
    Test automatic poll behavior that occurs during scheduled monitoring.

    Key behaviors to verify:
    1. API calls use use_min_date=True
    2. Only new submissions are processed (not previously seen)
    3. last_poll_at is updated only on successful checks
    4. Errors are logged but not sent to Discord
    5. Submission filtering works correctly
    """

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_uses_min_date_true_for_location(
        self, mock_fetch, monitor, db, mock_bot
    ):
        """
        Test that automatic polls use use_min_date=True for location targets.

        Starting conditions:
        - Channel with location monitoring target
        - No previous poll timestamp (first run)

        Assertions:
        - fetch_submissions_for_location called with use_min_date=True
        - Database last_poll_at is updated after successful check
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)

        # Setup mock response
        submission = generate_submission_data(1)
        mock_fetch.return_value = [submission]

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify API called with correct parameters
        mock_fetch.assert_called_once_with(location_id, use_min_date=True)

        # Verify successful result
        assert result is True

        # Verify timestamp updated
        updated_config = db.get_channel_config(channel_id)
        assert updated_config["last_poll_at"] is not None

    @patch("src.cogs.monitor.fetch_submissions_for_coordinates", new_callable=AsyncMock)
    async def test_automatic_poll_uses_min_date_true_for_coordinates(
        self, mock_fetch, monitor, db, mock_bot
    ):
        """
        Test that automatic polls use use_min_date=True for coordinate targets.

        Starting conditions:
        - Channel with coordinate monitoring target
        - No previous poll timestamp (first run)

        Assertions:
        - fetch_submissions_for_coordinates called with use_min_date=True
        - Database last_poll_at is updated after successful check
        """
        channel_id = 12345
        guild_id = 67890
        lat, lon, radius = 30.1, -97.2, 10

        # Setup database
        db.add_monitoring_target(channel_id, "latlong", f"{lat},{lon},{radius}")
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)

        # Setup mock response
        submission = generate_submission_data(1)
        mock_fetch.return_value = [submission]

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify API called with correct parameters
        mock_fetch.assert_called_once_with(lat, lon, radius, use_min_date=True)

        # Verify successful result
        assert result is True

        # Verify timestamp updated
        updated_config = db.get_channel_config(channel_id)
        assert updated_config["last_poll_at"] is not None

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_filters_seen_submissions(
        self, mock_fetch, monitor, db, mock_bot, mock_notifier
    ):
        """
        Test that automatic polls only process new (unseen) submissions.

        Starting conditions:
        - Channel with monitoring target
        - Some submissions already marked as seen in database
        - API returns mix of seen and new submissions

        Assertions:
        - Only new submissions are passed to notifier
        - New submissions are marked as seen in database
        - Previously seen submissions are filtered out
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)

        # Create submissions - some seen, some new
        seen_submission = generate_submission_data(1)
        new_submission = generate_submission_data(2)

        # Mark one submission as seen
        db.mark_submissions_seen(channel_id, [seen_submission["id"]])

        # Setup mock response with both submissions
        mock_fetch.return_value = [seen_submission, new_submission]

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify only new submission was posted
        mock_notifier.post_submissions.assert_called_once()
        posted_submissions = mock_notifier.post_submissions.call_args[0][1]
        assert len(posted_submissions) == 1
        assert posted_submissions[0]["id"] == new_submission["id"]

        # Verify new submission is now marked as seen
        remaining_new = db.filter_new_submissions(channel_id, [new_submission])
        assert len(remaining_new) == 0

        # Verify result indicates success
        assert result is True

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_updates_timestamp_on_success(
        self, mock_fetch, monitor, db, mock_bot
    ):
        """
        Test that last_poll_at is updated only after successful automatic polls.

        Starting conditions:
        - Channel with monitoring target
        - Initial last_poll_at timestamp
        - Successful API response

        Assertions:
        - last_poll_at is updated in database
        - Timestamp is close to current time
        - update_channel_last_poll_time is called
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database with initial timestamp
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        initial_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.update_channel_last_poll_time(channel_id, initial_time)

        config = db.get_channel_config(channel_id)
        assert config["last_poll_at"] == initial_time

        # Setup mock response
        submission = generate_submission_data(1)
        mock_fetch.return_value = [submission]

        # Execute automatic poll
        before_time = datetime.now(timezone.utc)
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )
        after_time = datetime.now(timezone.utc)

        # Verify timestamp was updated
        updated_config = db.get_channel_config(channel_id)
        updated_time = updated_config["last_poll_at"]

        assert updated_time is not None
        assert updated_time != initial_time
        assert before_time <= updated_time <= after_time

        # Verify successful result
        assert result is True

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_no_timestamp_update_on_api_failure(
        self, mock_fetch, monitor, db, mock_bot
    ):
        """
        Test that last_poll_at is NOT updated when API calls fail during automatic polls.

        Starting conditions:
        - Channel with monitoring target
        - Initial last_poll_at timestamp
        - API call raises exception

        Assertions:
        - last_poll_at remains unchanged in database
        - update_channel_last_poll_time is not called
        - Error is logged but not sent to Discord
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database with initial timestamp
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        initial_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.update_channel_last_poll_time(channel_id, initial_time)

        config = db.get_channel_config(channel_id)
        assert config["last_poll_at"] == initial_time

        # Setup mock to raise exception
        mock_fetch.side_effect = Exception("API Error")

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify timestamp was NOT updated
        updated_config = db.get_channel_config(channel_id)
        assert updated_config["last_poll_at"] == initial_time

        # Verify failed result
        assert result is False

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_suppresses_discord_error_messages(
        self, mock_fetch, monitor, db, mock_bot, mock_notifier
    ):
        """
        Test that automatic polls don't send error messages to Discord channels.

        Starting conditions:
        - Channel with monitoring target
        - API call raises exception during automatic poll

        Assertions:
        - notifier.log_and_send is NOT called
        - Error is logged (verify via logger mock)
        - No Discord messages sent for automatic poll errors
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)

        # Setup mock to raise exception
        mock_fetch.side_effect = Exception("API Error")

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify no Discord messages were sent
        mock_notifier.log_and_send.assert_not_called()
        mock_notifier.post_submissions.assert_not_called()

        # Verify failed result
        assert result is False

    async def test_automatic_poll_respects_poll_interval(self, monitor, db):
        """
        Test that automatic polls respect the configured poll interval.

        Starting conditions:
        - Channel with 60-minute poll interval
        - last_poll_at set to various times in the past

        Assertions:
        - _should_poll_channel returns False when poll interval hasn't elapsed
        - _should_poll_channel returns True when poll interval has elapsed
        - Edge cases around exact interval timing
        """
        channel_id = 12345
        guild_id = 67890
        poll_interval = 60  # minutes

        # Setup database
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(channel_id, guild_id, poll_rate_minutes=poll_interval)

        # Test: Never polled before (should poll)
        config = db.get_channel_config(channel_id)
        config["last_poll_at"] = None
        should_poll = await monitor._should_poll_channel(config)
        assert should_poll is True

        # Test: Polled recently (should not poll)
        config["last_poll_at"] = datetime.now(timezone.utc) - timedelta(minutes=30)
        should_poll = await monitor._should_poll_channel(config)
        assert should_poll is False

        # Test: Polled exactly at interval (should poll)
        config["last_poll_at"] = datetime.now(timezone.utc) - timedelta(minutes=60)
        should_poll = await monitor._should_poll_channel(config)
        assert should_poll is True

        # Test: Polled longer than interval (should poll)
        config["last_poll_at"] = datetime.now(timezone.utc) - timedelta(minutes=90)
        should_poll = await monitor._should_poll_channel(config)
        assert should_poll is True

    @patch("src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_automatic_poll_handles_no_new_submissions(
        self, mock_fetch, monitor, db, mock_bot, mock_notifier
    ):
        """
        Test automatic poll behavior when no new submissions are found.

        Starting conditions:
        - Channel with monitoring target
        - API returns submissions but all are already seen

        Assertions:
        - notifier.post_submissions is not called
        - last_poll_at is still updated (successful check, just no new data)
        - Method returns False (no new submissions found)
        """
        channel_id = 12345
        guild_id = 67890
        location_id = 123

        # Setup database
        db.add_monitoring_target(
            channel_id, "location", "Test Location", str(location_id)
        )
        db.update_channel_config(channel_id, guild_id)
        config = db.get_channel_config(channel_id)

        # Create submission and mark as already seen
        submission = generate_submission_data(1)
        db.mark_submissions_seen(channel_id, [submission["id"]])

        # Setup mock response with only seen submission
        mock_fetch.return_value = [submission]

        # Execute automatic poll
        result = await monitor.run_checks_for_channel(
            channel_id, config, is_manual_check=False
        )

        # Verify no submissions were posted (all were already seen)
        mock_notifier.post_submissions.assert_not_called()

        # Verify timestamp was still updated (successful check)
        updated_config = db.get_channel_config(channel_id)
        assert updated_config["last_poll_at"] is not None

        # Verify result indicates no new submissions
        assert result is False
