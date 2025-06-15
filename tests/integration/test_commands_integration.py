"""
Integration tests for command handlers
Tests the interaction between different components
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
def notifier():
    """Create notifier instance"""
    return Notifier()


@pytest.fixture
def bot(db, notifier):
    """Create a mock bot with shared db and notifier"""
    b = MagicMock()
    b.database = db
    b.notifier = notifier
    return b


@pytest.fixture
def monitoring_cog(bot):
    """Create monitoring cog with test database"""
    return MonitoringCog(bot, bot.database, bot.notifier)


@pytest.fixture
def config_cog(bot):
    """Create config cog with test database"""
    return ConfigCog(bot, bot.database, bot.notifier)


class TestMonitoringAndConfigIntegration:
    @pytest.mark.asyncio
    async def test_add_and_configure_target(self, monitoring_cog, config_cog, db, bot):
        """Test adding a target and configuring it"""
        ctx = MockContext(12345, 67890, bot=bot)
        monitoring_cog.bot.get_cog.return_value = config_cog
        config_cog.bot.get_cog.return_value = monitoring_cog

        # Add a location
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

        # Configure poll rate
        ctx.message.content = "!poll_rate 5 1"
        await config_cog.poll_rate.callback(config_cog, ctx, "5", "1")

        # Configure notifications
        ctx.message.content = "!notifications machines 1"
        await config_cog.notifications.callback(config_cog, ctx, "machines", "1")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_add_multiple_and_configure(self, monitoring_cog, config_cog, db, bot):
        """Test adding multiple targets and configuring them"""
        ctx = MockContext(12345, 67890, bot=bot)
        monitoring_cog.bot.get_cog.return_value = config_cog
        config_cog.bot.get_cog.return_value = monitoring_cog

        # Add a location
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

        # Add coordinates
        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add.callback(monitoring_cog, ctx, "coordinates", "30.0", "97.0", "10")

        # Configure channel poll rate
        ctx.message.content = "!poll_rate 10"
        await config_cog.poll_rate.callback(config_cog, ctx, "10")

        # Configure channel notifications
        ctx.message.content = "!notifications all"
        await config_cog.notifications.callback(config_cog, ctx, "all")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 2)

    @pytest.mark.asyncio
    async def test_remove_and_reconfigure(self, monitoring_cog, config_cog, db, bot):
        """Test removing a target and reconfiguring remaining ones"""
        ctx = MockContext(12345, 67890, bot=bot)
        monitoring_cog.bot.get_cog.return_value = config_cog
        config_cog.bot.get_cog.return_value = monitoring_cog

        # Add two locations
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location 1',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

            mock_get.return_value = {
                'id': 456,
                'name': 'Test Location 2',
                'lat': 30.1,
                'lon': 97.1
            }
            ctx.message.content = "!add location 456"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "456")

        # Remove first target
        ctx.message.content = "!rm 1"
        await monitoring_cog.remove.callback(monitoring_cog, ctx, 1)

        # Configure remaining target
        ctx.message.content = "!poll_rate 15 1"
        await config_cog.poll_rate.callback(config_cog, ctx, "15", "1")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_export_and_reimport(self, monitoring_cog, db, bot):
        """Test exporting targets and reimporting them"""
        ctx = MockContext(12345, 67890, bot=bot)
        monitoring_cog.bot.get_cog.return_value = monitoring_cog

        # Add some targets
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add.callback(monitoring_cog, ctx, "coordinates", "30.0", "97.0", "10")

        # Export targets
        ctx.message.content = "!export"
        await monitoring_cog.export.callback(monitoring_cog, ctx)

        # Clear database
        db.clear_monitoring_targets(ctx.channel.id)

        # Reimport targets using export commands
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add.callback(monitoring_cog, ctx, "location", "123")

        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add.callback(monitoring_cog, ctx, "coordinates", "30.0", "97.0", "10")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 2)
