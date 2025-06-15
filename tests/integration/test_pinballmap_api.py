"""
Integration tests for Pinball Map API that make real API calls
"""

import pytest
import asyncio
from src.api import (
    fetch_submissions_for_coordinates,
    fetch_submissions_for_location,
    fetch_location_autocomplete,
    fetch_location_details,
    search_location_by_name
)

# Known good test data
TEST_LOCATION_ID = 6805  # Pinballz Austin
TEST_COORDINATES = (30.2672, -97.7431)  # Austin, TX coordinates
TEST_RADIUS = 50  # 50 mile radius

@pytest.mark.integration
class TestPinballMapAPI:
    @pytest.mark.asyncio
    async def test_fetch_submissions_for_coordinates(self):
        """Test fetching submissions for coordinates with real API"""
        lat, lon = TEST_COORDINATES
        submissions = await fetch_submissions_for_coordinates(lat, lon, TEST_RADIUS)

        # Verify we got a list of submissions
        assert isinstance(submissions, list)

        # If we got submissions, verify their structure
        if submissions:
            submission = submissions[0]
            assert 'id' in submission
            assert 'machine_name' in submission
            assert 'location_name' in submission
            assert 'user_name' in submission

    @pytest.mark.asyncio
    async def test_fetch_submissions_for_coordinates_without_min_date(self):
        """Test fetching submissions for coordinates without min_date filter"""
        lat, lon = TEST_COORDINATES
        submissions = await fetch_submissions_for_coordinates(lat, lon, TEST_RADIUS, use_min_date=False)

        # Verify we got a list of submissions
        assert isinstance(submissions, list)

        # If we got submissions, verify their structure
        if submissions:
            submission = submissions[0]
            assert 'id' in submission
            assert 'machine_name' in submission
            assert 'location_name' in submission
            assert 'user_name' in submission

    @pytest.mark.asyncio
    async def test_fetch_submissions_for_location(self):
        """Test fetching submissions for a specific location with real API"""
        submissions = await fetch_submissions_for_location(TEST_LOCATION_ID)

        # Verify we got a list of submissions
        assert isinstance(submissions, list)

        # If we got submissions, verify their structure
        if submissions:
            submission = submissions[0]
            assert 'id' in submission
            assert 'machine_name' in submission
            assert 'location_name' in submission
            assert 'user_name' in submission

    @pytest.mark.asyncio
    async def test_fetch_submissions_for_location_without_min_date(self):
        """Test fetching submissions for location without min_date filter"""
        submissions = await fetch_submissions_for_location(TEST_LOCATION_ID, use_min_date=False)

        # Verify we got a list of submissions
        assert isinstance(submissions, list)

        # If we got submissions, verify their structure
        if submissions:
            submission = submissions[0]
            assert 'id' in submission
            assert 'machine_name' in submission
            assert 'location_name' in submission
            assert 'user_name' in submission

    @pytest.mark.asyncio
    async def test_fetch_location_autocomplete(self):
        """Test location autocomplete with real API"""
        locations = await fetch_location_autocomplete("Pinballz")

        # Verify we got a list of locations
        assert isinstance(locations, list)

        # If we got locations, verify their structure
        if locations:
            location = locations[0]
            assert 'id' in location
            assert 'name' in location
            assert 'city' in location
            assert 'state' in location

    @pytest.mark.asyncio
    async def test_fetch_location_details(self):
        """Test fetching location details with real API"""
        location = await fetch_location_details(TEST_LOCATION_ID)

        # Verify we got location details
        assert isinstance(location, dict)
        assert 'id' in location
        assert 'name' in location
        assert 'city' in location
        assert 'state' in location
        assert 'lat' in location
        assert 'lon' in location

    @pytest.mark.asyncio
    async def test_search_location_by_name(self):
        """Test searching for a location by name with real API"""
        result = await search_location_by_name("Pinballz Austin")

        # Verify we got a valid result
        assert isinstance(result, dict)
        assert result['status'] in ['found', 'not_found']

        if result['status'] == 'found':
            assert 'data' in result
            location = result['data']
            assert 'id' in location
            assert 'name' in location
            assert 'city' in location
            assert 'state' in location

    @pytest.mark.asyncio
    async def test_search_location_by_name_not_found(self):
        """Test searching for a non-existent location"""
        result = await search_location_by_name("This Location Does Not Exist 123456789")
        assert result['status'] == 'not_found'
        assert result['data'] is None

    @pytest.mark.asyncio
    async def test_invalid_location_id(self):
        """Test fetching non-existent location with real API"""
        # Use a very large ID that's unlikely to exist
        location = await fetch_location_details(999999)
        assert location == {}  # Should return empty dict for non-existent location

    @pytest.mark.asyncio
    async def test_coordinates_outside_radius(self):
        """Test fetching submissions for coordinates with no nearby locations"""
        # Use coordinates in the middle of the ocean
        submissions = await fetch_submissions_for_coordinates(0, 0, TEST_RADIUS)
        assert submissions == []  # Should return empty list for no nearby locations
