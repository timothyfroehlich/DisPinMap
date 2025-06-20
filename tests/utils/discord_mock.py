"""
Discord Simulation Framework

This module provides comprehensive Discord bot simulation capabilities including
fake Discord objects, command execution, and message verification.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock

logger = logging.getLogger(__name__)


class MockUser:
    """Mock Discord user object."""

    def __init__(
        self, user_id: int = None, name: str = "TestUser", discriminator: str = "0001"
    ):
        self.id = user_id or int(str(uuid.uuid4().int)[:18])  # 18-digit Discord ID
        self.name = name
        self.discriminator = discriminator
        self.mention = f"<@{self.id}>"
        self.display_name = name
        self.bot = False

    def __str__(self):
        return f"{self.name}#{self.discriminator}"


class MockChannel:
    """Mock Discord channel object with message tracking."""

    def __init__(
        self, channel_id: int = None, name: str = "test-channel", guild_id: int = None
    ):
        self.id = channel_id or int(str(uuid.uuid4().int)[:18])
        self.name = name
        self.guild_id = guild_id or int(str(uuid.uuid4().int)[:18])
        self.mention = f"<#{self.id}>"
        self.type = "text"

        # Track sent messages
        self.sent_messages = []

    async def send(self, content: str = None, **kwargs) -> "MockMessage":
        """Mock channel.send() method that captures messages."""
        message = MockMessage(
            content=content,
            channel=self,
            author=MockUser(name="Bot"),  # Bot user
            **kwargs,
        )
        self.sent_messages.append(message)

        # Log the message
        logger.debug(f"Channel {self.name} sent: {content}")

        return message

    def get_sent_messages(self) -> List["MockMessage"]:
        """Get all messages sent to this channel."""
        return self.sent_messages.copy()

    def clear_messages(self):
        """Clear message history."""
        self.sent_messages.clear()

    def get_last_message(self) -> Optional["MockMessage"]:
        """Get the most recent message."""
        return self.sent_messages[-1] if self.sent_messages else None


class MockGuild:
    """Mock Discord guild (server) object."""

    def __init__(self, guild_id: int = None, name: str = "Test Server"):
        self.id = guild_id or int(str(uuid.uuid4().int)[:18])
        self.name = name
        self.channels = {}

    def add_channel(self, channel: MockChannel) -> MockChannel:
        """Add a channel to this guild."""
        channel.guild_id = self.id
        self.channels[channel.id] = channel
        return channel

    def get_channel(self, channel_id: int) -> Optional[MockChannel]:
        """Get a channel by ID."""
        return self.channels.get(channel_id)


class MockMessage:
    """Mock Discord message object."""

    def __init__(self, content: str, channel: MockChannel, author: MockUser, **kwargs):
        self.id = int(str(uuid.uuid4().int)[:18])
        self.content = content
        self.channel = channel
        self.author = author
        self.guild = MockGuild(guild_id=channel.guild_id)
        self.created_at = datetime.now(timezone.utc)

        # Additional message attributes
        self.embeds = kwargs.get("embeds", [])
        self.attachments = kwargs.get("attachments", [])
        self.reactions = []


class MockContext:
    """Mock Discord command context."""

    def __init__(
        self, channel: MockChannel, user: MockUser, command: str, args: List[str] = None
    ):
        self.channel = channel
        self.author = user
        self.guild = MockGuild(guild_id=channel.guild_id)
        self.command = command
        self.args = args or []

        # Track sent messages for this context
        self.sent_messages = []

    async def send(self, content: str = None, **kwargs) -> MockMessage:
        """Mock ctx.send() method."""
        message = await self.channel.send(content, **kwargs)
        self.sent_messages.append(message)
        return message

    def get_sent_messages(self) -> List[MockMessage]:
        """Get messages sent in response to this command."""
        return self.sent_messages.copy()


class MockBot:
    """Mock Discord bot with command execution capabilities."""

    def __init__(self, command_prefix: str = "!"):
        self.command_prefix = command_prefix
        self.user = MockUser(name="DisPinMap Bot")
        self.guilds = {}
        self.cogs = {}

        # Mock database and notifier (to be injected)
        self.database = None
        self.notifier = None

        # Track events
        self.events = []

    def add_guild(self, guild: MockGuild) -> MockGuild:
        """Add a guild to the bot."""
        self.guilds[guild.id] = guild
        return guild

    def get_channel(self, channel_id: int) -> Optional[MockChannel]:
        """Get a channel by ID across all guilds."""
        for guild in self.guilds.values():
            channel = guild.get_channel(channel_id)
            if channel:
                return channel
        return None

    def add_cog(self, name: str, cog_instance: Any):
        """Add a cog to the bot."""
        self.cogs[name] = cog_instance

    def get_cog(self, name: str) -> Optional[Any]:
        """Get a cog by name."""
        return self.cogs.get(name)

    async def wait_until_ready(self):
        """Mock wait_until_ready method."""
        # Instant ready for testing
        pass

    async def close(self):
        """Mock close method."""
        pass

    def is_closed(self) -> bool:
        """Mock is_closed method."""
        return False


class CommandSimulator:
    """Simulates Discord command execution."""

    def __init__(self, bot: MockBot):
        self.bot = bot
        self.execution_log = []

    async def execute_command(
        self,
        command: str,
        channel: MockChannel,
        user: MockUser = None,
        args: List[str] = None,
    ) -> MockContext:
        """Execute a command and return the context."""
        user = user or MockUser()
        args = args or []

        # Create context
        ctx = MockContext(channel, user, command, args)

        # Log execution
        self.execution_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "args": args,
                "channel_id": channel.id,
                "user_id": user.id,
            }
        )

        # Try to find and execute the command
        success = await self._execute_command_on_cogs(ctx, command, args)

        if not success:
            await ctx.send(f"❌ Unknown command: {command}")

        return ctx

    async def _execute_command_on_cogs(
        self, ctx: MockContext, command: str, args: List[str]
    ) -> bool:
        """Try to execute command on loaded cogs."""
        # This is a simplified command dispatcher
        # In a real implementation, we'd use discord.py's command system

        for cog_name, cog in self.bot.cogs.items():
            if hasattr(cog, command):
                try:
                    command_func = getattr(cog, command)
                    if asyncio.iscoroutinefunction(command_func):
                        await command_func(ctx, *args)
                    else:
                        command_func(ctx, *args)
                    return True
                except Exception as e:
                    logger.error(f"Error executing command {command}: {e}")
                    await ctx.send(f"❌ Error executing command: {str(e)}")
                    return True  # Command was found but failed

        return False  # Command not found


class DiscordSimulator:
    """Main Discord simulation coordinator."""

    def __init__(self):
        self.bot = MockBot()
        self.command_simulator = CommandSimulator(self.bot)
        self.setup_done = False

    def setup_test_environment(
        self, guild_name: str = "Test Server", channel_name: str = "test-channel"
    ) -> tuple[MockGuild, MockChannel]:
        """Set up a basic test environment with guild and channel."""
        guild = MockGuild(name=guild_name)
        channel = MockChannel(name=channel_name)

        guild.add_channel(channel)
        self.bot.add_guild(guild)

        return guild, channel

    def inject_dependencies(self, database, notifier):
        """Inject database and notifier dependencies."""
        self.bot.database = database
        self.bot.notifier = notifier

    def load_cogs(self, cog_instances: Dict[str, Any]):
        """Load cogs into the bot."""
        for name, cog in cog_instances.items():
            self.bot.add_cog(name, cog)

    async def simulate_user_interaction(
        self,
        command: str,
        args: List[str] = None,
        channel: MockChannel = None,
        user: MockUser = None,
    ) -> MockContext:
        """Simulate a user running a command."""
        if not channel:
            # Use first available channel
            for guild in self.bot.guilds.values():
                for ch in guild.channels.values():
                    channel = ch
                    break
                if channel:
                    break

        if not channel:
            raise ValueError("No channel available for simulation")

        return await self.command_simulator.execute_command(
            command, channel, user, args
        )

    def get_execution_log(self) -> List[Dict]:
        """Get command execution log."""
        return self.command_simulator.execution_log.copy()

    def clear_logs(self):
        """Clear all logs and messages."""
        self.command_simulator.execution_log.clear()
        for guild in self.bot.guilds.values():
            for channel in guild.channels.values():
                channel.clear_messages()


class MessageAnalyzer:
    """Analyzes bot responses for validation."""

    def __init__(self):
        self.patterns = {
            "success": ["✅", "Added", "Success", "✨"],
            "error": ["❌", "Error", "Failed", "Invalid"],
            "info": ["📋", "Found", "Status", "📍"],
            "notification": ["🎮", "🗑️", "🔧"],
        }

    def categorize_message(self, message: str) -> str:
        """Categorize a message by its content."""
        message_lower = message.lower()

        for category, indicators in self.patterns.items():
            for indicator in indicators:
                if indicator.lower() in message_lower:
                    return category

        return "unknown"

    def extract_location_info(self, message: str) -> Optional[Dict[str, str]]:
        """Extract location information from bot messages."""
        # Simple extraction logic - could be enhanced
        if "location" in message.lower():
            # Try to extract location ID or name
            import re

            # Look for location ID pattern
            id_match = re.search(r"ID:\s*(\d+)", message)
            if id_match:
                return {"type": "location", "id": id_match.group(1)}

            # Look for coordinates pattern
            coord_match = re.search(
                r"coordinates.*?(\d+\.\d+),\s*(-?\d+\.\d+)", message
            )
            if coord_match:
                return {
                    "type": "coordinates",
                    "lat": coord_match.group(1),
                    "lon": coord_match.group(2),
                }

        return None

    def validate_response_format(self, message: str, expected_format: str) -> bool:
        """Validate that a message matches expected format patterns."""
        format_patterns = {
            "success_with_name": r"✅.*Added.*:.*\*\*.*\*\*",
            "error_with_reason": r"❌.*:",
            "list_format": r"\*\*.*\*\*.*\n.*",
            "notification": r"🎮.*\*\*.*\*\*.*added.*at.*\*\*.*\*\*",
        }

        pattern = format_patterns.get(expected_format)
        if pattern:
            import re

            return bool(re.search(pattern, message, re.DOTALL))

        return False


# Convenience functions for quick setup


def create_basic_simulation() -> tuple[DiscordSimulator, MockChannel]:
    """Create a basic simulation setup with one channel."""
    simulator = DiscordSimulator()
    guild, channel = simulator.setup_test_environment()
    return simulator, channel


def create_multi_channel_simulation() -> tuple[DiscordSimulator, List[MockChannel]]:
    """Create a simulation with multiple channels for testing."""
    simulator = DiscordSimulator()

    channels = []
    for i in range(3):
        guild, channel = simulator.setup_test_environment(
            guild_name=f"Test Server {i+1}", channel_name=f"test-channel-{i+1}"
        )
        channels.append(channel)

    return simulator, channels
