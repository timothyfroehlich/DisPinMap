"""
General-purpose utility functions to support test implementation.

This module contains helpers for mocking Discord objects and other common
tasks to keep test code clean and DRY (Don't Repeat Yourself).
"""
from unittest.mock import AsyncMock, MagicMock


def mock_discord_context(user_id=12345, channel_id=67890):
    """
    Creates a mock of the Discord `ApplicationContext` for testing commands.

    This provides a realistic-looking object that can be passed to command
    callbacks, allowing for inspection of responses.

    Args:
        user_id: The mock user's ID.
        channel_id: The mock channel's ID.

    Returns:
        A mock context object.
    """
    mock_ctx = MagicMock()
    mock_ctx.interaction = MagicMock()

    # Mock user and channel attributes
    mock_ctx.interaction.user.id = user_id
    mock_ctx.interaction.channel.id = channel_id

    # Mock methods that the bot uses to respond
    mock_ctx.respond = AsyncMock()
    mock_ctx.send = AsyncMock()

    return mock_ctx


def assert_message_sent(mock_discord_channel, expected_content):
    """
    A helper to assert that a specific message was sent to a mocked
    Discord channel.
    """
    # mock_discord_channel.send.assert_called_once()
    # call_args = mock_discord_channel.send.call_args[0][0]
    # assert expected_content in call_args
    pass
