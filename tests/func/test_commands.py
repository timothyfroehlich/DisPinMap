"""
Functional tests for command handlers
Tests the full command flow from user input to bot response
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.cogs.monitoring import MonitoringCog
from src.cogs.config import ConfigCog
from src.database import Database
from src.notifier import Notifier
from tests.utils import MockContext, assert_discord_message, verify_database_target
from tests.utils.database import setup_test_database, cleanup_test_database
from src.messages import Messages


@pytest.fixture
def db():
    """Create test database"""
    test_db = setup_test_database()
    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def notifier(db):
    """Create notifier instance"""
    return Notifier(db)


@pytest.fixture
def monitoring_cog(db, notifier):
    """Create monitoring cog with test database"""
    bot = MagicMock()
    return MonitoringCog(bot, db, notifier)


@pytest.fixture
def config_cog(db, notifier):
    """Create config cog with test database"""
    bot = MagicMock()
    return ConfigCog(bot, db, notifier)


@pytest.fixture
def mock_bot():
    """Create mock bot instance"""
    return MagicMock()


@pytest.fixture
def mock_notifier():
    """Create mock notifier instance"""
    return AsyncMock()


class TestAddCommand:
    @pytest.mark.asyncio
    async def test_add_location_by_id(self, monitoring_cog, db):
        """Test adding a location by ID"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!add location 123"

        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

            # Verify API was called
            mock_get.assert_called_once_with(123)
            # Verify user got success message
            await assert_discord_message(ctx, Messages.Notification.Initial.NONE.format(
                target_type="location **Test Location** (ID: 123)"
            ))
            # Verify database was updated
            verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_add_location_by_name(self, monitoring_cog, db):
        """Test adding a location by name"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!add location Test Location"

        with patch('src.cogs.monitoring.search_location_by_name', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                'status': 'exact',
                'data': {
                    'id': 123,
                    'name': 'Test Location',
                    'lat': 30.0,
                    'lon': 97.0
                }
            }
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "Test Location")

            # Verify API was called
            mock_search.assert_called_once_with("Test Location")
            # Verify user got success message
            await assert_discord_message(ctx, Messages.Notification.Initial.NONE.format(
                target_type="location **Test Location** (ID: 123)"
            ))
            # Verify database was updated
            verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_add_coordinates(self, monitoring_cog, db):
        """Test adding coordinates"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!add coordinates 30.0 97.0 10"

        await monitoring_cog.add.callback(monitoring_cog, ctx, "coordinates", "30.0", "97.0", "10")

        # Verify user got success message
        await assert_discord_message(ctx, Messages.Notification.Initial.NONE.format(
            target_type="coordinates **30.0, 97.0**"
        ))
        # Verify database was updated
        verify_database_target(db, ctx.channel.id, 1, 'latlong')

    @pytest.mark.asyncio
    async def test_add_city(self, monitoring_cog, db):
        """Test adding a city"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!add city Austin,TX"

        with patch('src.cogs.monitoring.geocode_city_name', new_callable=AsyncMock) as mock_geocode, \
             patch('src.cogs.monitoring.fetch_submissions_for_coordinates', new_callable=AsyncMock) as mock_fetch:
            mock_geocode.return_value = {
                'status': 'success',
                'lat': 30.2672,
                'lon': -97.7431,
                'display_name': 'Austin, Texas, US'
            }
            mock_fetch.return_value = []
            await monitoring_cog.add.callback(monitoring_cog, ctx, "city", "Austin,TX")

            # Verify API was called
            mock_geocode.assert_called_once_with("Austin,TX")
            # Verify user got initial message (success message was removed as redundant)
            await assert_discord_message(ctx, Messages.Notification.Initial.NONE.format(
                target_type="city **Austin, Texas, US**"
            ))
            # Verify database was updated
            verify_database_target(db, ctx.channel.id, 1, 'city')

    @pytest.mark.asyncio
    async def test_add_invalid_type(self, monitoring_cog, db):
        """Test adding with invalid target type"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!add invalid_type test"

        await monitoring_cog.add.callback(monitoring_cog, ctx, "invalid_type", "test")

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.Add.INVALID_TYPE)
        # Verify database was not updated
        verify_database_target(db, ctx.channel.id, 0)


