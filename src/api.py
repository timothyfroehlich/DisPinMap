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


async def search_location_by_name(location_name: str) -> List[Dict[str, Any]]:
    """Search for locations by name using coordinate search across major cities"""
    # Major US cities coordinates for searching
    major_cities = [
        {"name": "New York", "lat": 40.7128, "lon": -74.0060},
        {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
        {"name": "Chicago", "lat": 41.8781, "lon": -87.6298},
        {"name": "Houston", "lat": 29.7604, "lon": -95.3698},
        {"name": "Phoenix", "lat": 33.4484, "lon": -112.0740},
        {"name": "Philadelphia", "lat": 39.9526, "lon": -75.1652},
        {"name": "San Antonio", "lat": 29.4241, "lon": -98.4936},
        {"name": "San Diego", "lat": 32.7157, "lon": -117.1611},
        {"name": "Dallas", "lat": 32.7767, "lon": -96.7970},
        {"name": "San Jose", "lat": 37.3382, "lon": -121.8863},
        {"name": "Austin", "lat": 30.2672, "lon": -97.7431},
        {"name": "Jacksonville", "lat": 30.3322, "lon": -81.6557},
        {"name": "Fort Worth", "lat": 32.7555, "lon": -97.3308},
        {"name": "Columbus", "lat": 39.9612, "lon": -82.9988},
        {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194},
        {"name": "Charlotte", "lat": 35.2271, "lon": -80.8431},
        {"name": "Indianapolis", "lat": 39.7684, "lon": -86.1581},
        {"name": "Seattle", "lat": 47.6062, "lon": -122.3321},
        {"name": "Denver", "lat": 39.7392, "lon": -104.9903},
        {"name": "Boston", "lat": 42.3601, "lon": -71.0589},
    ]
    
    matching_locations = []
    location_name_lower = location_name.lower().strip()
    
    try:
        # Search in each major city area
        for city in major_cities:
            try:
                # Search with a large radius to cover metro area
                submissions = await fetch_submissions_for_coordinates(city["lat"], city["lon"], 50)
                
                # Filter submissions to find matching location names
                seen_locations = set()
                for submission in submissions:
                    sub_location_name = submission.get('location_name', '')
                    location_id = submission.get('location_id')
                    
                    if (location_name_lower in sub_location_name.lower() and 
                        location_id and 
                        location_id not in seen_locations):
                        
                        matching_locations.append({
                            'location_id': location_id,
                            'location_name': sub_location_name,
                            'city_name': submission.get('city_name', city["name"]),
                            'lat': submission.get('lat'),
                            'lon': submission.get('lon')
                        })
                        seen_locations.add(location_id)
                        
            except Exception:
                # Skip this city if there's an error
                continue
        
        # Remove duplicates and sort by name
        unique_locations = []
        seen_ids = set()
        for loc in matching_locations:
            if loc['location_id'] not in seen_ids:
                unique_locations.append(loc)
                seen_ids.add(loc['location_id'])
        
        return sorted(unique_locations, key=lambda x: x['location_name'])
        
    except Exception as e:
        raise Exception(f"Failed to search for location '{location_name}': {e}")


# Legacy function for compatibility (used in test simulation)
async def fetch_austin_machines() -> Dict[str, Any]:
    """Fetch submissions from Austin area (for compatibility with existing test code)"""
    try:
        # Austin coordinates
        submissions = await fetch_submissions_for_coordinates(30.2672, -97.7431, 25)
        
        # Convert to legacy format expected by test code
        locations = []
        seen_locations = set()
        
        for submission in submissions:
            location_id = submission.get('location_id')
            if location_id and location_id not in seen_locations:
                locations.append({
                    'id': location_id,
                    'name': submission.get('location_name', f'Location {location_id}'),
                    'lat': submission.get('lat'),
                    'lon': submission.get('lon'),
                    'machine_count': 1  # Simplified
                })
                seen_locations.add(location_id)
        
        return {'locations': locations}
        
    except Exception as e:
        raise Exception(f"Failed to fetch Austin submissions: {e}")