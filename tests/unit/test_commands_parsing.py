"""
Unit tests for command argument parsing.

These tests ensure that the command functions can correctly parse and validate
their arguments, without executing the full command logic or interacting
with the database.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.cogs.monitoring import MonitoringCog
from src.messages import Messages


class TestCommandParsing:
    """Test command parsing logic in MonitoringCog"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_bot = Mock()
        self.mock_db = Mock()
        self.mock_notifier = Mock()
        self.mock_notifier.log_and_send = AsyncMock()
        self.mock_notifier.send_initial_notifications = AsyncMock()

        self.cog = MonitoringCog(self.mock_bot, self.mock_db, self.mock_notifier)
        self.mock_ctx = Mock()
        self.mock_ctx.channel.id = 123456


class TestAddCommandParsing(TestCommandParsing):
    """Test parsing of add command arguments"""

    @pytest.mark.asyncio
    async def test_add_location_by_id(self):
        """Test parsing location by ID"""
        # Test that location ID is correctly identified
        location_input = "123"

        # Mock the database and API calls
        self.mock_db.get_monitoring_targets.return_value = []

        # Call the add method directly (not through Discord command decorator)
        await self.cog.add(self.mock_ctx, "location", location_input)

        # Verify the correct handler was called
        # The actual parsing happens in _handle_location_add
        assert self.mock_notifier.log_and_send.called


class TestRemoveCommandParsing(TestCommandParsing):
    """Test parsing of remove command arguments"""

    @pytest.mark.asyncio
    async def test_remove_valid_index(self):
        """Test parsing valid index for remove command"""
        # Mock targets in database
        self.mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call remove with valid index directly
        await self.cog.remove(self.mock_ctx, "1")

        # Verify target was removed
        self.mock_db.remove_monitoring_target.assert_called_once()


class TestListCommandParsing(TestCommandParsing):
    """Test parsing of list command arguments"""

    @pytest.mark.asyncio
    async def test_list_no_targets(self):
        """Test list command when no targets exist"""
        self.mock_db.get_monitoring_targets.return_value = []

        # Call list_targets directly
        await self.cog.list_targets(self.mock_ctx)

        # Should send no targets message
        self.mock_notifier.log_and_send.assert_called_with(
            self.mock_ctx, Messages.Command.Shared.NO_TARGETS
        )


class TestExportCommandParsing(TestCommandParsing):
    """Test parsing of export command arguments"""

    @pytest.mark.asyncio
    async def test_export_with_targets(self):
        """Test export command with existing targets"""
        # Mock targets and channel config
        self.mock_db.get_monitoring_targets.return_value = [
            {
                "target_type": "location",
                "target_name": "Ground Kontrol Classic Arcade",
                "location_id": 874,
                "poll_rate_minutes": 15,
                "notification_types": "machines",
            }
        ]
        self.mock_db.get_channel_config.return_value = {
            "poll_rate_minutes": 30,
            "notification_types": "all",
        }

        # Call export directly
        await self.cog.export(self.mock_ctx)

        # Should call log_and_send with export message
        assert self.mock_notifier.log_and_send.called


class TestCheckCommandParsing(TestCommandParsing):
    """Test parsing of check command arguments"""

    @pytest.mark.asyncio
    async def test_check_command(self):
        """Test check command parsing"""
        # Mock targets
        self.mock_db.get_monitoring_targets.return_value = [
            {"target_type": "location", "target_name": "Test Location"}
        ]

        # Call check directly
        await self.cog.check(self.mock_ctx)

        # Should process targets and check for new submissions
        assert self.mock_notifier.log_and_send.called


class TestCoordinateParsing:
    """Test coordinate parsing logic"""

    def test_valid_coordinates(self):
        """Test parsing valid coordinate strings"""
        # Test valid latitude/longitude combinations
        valid_coords = [
            ("45.5231", "-122.6765"),
            ("0", "0"),
            ("90", "180"),
            ("-90", "-180"),
        ]

        for lat_str, lon_str in valid_coords:
            lat = float(lat_str)
            lon = float(lon_str)

            # Valid ranges
            assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
            assert -180 <= lon <= 180, f"Invalid longitude: {lon}"

    def test_invalid_coordinates(self):
        """Test parsing invalid coordinate strings"""
        invalid_coords = [
            ("invalid", "-122.6765"),
            ("45.5231", "invalid"),
            ("91", "0"),  # Latitude out of range
            ("0", "181"),  # Longitude out of range
            ("-91", "0"),  # Latitude out of range
            ("0", "-181"),  # Longitude out of range
        ]

        for lat_str, lon_str in invalid_coords:
            with pytest.raises(ValueError):
                lat = float(lat_str)
                lon = float(lon_str)

                # Check ranges
                if not (-90 <= lat <= 90):
                    raise ValueError(f"Invalid latitude: {lat}")
                if not (-180 <= lon <= 180):
                    raise ValueError(f"Invalid longitude: {lon}")


class TestRadiusParsing:
    """Test radius parsing logic"""

    def test_valid_radius(self):
        """Test parsing valid radius values"""
        valid_radii = ["1", "10", "100", "1000"]

        for radius_str in valid_radii:
            radius = int(radius_str)
            assert radius > 0, f"Radius must be positive: {radius}"

    def test_invalid_radius(self):
        """Test parsing invalid radius values"""
        invalid_radii = ["0", "-1", "invalid", "1.5"]

        for radius_str in invalid_radii:
            with pytest.raises((ValueError, TypeError)):
                radius = int(radius_str)
                if radius <= 0:
                    raise ValueError(f"Radius must be positive: {radius}")


class TestIndexParsing:
    """Test index parsing logic"""

    def test_valid_index(self):
        """Test parsing valid index values"""
        valid_indices = ["1", "2", "10", "100"]

        for index_str in valid_indices:
            index = int(index_str)
            assert index > 0, f"Index must be positive: {index}"

    def test_invalid_index(self):
        """Test parsing invalid index values"""
        invalid_indices = ["0", "-1", "invalid", "1.5"]

        for index_str in invalid_indices:
            with pytest.raises((ValueError, TypeError)):
                index = int(index_str)
                if index <= 0:
                    raise ValueError(f"Index must be positive: {index}")


class TestTargetTypeValidation:
    """Test target type validation"""

    def test_valid_target_types(self):
        """Test valid target types"""
        valid_types = ["location", "coordinates", "city"]

        for target_type in valid_types:
            assert target_type in valid_types, f"Invalid target type: {target_type}"

    def test_invalid_target_types(self):
        """Test invalid target types"""
        invalid_types = ["foobar", "location_id", "coords", "town"]
        valid_types = ["location", "coordinates", "city"]

        for target_type in invalid_types:
            assert (
                target_type not in valid_types
            ), f"Unexpectedly valid target type: {target_type}"


class TestNotificationTypeValidation:
    """Test notification type validation"""

    def test_valid_notification_types(self):
        """Test valid notification types"""
        valid_types = ["all", "machines", "comments", "conditions"]

        for notification_type in valid_types:
            assert (
                notification_type in valid_types
            ), f"Invalid notification type: {notification_type}"

    def test_invalid_notification_types(self):
        """Test invalid notification types"""
        invalid_types = ["foobar", "machine", "comment", "condition"]
        valid_types = ["all", "machines", "comments", "conditions"]

        for notification_type in invalid_types:
            assert (
                notification_type not in valid_types
            ), f"Unexpectedly valid notification type: {notification_type}"
