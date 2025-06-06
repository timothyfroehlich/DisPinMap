"""
API module for Discord Pinball Map Bot
Handles pinballmap.com API interactions using the new user submissions endpoints
"""

import requests
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any


async def rate_limited_request(url: str, max_retries: int = 3, base_delay: float = 1.0) -> requests.Response:
    """Make a rate-limited request with exponential backoff"""
    # Extract endpoint for cleaner debug message
    endpoint = url.split('/')[-1].split('.json')[0]
    print(f"🌐 API: {endpoint}")

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
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
                print(f"Request failed, retrying in {delay} seconds: {e}")
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


async def fetch_submissions_for_coordinates(lat: float, lon: float, radius_miles: int) -> List[Dict[str, Any]]:
    """Fetch user submissions within radius of given coordinates"""
    try:
        yesterday = get_yesterday_date()
        url = f'https://pinballmap.com/api/v1/user_submissions/list_within_range.json?lat={lat}&lon={lon}&max_distance={radius_miles}&min_date_of_submission={yesterday}'

        response = await rate_limited_request(url)
        data = response.json()

        return data.get('user_submissions', [])

    except Exception as e:
        print(f"Error fetching submissions for coordinates {lat}, {lon}: {e}")
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
        print(f"Error fetching submissions for location {location_id}: {e}")
        return []


async def fetch_location_autocomplete(query: str) -> List[Dict[str, Any]]:
    """Fetch location suggestions using by_location_name search"""
    try:
        # Use the working API endpoint instead of autocomplete
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f'https://pinballmap.com/api/v1/locations.json?by_location_name={encoded_query}'
        response = await rate_limited_request(url)
        data = response.json()
        return data.get('locations', [])
    except Exception as e:
        print(f"Error fetching location autocomplete for '{query}': {e}")
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
        print(f"Error fetching location details for ID {location_id}: {e}")
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
        print(f"Error in search_location_by_name for '{location_name}': {e}")
        # Fallback to not_found in case of unexpected errors during the process
        return {'status': 'not_found', 'data': None}


# Legacy function removed - test simulation no longer supported