class TestRemoveCommand:
    @pytest.mark.asyncio
    async def test_remove_by_index(self, monitoring_cog, db):
        """Test removing a target by index"""
        ctx = MockContext(12345, 67890)

        # Add a target first
        db.add_monitoring_target(ctx.channel.id, 'location', '123')

        ctx.message.content = "!rm 1"
        await monitoring_cog.remove.callback(monitoring_cog, ctx, 1)

        # Verify user got success message
        await assert_discord_message(ctx, "Removed location:")
        # Verify database was updated
        verify_database_target(db, ctx.channel.id, 0)

    @pytest.mark.asyncio
    async def test_remove_invalid_index(self, monitoring_cog, db):
        """Test removing with invalid index"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!rm 999"

        await monitoring_cog.remove.callback(monitoring_cog, ctx, 999)

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.Remove.NO_TARGETS)
        # Verify database was not changed
        verify_database_target(db, ctx.channel.id, 0)

    @pytest.mark.asyncio
    async def test_remove_no_targets(self, monitoring_cog, db):
        """Test removing when no targets exist"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!rm 1"

        await monitoring_cog.remove.callback(monitoring_cog, ctx, 1)

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.Remove.NO_TARGETS)


class TestListCommand:
    @pytest.mark.asyncio
    async def test_list_targets(self, monitoring_cog, db):
        """Test listing targets in the new table format."""
        ctx = MockContext(12345, 67890)
        db.update_channel_config(ctx.channel.id, ctx.guild.id, poll_rate_minutes=60, notification_types='machines')

        # Add some targets
        db.add_monitoring_target(ctx.channel.id, 'location', 'Test Location', '123')
        db.add_monitoring_target(ctx.channel.id, 'latlong', '30.0,-97.0,10')

        ctx.message.content = "!list"
        await monitoring_cog.list_targets.callback(monitoring_cog, ctx)

        # Verify the response is a formatted code block table
        response = ctx.sent_messages[0]
        assert response.startswith("```")
        assert response.endswith("```")

        # Verify headers
        assert "Index" in response
        assert "Target" in response
        assert "Poll (min)" in response
        assert "Notifications" in response
        assert "Last Checked" in response

        # Verify content
        assert "1" in response
        assert "Location: Test Location" in response
        assert "2" in response
        assert "Coords: 30.0, -97.0" in response
        assert "60" in response # Default poll rate
        assert "machines" in response # Default notifications
        assert "Never" in response # Should not have been checked

    @pytest.mark.asyncio
    async def test_list_empty(self, monitoring_cog, db):
        """Test listing when no targets exist"""
        ctx = MockContext(12345, 67890)
        ctx.message.content = "!list"
        await monitoring_cog.list_targets.callback(monitoring_cog, ctx)
        await assert_discord_message(ctx, Messages.Command.List.NO_TARGETS)


class TestExportCommand:
    @pytest.mark.asyncio
    async def test_export_targets(self, monitoring_cog, db):
        """Test exporting targets"""
        ctx = MockContext(12345, 67890)

        # Add some targets
        db.add_monitoring_target(ctx.channel.id, 'location', '123')
        db.add_monitoring_target(ctx.channel.id, 'latlong', '30.0,97.0,10')

        ctx.message.content = "!export"
        await monitoring_cog.export.callback(monitoring_cog, ctx)

        # Verify user got export message
        await assert_discord_message(ctx, "**Export Commands:**")

    @pytest.mark.asyncio
    async def test_export_empty(self, monitoring_cog, db):
        """Test exporting when no targets exist"""
        ctx = MockContext(12345, 67890)

        ctx.message.content = "!export"
        await monitoring_cog.export.callback(monitoring_cog, ctx)

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.Export.NO_TARGETS)


