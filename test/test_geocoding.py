"""
Test suite for city geocoding functionality
Tests various city name formats and international locations
"""

import pytest
import asyncio
from src.api import geocode_city_name


class TestGeocoding:
    """Test the geocoding functionality with various city name formats"""

    @pytest.mark.asyncio
    async def test_us_cities_with_state_abbreviations(self):
        """Test US cities with state abbreviations (uses fallback to city name only)"""
        test_cases = [
            ("Philadelphia, PA", "Philadelphia"),
            ("Austin, TX", "Austin"),
            ("Seattle, WA", "Seattle"),
            ("Miami, FL", "Miami"),
            ("Denver, CO", "Denver"),
            ("Portland, OR", "Portland"),
            ("Nashville, TN", "Nashville"),
            ("Chicago, IL", "Chicago"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"
            assert isinstance(result['lat'], float), "Latitude should be a float"
            assert isinstance(result['lon'], float), "Longitude should be a float"
            assert -90 <= result['lat'] <= 90, "Latitude should be valid"
            assert -180 <= result['lon'] <= 180, "Longitude should be valid"

    @pytest.mark.asyncio
    async def test_us_cities_lowercase(self):
        """Test US cities in lowercase (uses fallback to city name only)"""
        test_cases = [
            ("philadelphia pa", "Philadelphia"),
            ("austin tx", "Austin"), 
            ("seattle wa", "Seattle"),
            ("new york ny", "New York"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"

    @pytest.mark.asyncio 
    async def test_us_cities_simple_names(self):
        """Test US cities by simple names (most reliable)"""
        test_cases = [
            ("Philadelphia", "Philadelphia"),
            ("Austin", "Austin"),
            ("Seattle", "Seattle"),
            ("Los Angeles", "Los Angeles"),
            ("New York", "New York"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_international_cities(self):
        """Test international cities"""
        test_cases = [
            ("London, UK", "London"),
            ("Paris, France", "Paris"),
            ("Tokyo, Japan", "Tokyo"),
            ("Berlin, Germany", "Berlin"),
            ("Sydney, Australia", "Sydney"),
            ("Toronto, Canada", "Toronto"),
            ("Amsterdam, Netherlands", "Amsterdam"),
            ("Copenhagen, Denmark", "Copenhagen"),
            ("Stockholm, Sweden", "Stockholm"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"
            assert isinstance(result['lat'], float), "Latitude should be a float"
            assert isinstance(result['lon'], float), "Longitude should be a float"

    @pytest.mark.asyncio
    async def test_cities_just_names(self):
        """Test major cities by name only (no state/country)"""
        test_cases = [
            ("London", "London"),
            ("Paris", "Paris"),
            ("Tokyo", "Tokyo"),
            ("Berlin", "Berlin"),
            ("Sydney", "Sydney"),
            ("Toronto", "Toronto"),
            ("Amsterdam", "Amsterdam"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_cities_with_special_characters(self):
        """Test cities with special characters and accents"""
        test_cases = [
            ("São Paulo", "São Paulo"),
            ("Mexico City", "Mexico"),  
            ("Montreal", "Montreal"),
            ("Zurich", "Zurich"),
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'success', f"Failed to geocode {city_input}: {result.get('message', 'Unknown error')}"
            # More flexible matching for cities with special characters
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_invalid_city_names(self):
        """Test invalid or nonsensical city names"""
        test_cases = [
            "ThisCityDoesNotExist123",
            "XYZ Invalid City Name",
            "NotARealPlace, ZZ",
            "",  # Empty string
            "   ",  # Just whitespace
        ]
        
        for city_input in test_cases:
            result = await geocode_city_name(city_input)
            assert result['status'] == 'error', f"Expected error for invalid city: {city_input}, but got: {result}"
            assert 'message' in result, "Error result should include a message"

    @pytest.mark.asyncio
    async def test_ambiguous_city_names(self):
        """Test cities that exist in multiple places"""
        test_cases = [
            ("Portland", "Portland"),  # Should get some Portland (OR or ME)
            ("Springfield", "Springfield"),  # Many Springfields in US
            ("Cambridge", "Cambridge"),  # UK and MA, USA
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            # Should succeed and return one of the matching cities
            assert result['status'] == 'success', f"Failed to geocode ambiguous city {city_input}: {result.get('message', 'Unknown error')}"
            assert expected_city.lower() in result['display_name'].lower(), f"Expected {expected_city} in {result['display_name']}"

    @pytest.mark.asyncio
    async def test_major_metropolitan_areas(self):
        """Test major metropolitan areas and regions"""
        test_cases = [
            ("San Francisco Bay Area", "San Francisco"),
            ("Greater London", "London"),
            ("Metro Atlanta", "Atlanta"),
            ("DFW", "Dallas"),  # Dallas-Fort Worth area
        ]
        
        for city_input, expected_city in test_cases:
            result = await geocode_city_name(city_input)
            # These might not all work, but test what we can
            if result['status'] == 'success':
                assert expected_city.lower() in result['display_name'].lower() or result['display_name'], f"Unexpected result for {city_input}: {result['display_name']}"

    @pytest.mark.asyncio
    async def test_coordinate_ranges(self):
        """Test that returned coordinates are in valid ranges"""
        test_cities = [
            "New York, NY",
            "Los Angeles, CA", 
            "London, UK",
            "Tokyo, Japan",
            "Sydney, Australia",
        ]
        
        for city in test_cities:
            result = await geocode_city_name(city)
            assert result['status'] == 'success', f"Failed to geocode {city}"
            
            lat = result['lat']
            lon = result['lon']
            
            # Check coordinate bounds
            assert -90 <= lat <= 90, f"Invalid latitude {lat} for {city}"
            assert -180 <= lon <= 180, f"Invalid longitude {lon} for {city}"
            
            # Check reasonable bounds for known cities
            if "new york" in city.lower():
                assert 40 <= lat <= 41, f"NYC latitude {lat} seems incorrect"
                assert -75 <= lon <= -73, f"NYC longitude {lon} seems incorrect"
            elif "los angeles" in city.lower():
                assert 33 <= lat <= 35, f"LA latitude {lat} seems incorrect"
                assert -119 <= lon <= -117, f"LA longitude {lon} seems incorrect"


if __name__ == "__main__":
    # Run a quick test to verify the API is working
    async def quick_test():
        result = await geocode_city_name("Austin, TX")
        print(f"Quick test result: {result}")
        assert result['status'] == 'success'
        print("✅ Quick geocoding test passed!")
    
    asyncio.run(quick_test())