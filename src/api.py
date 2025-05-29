"""
API module for Discord Pinball Map Bot
Handles pinballmap.com API interactions and location-based machine searches
"""

import requests
import math
import time
import asyncio
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


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


async def fetch_machines_for_location(lat: float, lon: float, radius_miles: int) -> List[Dict[str, Any]]:
    """Fetch machines within radius of given location"""
    try:
        # Get all regions first to find which ones might contain our area
        response = await rate_limited_request('https://pinballmap.com/api/v1/regions.json')
        regions = response.json()['regions']
        
        all_machines = []
        
        # Check each region (for now we'll use a simple approach)
        for region in regions:
            try:
                # Fetch locations for this region
                locations_response = await rate_limited_request(f'https://pinballmap.com/api/v1/region/{region["name"]}/locations.json')
                locations_data = locations_response.json()['locations']
                
                # Filter locations by distance
                for location in locations_data:
                    if location.get('lat') and location.get('lon'):
                        distance = calculate_distance(lat, lon, float(location['lat']), float(location['lon']))
                        
                        if distance <= radius_miles and location.get('machine_count', 0) > 0:
                            # Fetch detailed machine info for this location
                            try:
                                machines_response = await rate_limited_request(f'https://pinballmap.com/api/v1/location/{location["id"]}/machine_details.json')
                                machines_data = machines_response.json()['machines']
                                
                                for machine in machines_data:
                                    all_machines.append({
                                        'location_id': location['id'],
                                        'location_name': location['name'],
                                        'machine_id': machine['id'],
                                        'machine_name': machine.get('name', 'Unknown'),
                                        'manufacturer': machine.get('manufacturer'),
                                        'year': machine.get('year')
                                    })
                                    
                            except requests.exceptions.HTTPError as e:
                                if e.response.status_code == 404:
                                    # Location has no machine details available
                                    continue
                                else:
                                    raise
                            except requests.RequestException:
                                # Skip this location if we can't get machine details
                                continue
                                
            except requests.RequestException:
                # Skip this region if we can't fetch data
                continue
                
        return all_machines
        
    except Exception as e:
        print(f"Error fetching machines: {e}")
        return []


async def get_all_regions() -> List[Dict[str, Any]]:
    """Get list of all available regions"""
    try:
        response = await rate_limited_request('https://pinballmap.com/api/v1/regions.json')
        return response.json()['regions']
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch regions: {e}")


async def find_region_by_name(region_name: str) -> Dict[str, Any]:
    """Find a region by name (case-insensitive, partial match)"""
    regions = await get_all_regions()
    region_name_lower = region_name.lower().strip()
    
    # Try exact match first
    for region in regions:
        if region['name'].lower() == region_name_lower:
            return region
    
    # Try partial match
    matches = []
    for region in regions:
        if region_name_lower in region['name'].lower():
            matches.append(region)
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        region_names = [r['name'] for r in matches]
        raise Exception(f"Multiple regions found: {', '.join(region_names)}. Please be more specific.")
    else:
        raise Exception(f"No region found matching '{region_name}'. Use !regions to see all available regions.")


async def fetch_region_machines(region_name: str) -> List[Dict[str, Any]]:
    """Fetch machines from a specific region"""
    try:
        response = await rate_limited_request(f'https://pinballmap.com/api/v1/region/{region_name}/locations.json')
        locations = response.json()['locations']
        
        all_machines = []
        for location in locations:
            if location.get('machine_count', 0) > 0:
                try:
                    machines_response = await rate_limited_request(f'https://pinballmap.com/api/v1/location/{location["id"]}/machine_details.json')
                    machines_data = machines_response.json()['machines']
                    
                    for machine in machines_data:
                        all_machines.append({
                            'location_id': location['id'],
                            'location_name': location['name'],
                            'machine_id': machine['id'],
                            'machine_name': machine.get('name', 'Unknown'),
                            'manufacturer': machine.get('manufacturer'),
                            'year': machine.get('year')
                        })
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # Location has no machine details available
                        continue
                    else:
                        raise
                except requests.RequestException:
                    # Skip this location if we can't get machine details for other reasons
                    continue
        
        return all_machines
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch machines from region '{region_name}': {e}")


async def search_location_by_name(location_name: str) -> List[Dict[str, Any]]:
    """Search for specific pinball locations by name across all regions"""
    try:
        regions = await get_all_regions()
        matching_locations = []
        location_name_lower = location_name.lower().strip()
        
        # Search through all regions for matching location names
        for region in regions:
            try:
                response = await rate_limited_request(f'https://pinballmap.com/api/v1/region/{region["name"]}/locations.json')
                locations = response.json()['locations']
                
                for location in locations:
                    if location_name_lower in location.get('name', '').lower():
                        location['region_name'] = region['name']
                        matching_locations.append(location)
                        
            except requests.RequestException:
                # Skip this region if we can't fetch data
                continue
        
        return matching_locations
    except Exception as e:
        raise Exception(f"Failed to search for location '{location_name}': {e}")


async def fetch_location_machines(location_id: int, region_name: str) -> List[Dict[str, Any]]:
    """Fetch machines from a specific location"""
    try:
        response = await rate_limited_request(f'https://pinballmap.com/api/v1/location/{location_id}/machine_details.json')
        machines_data = response.json()['machines']
        
        # Get location info
        location_response = await rate_limited_request(f'https://pinballmap.com/api/v1/region/{region_name}/locations.json')
        locations = location_response.json()['locations']
        
        location_info = next((loc for loc in locations if loc['id'] == location_id), None)
        location_name = location_info['name'] if location_info else f"Location {location_id}"
        
        all_machines = []
        for machine in machines_data:
            all_machines.append({
                'location_id': location_id,
                'location_name': location_name,
                'machine_id': machine['id'],
                'machine_name': machine.get('name', 'Unknown'),
                'manufacturer': machine.get('manufacturer'),
                'year': machine.get('year')
            })
        
        return all_machines
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch machines from location {location_id}: {e}")


async def fetch_austin_machines() -> Dict[str, Any]:
    """Fetch machines from Austin region (for compatibility)"""
    try:
        response = await rate_limited_request('https://pinballmap.com/api/v1/region/austin/locations.json')
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Austin machines: {e}")