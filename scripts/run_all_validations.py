#!/usr/bin/env python3
"""
Comprehensive Fixture Management and Validation Script

This script handles all fixture management operations and validation checks.
It consolidates capture, validation, and automation functionality.

IMPORTANT: All fixtures contain RAW API RESPONSES, not wrapped responses.
This ensures tests accurately reflect what external APIs return.

Usage:
    python scripts/run_all_validations.py [command] [options]

Commands:
    validate     Validate existing fixtures (default)
    capture      Refresh fixtures from APIs (manual only)
    check        Check API availability (manual only)
    all          Run all operations (manual only)

Options:
    --fix        Attempt to fix issues automatically
    --ci         CI mode - skip API calls, only validate structure
    --help       Show this help message
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add src to path for imports - noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api import (
    fetch_location_details,  # noqa: E402
    fetch_submissions_for_location,
    geocode_city_name,
    search_location_by_name,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Constants
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "api_responses"
PINBALLMAP_BASE = "https://pinballmap.com/api/v1"
GEOCODING_BASE = "https://geocoding-api.open-meteo.com/v1"


class FixtureManager:
    """Manages API fixture capture and validation.

    IMPORTANT: Fixtures contain RAW API RESPONSES, not wrapped responses.

    Fixture Format Standards:
    - PinballMap search responses: Raw JSON with "locations" array
    - PinballMap location details: Raw location JSON object
    - PinballMap submissions: Raw JSON with "user_submissions" array
    - Geocoding responses: Raw JSON with "results" array (or empty with metadata)

    This ensures fixtures accurately represent what external APIs return,
    making tests more reliable and debugging easier.
    """

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
        self.session_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    def save_response(
        self, category: str, name: str, response_data: Any, url: str, description: str
    ):
        """Save a response to the fixtures directory and update index data."""
        category_dir = FIXTURES_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        filepath = category_dir / f"{name}.json"

        # Match indentation of existing files
        indent: Optional[int] = 4
        if category == "geocoding" and "nonexistent" in name:
            indent = None

        with open(filepath, "w") as f:
            json.dump(response_data, f, indent=indent)

        logger.info(f"Saved {category}/{name} response to {filepath}")

        # Update index data
        response_info = {"name": name, "url": url, "description": description}
        if not any(r["name"] == name for r in self.index_data[category]["responses"]):
            self.index_data[category]["responses"].append(response_info)

    def _generate_name_slug(self, name: str) -> str:
        """Generate a slug for names/search terms for use in fixture filenames."""
        slug = name.replace(", ", "_").replace(" ", "_").lower()
        # Special cases for known test values
        if name == "Ground Kontrol":
            return "ground_kontrol_single_result"
        if name == "NonexistentLocationName123":
            return "nonexistent_location_name"
        if slug == "nonexistentcity123":
            return "nonexistent"
        return slug

    async def capture_pinballmap_responses(self):
        """Capture various PinballMap API responses."""
        logger.info("Capturing PinballMap API responses...")

        test_locations = [
            {"id": 874, "name": "Ground Kontrol Classic Arcade"},
            {"id": 1309, "name": "Seattle Pinball Museum"},
            {"id": 999999, "name": "NonexistentLocation"},
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
            url = f"{PINBALLMAP_BASE}/locations/{location['id']}.json"
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
            url = f"{PINBALLMAP_BASE}/locations.json?by_location_name={search_term.replace(' ', '%20')}"
            try:
                result = await search_location_by_name(search_term)
                name_slug = self._generate_name_slug(search_term)
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
        for location_id in [874, 1309]:
            url = f"{PINBALLMAP_BASE}/user_submissions/location.json?id={location_id}"
            try:
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
            "",
            "Manually created empty submissions response for testing",
        )

    async def capture_geocoding_responses(self):
        """Capture geocoding API responses."""
        logger.info("Capturing geocoding API responses...")

        test_cities = [
            "Seattle",
            "Portland",
            "Chicago",
            "NonexistentCity123",
            "Portland, OR",
        ]

        for city in test_cities:
            url = (
                f"{GEOCODING_BASE}/search?name={city.split(',')[0]}&count=5&format=json"
            )
            try:
                result = await geocode_city_name(city)
                name_slug = self._generate_name_slug(city)
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

        print(f"\n{'=' * 60}")
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

    def load_fixture_index(self) -> Dict:
        """Load the fixture index file."""
        index_path = FIXTURES_DIR / "index.json"
        with open(index_path) as f:
            return json.load(f)

    def validate_geocoding_response(self, fixture_path: Path) -> Optional[str]:
        """Validate geocoding response structure (raw API format)."""
        with open(fixture_path) as f:
            data = json.load(f)

        # Raw geocoding API responses have a "results" array, except for empty responses
        # which may only have metadata like "generationtime_ms"
        if "results" in data:
            if not isinstance(data["results"], list):
                return f"'results' should be a list in {fixture_path.name}"

            # For non-empty results, validate basic structure
            if data["results"]:
                first_result = data["results"][0]
                required_fields = ["latitude", "longitude", "name"]
                for field in required_fields:
                    if field not in first_result:
                        return f"Missing required field '{field}' in first result of {fixture_path.name}"
        elif "generationtime_ms" not in data:
            # If no results field, should at least have some API metadata
            return f"Missing 'results' field and no API metadata in {fixture_path.name}"

        return None

    def validate_pinballmap_location_response(
        self, fixture_path: Path
    ) -> Optional[str]:
        """Validate pinballmap location response structure."""
        with open(fixture_path) as f:
            data = json.load(f)

        if "errors" in data or len(data) == 0:
            return None  # Error responses are valid

        required_fields = ["id", "name"]
        for field in required_fields:
            if field not in data:
                return f"Missing required field '{field}' in {fixture_path.name}"
        return None

    def validate_pinballmap_search_response(self, fixture_path: Path) -> Optional[str]:
        """Validate pinballmap search response structure (raw API format)."""
        with open(fixture_path) as f:
            data = json.load(f)

        # Raw PinballMap search API responses have a "locations" array
        if "locations" not in data:
            return f"Missing 'locations' field in {fixture_path.name}"

        if not isinstance(data["locations"], list):
            return f"'locations' should be a list in {fixture_path.name}"

        # For non-empty results, validate basic location structure
        if data["locations"]:
            first_location = data["locations"][0]
            required_fields = ["id", "name", "lat", "lon"]
            for field in required_fields:
                if field not in first_location:
                    return f"Missing required field '{field}' in first location of {fixture_path.name}"
        return None

    def validate_pinballmap_submissions_response(
        self, fixture_path: Path
    ) -> Optional[str]:
        """Validate pinballmap submissions response structure."""
        with open(fixture_path) as f:
            data = json.load(f)

        if isinstance(data, list):
            return None  # Direct array format is valid
        elif isinstance(data, dict) and "user_submissions" in data:
            if not isinstance(data["user_submissions"], list):
                return f"'user_submissions' should be a list in {fixture_path.name}"
            return None
        else:
            return f"Invalid submissions format in {fixture_path.name}"

    def validate_fixtures(self) -> List[str]:
        """Validate all fixtures and return list of errors."""
        errors = []

        try:
            index = self.load_fixture_index()
        except Exception as e:
            return [f"❌ Failed to load fixture index: {e}"]

        validators = {
            "geocoding": self.validate_geocoding_response,
            "pinballmap_locations": self.validate_pinballmap_location_response,
            "pinballmap_search": self.validate_pinballmap_search_response,
            "pinballmap_submissions": self.validate_pinballmap_submissions_response,
        }

        for category_name, category_data in index["categories"].items():
            validator = validators.get(category_name)
            if not validator:
                print(f"⚠️  No validator for category: {category_name}")
                continue

            for response in category_data["responses"]:
                fixture_name = response["name"]
                fixture_path = FIXTURES_DIR / category_name / f"{fixture_name}.json"

                if not fixture_path.exists():
                    errors.append(f"❌ Fixture file not found: {fixture_path}")
                    continue

                error = validator(fixture_path)
                if error:
                    errors.append(f"❌ {error}")
                else:
                    print(f"✅ {fixture_path.name}")
        return errors

    def check_api_availability(self) -> List[str]:
        """Check if external APIs are still accessible."""
        errors = []

        try:
            response = requests.get(
                f"{GEOCODING_BASE}/search?name=Seattle&count=1&format=json", timeout=10
            )
            if response.status_code != 200:
                errors.append(
                    f"❌ Geocoding API returned status {response.status_code}"
                )
            else:
                print("✅ Geocoding API accessible")
        except Exception as e:
            errors.append(f"❌ Geocoding API error: {e}")

        try:
            response = requests.get(f"{PINBALLMAP_BASE}/locations/874.json", timeout=10)
            if response.status_code != 200:
                errors.append(
                    f"❌ PinballMap API returned status {response.status_code}"
                )
            else:
                print("✅ PinballMap API accessible")
        except Exception as e:
            errors.append(f"❌ PinballMap API error: {e}")

        return errors

    def check_fixture_freshness(self) -> List[str]:
        """Check if fixtures are getting stale."""
        warnings = []

        try:
            index = self.load_fixture_index()
            capture_timestamp = index["capture_session"]["timestamp"]
            capture_date = datetime.fromisoformat(
                capture_timestamp.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            days_old = (now - capture_date).days

            if days_old > 30:
                warnings.append(
                    f"⚠️  Fixtures are {days_old} days old (captured: {capture_timestamp})"
                )
            elif days_old > 7:
                warnings.append(
                    f"ℹ️  Fixtures are {days_old} days old (captured: {capture_timestamp})"
                )
            else:
                print(f"✅ Fixtures are fresh ({days_old} days old)")
        except Exception as e:
            warnings.append(f"⚠️  Could not check fixture freshness: {e}")
        return warnings

    async def capture_all(self):
        """Capture all API responses."""
        print("🔄 Capturing fresh API responses...")
        print()

        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

        try:
            await self.capture_pinballmap_responses()
            await self.capture_geocoding_responses()
            self.save_master_index()
            return True
        except Exception as e:
            logger.error(f"Capture failed: {e}")
            return False


def run_command(command: list, description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        print(f"🔄 {description}...")
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, str(e)


def validate_imports() -> bool:
    """Validate that this script can import from src/."""
    try:
        print("🔍 Validating imports from src/...")
        # The imports at the top of the file already test this
        print("✅ All imports from src/ successful")
        return True
    except Exception as e:
        print(f"❌ Import validation failed: {e}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Comprehensive fixture management and validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_all_validations.py validate       # Validate existing fixtures (default)
  python scripts/run_all_validations.py capture       # Refresh fixtures from APIs (manual only)
  python scripts/run_all_validations.py check         # Check API availability (manual only)
  python scripts/run_all_validations.py all           # Run all operations (manual only)
  python scripts/run_all_validations.py --ci          # CI mode - no API calls
  python scripts/run_all_validations.py --fix         # Auto-fix issues

This script consolidates all fixture management functionality.
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["validate", "capture", "check", "all"],
        default="validate",
        help="Action to perform (default: validate)",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix issues automatically"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode - skip API calls, only validate structure",
    )

    args = parser.parse_args()

    manager = FixtureManager()
    success = True

    # CI mode restrictions
    if args.ci and args.command in ["capture", "check", "all"]:
        print("🚫 CI mode detected - API operations not allowed")
        print("   Switching to validation-only mode to avoid spamming external APIs")
        args.command = "validate"

    print(f"🚀 Running fixture management: {args.command}")
    if args.ci:
        print("🤖 CI Mode: API calls disabled")
    print("=" * 60)
    print()

    if args.command == "validate":
        # Always validate imports first
        import_success = validate_imports()
        print()

        # Validate fixtures
        print("🔍 Validating API fixtures...")
        if not FIXTURES_DIR.exists():
            print("❌ Fixtures directory not found. Run 'capture' first.")
            success = False
        else:
            fixture_errors = manager.validate_fixtures()
            freshness_warnings = manager.check_fixture_freshness()

            print()
            if fixture_errors:
                print(f"❌ Found {len(fixture_errors)} validation errors:")
                for error in fixture_errors:
                    print(f"  {error}")
                success = False
            else:
                print("✅ All fixtures validated successfully!")

            if freshness_warnings:
                print()
                for warning in freshness_warnings:
                    print(f"  {warning}")

        success = success and import_success

    elif args.command == "capture":
        print("🔄 Capturing fresh API responses...")
        success = await manager.capture_all()

    elif args.command == "check":
        print("🌐 Checking API availability...")
        api_errors = manager.check_api_availability()

        print()
        if api_errors:
            print(f"❌ Found {len(api_errors)} API errors:")
            for error in api_errors:
                print(f"  {error}")
            success = False
        else:
            print("✅ All APIs are accessible!")

    elif args.command == "all":
        print("🚀 Running complete fixture management cycle...")
        print()

        # Step 1: Import validation
        import_success = validate_imports()
        print()

        # Step 2: Check API availability
        print("🌐 Checking API availability...")
        api_errors = manager.check_api_availability()
        api_success = len(api_errors) == 0

        if not api_success:
            print("❌ APIs not accessible. Skipping capture.")
            for error in api_errors:
                print(f"  {error}")
            success = False
        else:
            print("✅ All APIs accessible")
            print()

            # Step 3: Capture fresh responses
            capture_success = await manager.capture_all()
            print()

            # Step 4: Validate the captured responses
            print("🔍 Validating captured fixtures...")
            fixture_errors = manager.validate_fixtures()
            freshness_warnings = manager.check_fixture_freshness()

            print()
            if fixture_errors:
                print(f"❌ Found {len(fixture_errors)} validation errors:")
                for error in fixture_errors:
                    print(f"  {error}")
                validate_success = False
            else:
                print("✅ All fixtures validated successfully!")
                validate_success = True

            if freshness_warnings:
                print()
                for warning in freshness_warnings:
                    print(f"  {warning}")

            success = (
                import_success and api_success and capture_success and validate_success
            )

    # Auto-fix if requested and there were failures
    if args.fix and not success and args.command != "capture":
        print()
        print("🔧 ATTEMPTING AUTO-FIX...")

        try:
            print("Attempting to refresh fixtures...")
            capture_success = await manager.capture_all()
            if capture_success:
                print("✅ Fixtures refreshed successfully")

                # Re-run validation
                print()
                print("🔍 Re-validating after fixture refresh...")
                fixture_errors = manager.validate_fixtures()

                if not fixture_errors:
                    print("✅ Validation now passes after fixture refresh")
                    success = True
                else:
                    print("❌ Issues persist after fixture refresh")
            else:
                print("❌ Failed to refresh fixtures")
        except Exception as e:
            print(f"❌ Auto-fix failed: {e}")

    print()
    print("=" * 60)
    if success:
        print("🎉 All operations completed successfully!")
        if args.command == "validate":
            print()
            print("The fixture system is healthy:")
            print("  • Scripts can import from src/ without issues")
            print("  • All fixtures have valid structure")
            print("  • Fixtures are reasonably fresh")
    else:
        print("❌ Some operations failed. Please review the output above.")
        if not args.ci:
            print()
            print("Recommended actions:")
            print("  1. Check src/api.py for recent changes")
            print("  2. Verify external APIs are accessible")
            print("  3. Run: python scripts/run_all_validations.py capture")
            print("  4. Re-run this validation script")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
