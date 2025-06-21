"""
Unit tests for API module including rate limiting, error handling, and input validation
"""

from unittest.mock import patch

import pytest
import requests

from src.api import (
    fetch_submissions_for_coordinates,
    fetch_submissions_for_location,
    geocode_city_name,
    rate_limited_request,
    search_location_by_name,
)
from tests.utils.api import (
    create_error_response,
    create_rate_limit_response,
    create_success_response,
)
from tests.utils.assertions import assert_error_response


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(self):
        """Test that rate limiting retries with exponential backoff and eventually succeeds"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("requests.get") as mock_get:
            # First call returns 429, second call succeeds
            mock_get.side_effect = [create_rate_limit_response(), mock_response]

            with patch("asyncio.sleep") as mock_sleep:
                result = await rate_limited_request("http://test.com")

                assert result == mock_response
                assert mock_get.call_count == 2
                mock_sleep.assert_called_once_with(1.0)  # base_delay

    @pytest.mark.asyncio
    async def test_rate_limit_max_retries_exceeded(self):
        """Test that rate limiting fails after max retries"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [create_rate_limit_response()] * 4

            with patch("asyncio.sleep"):
                with pytest.raises(
                    Exception, match="Rate limit exceeded after 3 attempts"
                ):
                    await rate_limited_request("http://test.com", max_retries=3)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that retry delays follow exponential backoff pattern"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [create_rate_limit_response()] * 4

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    await rate_limited_request(
                        "http://test.com", max_retries=3, base_delay=2.0
                    )

                # Check exponential backoff: 2.0, 4.0 (only 2 retries before max_retries=3)
                expected_delays = [2.0, 4.0]
                actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
                assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_404_no_retry(self):
        """Test that 404 errors don't trigger retries"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                await rate_limited_request("http://test.com")


class TestGeocodingValidation:
    @pytest.mark.asyncio
    async def test_empty_city_name(self):
        """Test geocoding with empty city name"""
        result = await geocode_city_name("")
        assert_error_response(result, "non-empty string")

    @pytest.mark.asyncio
    async def test_none_city_name(self):
        """Test geocoding with None city name"""
        result = await geocode_city_name(None)
        assert_error_response(result, "non-empty string")

    @pytest.mark.asyncio
    async def test_non_string_city_name(self):
        """Test geocoding with non-string city name"""
        result = await geocode_city_name(123)
        assert_error_response(result, "non-empty string")

    @pytest.mark.asyncio
    async def test_city_name_too_long(self):
        """Test geocoding with overly long city name"""
        long_name = "a" * 201  # Over 200 character limit
        result = await geocode_city_name(long_name)
        assert_error_response(result, "too long")

    @pytest.mark.asyncio
    async def test_city_name_invalid_characters(self):
        """Test geocoding with invalid characters"""
        invalid_names = ["City<script>", 'City"quote', "City&amp;", "City\nNewline"]

        for invalid_name in invalid_names:
            result = await geocode_city_name(invalid_name)
            assert_error_response(result, "invalid characters")

    @pytest.mark.asyncio
    async def test_geocoding_network_error(self):
        """Test geocoding with network error"""
        with patch("src.api.rate_limited_request") as mock_request:
            mock_request.side_effect = requests.exceptions.RequestException(
                "Network error"
            )

            result = await geocode_city_name("Austin, TX")
            assert_error_response(result, "Geocoding API request failed")


class TestAPIErrorHandling:
    @pytest.mark.asyncio
    async def test_coordinates_api_error(self):
        """Test fetch_submissions_for_coordinates handles API errors gracefully"""
        with patch("src.api.rate_limited_request") as mock_request:
            mock_request.side_effect = requests.exceptions.RequestException("API Error")

            result = await fetch_submissions_for_coordinates(30.2672, -97.7431, 10)
            assert result == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_location_api_error(self):
        """Test fetch_submissions_for_location handles API errors gracefully"""
        with patch("src.api.rate_limited_request") as mock_request:
            mock_request.side_effect = requests.exceptions.RequestException("API Error")

            result = await fetch_submissions_for_location(1234)
            assert result == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_location_not_found_error(self):
        """Test location API with location not found"""
        mock_response = create_error_response(404, "Location not found")

        with patch("src.api.rate_limited_request", return_value=mock_response):
            result = await fetch_submissions_for_location(99999)
            assert result == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_search_location_network_error(self):
        """Test search_location_by_name handles network errors"""
        with patch("src.api.fetch_location_autocomplete") as mock_autocomplete:
            mock_autocomplete.side_effect = Exception("Network error")

            result = await search_location_by_name("Test Location")
            assert result["status"] == "not_found"
            assert result["data"] is None

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON responses"""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("src.api.rate_limited_request", return_value=mock_response):
            result = await fetch_submissions_for_coordinates(30.0, -97.0, 10)
            assert result == []  # Should return empty list on JSON error


class TestAPIResponseHandling:
    @pytest.mark.asyncio
    async def test_missing_expected_fields(self):
        """Test handling of API responses missing expected fields"""
        mock_response = create_success_response({})  # Missing 'user_submissions' field

        with patch("src.api.rate_limited_request", return_value=mock_response):
            result = await fetch_submissions_for_coordinates(30.0, -97.0, 10)
            assert result == []  # Should handle missing fields gracefully

    @pytest.mark.asyncio
    async def test_coordinates_without_radius(self):
        """Test coordinates API without radius parameter"""
        test_data = {"user_submissions": [generate_submission_data(1)]}
        mock_response = create_success_response(test_data)

        with patch(
            "src.api.rate_limited_request", return_value=mock_response
        ) as mock_request:
            result = await fetch_submissions_for_coordinates(30.0, -97.0)

            # Verify URL doesn't include max_distance parameter
            called_url = mock_request.call_args[0][0]
            assert "max_distance" not in called_url
            assert result == test_data["user_submissions"]

    @pytest.mark.asyncio
    async def test_coordinates_with_radius(self):
        """Test coordinates API with radius parameter"""
        test_data = {"user_submissions": [generate_submission_data(1)]}
        mock_response = create_success_response(test_data)

        with patch(
            "src.api.rate_limited_request", return_value=mock_response
        ) as mock_request:
            result = await fetch_submissions_for_coordinates(30.0, -97.0, 15)

            # Verify URL includes max_distance parameter
            called_url = mock_request.call_args[0][0]
            assert "max_distance=15" in called_url
            assert result == test_data["user_submissions"]
