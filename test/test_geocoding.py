"""
Test suite for city geocoding functionality
Tests both the geocoding function directly and the bot's handling of geocoding results
"""

import pytest
import asyncio
from src.api import geocode_city_name
from src.commands import CommandHandler
from src.database import Database
from .test_utils import MockContext


class TestGeocoding:
    """Test the geocoding functionality with known cities and error cases"""

    @pytest.mark.asyncio
    async def test_known_cities_coordinates(self):
        """Test that known cities return coordinates within expected ranges"""
        test_cases = [
            ("New York", 40.7128, -74.0060),  # NYC coordinates
            ("Los Angeles", 34.0522, -118.2437),  # LA coordinates
            ("London", 51.5074, -0.1278),  # London coordinates (will get London, England)
            ("Tokyo", 35.6762, 139.6503),  # Tokyo coordinates
            ("Sydney", -33.8688, 151.2093),  # Sydney coordinates
        ]

        for city, expected_lat, expected_lon in test_cases:
            result = await geocode_city_name(city)
            assert result['status'] == 'success', f"Failed to geocode {city}: {result.get('message', 'Unknown error')}"

            # Check that coordinates are within 1 degree of expected values
            assert abs(result['lat'] - expected_lat) <= 1.0, f"Latitude for {city} too far from expected: {result['lat']} vs {expected_lat}"
            assert abs(result['lon'] - expected_lon) <= 1.0, f"Longitude for {city} too far from expected: {result['lon']} vs {expected_lon}"

            # Verify coordinate types and ranges
            assert isinstance(result['lat'], float), "Latitude should be a float"
            assert isinstance(result['lon'], float), "Longitude should be a float"
            assert -90 <= result['lat'] <= 90, "Latitude should be valid"
            assert -180 <= result['lon'] <= 180, "Longitude should be valid"

    @pytest.mark.asyncio
    async def test_invalid_inputs(self):
        """Test various invalid inputs return appropriate errors"""
        test_cases = [
            ("", "City name must be a non-empty string"),
            ("   ", "City name must be a non-empty string"),
            ("ThisCityDoesNotExist123", "No results found"),
            ("<script>alert('xss')</script>", "City name contains invalid characters"),
            ("A" * 201, "City name too long"),  # 201 chars
        ]

        for city, expected_error in test_cases:
            result = await geocode_city_name(city)
            assert result['status'] == 'error', f"Expected error for {city}, got: {result}"
            assert expected_error in result['message'], f"Expected error message containing '{expected_error}', got: {result['message']}"

    @pytest.mark.asyncio
    async def test_state_specification(self):
        """Test that state specifications are handled correctly"""
        test_cases = [
            # (input, expected_state_in_display_name)
            ("Louisville, CO", "Colorado"),
            ("Louisville, KY", "Kentucky"),
            ("Springfield, IL", "Illinois"),
            ("Springfield, MO", "Missouri"),
        ]

        for city_input, expected_state in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_state in result['display_name'], f"Expected state {expected_state} not found in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_country_specification(self):
        """Test that country specifications are handled correctly"""
        test_cases = [
            # (input, expected_country_code)
            ("London, GB", "GB"),  # Using country code
            ("Paris, FR", "FR"),   # Using country code
            ("Tokyo, JP", "JP"),   # Using country code
            ("Sydney, AU", "AU"),  # Using country code
        ]

        for city_input, expected_country in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_country in result['display_name'], f"Expected country {expected_country} not found in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_ambiguous_cities(self):
        """Test handling of ambiguous city names"""
        test_cases = [
            "Springfield",  # Multiple Springfields in US
            "Paris",       # Multiple Parises worldwide
            "London",      # Multiple Londons worldwide
        ]

        for city in test_cases:
            result = await geocode_city_name(city)
            # The API returns the first result for ambiguous cities
            assert result['status'] == 'success', f"Failed to geocode {city}: {result.get('message', 'Unknown error')}"
            # Verify that the result contains a valid city name and coordinates
            assert isinstance(result['lat'], float), "Latitude should be a float"
            assert isinstance(result['lon'], float), "Longitude should be a float"
            assert -90 <= result['lat'] <= 90, "Latitude should be valid"
            assert -180 <= result['lon'] <= 180, "Longitude should be valid"


