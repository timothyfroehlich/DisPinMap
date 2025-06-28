"""
Tests for config cog module
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.cogs.config import ConfigCog
from src.database import Database
from src.notifier import Notifier


class TestConfigCog:
    """Test the ConfigCog class"""

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
        return notifier

    @pytest.fixture
    def config_cog(self, mock_bot, mock_db, mock_notifier):
        """Create a ConfigCog instance"""
        return ConfigCog(mock_bot, mock_db, mock_notifier)

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
        self, config_cog, mock_ctx, mock_db, mock_notifier
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
        await config_cog.poll_rate.callback(config_cog, mock_ctx, "10")

        # Should update channel config
        mock_db.update_channel_config.assert_called_with(
            123456, 789012, poll_rate_minutes=10
        )
        # Should update monitoring targets that match channel config
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", poll_rate_minutes=10
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_target_success(
        self, config_cog, mock_ctx, mock_db, mock_notifier
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
        await config_cog.poll_rate.callback(config_cog, mock_ctx, "15", "1")

        # Should update specific target
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", poll_rate_minutes=15
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_rate(self, config_cog, mock_ctx, mock_notifier):
        """Test setting poll rate with invalid rate"""
        # Call the underlying callback function directly
        await config_cog.poll_rate.callback(config_cog, mock_ctx, "0")

        # Should send invalid rate message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_target_index(
        self, config_cog, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting poll rate with invalid target index"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call the underlying callback function directly
        await config_cog.poll_rate.callback(
            config_cog, mock_ctx, "10", "2"
        )  # Index 2 when only 1 target exists

        # Should send invalid index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_target_selector(
        self, config_cog, mock_ctx, mock_notifier
    ):
        """Test setting poll rate with invalid target selector"""
        # Call the underlying callback function directly
        await config_cog.poll_rate.callback(config_cog, mock_ctx, "10", "invalid")

        # Should send invalid target index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_rate_invalid_minutes(self, config_cog, mock_ctx, mock_notifier):
        """Test setting poll rate with invalid minutes value"""
        # Call the underlying callback function directly
        await config_cog.poll_rate.callback(config_cog, mock_ctx, "invalid")

        # Should send error message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_channel_success(
        self, config_cog, mock_ctx, mock_db, mock_notifier
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
        await config_cog.notifications.callback(config_cog, mock_ctx, "machines")

        # Should update channel config
        mock_db.update_channel_config.assert_called_with(
            123456, 789012, notification_types="machines"
        )
        # Should update monitoring targets that match channel config
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", notification_types="machines"
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_target_success(
        self, config_cog, mock_ctx, mock_db, mock_notifier
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
        await config_cog.notifications.callback(config_cog, mock_ctx, "comments", "1")

        # Should update specific target
        mock_db.update_monitoring_target.assert_called_with(
            123456, "location", "Test Location", notification_types="comments"
        )
        # Should send success message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_invalid_type(
        self, config_cog, mock_ctx, mock_notifier
    ):
        """Test setting notification type with invalid type"""
        # Call the underlying callback function directly
        await config_cog.notifications.callback(config_cog, mock_ctx, "invalid_type")

        # Should send error message with valid types
        mock_notifier.log_and_send.assert_called_once()
        call_args = mock_notifier.log_and_send.call_args[0]
        assert "machines, comments, all" in call_args[1]

    @pytest.mark.asyncio
    async def test_notifications_invalid_target_index(
        self, config_cog, mock_ctx, mock_db, mock_notifier
    ):
        """Test setting notification type with invalid target index"""
        mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call the underlying callback function directly
        await config_cog.notifications.callback(
            config_cog, mock_ctx, "machines", "2"
        )  # Index 2 when only 1 target exists

        # Should send invalid index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_invalid_target_selector(
        self, config_cog, mock_ctx, mock_notifier
    ):
        """Test setting notification type with invalid target selector"""
        # Call the underlying callback function directly
        await config_cog.notifications.callback(
            config_cog, mock_ctx, "machines", "invalid"
        )

        # Should send invalid target index message
        mock_notifier.log_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_all_valid_types(
        self, config_cog, mock_ctx, mock_db, mock_notifier
    ):
        """Test all valid notification types"""
        mock_db.get_monitoring_targets.return_value = []

        valid_types = ["machines", "comments", "all"]

        for notification_type in valid_types:
            mock_db.reset_mock()
            mock_notifier.log_and_send.reset_mock()

            # Call the underlying callback function directly
            await config_cog.notifications.callback(
                config_cog, mock_ctx, notification_type
            )

            # Should update channel config with valid type
            mock_db.update_channel_config.assert_called_with(
                123456, 789012, notification_types=notification_type
            )
            # Should send success message
            mock_notifier.log_and_send.assert_called_once()


class TestConfigCogSetup:
    """Test the setup function for ConfigCog"""

    @pytest.mark.asyncio
    async def test_setup_success(self):
        """Test successful setup of ConfigCog"""
        from src.cogs.config import setup

        mock_bot = Mock()
        mock_bot.database = Mock()
        mock_bot.notifier = Mock()
        mock_bot.add_cog = AsyncMock()

        await setup(mock_bot)

        # Should add the cog
        mock_bot.add_cog.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_missing_database(self):
        """Test setup with missing database"""
        from src.cogs.config import setup

        mock_bot = Mock()
        mock_bot.database = None
        mock_bot.notifier = Mock()

        with pytest.raises(
            RuntimeError, match="Database and Notifier must be initialized"
        ):
            await setup(mock_bot)

    @pytest.mark.asyncio
    async def test_setup_missing_notifier(self):
        """Test setup with missing notifier"""
        from src.cogs.config import setup

        mock_bot = Mock()
        mock_bot.database = Mock()
        mock_bot.notifier = None

        with pytest.raises(
            RuntimeError, match="Database and Notifier must be initialized"
        ):
            await setup(mock_bot)

    @pytest.mark.asyncio
    async def test_setup_missing_both(self):
        """Test setup with missing both database and notifier"""
        from src.cogs.config import setup

        mock_bot = Mock()
        mock_bot.database = None
        mock_bot.notifier = None

        with pytest.raises(
            RuntimeError, match="Database and Notifier must be initialized"
        ):
            await setup(mock_bot)
