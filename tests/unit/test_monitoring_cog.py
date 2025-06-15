import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.cogs.monitoring import MonitoringCog

@pytest.fixture
def mock_db():
    """Fixture for a mock database."""
    return MagicMock()

@pytest.fixture
def mock_notifier():
    """Fixture for a mock notifier."""
    return AsyncMock()

@pytest.fixture
def monitoring_cog(mock_db, mock_notifier):
    """Fixture for the MonitoringCog with mocked dependencies."""
    bot = AsyncMock()
    cog = MonitoringCog(bot, mock_db, mock_notifier)
    return cog

@pytest.mark.asyncio
class TestMonitoringCogCommands:
    @patch('src.cogs.monitoring.search_location_by_name', new_callable=AsyncMock)
    async def test_add_location_with_multiple_words(self, mock_search, monitoring_cog):
        """
        Verify that the !add location command correctly handles multi-word location names.
        """
        # Arrange
        mock_search.return_value = {'status': 'none', 'data': []}
        mock_ctx = AsyncMock()
        location_name = "Austin Pinball Collective"
        args = tuple(location_name.split())

        # Act
        await monitoring_cog.add.callback(monitoring_cog, mock_ctx, 'location', *args)

        # Assert
        mock_search.assert_awaited_once_with(location_name)
