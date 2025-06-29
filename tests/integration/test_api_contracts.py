"""
Integration tests for API contracts.

These tests verify that the application can correctly parse and handle
real, saved API responses. This ensures that if the external API changes its
data format, these tests will fail, alerting us to the necessary updates.
"""

# To be migrated from `tests_backup/integration/test_geocoding_api_integration.py`
# and `tests_backup/integration/test_pinballmap_api.py`

import pytest

from src.api import search_location_by_name


def test_handle_geocoding_response_for_seattle(api_mocker):
    """
    Tests handling of a real geocoding response for 'Seattle, WA'.
    - Mocks the HTTP request to return the contents of 'city_seattle_wa.json'.
    - Calls the geocoding logic.
    - Asserts that the correct lat/long is extracted.
    """
    pass


def test_handle_pinballmap_location_details_response(api_mocker):
    """
    Tests handling of a real location details response from PinballMap.
    - Mocks the HTTP request to return 'location_1_details.json'.
    - Calls the location details fetching logic.
    - Asserts that the name, city, and other details are parsed correctly.
    """
    pass


def test_handle_pinballmap_submissions_response(api_mocker):
    """
    Tests handling of a real submissions response from PinballMap.
    - Mocks the HTTP request to return 'coords_seattle_5mi_all.json'.
    - Calls the submission fetching logic.
    - Asserts that the list of submissions is parsed into the correct data structure.
    """
    pass


def test_handle_api_error_responses(api_mocker):
    """
    Tests that the API clients handle error responses (e.g., 404, 500) gracefully.
    - Mocks an HTTP request to return a non-200 status code.
    - Asserts that the client returns an appropriate error indicator or raises a specific exception.
    """
    pass


@pytest.mark.asyncio
async def test_pinballmap_location_search_contract(api_mocker):
    """
    Tests that the application can correctly parse a successful response
    from the PinballMap `locations.json?by_location_name=` endpoint.
    - Uses the `api_mocker` to simulate the API response.
    - Asserts that the data is parsed into the expected format.
    """
    # 1. SETUP
    # Configure the API mocker to respond to a specific query.
    search_term = "Ground Kontrol"
    api_mocker.add_response(
        url_substring=f"by_location_name={search_term.replace(' ', '%20')}",
        json_fixture_path="pinballmap_search/search_ground_kontrol_single_result.json",
    )

    # 2. ACTION
    # Call the function that makes the API request.
    result = await search_location_by_name(search_term)

    # 3. ASSERT
    # Check that the function correctly parsed the data from the fixture.
    assert result["status"] in ["suggestions", "exact"]
    assert "data" in result
    if result["status"] == "suggestions":
        assert len(result["data"]) > 0
        # Verify we can access the first result
        first_suggestion = result["data"][0]
        assert "name" in first_suggestion
        assert "id" in first_suggestion


@pytest.mark.asyncio
async def test_geocode_api_contract_for_known_city(api_mocker):
    """Test that geocoding API client handles known city response correctly."""
    from src.api import geocode_city_name

    # Mock using fixture file instead of inline data
    api_mocker.add_response(
        url_substring="geocoding-api.open-meteo.com",
        json_fixture_path="geocoding/city_portland_or.json",
    )

    # Test the geocoding function
    result = await geocode_city_name("Portland, OR")

    # Should return properly formatted result
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "lat" in result
    assert "lon" in result
    assert "display_name" in result


def test_api_returns_error_for_unknown_location_id():
    """
    Tests that the PinballMap client handles a 'not found' error gracefully.
    - Mocks the API to return an error for a non-existent location ID.
    - Asserts that the function returns an appropriate error indicator.
    """
    pass
