"""
Unit tests for the API client logic in `src/api.py`.

These tests will verify the parsing and data extraction logic of the API
client, ensuring it correctly handles various response formats.
All network requests will be mocked.
"""

# To be migrated from `tests_backup/unit/test_api.py` and `tests_backup/unit/test_geocoding_api.py`

import pytest

from src.api import geocode_city_name

# from tests.utils.mock_factories import create_api_client_mock  # Unused for now


@pytest.mark.asyncio
async def test_parse_location_details():
    """
    Tests the successful parsing of a location details JSON response.
    - Mocks the API response with a valid location details payload.
    - Asserts that the function returns a correctly structured dictionary.
    """
    import json
    from unittest.mock import patch

    from src.api import fetch_location_details
    from tests.utils.mock_factories import create_requests_response_mock

    # Load fixture data
    with open(
        "tests/fixtures/api_responses/pinballmap_locations/location_874_details.json",
        "r",
    ) as f:
        fixture_data = json.load(f)

    mock_response = create_requests_response_mock(200, fixture_data)

    with patch("src.api.rate_limited_request", return_value=mock_response):
        result = await fetch_location_details(874)

        # Assert the function returns the expected structure
        assert isinstance(result, dict)
        assert result["id"] == 874
        assert result["name"] == "Ground Kontrol Classic Arcade"
        assert result["city"] == "Portland"
        assert result["state"] == "OR"
        assert "location_machine_xrefs" in result
        assert isinstance(result["location_machine_xrefs"], list)


@pytest.mark.asyncio
async def test_search_location_by_name_exact_match():
    """
    Tests the location search functionality for an exact match.
    - Mocks the search API to return an 'exact' status.
    - Asserts that the function returns the correct location data.
    """
    import json
    from unittest.mock import AsyncMock, patch

    from src.api import search_location_by_name

    # Load fixtures
    with open(
        "tests/fixtures/api_responses/pinballmap_search/search_ground_kontrol_single_result.json",
        "r",
    ) as f:
        search_fixture = json.load(f)

    with open(
        "tests/fixtures/api_responses/pinballmap_locations/location_874_details.json",
        "r",
    ) as f:
        details_fixture = json.load(f)

    # Mock the autocomplete and details functions
    with patch(
        "src.api.fetch_location_autocomplete", new_callable=AsyncMock
    ) as mock_autocomplete:
        with patch(
            "src.api.fetch_location_details", new_callable=AsyncMock
        ) as mock_details:
            mock_autocomplete.return_value = search_fixture["locations"]
            mock_details.return_value = details_fixture

            result = await search_location_by_name("Ground Kontrol Classic Arcade")

            # Assert exact match status and data
            assert result["status"] == "exact"
            assert result["data"]["id"] == 874
            assert result["data"]["name"] == "Ground Kontrol Classic Arcade"

            # Verify the functions were called correctly
            mock_autocomplete.assert_called_once_with("Ground Kontrol Classic Arcade")
            mock_details.assert_called_once_with(874)


@pytest.mark.asyncio
async def test_search_location_by_name_multiple_matches():
    """
    Tests the location search functionality when multiple matches are found.
    - Mocks the search API to return a 'multiple' status.
    - Asserts that the function correctly identifies the status and returns the list of locations.
    """
    from unittest.mock import AsyncMock, patch

    from src.api import search_location_by_name

    # Create mock data for multiple results (no exact name match)
    multiple_locations = [
        {"id": 1, "name": "Pin Central", "city": "New York", "state": "NY"},
        {"id": 2, "name": "Pin Palace", "city": "Los Angeles", "state": "CA"},
        {"id": 3, "name": "Pinball Paradise", "city": "Chicago", "state": "IL"},
    ]

    with patch(
        "src.api.fetch_location_autocomplete", new_callable=AsyncMock
    ) as mock_autocomplete:
        mock_autocomplete.return_value = multiple_locations

        result = await search_location_by_name("pin")

        # Assert suggestions status and multiple results
        assert result["status"] == "suggestions"
        assert len(result["data"]) == 3
        assert all(isinstance(loc, dict) for loc in result["data"])
        assert result["data"][0]["name"] == "Pin Central"
        assert result["data"][1]["name"] == "Pin Palace"
        assert result["data"][2]["name"] == "Pinball Paradise"

        # Verify autocomplete was called correctly
        mock_autocomplete.assert_called_once_with("pin")


