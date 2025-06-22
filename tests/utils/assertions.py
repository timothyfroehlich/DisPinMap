"""
Custom assertion helpers for testing.

This module provides custom assertion helpers for verifying API responses,
database state, and message formatting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

from src.messages import Messages


class MockContext:
    """Mock Discord context for testing commands."""

    def __init__(self, channel_id: int, guild_id: int, bot=None):
        self.bot = bot
        self.channel = type("Channel", (), {"id": channel_id})()
        self.guild = type("Guild", (), {"id": guild_id})()
        self.message = type(
            "Message",
            (),
            {"content": "", "author": type("Author", (), {"name": "TestUser"})()},
        )()
        self.sent_messages: List[str] = []

        # Create a custom send method that populates sent_messages
        async def send(message):
            self.sent_messages.append(message)

        self.send = AsyncMock(side_effect=send)

        if self.bot and hasattr(self.bot, "notifier"):
            self.notifier = self.bot.notifier


async def assert_discord_message(ctx: MockContext, expected_content: str):
    """
    Verify that a Discord message was sent containing the expected content.

    Args:
        ctx: Mock Discord context
        expected_content: Expected message content (can be a Messages class string or raw string)
    """
    assert ctx.send.call_count > 0, "No messages were sent"
    actual_messages = [call[0][0] for call in ctx.send.call_args_list]

    # Handle Messages class strings
    if isinstance(expected_content, str) and hasattr(
        Messages, expected_content.split(".")[0]
    ):
        # Extract the message without emoji for comparison
        expected_core = expected_content.replace("✅ ", "").replace("❌ ", "")
        assert any(
            expected_core in msg for msg in actual_messages
        ), f"Expected '{expected_core}' in any message, got: {actual_messages}"
    else:
        # Allow for emoji or not at the start of the message
        if expected_content.startswith("❌") or expected_content.startswith("✅"):
            expected_core = expected_content[1:].strip()
            assert any(
                expected_core in msg for msg in actual_messages
            ), f"Expected '{expected_core}' in any message, got: {actual_messages}"
        else:
            assert any(
                expected_content in msg for msg in actual_messages
            ), f"Expected '{expected_content}' in any message, got: {actual_messages}"


def assert_api_response(response: Dict[str, Any]):
    """
    Verify that an API response is a geocoding success response.
    Args:
        response: API response to verify
    """
    assert "status" in response, "Response missing 'status' field"
    assert (
        response["status"] == "success"
    ), f"Expected status 'success', got {response['status']}"
    assert "lat" in response and "lon" in response, "Response missing coordinates"
    assert "display_name" in response, "Response missing display_name"


def assert_error_response(response: Dict[str, Any], expected_error: str):
    """
    Verify that an error response contains the expected error message.
    Args:
        response: Error response to verify
        expected_error: Expected error message (substring match)
    """
    assert "status" in response, Messages.System.Error.RESPONSE_MISSING_FIELD.format(
        field="status"
    )
    assert (
        response["status"] == "error"
    ), f"Expected status 'error', got {response['status']}"
    assert "message" in response, Messages.System.Error.RESPONSE_MISSING_FIELD.format(
        field="message"
    )
    assert (
        expected_error.lower() in response["message"].lower()
    ), f"Expected error message to contain '{expected_error}', got '{response['message']}'"


def assert_location_data(location: Dict[str, Any], expected_name: Optional[str] = None):
    """
    Verify that location data has the expected structure and values.

    Args:
        location: Location data to verify
        expected_name: Optional expected location name
    """
    required_fields = ["id", "name", "lat", "lon"]
    for field in required_fields:
        assert field in location, Messages.System.Error.DATA_MISSING_FIELD.format(
            data_type="Location", field=field
        )

    if expected_name:
        assert (
            location["name"] == expected_name
        ), f"Expected location name '{expected_name}', got '{location['name']}'"


def assert_submission_data(
    submission: Dict[str, Any], expected_type: Optional[str] = None
):
    """
    Verify that submission data has the expected structure and values.

    Args:
        submission: Submission data to verify
        expected_type: Optional expected submission type
    """
    required_fields = [
        "id",
        "location_id",
        "machine_id",
        "machine_name",
        "submission_type",
        "created_at",
    ]
    for field in required_fields:
        assert field in submission, Messages.System.Error.DATA_MISSING_FIELD.format(
            data_type="Submission", field=field
        )

    if expected_type:
        assert (
            submission["submission_type"] == expected_type
        ), f"Expected submission type '{expected_type}', got '{submission['submission_type']}'"


def assert_timestamp_format(timestamp: str):
    """
    Verify that a timestamp string is in ISO 8601 format.

    Args:
        timestamp: Timestamp string to verify
    """
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        assert False, Messages.System.Error.INVALID_TIMESTAMP.format(
            timestamp=timestamp
        )


def assert_coordinates(lat: float, lon: float):
    """
    Verify that coordinates are within valid ranges.

    Args:
        lat: Latitude to verify
        lon: Longitude to verify
    """
    assert isinstance(
        lat, (int, float)
    ), Messages.System.Error.INVALID_COORDINATE_TYPE.format(
        coord_type="Latitude", type=type(lat)
    )
    assert isinstance(
        lon, (int, float)
    ), Messages.System.Error.INVALID_COORDINATE_TYPE.format(
        coord_type="Longitude", type=type(lon)
    )
    assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
    assert -180 <= lon <= 180, f"Invalid longitude: {lon}"
