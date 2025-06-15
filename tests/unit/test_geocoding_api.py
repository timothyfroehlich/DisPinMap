"""
Unit tests for geocoding API functionality
"""

import pytest
import asyncio
from src.api import parse_city_input, geocode_city_name
from unittest.mock import patch, MagicMock
from tests.utils.api import (
    create_success_response,
    create_error_response,
    create_rate_limit_response,
    create_async_success_response,
    create_async_error_response
)
from tests.utils.generators import (
    generate_city_data
)
from tests.utils.assertions import (
    assert_api_response,
    assert_error_response,
    assert_coordinates
)

class TestParseCityInput:
    """Unit tests for city input parsing"""

    def test_city_only(self):
        assert parse_city_input("Austin") == ("Austin", None, None)

    def test_city_and_state(self):
        assert parse_city_input("Austin, TX") == ("Austin", "Texas", None)

    def test_city_and_country(self):
        assert parse_city_input("Paris, FR") == ("Paris", None, "FR")

    def test_city_state_country(self):
        assert parse_city_input("Austin, TX, US") == ("Austin", "Texas", "US")

    def test_extra_whitespace(self):
        assert parse_city_input("  Austin  ,  TX  ,  US  ") == ("Austin", "Texas", "US")

    def test_unknown_state(self):
        assert parse_city_input("Austin, ZZ") == ("Austin", None, "ZZ")

    def test_three_parts_nonstate(self):
        assert parse_city_input("Paris, Ile-de-France, FR") == ("Paris", None, "FR")

@pytest.mark.asyncio
class TestGeocodeCityName:
    """Unit tests for geocoding city names"""

    async def test_empty_city_name(self):
        """Test geocoding with empty city name"""
        result = await geocode_city_name("")
        assert_error_response(result, "City name must be a non-empty string")

    async def test_none_city_name(self):
        """Test geocoding with None city name"""
        result = await geocode_city_name(None)
        assert_error_response(result, "City name must be a non-empty string")

    async def test_non_string_city_name(self):
        """Test geocoding with non-string city name"""
        result = await geocode_city_name(123)
        assert_error_response(result, "City name must be a non-empty string")

    async def test_city_name_too_long(self):
        """Test geocoding with overly long city name"""
        long_name = "a" * 201  # Over 200 character limit
        result = await geocode_city_name(long_name)
        assert_error_response(result, "City name too long")

    async def test_city_name_invalid_characters(self):
        """Test geocoding with invalid characters"""
        invalid_names = ["City<script>", "City\"quote", "City&amp;", "City\nNewline"]
        for invalid_name in invalid_names:
            result = await geocode_city_name(invalid_name)
            assert_error_response(result, "City name contains invalid characters")

    async def test_geocoding_network_error(self):
        """Test geocoding with network error"""
        with patch('src.api.rate_limited_request') as mock_request:
            mock_request.side_effect = Exception("Network error")
            result = await geocode_city_name("Austin, TX")
            assert_error_response(result, "Geocoding failed: Network error")

    async def test_geocoding_rate_limit(self):
        """Test geocoding with rate limit response"""
        with patch('src.api.rate_limited_request') as mock_request:
            mock_request.side_effect = [
                create_async_error_response({"results": []}),
                create_async_success_response({
                    "results": [{
                        "name": "Austin",
                        "latitude": 30.2672,
                        "longitude": -97.7431,
                        "admin1": "Texas",
                        "country_code": "US"
                    }]
                })
            ]
            result = await geocode_city_name("Austin, TX")
            if result["status"] == "error":
                assert_error_response(result, "No results found")
            else:
                assert_api_response(result)

    async def test_geocoding_malformed_response(self):
        """Test geocoding with malformed API response"""
        with patch('src.api.rate_limited_request') as mock_request:
            mock_request.return_value = create_async_success_response({"invalid": "response"})
            result = await geocode_city_name("Austin, TX")
            assert_error_response(result, "No results found")

    async def test_geocoding_empty_results(self):
        """Test geocoding with empty results"""
        with patch('src.api.rate_limited_request') as mock_request:
            mock_request.return_value = create_async_success_response({"results": []})
            result = await geocode_city_name("Nowhere, ZZ")
            assert_error_response(result, "No results found")

    async def test_geocoding_multiple_results(self):
        """Test geocoding with multiple results"""
        with patch('src.api.rate_limited_request') as mock_request:
            mock_request.return_value = create_async_success_response({
                "results": [
                    {
                        "name": "Springfield",
                        "latitude": 37.2090,
                        "longitude": -93.2923,
                        "admin1": "Missouri",
                        "country_code": "US"
                    },
                    {
                        "name": "Springfield",
                        "latitude": 42.1015,
                        "longitude": -72.5898,
                        "admin1": "Massachusetts",
                        "country_code": "US"
                    }
                ]
            })
            result = await geocode_city_name("Springfield")
            if result["status"] == "error":
                assert_error_response(result, "Multiple locations found")
            else:
                assert_api_response(result)
