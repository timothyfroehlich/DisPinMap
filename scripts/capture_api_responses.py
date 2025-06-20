#!/usr/bin/env python3
"""
API Response Capture Script

This script captures real API responses from pinballmap.com and geocoding services
for use in simulation testing. It saves responses in a structured format that can
be used to create realistic mocks.

Usage:
    python scripts/capture_api_responses.py

The script will:
1. Make real API calls to gather various response types
2. Save responses as JSON files in tests/fixtures/api_responses/
3. Create both success and error scenarios
4. Generate variations for different data scenarios
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
    fetch_submissions_for_coordinates,
    fetch_submissions_for_location,
    geocode_city_name,
    search_location_by_name,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Response storage directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "api_responses"


class APIResponseCapture:
    """Captures and saves API responses for testing."""

    def __init__(self):
        self.responses = {}
        self.session_timestamp = datetime.now().isoformat()

    def save_response(
        self,
        category: str,
        name: str,
        response_data: Any,
        metadata: Optional[Dict] = None,
    ):
        """Save a response to the fixtures directory."""
        if category not in self.responses:
            self.responses[category] = {}

        # Create response record
        response_record = {
            "captured_at": self.session_timestamp,
            "name": name,
            "metadata": metadata or {},
            "data": response_data,
        }

        self.responses[category][name] = response_record

        # Also save individual file
        category_dir = FIXTURES_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{name}.json"
        filepath = category_dir / filename

        with open(filepath, "w") as f:
            json.dump(response_record, f, indent=2, default=str)

        logger.info(f"Saved {category}/{name} response to {filepath}")

    async def capture_pinballmap_responses(self):
        """Capture various PinballMap API responses."""
        logger.info("Capturing PinballMap API responses...")

        # Test location IDs and names to capture
        test_locations = [
            {"id": 1, "name": "Shorty's"},  # Known Seattle location
            {"id": 2, "name": "Add-a-Ball Amusements"},  # Known location
            {"id": 999999, "name": "NonexistentLocation"},  # For error testing
        ]

        test_searches = [
            "Seattle",
            "Dave and Busters",
            "Nonexistent Location Name",
            "Pin",  # Short search term
        ]

        # Capture location details
        for location in test_locations:
            try:
                details = await fetch_location_details(location["id"])
                self.save_response(
                    "pinballmap_locations",
                    f"location_{location['id']}_details",
                    details,
                    {"location_id": location["id"], "expected_name": location["name"]},
                )
            except Exception as e:
                logger.error(f"Failed to fetch location {location['id']}: {e}")
                # Save error response
                self.save_response(
                    "pinballmap_locations",
                    f"location_{location['id']}_error",
                    {"error": str(e), "type": type(e).__name__},
                    {"location_id": location["id"], "is_error": True},
                )

        # Capture location search responses
        for search_term in test_searches:
            try:
                result = await search_location_by_name(search_term)
                self.save_response(
                    "pinballmap_search",
                    f"search_{search_term.replace(' ', '_').lower()}",
                    result,
                    {"search_term": search_term},
                )
            except Exception as e:
                logger.error(f"Failed to search for '{search_term}': {e}")
                self.save_response(
                    "pinballmap_search",
                    f"search_{search_term.replace(' ', '_').lower()}_error",
                    {"error": str(e), "type": type(e).__name__},
                    {"search_term": search_term, "is_error": True},
                )

        # Capture submissions for locations
        test_submission_locations = [1, 2]  # Use known good location IDs

        for location_id in test_submission_locations:
            try:
                # Recent submissions (for monitoring)
                recent_submissions = await fetch_submissions_for_location(
                    location_id, use_min_date=True
                )
                self.save_response(
                    "pinballmap_submissions",
                    f"location_{location_id}_recent",
                    recent_submissions,
                    {"location_id": location_id, "use_min_date": True},
                )

                # All submissions (for initial checks)
                all_submissions = await fetch_submissions_for_location(
                    location_id, use_min_date=False
                )
                self.save_response(
                    "pinballmap_submissions",
                    f"location_{location_id}_all",
                    all_submissions,
                    {"location_id": location_id, "use_min_date": False},
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch submissions for location {location_id}: {e}"
                )

        # Capture coordinate-based submissions
        test_coordinates = [
            {
                "lat": 47.6062,
                "lon": -122.3321,
                "radius": None,
                "name": "seattle_center",
            },
            {"lat": 47.6062, "lon": -122.3321, "radius": 5, "name": "seattle_5mi"},
            {
                "lat": 40.7589,
                "lon": -73.9851,
                "radius": 10,
                "name": "times_square_10mi",
            },
        ]

        for coord in test_coordinates:
            try:
                recent_submissions = await fetch_submissions_for_coordinates(
                    coord["lat"], coord["lon"], coord["radius"], use_min_date=True
                )
                self.save_response(
                    "pinballmap_submissions",
                    f"coords_{coord['name']}_recent",
                    recent_submissions,
                    {
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "radius": coord["radius"],
                        "use_min_date": True,
                    },
                )

                all_submissions = await fetch_submissions_for_coordinates(
                    coord["lat"], coord["lon"], coord["radius"], use_min_date=False
                )
                self.save_response(
                    "pinballmap_submissions",
                    f"coords_{coord['name']}_all",
                    all_submissions,
                    {
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "radius": coord["radius"],
                        "use_min_date": False,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch coordinate submissions for {coord['name']}: {e}"
                )

    async def capture_geocoding_responses(self):
        """Capture geocoding API responses."""
        logger.info("Capturing geocoding API responses...")

        test_cities = [
            "Seattle, WA",
            "New York, NY",
            "Los Angeles, CA",
            "Portland, OR",
            "Chicago, IL",
            "Seattle",  # Without state
            "Portland",  # Ambiguous city name
            "Nonexistent City, XX",  # Error case
            "InvalidCityName123",  # Error case
        ]

        for city in test_cities:
            try:
                result = await geocode_city_name(city)
                self.save_response(
                    "geocoding",
                    f"city_{city.replace(' ', '_').replace(',', '').lower()}",
                    result,
                    {"city_input": city},
                )
            except Exception as e:
                logger.error(f"Failed to geocode '{city}': {e}")
                self.save_response(
                    "geocoding",
                    f"city_{city.replace(' ', '_').replace(',', '').lower()}_error",
                    {"error": str(e), "type": type(e).__name__},
                    {"city_input": city, "is_error": True},
                )

    def save_master_index(self):
        """Save a master index of all captured responses."""
        index = {
            "capture_session": {
                "timestamp": self.session_timestamp,
                "captured_categories": list(self.responses.keys()),
                "total_responses": sum(len(cat) for cat in self.responses.values()),
            },
            "categories": {},
        }

        for category, responses in self.responses.items():
            index["categories"][category] = {
                "count": len(responses),
                "responses": [
                    {
                        "name": name,
                        "captured_at": resp["captured_at"],
                        "metadata": resp["metadata"],
                    }
                    for name, resp in responses.items()
                ],
            }

        index_path = FIXTURES_DIR / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2, default=str)

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
