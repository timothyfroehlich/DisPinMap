"""
Integration tests for geocoding API functionality using Open-Meteo API
"""

import pytest
import asyncio
from src.api import geocode_city_name
from tests.utils.assertions import assert_api_response, assert_error_response, assert_coordinates

# Known city coordinates for accuracy testing
KNOWN_CITIES = {
    "Austin, TX": (30.2672, -97.7431),
    "New York, NY": (40.7128, -74.0060),
    "London, GB": (51.5074, -0.1278),
    "Tokyo, JP": (35.6762, 139.6503),
    "Sydney, AU": (-33.8688, 151.2093)
}

@pytest.mark.integration
@pytest.mark.asyncio
class TestGeocodingAPI:
    """Integration tests for geocoding API functionality"""

    async def test_successful_geocoding(self):
        """Test successful geocoding of various city formats"""
        test_cases = [
            "Austin, TX",
            "New York, NY",
            "London, GB",
            "Tokyo, JP",
            "Sydney, AU"
        ]

        for city in test_cases:
            result = await geocode_city_name(city)
            assert_api_response(result)
            assert_coordinates(result["lat"], result["lon"])
            assert city.split(",")[0] in result["display_name"]

    async def test_coordinate_accuracy(self):
        """Test coordinate accuracy against known values"""
        for city, (expected_lat, expected_lon) in KNOWN_CITIES.items():
            result = await geocode_city_name(city)
            assert_api_response(result)
            # Allow for small coordinate differences (within ~2km for latitude, ~5km for longitude)
            assert abs(result["lat"] - expected_lat) < 0.02
            assert abs(result["lon"] - expected_lon) < 0.05

    async def test_international_cities(self):
        """Test geocoding of international cities with various formats"""
        test_cases = [
            ("Paris, FR", "Paris"),
            ("Berlin, DE", "Berlin"),
            ("Moscow, RU", "Moscow"),
            ("São Paulo, BR", "São Paulo"),
            ("北京, CN", "Beijing")
        ]

        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            if result["status"] == "success":
                assert_coordinates(result["lat"], result["lon"])
                assert expected_city in result["display_name"]
            else:
                # Accept 'no results found' or 'multiple locations found' as valid for edge cases
                assert result["status"] == "error"
                assert ("No results found" in result["message"] or 
                       "Multiple locations found" in result["message"])

    async def test_cities_with_multiple_matches(self):
        """Test cities with multiple matches requiring disambiguation"""
        test_cases = [
            "Springfield",
            "Paris",
            "San Jose"
        ]

        for city in test_cases:
            result = await geocode_city_name(city)
            if result["status"] == "success":
                # Accept if API picks one
                assert_coordinates(result["lat"], result["lon"])
            else:
                # Accept if API returns ambiguity error
                assert result["status"] == "error"
                assert "Multiple locations found" in result["message"]

    async def test_cities_with_no_matches(self):
        """Test cities that don't exist"""
        test_cases = [
            "Fake City, XX",
            "123456789, YY"
        ]

        for city in test_cases:
            result = await geocode_city_name(city)
            assert_error_response(result, "No results found")

    async def test_special_characters(self):
        """Test cities with special characters and formatting"""
        test_cases = [
            ("Saint-Émilion, FR", "Saint-Émilion"),
            ("São Paulo, BR", "São Paulo"),
            ("München, DE", "München"),
            ("Côte d'Azur, FR", "Côte d'Azur")
        ]

        for city, expected_city in test_cases:
            result = await geocode_city_name(city)
            if result["status"] == "success":
                assert_coordinates(result["lat"], result["lon"])
                assert expected_city in result["display_name"]
            else:
                # Accept various error types (ambiguity, invalid characters, not found)
                assert result["status"] == "error"
                assert ("Multiple locations found" in result["message"] or
                       "invalid characters" in result["message"] or
                       "No results found" in result["message"])

    async def test_state_specifications(self):
        """Test various state specification formats"""
        test_cases = [
            ("Austin, TX", "Texas"),
            ("New York, NY", "New York"),
            ("Los Angeles, CA", "California"),
            ("Chicago, IL", "Illinois")
        ]

        for city_input, expected_state in test_cases:
            result = await geocode_city_name(city_input)
            assert_api_response(result)
            assert_coordinates(result["lat"], result["lon"])
            assert expected_state in result["display_name"]

    async def test_rate_limiting(self):
        """Test rate limiting behavior with multiple rapid requests"""
        # Make multiple requests in quick succession
        tasks = [geocode_city_name("Austin, TX") for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All requests should succeed despite rate limiting
        for result in results:
            assert_api_response(result)
            assert_coordinates(result["lat"], result["lon"])

    async def test_invalid_inputs(self):
        """Test various invalid input cases"""
        test_cases = [
            ("", "City name must be a non-empty string"),
            ("a" * 201, "City name too long"),
            ("City<script>", "City name contains invalid characters"),
            ("City\nNewline", "City name contains invalid characters"),
            ("City\"quote", "City name contains invalid characters")
        ]

        for city, expected_error in test_cases:
            result = await geocode_city_name(city)
            assert_error_response(result, expected_error)