class TestGeocodingFunctional:
    """Test the bot's handling of geocoding results through the command interface"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database and handler for each test"""
        self.db = Database(':memory:')
        self.handler = CommandHandler(self.db)
        self.ctx = MockContext()

    @pytest.mark.asyncio
    async def test_city_add_success(self):
        """Test successful city addition through bot command"""
        await self.handler.handle_city_add(self.ctx, "New York")

        # Check success message
        success_message = self.ctx.sent_messages[-1]
        assert "✅ Added city:" in success_message
        assert "New York" in success_message
        assert "Monitoring started!" in success_message

        # Verify database state
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Verify coordinates are stored
        coords = targets[0]['target_name'].split(',')
        assert len(coords) >= 2
        lat, lon = float(coords[0]), float(coords[1])
        assert 39 <= lat <= 41  # NYC latitude range
        assert -75 <= lon <= -73  # NYC longitude range

    @pytest.mark.asyncio
    async def test_city_add_with_state(self):
        """Test city addition with state specification"""
        await self.handler.handle_city_add(self.ctx, "Louisville, CO")

        # Check success message
        success_message = self.ctx.sent_messages[-1]
        assert "✅ Added city:" in success_message
        assert "Louisville" in success_message
        assert "Colorado" in success_message
        assert "Monitoring started!" in success_message

        # Verify database state
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Verify coordinates are stored
        coords = targets[0]['target_name'].split(',')
        assert len(coords) >= 2
        lat, lon = float(coords[0]), float(coords[1])
        # Louisville, CO coordinates
        assert 39 <= lat <= 40
        assert -106 <= lon <= -105

    @pytest.mark.asyncio
    async def test_city_add_with_country(self):
        """Test city addition with country specification"""
        await self.handler.handle_city_add(self.ctx, "London, GB")

        # Check success message
        success_message = self.ctx.sent_messages[-1]
        assert "✅ Added city:" in success_message
        assert "London" in success_message
        assert "GB" in success_message
        assert "Monitoring started!" in success_message

        # Verify database state
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Verify coordinates are stored
        coords = targets[0]['target_name'].split(',')
        assert len(coords) >= 2
        lat, lon = float(coords[0]), float(coords[1])
        # London coordinates
        assert 51 <= lat <= 52
        assert -1 <= lon <= 0

    @pytest.mark.asyncio
    async def test_city_add_ambiguous(self):
        """Test handling of ambiguous city names"""
        await self.handler.handle_city_add(self.ctx, "Springfield")

        # Check success message (API returns first result for ambiguous cities)
        success_message = self.ctx.sent_messages[-1]
        assert "✅ Added city:" in success_message
        assert "Springfield" in success_message
        assert "Monitoring started!" in success_message

        # Verify database state
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Verify coordinates are stored
        coords = targets[0]['target_name'].split(',')
        assert len(coords) >= 2
        lat, lon = float(coords[0]), float(coords[1])
        assert isinstance(lat, float), "Latitude should be a float"
        assert isinstance(lon, float), "Longitude should be a float"
        assert -90 <= lat <= 90, "Latitude should be valid"
        assert -180 <= lon <= 180, "Longitude should be valid"

    @pytest.mark.asyncio
    async def test_city_add_invalid(self):
        """Test handling of invalid city names through bot command"""
        await self.handler.handle_city_add(self.ctx, "ThisCityDoesNotExist123")

        # Check error message
        error_message = self.ctx.sent_messages[-1]
        assert "❌" in error_message
        assert "No results found" in error_message

        # Verify no targets were added
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 0

    @pytest.mark.asyncio
    async def test_city_add_with_radius(self):
        """Test city addition with custom radius"""
        await self.handler.handle_city_add(self.ctx, "Los Angeles", 25)

        # Check success message
        success_message = self.ctx.sent_messages[-1]
        assert "✅ Added city:" in success_message
        assert "Los Angeles" in success_message
        assert "25 miles" in success_message

        # Verify database state
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Verify coordinates and radius are stored
        coords = targets[0]['target_name'].split(',')
        assert len(coords) == 3
        lat, lon, radius = float(coords[0]), float(coords[1]), int(coords[2])
        assert 33 <= lat <= 35  # LA latitude range
        assert -119 <= lon <= -117  # LA longitude range
        assert radius == 25

    @pytest.mark.asyncio
    async def test_city_add_invalid_radius(self):
        """Test handling of invalid radius values"""
        # Test radius too small
        await self.handler.handle_city_add(self.ctx, "New York", 0)
        error_message = self.ctx.sent_messages[-1]
        assert "❌" in error_message
        assert "Radius must be between 1 and 100 miles" in error_message

        # Test radius too large
        await self.handler.handle_city_add(self.ctx, "New York", 101)
        error_message = self.ctx.sent_messages[-1]
        assert "❌" in error_message
        assert "Radius must be between 1 and 100 miles" in error_message

        # Verify no targets were added
        targets = self.db.get_monitoring_targets(self.ctx.channel.id)
        assert len(targets) == 0


if __name__ == "__main__":
    # Run a quick test to verify the API is working
    async def quick_test():
        result = await geocode_city_name("New York")
        print(f"Quick test result: {result}")
        assert result['status'] == 'success'
        print("✅ Quick geocoding test passed!")

    asyncio.run(quick_test())
