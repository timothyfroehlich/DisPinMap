"""
@copilot-context-file AGENTS.md
Main module for Discord Pinball Map Bot
Handles Discord bot setup and command registration
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv

# Load .env from the repo root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Try to import from src, fallback for running directly
try:
    from .database import Database  # type: ignore

    # from .messages import Messages
except ImportError:
    from database import Database  # type: ignore

    # from messages import Messages

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add a global flag to indicate test mode
TEST_STARTUP = "--test-startup" in sys.argv

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True

# Global for cleanup
http_runner = None


async def create_bot(db_session_factory=None, notifier=None):
    """
    Creates and configures the Discord bot instance.
    This factory allows creating bot instances for both production and testing.

    Args:
        db_session_factory: Optional database session factory for dependency injection
        notifier: Optional notifier instance for dependency injection. If None, creates a new Notifier instance.
    """
    # Initialize bot with intents
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="/", intents=intents)

    # Use the provided session factory for tests, or create a new default DB for production
    database = Database(session_factory=db_session_factory)
    bot.database = database

    # Use injected notifier or create a new one for production
    if notifier is None:
        # Import notifier after other imports
        try:
            from .notifier import Notifier
        except ImportError:
            from notifier import Notifier
        notifier = Notifier(database)
    bot.notifier = notifier

    # Determine the absolute path to the cogs directory
    cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cogs")

    # Load command cogs
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"src.cogs.{filename[:-3]}")
            except Exception as e:
                logger.error(
                    f"❌ Failed to load extension {filename}: {e}", exc_info=True
                )

    @bot.event
    async def on_ready():
        """Log when bot is ready"""
        logger.info(f"Bot is ready! Logged in as {bot.user.name} ({bot.user.id})")
        if TEST_STARTUP:
            logger.info(
                "Test startup flag detected. Shutting down after successful connection."
            )
            await bot.close()

    @bot.event
    async def on_message(message):
        """Log received messages and handle commands"""
        if message.author != bot.user:
            logger.info(
                f"Received message from {message.author.name} ({message.author.id}) in channel {message.channel.name} ({message.channel.id}): {message.content}"
            )
        await bot.process_commands(message)

    @bot.event
    async def on_command_error(ctx, error):
        """Handle command errors"""
        logger.error(f"An error occurred in command '{ctx.command}': {error}")

    return bot


def get_secret(secret_name, project_id):
    """Retrieve a secret from Google Cloud Secret Manager."""
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except ImportError:
        logger.warning(
            "google-cloud-secret-manager is not installed. Cannot fetch secrets from GCP."
        )
        return None
    except Exception as e:
        logger.error(f"Failed to access secret {secret_name}: {e}")
        return None


async def handle_health_check(request):
    """Health check endpoint for Cloud Run"""
    return web.Response(text="OK", status=200)


async def start_http_server():
    """Start HTTP server for health checks"""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)

    # Get port from environment (Cloud Run sets this)
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"  # Listen on all interfaces for Cloud Run

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"HTTP health check server started on {host}:{port}")
    return runner


async def cleanup(bot_instance):
    """Graceful shutdown"""
    logger.info("Starting graceful shutdown...")
    if http_runner:
        await http_runner.cleanup()
        logger.info("HTTP server cleaned up.")
    if not bot_instance.is_closed():
        await bot_instance.close()
        logger.info("Discord bot client closed.")
    logger.info("Graceful shutdown complete.")


def handle_signal(signum, frame, bot_instance):
    """Handle OS signals for graceful shutdown"""
    logger.info(f"Received signal {signum}, initiating shutdown.")
    asyncio.create_task(cleanup(bot_instance))


async def main():
    """Async entry point for the bot"""
    global http_runner

    bot = await create_bot()

    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda s, f: handle_signal(s, f, bot))
    signal.signal(signal.SIGTERM, lambda s, f: handle_signal(s, f, bot))

    try:
        # Log all environment variables for debugging
        logger.info(f"Environment variables: {os.environ}")

        # Get Discord token from environment variable or Secret Manager
        token = os.environ.get("DISCORD_TOKEN")
        if token is None:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            secret_name = os.environ.get("DISCORD_TOKEN_SECRET_NAME")
            logger.info(f"Project ID: {project_id}, Secret Name: {secret_name}")
            if project_id and secret_name:
                logger.info(
                    f"Attempting to fetch secret '{secret_name}' from project '{project_id}'"
                )
                token = get_secret(secret_name, project_id)
                if token:
                    logger.info(
                        "Successfully fetched Discord token from Secret Manager."
                    )
                    logger.info(f"Token length: {len(token)}")
                else:
                    logger.warning(
                        "Fetched Discord token from Secret Manager, but it is empty."
                    )

        if not token:
            logger.critical(
                "DISCORD_TOKEN is not set after checking environment and Secret Manager."
            )
            raise ValueError("DISCORD_TOKEN is not set.")

        # Start http server and bot concurrently
        http_runner = await start_http_server()
        await bot.start(token)

    except (asyncio.CancelledError, ValueError):
        # Let the cleanup handler manage shutdown
        pass
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally:
        if not bot.is_closed():
            await cleanup(bot)


if __name__ == "__main__":
    asyncio.run(main())
