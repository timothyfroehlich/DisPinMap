"""
@copilot-context-file AGENTS.md
Main module for Discord Pinball Map Bot
Handles Discord bot setup and command registration
"""

import os
import logging
import discord
from discord.ext import commands
import sys
from dotenv import load_dotenv
from pathlib import Path
import asyncio
from google.cloud import secretmanager
from aiohttp import web
import signal

# Load .env from the repo root
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# Try to import from src, fallback for running directly
try:
    from .database import Database
    from .messages import Messages
except ImportError:
    from database import Database
    from messages import Messages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add a global flag to indicate test mode
TEST_STARTUP = '--test-startup' in sys.argv

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global for cleanup
http_runner = None

def get_secret(secret_name, project_id):
    """Retrieve a secret from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to access secret {secret_name}: {e}")
        return None

async def handle_health_check(request):
    """Health check endpoint for Cloud Run"""
    return web.Response(text="OK", status=200)

async def start_http_server():
    """Start HTTP server for health checks"""
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)

    # Get port from environment (Cloud Run sets this)
    port = int(os.getenv('PORT', 8080))
    host = '0.0.0.0'  # Listen on all interfaces for Cloud Run

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"HTTP health check server started on {host}:{port}")
    return runner

@bot.event
async def on_ready():
    """Log when bot is ready"""
    logger.info(f'Bot is ready! Logged in as {bot.user.name} ({bot.user.id})')
    if TEST_STARTUP:
        logger.info('Test startup flag detected. Shutting down after successful connection.')
        await bot.close()

@bot.event
async def on_message(message):
    """Log received messages and handle commands"""
    if message.author != bot.user:
        logger.info(f'Received message from {message.author.name} ({message.author.id}) in channel {message.channel.name} ({message.channel.id}): {message.content}')
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    logger.error(f"An error occurred in command '{ctx.command}': {error}")
    # No need to send messages, logging is sufficient

async def cleanup():
    """Graceful shutdown"""
    logger.info("Starting graceful shutdown...")
    if http_runner:
        await http_runner.cleanup()
        logger.info("HTTP server cleaned up.")
    if bot.database:
        bot.database.close()
        logger.info("Database connection closed.")
    if not bot.is_closed():
        await bot.close()
        logger.info("Discord bot client closed.")
    logger.info("Graceful shutdown complete.")

def handle_signal(signum, frame):
    """Handle OS signals for graceful shutdown"""
    logger.info(f"Received signal {signum}, initiating shutdown.")
    asyncio.create_task(cleanup())

async def main():
    """Async entry point for the bot"""
    global http_runner

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        # Log all environment variables for debugging
        logger.info(f"Environment variables: {os.environ}")

        # Create shared instances (not cogs)
        database = Database()
        bot.database = database # Attach db to bot for cleanup

        # Import notifier after other imports
        try:
            from .notifier import Notifier
        except ImportError:
            from notifier import Notifier

        notifier = Notifier(database)

        # Store shared instances on bot for cogs to access
        bot.notifier = notifier

        # Determine the absolute path to the cogs directory
        cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cogs')
        logger.info(f"Loading cogs from: {cogs_dir}")

        # Load command cogs
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await bot.load_extension(f'src.cogs.{filename[:-3]}')
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f'Failed to load extension {filename}: {e}', exc_info=True)

        # Load monitor cog
        try:
            await bot.load_extension('src.monitor')
            logger.info("Successfully loaded monitor cog")
        except Exception as e:
            logger.error(f"Failed to load monitor cog: {e}")

        # Get Discord token from environment variable or Secret Manager
        token = os.environ.get("DISCORD_TOKEN")
        if token is None:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            secret_name = os.environ.get("DISCORD_TOKEN_SECRET_NAME")
            logger.info(f"Project ID: {project_id}, Secret Name: {secret_name}")
            if project_id and secret_name:
                logger.info(f"Attempting to fetch secret '{secret_name}' from project '{project_id}'")
                token = get_secret(secret_name, project_id)
                if token:
                    logger.info("Successfully fetched Discord token from Secret Manager.")
                    logger.info(f"Token length: {len(token)}")
                else:
                    logger.warning("Fetched Discord token from Secret Manager, but it is empty.")

        if not token:
            logger.critical("DISCORD_TOKEN is not set after checking environment and Secret Manager.")
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
            await cleanup()

if __name__ == '__main__':
    asyncio.run(main())
