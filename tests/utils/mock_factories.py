"""
Mock factory utilities with proper spec validation.

This module provides factory functions for creating properly spec'd mocks
that enforce interface compliance and catch development errors early.
All mocks use the `spec` parameter to ensure they match real interfaces.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
    """
    mock = AsyncMock(spec=Notifier)

    # Validate that log_and_send is properly awaitable
    assert asyncio.iscoroutinefunction(
        mock.log_and_send
    ), "log_and_send mock is not recognized as a coroutine function"

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
    # TODO: Add specific spec when API client interface is formalized
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
    assert asyncio.iscoroutinefunction(
        method
    ), f"{method_name} is not recognized as a coroutine function"


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
    assert (
        mock._spec_class == expected_spec
    ), f"Mock spec is {mock._spec_class}, expected {expected_spec}"
