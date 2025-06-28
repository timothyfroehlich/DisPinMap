#!/usr/bin/env python3
"""
Fixture Validation Script

This script validates that API fixtures still match current API schemas.
Run periodically to catch breaking API changes early.

Usage:
    python scripts/validate_fixtures.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests


def load_fixture_index() -> Dict:
    """Load the fixture index file."""
    index_path = Path("tests/fixtures/api_responses/index.json")
    with open(index_path) as f:
        return json.load(f)


def validate_geocoding_response(fixture_path: Path) -> Optional[str]:
    """Validate geocoding response structure."""
    with open(fixture_path) as f:
        data = json.load(f)

    if "results" not in data:
        return f"Missing 'results' field in {fixture_path.name}"

    if not isinstance(data["results"], list):
        return f"'results' should be a list in {fixture_path.name}"

    return None


def validate_pinballmap_location_response(fixture_path: Path) -> Optional[str]:
    """Validate pinballmap location response structure."""
    with open(fixture_path) as f:
        data = json.load(f)

    # Handle error responses
    if "errors" in data:
        return None  # Error responses are valid

    required_fields = ["id", "name"]
    for field in required_fields:
        if field not in data:
            return f"Missing required field '{field}' in {fixture_path.name}"

    return None


def validate_pinballmap_search_response(fixture_path: Path) -> Optional[str]:
    """Validate pinballmap search response structure."""
    with open(fixture_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        return f"Search response should be a list in {fixture_path.name}"

    return None


def validate_pinballmap_submissions_response(fixture_path: Path) -> Optional[str]:
    """Validate pinballmap submissions response structure."""
    with open(fixture_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        return f"Submissions response should be a list in {fixture_path.name}"

    return None


def validate_fixtures() -> List[str]:
    """Validate all fixtures and return list of errors."""
    errors = []
    index = load_fixture_index()

    validators = {
        "geocoding": validate_geocoding_response,
        "pinballmap_locations": validate_pinballmap_location_response,
        "pinballmap_search": validate_pinballmap_search_response,
        "pinballmap_submissions": validate_pinballmap_submissions_response,
    }

    for category_name, category_data in index["categories"].items():
        validator = validators.get(category_name)
        if not validator:
            print(f"⚠️  No validator for category: {category_name}")
            continue

        for response in category_data["responses"]:
            fixture_name = response["name"]
            fixture_path = Path(
                f"tests/fixtures/api_responses/{category_name}/{fixture_name}.json"
            )

            if not fixture_path.exists():
                errors.append(f"❌ Fixture file not found: {fixture_path}")
                continue

            error = validator(fixture_path)
            if error:
                errors.append(f"❌ {error}")
            else:
                print(f"✅ {fixture_path.name}")

    return errors


def check_api_availability() -> List[str]:
    """Check if external APIs are still accessible."""
    errors = []

    # Test geocoding API
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search?name=Seattle&count=1&format=json",
            timeout=10,
        )
        if response.status_code != 200:
            errors.append(f"❌ Geocoding API returned status {response.status_code}")
        else:
            print("✅ Geocoding API accessible")
    except Exception as e:
        errors.append(f"❌ Geocoding API error: {e}")

    # Test pinballmap API
    try:
        response = requests.get(
            "https://pinballmap.com/api/v1/locations/874.json", timeout=10
        )
        if response.status_code != 200:
            errors.append(f"❌ PinballMap API returned status {response.status_code}")
        else:
            print("✅ PinballMap API accessible")
    except Exception as e:
        errors.append(f"❌ PinballMap API error: {e}")

    return errors


def main():
    """Main validation function."""
    print("🔍 Validating API fixtures...")
    print()

    # Validate fixture structure
    fixture_errors = validate_fixtures()

    print()
    print("🌐 Checking API availability...")
    print()

    # Check API availability
    api_errors = check_api_availability()

    # Summary
    print()
    print("=" * 50)
    total_errors = len(fixture_errors) + len(api_errors)

    if total_errors == 0:
        print("✅ All fixtures validated successfully!")
        sys.exit(0)
    else:
        print(f"❌ Found {total_errors} validation errors:")
        for error in fixture_errors + api_errors:
            print(f"  {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
