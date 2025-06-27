"""
A simplified, fixture-based API mocker for tests.

This utility provides a pytest fixture (`api_mocker`) that allows tests
to easily mock `aiohttp` responses for specific URLs, loading the response
body from the JSON files stored in `tests/fixtures/api_responses/`.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.utils.mock_factories import create_api_client_mock

# Path to the directory containing captured API response fixtures.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "api_responses"


class APIMocker:
    """A simple class to manage mocking for aiohttp client sessions."""

    def __init__(self):
        # Maps a URL (or a substring) to the JSON file that should be returned.
        self.url_map = {}
        # The actual patcher for the aiohttp session object.
        self._patcher = None
        self.mock_session = None

    def start(self):
        """Starts patching the aiohttp session with proper spec'd mocks."""
        self._patcher = patch("aiohttp.ClientSession")
        mock_client_session_class = self._patcher.start()
        self.mock_session = create_api_client_mock()
        mock_client_session_class.return_value = self.mock_session
        self.mock_session.get.side_effect = self._mock_get_request
        return self

    def stop(self):
        """Stops the patch."""
        if self._patcher:
            self._patcher.stop()

    def add_response(
        self, url_substring: str, json_fixture_path: str, status: int = 200
    ):
        """
        Maps a URL substring to a JSON fixture file.

        Args:
            url_substring: A substring to match against the request URL.
            json_fixture_path: The relative path to the fixture file
                               (e.g., 'geocoding/city_portland_or.json').
            status: The HTTP status code to return.
        """
        fixture_file = FIXTURES_DIR / json_fixture_path
        if not fixture_file.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_file}")

        self.url_map[url_substring] = (fixture_file, status)

    async def _mock_get_request(self, url: str, **kwargs):
        """
        The side effect function for the mocked session.get().

        It finds a matching URL from the map and returns a mock response
        with the content of the corresponding fixture file.
        """
        for substring, (fixture_file, status) in self.url_map.items():
            if substring in url:
                with open(fixture_file, "r") as f:
                    data = json.load(f)

                # Create a properly spec'd mock response object
                mock_response = create_api_client_mock()
                mock_response.status = status
                mock_response.json.return_value = data

                # To make it awaitable, wrap it in a future
                future: asyncio.Future = asyncio.Future()
                future.set_result(mock_response)
                return future

        # If no match is found, raise an error to fail the test clearly.
        raise NotImplementedError(
            f"API Mocker: No response registered for GET request to URL containing: {url}"
        )


@pytest.fixture
def api_mocker():
    """A pytest fixture that provides a configured APIMocker instance."""
    mocker = APIMocker()
    mocker.start()
    yield mocker
    mocker.stop()