@pytest.mark.asyncio
async def test_geocode_city_name_success():
    """
    Tests successful geocoding of a city name.
    - Mocks the geocoding API with a successful response.
    - Asserts that the function returns the correct latitude and longitude.
    """
    import json
    from unittest.mock import patch

    from src.api import geocode_city_name
    from tests.utils.mock_factories import create_requests_response_mock

    # Load fixture data for Portland, OR
    with open("tests/fixtures/api_responses/geocoding/city_portland_or.json", "r") as f:
        fixture_data = json.load(f)

    mock_response = create_requests_response_mock(200, fixture_data)

    with patch("src.api.rate_limited_request", return_value=mock_response):
        result = await geocode_city_name("Portland, OR")

        # Assert successful geocoding result
        assert result["status"] == "success"
        assert result["lat"] == 45.52345
        assert result["lon"] == -122.67621
        assert result["display_name"] == "Portland, Oregon, US"


@pytest.mark.asyncio
async def test_geocode_city_name_failure():
    """
    Tests geocoding failure for an invalid city name.
    - Mocks the geocoding API with a failure or empty response.
    - Asserts that the function handles the failure gracefully (e.g., returns None or raises an exception).
    """
    import json
    from unittest.mock import patch

    from src.api import geocode_city_name
    from tests.utils.mock_factories import create_requests_response_mock

    # Load fixture data for nonexistent city (empty results)
    with open("tests/fixtures/api_responses/geocoding/city_nonexistent.json", "r") as f:
        fixture_data = json.load(f)

    mock_response = create_requests_response_mock(200, fixture_data)

    with patch("src.api.rate_limited_request", return_value=mock_response):
        result = await geocode_city_name("NonexistentCity123")

        # Assert error status for failed geocoding
        assert result["status"] == "error"
        assert "No results found" in result["message"]
        assert "NonexistentCity123" in result["message"]


@pytest.mark.asyncio
async def test_geocode_client_parses_success_response(api_mocker):
    """
    Tests that the geocode client correctly parses a successful response.
    - Mocks the `requests.get` call to return a mock response using a real fixture.
    - Asserts that the function returns the expected dictionary of coordinates.
    """
    # 1. SETUP
    # Configure the API mocker to return a specific fixture for the geocoding URL.
    api_mocker.add_response(
        url_substring="geocoding-api.open-meteo.com/v1/search",
        json_fixture_path="geocoding/city_portland_or.json",
    )

    # 2. ACTION
    # Call the function we are testing
    result = await geocode_city_name("portland, or")

    # 3. ASSERT
    # Verify that the function returned the correctly parsed data
    assert result["status"] == "success"
    assert result["lat"] == 45.52345
    assert result["lon"] == -122.67621
    assert result["display_name"] == "Portland, Oregon, US"


@pytest.mark.asyncio
async def test_pinball_map_client_handles_api_error():
    """Test that API client handles network errors gracefully."""
    from unittest.mock import patch

    from src.api import fetch_location_details

    with patch("src.api.requests.get", autospec=True) as mock_get:
        # Setup mock to raise an exception
        mock_get.side_effect = Exception("Network error")

        # Test that function handles the error
        result = await fetch_location_details(12345)

        # Function returns empty dict on error according to log output
        assert result == {} or result is None or result.get("status") == "error"


@pytest.mark.asyncio
async def test_client_handles_empty_response():
    """Test that API client handles empty responses gracefully."""
    from unittest.mock import patch

    from src.api import fetch_location_details
    from tests.utils.mock_factories import create_requests_response_mock

    # Mock empty response
    mock_response = create_requests_response_mock(200, {})

    with patch("src.api.rate_limited_request", return_value=mock_response):
        result = await fetch_location_details(99999)

        # Function should return empty dict for empty response
        assert result == {}
