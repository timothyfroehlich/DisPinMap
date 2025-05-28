"""
API module for Discord Pinball Map Bot
Handles pinballmap.com API interactions and location-based machine searches
"""

import requests
import math
from typing import List, Dict, Any


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
        response = requests.get('https://pinballmap.com/api/v1/regions.json')
        response.raise_for_status()
        regions = response.json()['regions']
        
        all_machines = []
        
        # Check each region (for now we'll use a simple approach)
        for region in regions:
            try:
                # Fetch locations for this region
                locations_response = requests.get(f'https://pinballmap.com/api/v1/region/{region["name"]}/locations.json')
                locations_response.raise_for_status()
                locations_data = locations_response.json()['locations']
                
                # Filter locations by distance
                for location in locations_data:
                    if location.get('lat') and location.get('lon'):
                        distance = calculate_distance(lat, lon, float(location['lat']), float(location['lon']))
                        
                        if distance <= radius_miles and location.get('machine_count', 0) > 0:
                            # Fetch detailed machine info for this location
                            try:
                                machines_response = requests.get(f'https://pinballmap.com/api/v1/location/{location["id"]}/machine_details.json')
                                machines_response.raise_for_status()
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
        response = requests.get('https://pinballmap.com/api/v1/regions.json')
        response.raise_for_status()
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
        response = requests.get(f'https://pinballmap.com/api/v1/region/{region_name}/locations.json')
        response.raise_for_status()
        locations = response.json()['locations']
        
        all_machines = []
        for location in locations:
            if location.get('machine_count', 0) > 0:
                try:
                    machines_response = requests.get(f'https://pinballmap.com/api/v1/location/{location["id"]}/machine_details.json')
                    machines_response.raise_for_status()
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
                except requests.RequestException:
                    # Skip this location if we can't get machine details
                    continue
        
        return all_machines
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch machines from region '{region_name}': {e}")


async def fetch_austin_machines() -> Dict[str, Any]:
    """Fetch machines from Austin region (for compatibility)"""
    try:
        response = requests.get('https://pinballmap.com/api/v1/region/austin/locations.json')
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Austin machines: {e}")