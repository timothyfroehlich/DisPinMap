"""
General-purpose utility functions to support test implementation.

This module contains helpers for mocking Discord objects and other common
tasks to keep test code clean and DRY (Don't Repeat Yourself).

DEPRECATED: Use mock_factories.py for new test code. This module is maintained
for backward compatibility but new tests should use the spec-based factories.
"""

import warnings
from unittest.mock import AsyncMock, MagicMock


def mock_discord_context(user_id=12345, channel_id=67890):
    """
    Creates a mock of the Discord `ApplicationContext` for testing commands.

    DEPRECATED: Use create_discord_context_mock() from mock_factories.py instead.
    This function lacks proper spec validation and should not be used for new tests.

    This provides a realistic-looking object that can be passed to command
    callbacks, allowing for inspection of responses.

    Args:
        user_id: The mock user's ID.
        channel_id: The mock channel's ID.

    Returns:
        A mock context object.
    """
    warnings.warn(
        "mock_discord_context() is deprecated. Use create_discord_context_mock() "
        "from mock_factories.py for proper spec validation.",
        DeprecationWarning,
        stacklevel=2,
    )

    mock_ctx = MagicMock()
    mock_ctx.interaction = MagicMock()

    # Mock user and channel attributes
    mock_ctx.interaction.user.id = user_id
    mock_ctx.interaction.channel.id = channel_id

    # The real context has a .channel attribute that is used by the notifier
    mock_ctx.channel = MagicMock()
    mock_ctx.channel.send = AsyncMock()

    # Mock methods that the bot uses to respond
    mock_ctx.respond = AsyncMock()
    mock_ctx.send = AsyncMock()

    return mock_ctx


def assert_message_sent(mock_discord_channel, expected_content):
    """
    A helper to assert that a specific message was sent to a mocked
    Discord channel.

    DEPRECATED: This function is no longer maintained. Use direct
    assertion patterns with spec-based mocks from mock_factories.py.
    """
    warnings.warn(
        "assert_message_sent() is deprecated. Use direct assertions with "
        "spec-based mocks from mock_factories.py.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Basic implementation for backward compatibility
    mock_discord_channel.send.assert_called()

    # Check if expected content is in any of the sent messages
    call_args_list = mock_discord_channel.send.call_args_list
    messages_sent = []

    for call in call_args_list:
        args, kwargs = call
        # Extract message from positional args (first argument)
        if args:
            messages_sent.append(str(args[0]))
        # Extract message from keyword arguments ('content' key)
        elif kwargs and "content" in kwargs:
            messages_sent.append(str(kwargs["content"]))
        # Fallback for other patterns
        elif kwargs:
            messages_sent.append(str(kwargs))
        else:
            messages_sent.append("(no message content)")

    found = any(expected_content in message for message in messages_sent)
    assert (
        found
    ), f"Expected content '{expected_content}' not found in sent messages: {messages_sent}"
