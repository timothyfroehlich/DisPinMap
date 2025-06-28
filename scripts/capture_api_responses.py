#!/usr/bin/env python3
"""
API Response Capture Script

This script captures real API responses from pinballmap.com and geocoding services
for use in simulation testing. It saves responses as raw JSON files and updates a
master index.

Usage:
    python scripts/capture_api_responses.py

The script will:
1. Make real API calls to gather various response types.
2. Save responses as raw JSON files in tests/fixtures/api_responses/.
3. Update the master index file (index.json).
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path for imports - noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api import (  # noqa: E402
    fetch_location_details,
    fetch_submissions_for_location,
    geocode_city_name,
    search_location_by_name,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Response storage directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "api_responses"

# Base URLs for API endpoints
BASE_URLS = {
    "pinballmap": "https://pinballmap.com/api/v1",
    "geocoding": "https://geocoding-api.open-meteo.com/v1",
}


class APIResponseCapture:
    """Captures and saves API responses for testing."""

    def __init__(self):
        self.index_data: Dict[str, Dict[str, Any]] = {
            "pinballmap_search": {
                "description": "Location search responses from pinballmap.com API",
                "count": 0,
                "responses": [],
            },
            "pinballmap_locations": {
                "description": "Location detail responses from pinballmap.com API",
                "count": 0,
                "responses": [],
            },
            "pinballmap_submissions": {
                "description": "User submission responses from pinballmap.com API",
                "count": 0,
                "responses": [],
            },
            "geocoding": {
                "description": "Geocoding responses from Open-Meteo API",
                "count": 0,
                "responses": [],
            },
        }
        self.session_timestamp = datetime.utcnow().isoformat() + "Z"

    def save_response(
        self,
        category: str,
        name: str,
        response_data: Any,
        url: str,
        description: str,
    ):
        """Save a response to the fixtures directory and update index data."""
        # Save individual file as raw JSON
        category_dir = FIXTURES_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        filepath = category_dir / f"{name}.json"

        # Match indentation of existing files
        indent: Optional[int] = 4
        if category == "geocoding" and "nonexistent" in name:
            indent = None
        elif category == "geocoding":
            indent = 4

        with open(filepath, "w") as f:
            json.dump(response_data, f, indent=indent)

        logger.info(f"Saved {category}/{name} response to {filepath}")

        # Update index data
        response_info = {"name": name, "url": url, "description": description}

        # Avoid duplicates in index
        if not any(r["name"] == name for r in self.index_data[category]["responses"]):
            self.index_data[category]["responses"].append(response_info)

    async def capture_pinballmap_responses(self):
        """Capture various PinballMap API responses."""
        logger.info("Capturing PinballMap API responses...")

        # From existing fixtures
        test_locations = [
            {"id": 874, "name": "Ground Kontrol Classic Arcade"},
            {"id": 1309, "name": "Seattle Pinball Museum"},
            {"id": 999999, "name": "NonexistentLocation"},  # For error testing
        ]

        test_searches = [
            "Seattle",
            "Ground Kontrol",
            "Dave and Busters",
            "NonexistentLocationName123",
            "Pin",
        ]

        # Capture location details
        for location in test_locations:
            url = f"{BASE_URLS['pinballmap']}/locations/{location['id']}.json"
            try:
                details = await fetch_location_details(location["id"])
                desc = (
                    f"{location['name']} details"
                    if "Nonexistent" not in location["name"]
                    else "Error response for nonexistent location"
                )
                self.save_response(
                    "pinballmap_locations",
                    f"location_{location['id']}_details",
                    details,
                    url,
                    desc,
                )
            except Exception as e:
                logger.error(f"Failed to fetch location {location['id']}: {e}")

        # Capture location search responses
        for search_term in test_searches:
            url = f"{BASE_URLS['pinballmap']}/locations.json?by_location_name={search_term.replace(' ', '%20')}"
            try:
                result = await search_location_by_name(search_term)
                name_slug = search_term.replace(" ", "_").lower()
                if search_term == "Ground Kontrol":
                    name_slug = "ground_kontrol_single_result"
                elif search_term == "NonexistentLocationName123":
                    name_slug = "nonexistent_location_name"

                descriptions = {
                    "Seattle": "Multiple location results for Seattle search",
                    "Ground Kontrol": "Single result for Ground Kontrol search",
                    "Dave and Busters": "Multiple Dave & Busters locations",
                    "NonexistentLocationName123": "Empty results for nonexistent location",
                    "Pin": "Multiple results for short search term 'Pin'",
                }
                self.save_response(
                    "pinballmap_search",
                    f"search_{name_slug}",
                    result,
                    url,
                    descriptions.get(
                        search_term, f"Search results for '{search_term}'"
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to search for '{search_term}': {e}")

        # Capture submissions for locations
        # Existing fixtures: 874, 1309
        for location_id in [874, 1309]:
            url = f"{BASE_URLS['pinballmap']}/user_submissions/location.json?id={location_id}"
            try:
                # Recent submissions (for monitoring)
                recent_submissions = await fetch_submissions_for_location(
                    location_id, use_min_date=True
                )
                location_name = (
                    "Ground Kontrol" if location_id == 874 else "Seattle Pinball Museum"
                )
                self.save_response(
                    "pinballmap_submissions",
                    f"location_{location_id}_recent",
                    recent_submissions,
                    url,
                    f"Recent submissions for {location_name}",
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch submissions for location {location_id}: {e}"
                )

        # Manually add empty submission fixture
        self.save_response(
            "pinballmap_submissions",
            "location_874_empty",
            {"user_submissions": []},
            "",  # No URL for manual fixture
            "Manually created empty submissions response for testing",
        )

    async def capture_geocoding_responses(self):
        """Capture geocoding API responses."""
        logger.info("Capturing geocoding API responses...")

        # Based on existing fixtures
        test_cities = [
            "Seattle",
            "Portland",
            "Chicago",
            "NonexistentCity123",
            "Portland, OR",  # Specific query
        ]

        for city in test_cities:
            url = f"{BASE_URLS['geocoding']}/search?name={city.split(',')[0]}&count=5&format=json"
            try:
                result = await geocode_city_name(city)

                name_slug = city.replace(", ", "_").replace(" ", "_").lower()
                if name_slug == "nonexistentcity123":
                    name_slug = "nonexistent"

                descriptions = {
                    "Seattle": "Geocoding results for Seattle",
                    "Portland": "Geocoding results for Portland",
                    "Chicago": "Geocoding results for Chicago",
                    "NonexistentCity123": "Empty results for nonexistent city",
                    "Portland, OR": "Geocoding results for Portland, OR",
                }

                self.save_response(
                    "geocoding",
                    f"city_{name_slug}",
                    result,
                    url,
                    descriptions.get(city, f"Geocoding results for {city}"),
                )
            except Exception as e:
                logger.error(f"Failed to geocode '{city}': {e}")

    def save_master_index(self):
        """Save a master index of all captured responses."""
        # Update counts
        for category in self.index_data:
            self.index_data[category]["count"] = len(
                self.index_data[category]["responses"]
            )

        index = {
            "capture_session": {
                "timestamp": self.session_timestamp,
                "description": "All fixtures are authentic, unmodified API responses",
                "total_responses": sum(
                    cat["count"] for cat in self.index_data.values()
                ),
            },
            "categories": self.index_data,
        }

        index_path = FIXTURES_DIR / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

        logger.info(f"Saved master index to {index_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("API Response Capture Complete!")
        print("=" * 60)
        print(f"Capture session: {self.session_timestamp}")
        print(
            f"Total responses captured: {index['capture_session']['total_responses']}"
        )
        print("\nCategories:")
        for category, info in index["categories"].items():
            print(f"  {category}: {info['count']} responses")
        print(f"\nResponses saved to: {FIXTURES_DIR}")
        print("=" * 60)


async def main():
    """Main capture function."""
    logger.info("Starting API response capture...")

    # Ensure fixtures directory exists
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    capturer = APIResponseCapture()

    try:
        await capturer.capture_pinballmap_responses()
        await capturer.capture_geocoding_responses()
        capturer.save_master_index()

    except Exception as e:
        logger.error(f"Capture failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
