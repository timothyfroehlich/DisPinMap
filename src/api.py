"""
API module for Discord Pinball Map Bot
Handles pinballmap.com API interactions using the new user submissions endpoints
"""

import requests
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import urllib.parse
import logging

logger = logging.getLogger(__name__)


async def rate_limited_request(url: str, max_retries: int = 3, base_delay: float = 1.0) -> requests.Response:
    """Make a rate-limited request with exponential backoff"""
    # Extract endpoint for cleaner debug message
    endpoint = url.split('/')[-1].split('.json')[0]
    logger.info(f"🌐 API: {endpoint}")

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts")
            elif response.status_code == 404:  # Not Found - don't retry
                response.raise_for_status()  # This will raise the 404 error immediately

            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Request failed, retrying in {delay} seconds: {e}")
                await asyncio.sleep(delay)
            else:
                raise

        # Add small delay between requests to be nice to the API
        await asyncio.sleep(0.5)

    raise Exception(f"Failed after {max_retries} attempts")


def get_yesterday_date() -> str:
    """Get yesterday's date in YYYY-MM-DD format for API filtering"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


async def fetch_submissions_for_coordinates(lat: float, lon: float, radius_miles: int = None) -> List[Dict[str, Any]]:
    """Fetch user submissions within radius of given coordinates"""
    try:
        yesterday = get_yesterday_date()
        if radius_miles is not None:
            url = f'https://pinballmap.com/api/v1/user_submissions/list_within_range.json?lat={lat}&lon={lon}&max_distance={radius_miles}&min_date_of_submission={yesterday}'
        else:
            url = f'https://pinballmap.com/api/v1/user_submissions/list_within_range.json?lat={lat}&lon={lon}&min_date_of_submission={yesterday}'

        response = await rate_limited_request(url)
        data = response.json()

        return data.get('user_submissions', [])

    except Exception as e:
        logger.error(f"Error fetching submissions for coordinates {lat}, {lon}: {e}")
        return []


async def fetch_submissions_for_location(location_id: int) -> List[Dict[str, Any]]:
    """Fetch user submissions for a specific location"""
    try:
        yesterday = get_yesterday_date()
        url = f'https://pinballmap.com/api/v1/user_submissions/location.json?id={location_id}&min_date_of_submission={yesterday}'

        response = await rate_limited_request(url)
        data = response.json()

        # Check for errors
        if 'errors' in data:
            raise Exception(f"Location {location_id} not found: {data['errors']}")

        return data.get('user_submissions', [])

    except Exception as e:
        logger.error(f"Error fetching submissions for location {location_id}: {e}")
        return []


async def fetch_location_autocomplete(query: str) -> List[Dict[str, Any]]:
    """Fetch location suggestions using by_location_name search"""
    try:
        # Use the working API endpoint instead of autocomplete
        encoded_query = urllib.parse.quote(query)
        url = f'https://pinballmap.com/api/v1/locations.json?by_location_name={encoded_query}'
        response = await rate_limited_request(url)
        data = response.json()
        return data.get('locations', [])
    except Exception as e:
        logger.error(f"Error fetching location autocomplete for '{query}': {e}")
        return []

async def fetch_location_details(location_id: int) -> Dict[str, Any]:
    """Fetch full details for a specific location ID"""
    try:
        url = f'https://pinballmap.com/api/v1/locations/{location_id}.json'
        response = await rate_limited_request(url)
        data = response.json()
        if 'errors' in data: # PinballMap API returns errors in a list for this endpoint
            error_message = data['errors'][0] if isinstance(data['errors'], list) and data['errors'] else str(data['errors'])
            raise Exception(f"Location details for {location_id} not found: {error_message}")
        return data # The location data is at the root level, not under a 'location' key
    except Exception as e:
        logger.error(f"Error fetching location details for ID {location_id}: {e}")
        return {}


async def search_location_by_name(location_name: str) -> Dict[str, Any]:
    """
    Search for a location by name.
    1. Uses autocomplete to find potential matches.
    2. If an exact match (case-insensitive) is found in autocomplete, fetches full details.
    3. Otherwise, returns suggestions or a not_found status.
    """
    location_name_lower = location_name.lower().strip()

    try:
        autocomplete_results = await fetch_location_autocomplete(location_name)

        if not autocomplete_results:
            return {'status': 'not_found', 'data': None}

        exact_match = None
        for loc in autocomplete_results:
            if loc.get('name', '').lower() == location_name_lower:
                exact_match = loc
                break

        if exact_match:
            location_id = exact_match.get('id')
            if location_id:
                location_details = await fetch_location_details(location_id)
                if location_details: # Ensure details were actually fetched
                    return {'status': 'exact', 'data': location_details}
                else:
                    # If fetching details failed for some reason, fallback to suggestions
                    # but prioritize the "exact match" from autocomplete if it's the only one
                    if len(autocomplete_results) == 1:
                         return {'status': 'suggestions', 'data': [exact_match]} # Treat as suggestion
                    # Or if details failed, but other suggestions exist, return all suggestions
                    return {'status': 'suggestions', 'data': autocomplete_results[:5]}


        # No exact match found, return up to 5 suggestions
        return {'status': 'suggestions', 'data': autocomplete_results[:5]}

    except Exception as e:
        logger.error(f"Error in search_location_by_name for '{location_name}': {e}")
        # Fallback to not_found in case of unexpected errors during the process
        return {'status': 'not_found', 'data': None}


async def geocode_city_name(city_name: str) -> Dict[str, Any]:
    """
    Geocode a city name to latitude/longitude coordinates using Open-Meteo API
    Returns: {'status': 'success', 'lat': float, 'lon': float, 'display_name': str} or {'status': 'error', 'message': str}
    """
    try:
        # Input sanitization
        if not city_name or not isinstance(city_name, str):
            return {'status': 'error', 'message': 'City name must be a non-empty string'}
        
        city_name = city_name.strip()
        if len(city_name) > 200:  # Reasonable limit for city names
            return {'status': 'error', 'message': 'City name too long (max 200 characters)'}
        
        # Remove potentially dangerous characters
        if any(char in city_name for char in ['<', '>', '"', "'", '&', '\n', '\r', '\t']):
            return {'status': 'error', 'message': 'City name contains invalid characters'}
        
        # Try multiple formats if the first one fails
        search_terms = [
            city_name,  # Original format
        ]
        
        # If there's a comma, try variations
        if ',' in city_name:
            # Try without comma
            search_terms.append(city_name.replace(',', ' ').strip())
            
            # Try just the city name (first part before comma)
            city_part = city_name.split(',')[0].strip()
            if city_part not in search_terms:
                search_terms.append(city_part)
        
        # If there are US state abbreviations, try with full state names
        state_mapping = {
            'TX': 'Texas', 'CA': 'California', 'NY': 'New York', 'FL': 'Florida',
            'PA': 'Pennsylvania', 'IL': 'Illinois', 'OH': 'Ohio', 'GA': 'Georgia',
            'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey', 'VA': 'Virginia',
            'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts', 'TN': 'Tennessee',
            'IN': 'Indiana', 'MD': 'Maryland', 'MO': 'Missouri', 'WI': 'Wisconsin',
            'CO': 'Colorado', 'MN': 'Minnesota', 'SC': 'South Carolina', 'AL': 'Alabama',
            'LA': 'Louisiana', 'KY': 'Kentucky', 'OR': 'Oregon', 'OK': 'Oklahoma'
        }
        
        # Handle state abbreviations more intelligently  
        for state_abbr, state_full in state_mapping.items():
            if f' {state_abbr.upper()}' in f' {city_name.upper()}' or f' {state_abbr.lower()}' in f' {city_name.lower()}':
                # Try the full state name version
                expanded = city_name.replace(state_abbr, state_full).replace(state_abbr.lower(), state_full).replace(',', ' ')
                search_terms.append(' '.join(expanded.split()))
                
                # Also try just the city name without the state
                city_parts = city_name.split()
                if len(city_parts) > 1:
                    for i, part in enumerate(city_parts):
                        if part.upper() == state_abbr.upper() or part.lower() == state_abbr.lower():
                            city_only = ' '.join(city_parts[:i] + city_parts[i+1:]).strip()
                            if city_only and city_only not in search_terms:
                                search_terms.append(city_only)
        
        # If there are multiple spaces, also try with single spaces
        normalized = ' '.join(city_name.split())
        if normalized not in search_terms:
            search_terms.append(normalized)
        
        for search_term in search_terms:
            encoded_city = urllib.parse.quote(search_term)
            url = f'https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=5'
            
            response = await rate_limited_request(url)
            data = response.json()
            
            results = data.get('results', [])
            if results:
                # Use the first result
                location = results[0]
                return {
                    'status': 'success',
                    'lat': location['latitude'],
                    'lon': location['longitude'], 
                    'display_name': f"{location['name']}, {location.get('admin1', '')}, {location.get('country', '')}".strip(', ')
                }
        
        return {'status': 'error', 'message': f"No results found for city: {city_name}"}
        
    except Exception as e:
        logger.error(f"Error geocoding city '{city_name}': {e}")
        return {'status': 'error', 'message': f"Geocoding failed: {str(e)}"}
