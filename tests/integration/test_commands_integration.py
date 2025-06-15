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
def monitoring_cog(db, notifier):
    """Create monitoring cog with test database"""
    bot = MagicMock()
    return MonitoringCog(bot, db, notifier)


@pytest.fixture
def config_cog(db, notifier):
    """Create config cog with test database"""
    bot = MagicMock()
    return ConfigCog(bot, db, notifier)


class TestMonitoringAndConfigIntegration:
    @pytest.mark.asyncio
    async def test_add_and_configure_target(self, monitoring_cog, config_cog, db):
        """Test adding a target and configuring it"""
        ctx = MockContext(12345, 67890)

        # Add a location
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add(ctx, "location", "123")

        # Configure poll rate
        ctx.message.content = "!poll_rate 5 1"
        await config_cog.poll_rate(ctx, "5", "1")

        # Configure notifications
        ctx.message.content = "!notifications machines 1"
        await config_cog.notifications(ctx, "machines", "1")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_add_multiple_and_configure(self, monitoring_cog, config_cog, db):
        """Test adding multiple targets and configuring them"""
        ctx = MockContext(12345, 67890)

        # Add a location
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add(ctx, "location", "123")

        # Add coordinates
        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add(ctx, "coordinates", "30.0", "97.0", "10")

        # Configure channel poll rate
        ctx.message.content = "!poll_rate 10"
        await config_cog.poll_rate(ctx, "10")

        # Configure channel notifications
        ctx.message.content = "!notifications all"
        await config_cog.notifications(ctx, "all")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 2)

    @pytest.mark.asyncio
    async def test_remove_and_reconfigure(self, monitoring_cog, config_cog, db):
        """Test removing a target and reconfiguring remaining ones"""
        ctx = MockContext(12345, 67890)

        # Add two locations
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location 1',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add(ctx, "location", "123")

            mock_get.return_value = {
                'id': 456,
                'name': 'Test Location 2',
                'lat': 30.1,
                'lon': 97.1
            }
            ctx.message.content = "!add location 456"
            await monitoring_cog.add(ctx, "location", "456")

        # Remove first target
        ctx.message.content = "!rm 1"
        await monitoring_cog.remove(ctx, "1")

        # Configure remaining target
        ctx.message.content = "!poll_rate 15 1"
        await config_cog.poll_rate(ctx, "15", "1")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 1, 'location')

    @pytest.mark.asyncio
    async def test_export_and_reimport(self, monitoring_cog, db):
        """Test exporting targets and reimporting them"""
        ctx = MockContext(12345, 67890)

        # Add some targets
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add(ctx, "location", "123")

        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add(ctx, "coordinates", "30.0", "97.0", "10")

        # Export targets
        ctx.message.content = "!export"
        await monitoring_cog.export(ctx)

        # Clear database
        db.clear_channel_targets(ctx.channel.id)

        # Reimport targets using export commands
        with patch('src.cogs.monitoring.fetch_location_details', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                'id': 123,
                'name': 'Test Location',
                'lat': 30.0,
                'lon': 97.0
            }
            ctx.message.content = "!add location 123"
            await monitoring_cog.add(ctx, "location", "123")

        ctx.message.content = "!add coordinates 30.0 97.0 10"
        await monitoring_cog.add(ctx, "coordinates", "30.0", "97.0", "10")

        # Verify database state
        verify_database_target(db, ctx.channel.id, 2)
