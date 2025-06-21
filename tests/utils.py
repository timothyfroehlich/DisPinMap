"""
Shared test utilities for the DisPinMap test suite.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.database import Database


class MockContext:
    """Mock Discord context for testing commands."""

    def __init__(self, channel_id: int, guild_id: int):
        self.channel = MagicMock()
        self.channel.id = channel_id
        self.channel.name = f"test-channel-{channel_id}"
        self.guild = MagicMock()
        self.guild.id = guild_id
        self.author = MagicMock()
        self.author.name = "test-user"
        self.author.id = 123456789
        self.message = MagicMock()
        self.message.content = ""
        self.sent_messages: List[str] = []

    async def send(self, message: str):
        """Mock send method that records messages"""
        self.sent_messages.append(message)
        return None

    async def _record_send(self, message: str):
        self.sent_messages.append(message)


class MockResponse:
    """Mock response for API testing."""

    def __init__(self, status: int, data: Any):
        self.status = status
        self.data = data

    async def json(self):
        return self.data


@pytest.fixture
def mock_context():
    """Create a mock Discord context for testing."""
    return MockContext(12345, 67890)


def create_rate_limit_response():
    """Create a mock rate limit response."""
    return MockResponse(429, {})


def create_success_response(json_data: Dict[str, Any]):
    """Create a mock successful response."""
    return MockResponse(200, json_data)


def create_error_response(status_code: int, error_message: str):
    """Create a mock error response."""
    return MockResponse(status_code, {"errors": [error_message]})


async def verify_discord_message(ctx: MockContext, expected_content: str):
    """Verify that a Discord message was sent containing the expected content (emoji optional)."""
    assert ctx.send.call_count > 0, "No messages were sent"
    actual_messages = [call[0][0] for call in ctx.send.call_args_list]
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


def verify_database_target(
    db: Database, channel_id: int, expected_count: int, target_type: str = None
):
    """Verify that the expected number of targets exist in the database."""
    targets = db.get_monitoring_targets(channel_id)
    assert (
        len(targets) == expected_count
    ), f"Expected {expected_count} targets, got {len(targets)}"

    if target_type and expected_count > 0:
        assert all(
            t["target_type"] == target_type for t in targets
        ), f"Expected all targets to be of type {target_type}"


async def assert_discord_message(ctx, expected_message):
    """Assert that a message was sent to Discord"""
    assert any(
        expected_message in msg for msg in ctx.sent_messages
    ), f"Expected message '{expected_message}' not found in sent messages: {ctx.sent_messages}"


def verify_database_target(db, channel_id, expected_count, target_type=None):
    """Verify the number of targets in the database"""
    targets = db.get_monitoring_targets(channel_id)
    assert (
        len(targets) == expected_count
    ), f"Expected {expected_count} targets, got {len(targets)}"

    if target_type:
        assert all(
            t["target_type"] == target_type for t in targets
        ), f"Expected all targets to be of type {target_type}"