class TestPollRateCommand:
    @pytest.mark.asyncio
    async def test_set_poll_rate_target(self, config_cog, db):
        """Test setting poll rate for specific target"""
        ctx = MockContext(12345, 67890)

        # Add a target first
        db.add_monitoring_target(ctx.channel.id, 'location', '123')

        ctx.message.content = "!poll_rate 5 1"
        await config_cog.poll_rate.callback(config_cog, ctx, 5, "1")

        # Verify user got success message
        await assert_discord_message(ctx, Messages.Command.PollRate.SUCCESS_TARGET.format(
            minutes=5,
            target_id=1
        ))

    @pytest.mark.asyncio
    async def test_set_poll_rate_channel(self, config_cog, db):
        """Test setting poll rate for channel"""
        ctx = MockContext(12345, 67890)

        ctx.message.content = "!poll_rate 5"
        await config_cog.poll_rate.callback(config_cog, ctx, 5)

        # Verify user got success message
        await assert_discord_message(ctx, Messages.Command.PollRate.SUCCESS_CHANNEL.format(minutes=5))

    @pytest.mark.asyncio
    async def test_set_poll_rate_invalid(self, config_cog, db):
        """Test setting invalid poll rate"""
        ctx = MockContext(12345, 67890)

        ctx.message.content = "!poll_rate 0"
        await config_cog.poll_rate.callback(config_cog, ctx, 0)

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.PollRate.INVALID_RATE)


class TestNotificationsCommand:
    @pytest.mark.asyncio
    async def test_set_notifications_target(self, config_cog, db):
        """Test setting notifications for specific target"""
        ctx = MockContext(12345, 67890)

        # Add a target first
        db.add_monitoring_target(ctx.channel.id, 'location', '123')

        ctx.message.content = "!notifications machines 1"
        await config_cog.notifications.callback(config_cog, ctx, "machines", "1")

        # Verify user got success message
        await assert_discord_message(ctx, Messages.Command.Notifications.SUCCESS_TARGET.format(
            notification_type="machines",
            target_id=1
        ))

    @pytest.mark.asyncio
    async def test_set_notifications_channel(self, config_cog, db):
        """Test setting notifications for channel"""
        ctx = MockContext(12345, 67890)

        ctx.message.content = "!notifications machines"
        await config_cog.notifications.callback(config_cog, ctx, "machines")

        # Verify user got success message
        await assert_discord_message(ctx, Messages.Command.Notifications.SUCCESS_CHANNEL.format(notification_type="machines"))

    @pytest.mark.asyncio
    async def test_set_notifications_invalid(self, config_cog, db):
        """Test setting invalid notification type"""
        ctx = MockContext(12345, 67890)

        ctx.message.content = "!notifications invalid"
        await config_cog.notifications.callback(config_cog, ctx, "invalid")

        # Verify user got error message
        await assert_discord_message(ctx, Messages.Command.Notifications.ERROR.format(valid_types="machines, comments, all"))


