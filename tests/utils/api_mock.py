"""
API Mocking Framework for Simulation Testing

This module provides comprehensive mocking capabilities for the PinballMap and geocoding APIs
using captured real response data. It supports realistic response timing, error injection,
and scenario-based testing.
"""

import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

logger = logging.getLogger(__name__)

# Path to captured API fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "api_responses"


class APIResponseLoader:
    """Loads and manages captured API responses."""

    def __init__(self):
        self.responses = {}
        self._load_responses()

    def _load_responses(self):
        """Load all captured responses into memory."""
        if not FIXTURES_DIR.exists():
            logger.warning(f"Fixtures directory not found: {FIXTURES_DIR}")
            return

        try:
            # Load the master index
            index_path = FIXTURES_DIR / "index.json"
            if index_path.exists():
                with open(index_path) as f:
                    index = json.load(f)
                logger.info(
                    f"Loaded API response index with {index['capture_session']['total_responses']} responses"
                )

            # Load responses by category
            for category_dir in FIXTURES_DIR.iterdir():
                if category_dir.is_dir():
                    category = category_dir.name
                    self.responses[category] = {}

                    for response_file in category_dir.glob("*.json"):
                        response_name = response_file.stem
                        try:
                            with open(response_file) as f:
                                response_data = json.load(f)
                            self.responses[category][response_name] = response_data
                        except Exception as e:
                            logger.error(f"Failed to load {response_file}: {e}")

            logger.info(
                f"Loaded responses for categories: {list(self.responses.keys())}"
            )

        except Exception as e:
            logger.error(f"Failed to load API responses: {e}")

    def get_response(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific response by category and name."""
        return self.responses.get(category, {}).get(name)

    def list_responses(self, category: str) -> List[str]:
        """List all response names in a category."""
        return list(self.responses.get(category, {}).keys())

    def search_responses(
        self, category: str, **metadata_filters
    ) -> List[Dict[str, Any]]:
        """Find responses matching metadata criteria."""
        matches = []
        for name, response in self.responses.get(category, {}).items():
            metadata = response.get("metadata", {})

            # Check if all filters match
            match = True
            for key, value in metadata_filters.items():
                if metadata.get(key) != value:
                    match = False
                    break

            if match:
                matches.append(response)

        return matches


class MockAPIConfig:
    """Configuration for API mocking behavior."""

    def __init__(self):
        # Timing simulation
        self.enable_delays = True
        self.min_delay = 0.1  # seconds
        self.max_delay = 0.5  # seconds

        # Error injection
        self.error_rate = 0.0  # 0.0 to 1.0
        self.timeout_rate = 0.0

        # Response modification
        self.modify_responses = False
        self.add_test_markers = False

        # Logging
        self.log_requests = True

    def with_delays(self, min_delay: float = 0.1, max_delay: float = 0.5):
        """Enable realistic API delays."""
        self.enable_delays = True
        self.min_delay = min_delay
        self.max_delay = max_delay
        return self

    def with_errors(self, error_rate: float = 0.1, timeout_rate: float = 0.05):
        """Enable error injection."""
        self.error_rate = error_rate
        self.timeout_rate = timeout_rate
        return self

    def with_modifications(self, add_markers: bool = True):
        """Enable response modifications for testing."""
        self.modify_responses = True
        self.add_test_markers = add_markers
        return self

    def fast_mode(self):
        """Disable delays for fast testing."""
        self.enable_delays = False
        return self


class PinballMapAPIMock:
    """Mock for PinballMap API functions."""

    def __init__(
        self,
        config: Optional[MockAPIConfig] = None,
        loader: Optional[APIResponseLoader] = None,
    ):
        self.config = config or MockAPIConfig()
        self.loader = loader or APIResponseLoader()
        self.request_log: List[Dict[str, Any]] = []

    def _simulate_delay(self):
        """Simulate realistic API response time."""
        if self.config.enable_delays:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            time.sleep(delay)

    def _inject_errors(self):
        """Randomly inject errors based on configuration."""
        if random.random() < self.config.timeout_rate:
            raise TimeoutError("Simulated API timeout")

        if random.random() < self.config.error_rate:
            raise Exception("Simulated API error")

    def _log_request(self, function_name: str, args: tuple, kwargs: dict):
        """Log API request for debugging."""
        if self.config.log_requests:
            self.request_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "function": function_name,
                    "args": args,
                    "kwargs": kwargs,
                }
            )

    def _modify_response(self, response_data: Any) -> Any:
        """Modify response data for testing purposes."""
        if not self.config.modify_responses:
            return response_data

        if isinstance(response_data, dict) and self.config.add_test_markers:
            # Add test markers to identify mocked data
            response_data = response_data.copy()
            response_data["_test_marker"] = "simulation_test_data"
            response_data["_mock_timestamp"] = datetime.now().isoformat()

        return response_data

    async def fetch_location_details(self, location_id: int) -> Dict[str, Any]:
        """Mock fetch_location_details function."""
        self._log_request("fetch_location_details", (location_id,), {})
        self._simulate_delay()
        self._inject_errors()

        # Look for matching response
        response = self.loader.get_response(
            "pinballmap_locations", f"location_{location_id}_details"
        )

        if response:
            return self._modify_response(response["data"])
        else:
            # Return error for unknown location
            raise Exception(
                f"Location details for {location_id} not found: Failed to find location"
            )

    async def search_location_by_name(self, search_term: str) -> Dict[str, Any]:
        """Mock search_location_by_name function."""
        self._log_request("search_location_by_name", (search_term,), {})
        self._simulate_delay()
        self._inject_errors()

        # Try to find matching search response
        search_key = search_term.lower().replace(" ", "_").replace(",", "")
        response = self.loader.get_response("pinballmap_search", f"search_{search_key}")

        if response:
            return self._modify_response(response["data"])
        else:
            # Return "not found" for unknown searches
            return {"status": "not_found", "data": []}

    async def fetch_submissions_for_location(
        self, location_id: int, use_min_date: bool = True
    ) -> List[Dict[str, Any]]:
        """Mock fetch_submissions_for_location function."""
        self._log_request(
            "fetch_submissions_for_location", (location_id, use_min_date), {}
        )
        self._simulate_delay()
        self._inject_errors()

        # Choose between recent or all submissions
        suffix = "recent" if use_min_date else "all"
        response = self.loader.get_response(
            "pinballmap_submissions", f"location_{location_id}_{suffix}"
        )

        if response:
            return self._modify_response(response["data"])
        else:
            # Return empty list for unknown locations
            return []

    async def fetch_submissions_for_coordinates(
        self,
        lat: float,
        lon: float,
        radius: Optional[int] = None,
        use_min_date: bool = True,
    ) -> List[Dict[str, Any]]:
        """Mock fetch_submissions_for_coordinates function."""
        self._log_request(
            "fetch_submissions_for_coordinates", (lat, lon, radius, use_min_date), {}
        )
        self._simulate_delay()
        self._inject_errors()

        # Find best matching coordinate response
        matches = self.loader.search_responses(
            "pinballmap_submissions",
            lat=lat,
            lon=lon,
            radius=radius,
            use_min_date=use_min_date,
        )

        if matches:
            # Use the first match
            return self._modify_response(matches[0]["data"])
        else:
            # Return empty list for unknown coordinates
            return []


class GeocodingAPIMock:
    """Mock for geocoding API functions."""

    def __init__(
        self,
        config: Optional[MockAPIConfig] = None,
        loader: Optional[APIResponseLoader] = None,
    ):
        self.config = config or MockAPIConfig()
        self.loader = loader or APIResponseLoader()
        self.request_log: List[Dict[str, Any]] = []

    def _simulate_delay(self):
        """Simulate realistic API response time."""
        if self.config.enable_delays:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            time.sleep(delay)

    def _inject_errors(self):
        """Randomly inject errors based on configuration."""
        if random.random() < self.config.timeout_rate:
            raise TimeoutError("Simulated geocoding timeout")

        if random.random() < self.config.error_rate:
            raise Exception("Simulated geocoding error")

    def _log_request(self, function_name: str, args: tuple, kwargs: dict):
        """Log API request for debugging."""
        if self.config.log_requests:
            self.request_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "function": function_name,
                    "args": args,
                    "kwargs": kwargs,
                }
            )

    async def geocode_city_name(self, city_name: str) -> Dict[str, Any]:
        """Mock geocode_city_name function."""
        self._log_request("geocode_city_name", (city_name,), {})
        self._simulate_delay()
        self._inject_errors()

        # Find matching geocoding response
        city_key = city_name.lower().replace(" ", "_").replace(",", "")
        response = self.loader.get_response("geocoding", f"city_{city_key}")

        if response:
            return response["data"]
        else:
            # Return error for unknown cities
            return {
                "status": "error",
                "message": f"Could not geocode city: {city_name}",
            }


class APISimulator:
    """Main API simulation coordinator."""

    def __init__(self, config: Optional[MockAPIConfig] = None):
        self.config = config or MockAPIConfig()
        self.loader = APIResponseLoader()
        self.pinballmap_mock = PinballMapAPIMock(self.config, self.loader)
        self.geocoding_mock = GeocodingAPIMock(self.config, self.loader)
        self.patches: List[Any] = []

    def __enter__(self):
        """Context manager entry - apply patches."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - remove patches."""
        self.stop()

    def start(self):
        """Start API mocking."""
        # Patch PinballMap API functions
        pinballmap_patches = [
            (
                "src.api.fetch_location_details",
                self.pinballmap_mock.fetch_location_details,
            ),
            (
                "src.api.search_location_by_name",
                self.pinballmap_mock.search_location_by_name,
            ),
            (
                "src.api.fetch_submissions_for_location",
                self.pinballmap_mock.fetch_submissions_for_location,
            ),
            (
                "src.api.fetch_submissions_for_coordinates",
                self.pinballmap_mock.fetch_submissions_for_coordinates,
            ),
        ]

        # Patch geocoding API functions
        geocoding_patches = [
            ("src.api.geocode_city_name", self.geocoding_mock.geocode_city_name),
        ]

        all_patches = pinballmap_patches + geocoding_patches

        for target, mock_func in all_patches:
            patcher = patch(target, side_effect=mock_func)
            self.patches.append(patcher)
            patcher.start()

        logger.info(f"Started API simulation with {len(all_patches)} patches")

    def stop(self):
        """Stop API mocking."""
        for patcher in self.patches:
            patcher.stop()
        self.patches.clear()
        logger.info("Stopped API simulation")

    def get_request_logs(self) -> Dict[str, List[Dict]]:
        """Get logged API requests for verification."""
        return {
            "pinballmap": self.pinballmap_mock.request_log,
            "geocoding": self.geocoding_mock.request_log,
        }

    def clear_logs(self):
        """Clear request logs."""
        self.pinballmap_mock.request_log.clear()
        self.geocoding_mock.request_log.clear()


# Convenience functions for common mock configurations


def create_fast_mock() -> APISimulator:
    """Create a fast mock with no delays for unit testing."""
    config = MockAPIConfig().fast_mode()
    return APISimulator(config)


def create_realistic_mock() -> APISimulator:
    """Create a realistic mock with delays and occasional errors."""
    config = MockAPIConfig().with_delays(0.1, 0.3).with_errors(0.05, 0.02)
    return APISimulator(config)


def create_error_prone_mock() -> APISimulator:
    """Create a mock that frequently fails for error testing."""
    config = MockAPIConfig().with_errors(0.3, 0.15)
    return APISimulator(config)


def create_test_mock() -> APISimulator:
    """Create a mock with test markers for development."""
    config = MockAPIConfig().fast_mode().with_modifications(add_markers=True)
    return APISimulator(config)
