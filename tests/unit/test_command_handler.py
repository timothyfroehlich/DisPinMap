"""
Tests for CommandHandler cog module
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.cogs.command_handler import CommandHandler
from src.database import Database
from src.messages import Messages
from src.notifier import Notifier


class TestCommandHandler:
    """Test the CommandHandler class"""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot"""
        return Mock()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        return Mock(spec=Database)

    @pytest.fixture
    def mock_notifier(self):
        """Create a mock notifier"""
        notifier = Mock(spec=Notifier)
        notifier.log_and_send = AsyncMock()
        notifier.send_initial_notifications = AsyncMock()
        return notifier

    @pytest.fixture
    def command_handler(self, mock_bot, mock_db, mock_notifier):
        """Create a CommandHandler instance"""
        return CommandHandler(mock_bot, mock_db, mock_notifier)

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Discord context"""
        ctx = Mock()
        ctx.send = AsyncMock()
        ctx.channel.id = 123456
        ctx.guild.id = 789012
        return ctx

    @pytest.mark.asyncio
    async def test_poll_rate_channel_success(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting poll rate for channel successfully"""
        mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Test Location",
                "poll_rate_minutes": 5,
            }
        ]
        mock_db.get_channel_config.return_value = {"poll_rate_minutes": 5}

        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(command_handler, mock_ctx, "10")

        # Should update channel config
        mock_db.update_channel_config.assert_called_with(
            123456, 789012, poll_rate_minutes=10
        )
        # Should NOT update monitoring targets directly anymore
        mock_db.update_monitoring_target.assert_not_called()
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_target_success(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting poll rate for specific target successfully"""
        mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Test Location",
                "poll_rate_minutes": 5,
            }
        ]

        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(command_handler, mock_ctx, "15", "1")

        # Should update specific target
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", poll_rate_minutes=15
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_rate(
        self, command_handler, mock_ctx, mock_notifier
    ):
        """Test setting poll rate with invalid rate"""
        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(command_handler, mock_ctx, "0")

        # Should send invalid rate message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_target_index(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting poll rate with invalid target index"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(
            command_handler, mock_ctx, "10", "2"
        )  # Index 2 when only 1 target exists

        # Should send invalid index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_target_selector(
        self, command_handler, mock_ctx, mock_notifier
    ):
        """Test setting poll rate with invalid target selector"""
        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(
            command_handler, mock_ctx, "10", "invalid"
        )

        # Should send invalid target index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_minutes(
        self, command_handler, mock_ctx, mock_notifier
    ):
        """Test setting poll rate with invalid minutes value"""
        # Call the underlying callback function directly
        await command_handler.poll_rate.callback(command_handler, mock_ctx, "invalid")

        # Should send error message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_channel_success(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting notification type for channel successfully"""
        mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Test Location",
                "notification_types": "all",
            }
        ]
        mock_db.get_channel_config.return_value = {"notification_types": "all"}

        # Call the underlying callback function directly
        await command_handler.notifications.callback(
            command_handler, mock_ctx, "machines"
        )

        # Should update channel config
        mock_db.update_channel_config.assert_called_with(
            123456, 789012, notification_types="machines"
        )
        # Should NOT update monitoring targets directly anymore
        mock_db.update_monitoring_target.assert_not_called()
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_target_success(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting notification type for specific target successfully"""
        mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Test Location",
                "notification_types": "all",
            }
        ]

        # Call the underlying callback function directly
        await command_handler.notifications.callback(
            command_handler, mock_ctx, "comments", "1"
        )

        # Should update specific target
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", notification_types="comments"
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_invalid_type(
        self, command_handler, mock_ctx, mock_notifier
    ):
        """Test setting notification type with invalid type"""
        # Call the underlying callback function directly
        await command_handler.notifications.callback(
            command_handler, mock_ctx, "invalid_type"
        )

        # Should send error message with valid types
        mock_notifier.log_and_send.assert_called_once()
        call_args = mock_notifier.log_and_send.call_args[0]
        assert "machines, comments, all" in call_args[1]

    @pytest.mark.asyncio
    async def test_notifications_invalid_target_index(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting notification type with invalid target index"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call the underlying callback function directly
        await command_handler.notifications.callback(
            command_handler, mock_ctx, "machines", "2"
        )  # Index 2 when only 1 target exists

        # Should send invalid index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_invalid_target_selector(
        self, command_handler, mock_ctx, mock_notifier
    ):
        """Test setting notification type with invalid target selector"""
        # Call the underlying callback function directly
        await command_handler.notifications.callback(
            command_handler, mock_ctx, "machines", "invalid"
        )

        # Should send invalid target index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_all_valid_types(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test all valid notification types"""
        mock_db.get_monitoring_targets.return_value = []

        valid_types = ["machines", "comments", "all"]

        for notification_type in valid_types:
            mock_db.reset_mock()
            mock_notifier.log_and_send.reset_mock()

            # Call the underlying callback function directly
            await command_handler.notifications.callback(
                command_handler, mock_ctx, notification_type
            )

            # Should update channel config
            mock_db.update_channel_config.assert_called_with(
                123456, 789012, notification_types=notification_type
            )
            # Should send success message
            mock_notifier.log_and_send.assert_called_once()


# region Merged from test_commands_parsing.py
class TestAddCommand(TestCommandHandler):
    """Test parsing of add command arguments"""

    @pytest.mark.asyncio
    async def test_add_location_by_id(
        self, command_handler, mock_ctx, mock_notifier, api_mocker
    ):
        """Test parsing location by ID using a real fixture."""
        # 1. SETUP
        # Test that location ID is correctly identified
        location_input = "874"  # Use an ID that has a corresponding fixture

        # Configure the API mocker to serve the location details from a fixture
        api_mocker.add_response(
            url_substring="locations/874.json",
            json_fixture_path="pinballmap_locations/location_874_details.json",
        )

        # 2. ACTION
        await command_handler.add.callback(
            command_handler, mock_ctx, "location", location_input
        )

        # 3. ASSERT
        # Verify the correct handler was called and a notification was sent
        mock_notifier.send_initial_notifications.assert_called_once()


class TestRemoveCommand(TestCommandHandler):
    """Test parsing of remove command arguments"""

    @pytest.mark.asyncio
    async def test_remove_valid_index(self, command_handler, mock_ctx, mock_db):
        """Test parsing valid index for remove command"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        await command_handler.remove.callback(command_handler, mock_ctx, index="1")

        mock_db.remove_monitoring_target.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_invalid_index(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test parsing invalid index for remove command"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        await command_handler.remove.callback(command_handler, mock_ctx, index="2")

        mock_notifier.log_and_send.assert_called_once()
        call_args = mock_notifier.log_and_send.call_args[0]
        assert "Invalid index" in call_args[1]


class TestListCommand(TestCommandHandler):
    """Test parsing of list command arguments"""

    @pytest.mark.asyncio
    async def test_list_no_targets(self, command_handler, mock_ctx, mock_notifier):
        """Test list command when no targets exist"""
        command_handler.db.get_monitoring_targets.return_value = []

        await command_handler.list_targets.callback(command_handler, mock_ctx)

        mock_notifier.log_and_send.assert_called_with(
            mock_ctx, Messages.Command.Shared.NO_TARGETS
        )


class TestExportCommand(TestCommandHandler):
    """Test parsing of export command arguments"""

    @pytest.mark.asyncio
    async def test_export_with_targets(
        self, command_handler, mock_ctx, mock_db, mock_notifier
    ):
        """Test export command with existing targets"""
        mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Ground Kontrol Classic Arcade",
                "location_id": 874,
                "poll_rate_minutes": 15,
                "notification_types": "machines",
            }
        ]
        mock_db.get_channel_config.return_value = {
            "poll_rate_minutes": 30,
            "notification_types": "all",
        }

        await command_handler.export.callback(command_handler, mock_ctx)

        mock_notifier.log_and_send.assert_called_once()
        call_args = mock_notifier.log_and_send.call_args[0]

        # Should contain the location ID, not the name
        assert "!add location 874" in call_args[1]

        # Should contain channel default poll rate
        assert "!poll_rate 30" in call_args[1]

        # Should contain per-target overrides
        assert "!poll_rate 15 1" in call_args[1]


class TestCheckCommand(TestCommandHandler):
    """Test parsing of check command arguments"""

    @pytest.mark.asyncio
    async def test_check_command(self, command_handler, mock_ctx, mock_bot):
        """Test check command parsing"""
        mock_runner_cog = Mock()
        mock_runner_cog.run_checks_for_channel = AsyncMock()
        mock_bot.get_cog.return_value = mock_runner_cog
        command_handler.db.get_channel_config.return_value = {"id": 123}

        await command_handler.check.callback(command_handler, mock_ctx)

        mock_bot.get_cog.assert_called_with("Runner")
        mock_runner_cog.run_checks_for_channel.assert_called_once()


# endregion