class TestCheckCommand:
    @pytest.mark.asyncio
    async def test_check_command_with_targets(self, monitoring_cog, db):
        """Test check command with valid targets"""
        ctx = MockContext(12345, 67890)

        # Add a monitoring target
        db.add_monitoring_target(ctx.channel.id, 'location', 'Test Location', '123')

        # Create a mock monitor cog
        mock_monitor_cog = AsyncMock()
        mock_monitor_cog.run_checks_for_channel = AsyncMock(return_value=True)
        monitoring_cog.bot.get_cog = MagicMock(return_value=mock_monitor_cog)

        ctx.message.content = "!check"
        await monitoring_cog.check.callback(monitoring_cog, ctx)

        # Verify monitor cog was called with correct parameters
        monitoring_cog.bot.get_cog.assert_called_with('MachineMonitor')
        mock_monitor_cog.run_checks_for_channel.assert_called_once()

        # Verify the call arguments
        call_args = mock_monitor_cog.run_checks_for_channel.call_args
        assert call_args[0][0] == ctx.channel.id  # channel_id
        assert call_args[1]['is_manual_check'] == True  # is_manual_check parameter

    @pytest.mark.asyncio
    async def test_check_command_no_monitor_cog(self, monitoring_cog, db):
        """Test check command when monitor cog is not found"""
        ctx = MockContext(12345, 67890)

        # Mock bot to return None for monitor cog
        monitoring_cog.bot.get_cog = MagicMock(return_value=None)

        ctx.message.content = "!check"
        await monitoring_cog.check.callback(monitoring_cog, ctx)

        # Verify error message was sent
        await assert_discord_message(ctx, "Error: Could not find the monitor.")

    @pytest.mark.asyncio
    async def test_check_command_no_targets(self, monitoring_cog, db):
        """Test check command when no targets are configured"""
        ctx = MockContext(12345, 67890)

        # Create a mock monitor cog
        mock_monitor_cog = AsyncMock()
        mock_monitor_cog.run_checks_for_channel = AsyncMock(return_value=False)
        monitoring_cog.bot.get_cog = MagicMock(return_value=mock_monitor_cog)

        # Don't add any targets to the database

        ctx.message.content = "!check"
        await monitoring_cog.check.callback(monitoring_cog, ctx)

        # Verify monitor cog was called
        mock_monitor_cog.run_checks_for_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_command_with_exception(self, monitoring_cog, db):
        """Test check command when monitor cog raises an exception"""
        ctx = MockContext(12345, 67890)

        # Add a monitoring target
        db.add_monitoring_target(ctx.channel.id, 'location', 'Test Location', '123')

        # Create a mock monitor cog that raises an exception
        mock_monitor_cog = AsyncMock()
        mock_monitor_cog.run_checks_for_channel = AsyncMock(side_effect=Exception("Test error"))
        monitoring_cog.bot.get_cog = MagicMock(return_value=mock_monitor_cog)

        ctx.message.content = "!check"
        # The exception should bubble up from the monitor cog since it's not handled in the check command
        with pytest.raises(Exception, match="Test error"):
            await monitoring_cog.check.callback(monitoring_cog, ctx)

        # Verify monitor cog was called despite the exception
        mock_monitor_cog.run_checks_for_channel.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_check_command_integration_with_real_monitor(self, monitoring_cog, db, mock_notifier):
        """Integration test for check command with real monitor cog"""
        from src.cogs.monitor import MachineMonitor

        ctx = MockContext(12345, 67890)

        # Create a real monitor cog
        mock_bot = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.id = ctx.channel.id
        mock_bot.get_channel.return_value = mock_channel

        monitor_cog = MachineMonitor(mock_bot, db, mock_notifier)

        # Add the monitor cog to the bot
        monitoring_cog.bot.get_cog = MagicMock(return_value=monitor_cog)

        # Add a monitoring target for Austin (a city that should have recent activity)
        db.add_monitoring_target(ctx.channel.id, 'city', 'Austin, TX', '30.2672,-97.7431,25')

        ctx.message.content = "!check"
        await monitoring_cog.check.callback(monitoring_cog, ctx)

        # The actual behavior will depend on real API data, but we can verify:
        # 1. The monitor cog was called
        monitoring_cog.bot.get_cog.assert_called_with('MachineMonitor')

        # 2. Some interaction with the notifier occurred (success or no results message)
        assert mock_notifier.log_and_send.call_count > 0 or mock_notifier.post_submissions.call_count > 0


class MockContext:
    def __init__(self, channel_id, guild_id):
        self.channel = type('Channel', (), {'id': channel_id})()
        self.guild = type('Guild', (), {'id': guild_id})()
        self.message = type('Message', (), {'content': ''})()
        self.sent_messages = []
        self.send = AsyncMock(side_effect=self._record_send)

    async def _record_send(self, message: str):
        self.sent_messages.append(message)
