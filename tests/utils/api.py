"""
API utilities for testing.

This module provides utilities for mocking API responses, simulating rate limiting,
and generating test data for API endpoints.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock


class MockResponse:
    """Mock response for API testing."""

    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code  # This is what requests.Response uses
        self.data = data

    def json(self):
        """Return JSON data (synchronous like requests.Response)"""
        return self.data

    def raise_for_status(self):
        """Mock the raise_for_status method"""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


class MockAsyncResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    async def json(self):
        return self._json_data

    def json(self):
        return self._json_data


def create_rate_limit_response() -> MockResponse:
    """Create a mock rate limit response."""
    return MockResponse(
        429, {"errors": ["Rate limit exceeded. Please try again later."]}
    )


def create_success_response(json_data: Dict[str, Any]) -> MockResponse:
    """Create a mock successful response."""
    return MockResponse(200, json_data)


def create_error_response(status_code: int, error_message: str) -> MockResponse:
    """Create a mock error response."""
    return MockResponse(status_code, {"errors": [error_message]})


def create_location_response(
    location_id: int, name: str, lat: float, lon: float
) -> Dict[str, Any]:
    """Create a mock location response."""
    return {
        "location": {
            "id": location_id,
            "name": name,
            "lat": lat,
            "lon": lon,
            "machine_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    }


def create_submission_response(
    location_id: int,
    machine_id: int,
    machine_name: str,
    submission_type: str = "new_machine",
) -> Dict[str, Any]:
    """Create a mock submission response."""
    return {
        "submission": {
            "id": 1,
            "location_id": location_id,
            "machine_id": machine_id,
            "machine_name": machine_name,
            "submission_type": submission_type,
            "created_at": "2024-01-01T00:00:00Z",
        }
    }


def create_autocomplete_response(locations: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a mock location autocomplete response."""
    return {"locations": locations}


def simulate_rate_limit(
    mock_func: AsyncMock, success_response: Dict[str, Any], attempts: int = 3
) -> AsyncMock:
    """
    Simulate rate limiting behavior for a mock function.

    Args:
        mock_func: The mock function to modify
        success_response: The response to return after rate limit is lifted
        attempts: Number of rate limit responses before success

    Returns:
        Modified mock function
    """
    responses = [create_rate_limit_response() for _ in range(attempts)]
    responses.append(create_success_response(success_response))

    async def rate_limited(*args, **kwargs):
        response = responses.pop(0)
        responses.append(response)  # Cycle responses
        return response

    mock_func.side_effect = rate_limited
    return mock_func


def create_async_success_response(data):
    return MockAsyncResponse(data)


def create_async_error_response(data):
    return MockAsyncResponse(data)
