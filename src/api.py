"""
API module for Discord Pinball Map Bot
Handles pinballmap.com API interactions using the new user submissions endpoints
"""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Map of US state abbreviations to full names (case-insensitive)
US_STATE_MAP = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}


def parse_city_input(city_input: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse city input to extract city name, state, and country.
    Returns (city_name, state, country)
    """
    # Remove any extra whitespace
    city_input = city_input.strip()

    # Try to match patterns like:
    # "City, State" or "City, Country" or "City, State, Country"
    parts = [part.strip() for part in city_input.split(",")]

    if len(parts) == 1:
        return parts[0], None, None

    city_name = parts[0]
    state = None
    country = None

    # If we have 2 parts, it could be either state or country
    if len(parts) == 2:
        second_part = parts[1].upper()
        # Check if it's a US state
        if second_part in US_STATE_MAP:
            state = US_STATE_MAP[second_part]
        else:
            country = second_part

    # If we have 3 parts, assume it's city, state, country
    elif len(parts) >= 3:
        state_part = parts[1].upper()
        if state_part in US_STATE_MAP:
            state = US_STATE_MAP[state_part]
        country = parts[2].upper()

    return city_name, state, country


def match_location(
    location: Dict[str, Any], target_state: Optional[str], target_country: Optional[str]
) -> bool:
    """Check if a location matches the target state and/or country"""
    if target_state and location.get("admin1"):
        if location["admin1"].lower() != target_state.lower():
            return False

    if target_country and location.get("country_code"):
        if location["country_code"].upper() != target_country.upper():
            return False

    return True


async def rate_limited_request(
    url: str, max_retries: int = 3, base_delay: float = 1.0
) -> requests.Response:
    """Make a rate-limited request with exponential backoff"""
    # Extract endpoint for cleaner debug message
    endpoint = url.split("/")[-1].split(".json")[0]
    logger.info(f"🌐 API: {endpoint}")

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}"
                    )
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
                delay = base_delay * (2**attempt)
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
    return yesterday.strftime("%Y-%m-%d")


async def fetch_submissions_for_coordinates(
    lat: float,
    lon: float,
    radius_miles: Optional[int] = None,
    use_min_date: bool = True,
) -> List[Dict[str, Any]]:
    """Fetch user submissions within radius of given coordinates"""
    try:
        yesterday = get_yesterday_date()
        if radius_miles is not None:
            url = f"https://pinballmap.com/api/v1/user_submissions/list_within_range.json?lat={lat}&lon={lon}&max_distance={radius_miles}"
        else:
            url = f"https://pinballmap.com/api/v1/user_submissions/list_within_range.json?lat={lat}&lon={lon}"
        if use_min_date:
            url += f"&min_date_of_submission={yesterday}"

        response = await rate_limited_request(url)
        data = response.json()

        return data.get("user_submissions", [])

    except Exception as e:
        logger.error(f"Error fetching submissions for coordinates {lat}, {lon}: {e}")
        return []


async def fetch_submissions_for_location(
    location_id: int, use_min_date: bool = True
) -> List[Dict[str, Any]]:
    """Fetch user submissions for a specific location"""
    try:
        yesterday = get_yesterday_date()
        url = f"https://pinballmap.com/api/v1/user_submissions/location.json?id={location_id}"
        if use_min_date:
            url += f"&min_date_of_submission={yesterday}"

        response = await rate_limited_request(url)
        data = response.json()

        # Check for errors
        if "errors" in data:
            raise Exception(f"Location {location_id} not found: {data['errors']}")

        return data.get("user_submissions", [])

    except Exception as e:
        logger.error(f"Error fetching submissions for location {location_id}: {e}")
        return []


async def fetch_location_autocomplete(query: str) -> List[Dict[str, Any]]:
    """Fetch location suggestions using by_location_name search"""
    try:
        # Use the working API endpoint instead of autocomplete
        encoded_query = urllib.parse.quote(query)
        url = f"https://pinballmap.com/api/v1/locations.json?by_location_name={encoded_query}"
        response = await rate_limited_request(url)
        data = response.json()
        return data.get("locations", [])
    except Exception as e:
        logger.error(f"Error fetching location autocomplete for '{query}': {e}")
        return []


async def fetch_location_details(location_id: int) -> Dict[str, Any]:
    """Fetch full details for a specific location ID"""
    try:
        url = f"https://pinballmap.com/api/v1/locations/{location_id}.json"
        response = await rate_limited_request(url)
        data = response.json()
        if (
            "errors" in data
        ):  # PinballMap API returns errors in a list for this endpoint
            error_message = (
                data["errors"][0]
                if isinstance(data["errors"], list) and data["errors"]
                else str(data["errors"])
            )
            raise Exception(
                f"Location details for {location_id} not found: {error_message}"
            )
        return (
            data  # The location data is at the root level, not under a 'location' key
        )
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
            return {"status": "not_found", "data": None}

        exact_match = None
        for loc in autocomplete_results:
            if loc.get("name", "").lower() == location_name_lower:
                exact_match = loc
                break

        if exact_match:
            location_id = exact_match.get("id")
            if location_id:
                location_details = await fetch_location_details(location_id)
                if location_details:  # Ensure details were actually fetched
                    return {"status": "exact", "data": location_details}
                else:
                    # If fetching details failed for some reason, fallback to suggestions
                    # but prioritize the "exact match" from autocomplete if it's the only one
                    if len(autocomplete_results) == 1:
                        return {
                            "status": "suggestions",
                            "data": [exact_match],
                        }  # Treat as suggestion
                    # Or if details failed, but other suggestions exist, return all suggestions
                    return {"status": "suggestions", "data": autocomplete_results[:5]}

        # No exact match found, return up to 5 suggestions
        return {"status": "suggestions", "data": autocomplete_results[:5]}

    except Exception as e:
        logger.error(f"Error in search_location_by_name for '{location_name}': {e}")
        # Fallback to not_found in case of unexpected errors during the process
        return {"status": "not_found", "data": None}


async def geocode_city_name(city_input: str) -> Dict[str, Any]:
    """
    Geocode a city name to latitude/longitude coordinates using Open-Meteo API.
    Supports state/country specification in the input.
    Returns: {'status': 'success', 'lat': float, 'lon': float, 'display_name': str} or {'status': 'error', 'message': str}
    """
    try:
        if not city_input or not isinstance(city_input, str):
            return {
                "status": "error",
                "message": "City name must be a non-empty string.",
            }

        # Parse the input to get city name and optional state/country
        city_name, target_state, target_country = parse_city_input(city_input)

        if not city_name:
            return {
                "status": "error",
                "message": "City name must be a non-empty string.",
            }

        if len(city_name) > 200:
            return {
                "status": "error",
                "message": "City name too long (max 200 characters).",
            }

        invalid_chars = ["<", ">", '"', "'", "&", "\n", "\r", "\t"]
        if any(char in city_name for char in invalid_chars):
            return {
                "status": "error",
                "message": "City name contains invalid characters.",
            }

        # Make the API call with just the city name
        encoded_city = urllib.parse.quote(city_name)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=5&format=json"

        response = await rate_limited_request(url)
        data = response.json()

        results = data.get("results", [])
        if not results:
            return {
                "status": "error",
                "message": f"No results found for city: {city_name}",
            }

        # If state/country was specified, try to find a matching result
        if target_state or target_country:
            matching_results = [
                loc
                for loc in results
                if match_location(loc, target_state, target_country)
            ]
            if matching_results:
                location = matching_results[0]
            else:
                # If no exact match, return all results for user to choose
                suggestions = []
                for loc in results:
                    name_parts = []
                    if loc.get("name"):
                        name_parts.append(str(loc["name"]))
                    if loc.get("admin1"):
                        name_parts.append(str(loc["admin1"]))
                    if loc.get("country_code"):
                        name_parts.append(str(loc["country_code"]))
                    suggestions.append(", ".join(filter(None, name_parts)))

                return {
                    "status": "error",
                    "message": f"Multiple locations found for '{city_name}'. Please specify which one you want:\n"
                    + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(suggestions)),
                }
        else:
            # If no state/country specified, use the first result
            location = results[0]

        # Build the display name
        name_parts = []
        if location.get("name"):
            name_parts.append(str(location["name"]))
        if location.get("admin1"):
            name_parts.append(str(location["admin1"]))
        if location.get("country_code"):
            name_parts.append(str(location["country_code"]))

        display_name = ", ".join(filter(None, name_parts))

        return {
            "status": "success",
            "lat": location["latitude"],
            "lon": location["longitude"],
            "display_name": display_name,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"API request error during geocoding city '{city_input}': {e}")
        return {"status": "error", "message": f"Geocoding API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error geocoding city '{city_input}': {e}")
        return {"status": "error", "message": f"Geocoding failed: {str(e)}"}
