"""
Mock factory utilities with proper spec validation.

This module provides factory functions for creating properly spec'd mocks
that enforce interface compliance and catch development errors early.
All mocks use the `spec` parameter to ensure they match real interfaces.
"""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import requests
from discord import Guild, Member, TextChannel
from discord.ext.commands import Context

from src.database import Database

# Import real classes for spec validation
from src.notifier import Notifier


def create_async_notifier_mock() -> AsyncMock:
    """
    Create a properly spec'd AsyncMock for the Notifier class.

    Returns:
        AsyncMock with Notifier spec that enforces interface compliance

    Example:
        >>> mock_notifier = create_async_notifier_mock()
        >>> # Use in test
        >>> await mock_notifier.log_and_send(ctx, "message")
        >>> mock_notifier.log_and_send.assert_called_once_with(ctx, "message")
    """
    mock = AsyncMock(spec=Notifier)

    # Validate that log_and_send is properly awaitable
    assert asyncio.iscoroutinefunction(mock.log_and_send), (
        "log_and_send mock is not recognized as a coroutine function"
    )

    return mock


def create_database_mock() -> MagicMock:
    """
    Create a properly spec'd MagicMock for the Database class.

    Returns:
        MagicMock with Database spec that enforces interface compliance
    """
    return MagicMock(spec=Database)


def create_discord_context_mock(
    user_id: int = 12345, channel_id: int = 67890, guild_id: int = 11111
) -> MagicMock:
    """
    Create a properly spec'd mock Discord context for command testing.

    Args:
        user_id: Mock user ID
        channel_id: Mock channel ID
        guild_id: Mock guild ID

    Returns:
        MagicMock with Context spec and proper async methods

    Example:
        >>> mock_ctx = create_discord_context_mock(user_id=123, channel_id=456)
        >>> # Use in command test
        >>> await command_function(mock_ctx, "test argument")
        >>> mock_ctx.respond.assert_called_once()
    """
    mock_ctx = MagicMock(spec=Context)

    # Set up interaction with proper specs
    mock_ctx.interaction = MagicMock()
    mock_ctx.interaction.user = MagicMock(spec=Member)
    mock_ctx.interaction.user.id = user_id
    mock_ctx.interaction.channel = MagicMock(spec=TextChannel)
    mock_ctx.interaction.channel.id = channel_id

    # Set up channel with proper spec
    mock_ctx.channel = MagicMock(spec=TextChannel)
    mock_ctx.channel.id = channel_id
    mock_ctx.channel.send = AsyncMock()

    # Set up guild
    mock_ctx.guild = MagicMock(spec=Guild)
    mock_ctx.guild.id = guild_id

    # Mock async response methods
    mock_ctx.respond = AsyncMock()
    mock_ctx.send = AsyncMock()

    return mock_ctx


def create_api_client_mock() -> AsyncMock:
    """
    Create a properly spec'd AsyncMock for API client classes.

    Returns:
        AsyncMock suitable for HTTP/API client mocking
    """
    # For now, use basic AsyncMock since we don't have a specific API client interface
    # TODO: Add specific spec when API client interface is formalized (Issue #54)
    mock = AsyncMock()

    # Ensure common HTTP methods are async
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.put = AsyncMock()
    mock.delete = AsyncMock()

    return mock


def create_bot_mock() -> MagicMock:
    """
    Create a properly spec'd mock for Discord bot instances.

    Returns:
        MagicMock with Discord bot interface
    """
    # Import here to avoid circular imports
    from discord.ext.commands import Bot

    mock_bot = MagicMock(spec=Bot)

    # Add commonly used bot attributes
    mock_bot.user = MagicMock()
    mock_bot.user.id = 99999
    mock_bot.user.name = "TestBot"

    # Mock async methods
    mock_bot.load_extension = AsyncMock()
    mock_bot.add_cog = AsyncMock()
    mock_bot.get_command = MagicMock()  # Returns command objects
    mock_bot.get_cog = MagicMock()  # Returns cog objects

    # Mock database and notifier attributes (added by our create_bot function)
    mock_bot.database = create_database_mock()
    mock_bot.notifier = create_async_notifier_mock()

    return mock_bot


def validate_async_mock(mock: AsyncMock, method_name: str) -> None:
    """
    Validate that a mock method is properly set up for async usage.

    Args:
        mock: The mock object to validate
        method_name: Name of the method to check

    Raises:
        AssertionError: If the method is not properly awaitable
    """
    method = getattr(mock, method_name)
    assert asyncio.iscoroutinefunction(method), (
        f"{method_name} is not recognized as a coroutine function"
    )


def create_requests_response_mock(
    status_code: int = 200, json_data: Optional[Dict] = None
) -> MagicMock:
    """
    Create a properly spec'd mock for requests.Response objects.

    Args:
        status_code: HTTP status code to return
        json_data: JSON data to return from .json() method

    Returns:
        MagicMock with requests.Response spec that enforces interface compliance

    Example:
        >>> response_data = {"results": [{"id": 1, "name": "test"}]}
        >>> mock_response = create_requests_response_mock(200, response_data)
        >>> assert mock_response.status_code == 200
        >>> assert mock_response.json() == response_data
    """
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.raise_for_status.return_value = (
        None  # No exception for successful responses
    )
    mock_response.text = str(json_data) if json_data else ""
    mock_response.content = b""
    mock_response.headers = {}
    mock_response.url = "http://example.com"

    return mock_response


def validate_mock_spec(mock: Any, expected_spec: type) -> None:
    """
    Validate that a mock has the expected spec.

    Args:
        mock: The mock object to validate
        expected_spec: The expected spec class

    Raises:
        AssertionError: If the mock doesn't have the expected spec
    """
    assert hasattr(mock, "_mock_methods"), "Object is not a mock"
    assert mock._spec_class == expected_spec, (
        f"Mock spec is {mock._spec_class}, expected {expected_spec}"
    )
