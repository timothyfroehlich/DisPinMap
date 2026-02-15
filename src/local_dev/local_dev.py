#!/usr/bin/env python3
"""
Local Development Entry Point

Runs the Discord bot with enhanced logging and console interface for local testing.
Loads configuration from .env.local and provides debugging capabilities.
"""

import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.local_dev.local_logging import setup_logging, get_logger
from src.local_dev.console_discord import create_console_interface
from src.local_dev.file_watcher import create_file_watcher
from src.main import create_bot
from src.database import Database

# Global variables for cleanup
bot = None
console_interface = None
file_watcher = None
database = None
logger = None


def load_local_environment():
    """Load local development environment variables"""
    env_file = ".env.local"
    if not os.path.exists(env_file):
        print(f"❌ Local environment file not found: {env_file}")
        print(
            "   Please create .env.local with your Discord bot token and configuration"
        )
        sys.exit(1)

    # Load environment variables
    load_dotenv(env_file)

    # Verify required variables
    required_vars = ["DISCORD_TOKEN", "DATABASE_PATH"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    return True


def setup_signal_handlers():
    """Set up graceful shutdown signal handlers"""

    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(cleanup_and_exit())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def cleanup_and_exit():
    """Clean up resources and exit gracefully"""
    global bot, console_interface, file_watcher, database, logger

    logger.info("🧹 Starting cleanup...")

    # Stop file watcher
    if file_watcher:
        file_watcher.stop()
        logger.info("✅ File watcher stopped")

    # Stop console interface
    if console_interface:
        console_interface.stop()
        logger.info("✅ Console interface stopped")

    # Close Discord bot
    if bot and not bot.is_closed():
        await bot.close()
        logger.info("✅ Discord bot closed")

    # Close database connections
    if database:
        # Database class doesn't have close method, connections are handled by SQLAlchemy
        logger.info("✅ Database connections closed")

    logger.info("👋 Local development session ended")
    sys.exit(0)


async def main():
    """Main local development function"""
    global bot, console_interface, file_watcher, database, logger

    print("🚀 Starting DisPinMap Bot - Local Development Mode")

    # Load environment
    load_local_environment()

    # Set up enhanced logging
    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    setup_logging(log_level, "logs/bot.log")
    logger = get_logger("local_dev")

    logger.info("=" * 60)
    logger.info("🏠 DisPinMap Bot - Local Development Session")
    logger.info("=" * 60)
    logger.info(f"📁 Database: {os.getenv('DATABASE_PATH')}")
    logger.info(f"📊 Log Level: {log_level}")
    logger.info(f"🔧 Local Mode: {os.getenv('LOCAL_DEV_MODE', 'false')}")

    # Set up signal handlers for graceful shutdown
    setup_signal_handlers()

    try:
        # Initialize database
        logger.info("🗄️  Initializing database...")
        database = Database()

        # Create Discord bot
        logger.info("🤖 Creating Discord bot...")
        bot = await create_bot()

        # Set up console interface
        logger.info("🖥️  Setting up console interface...")
        console_interface = await create_console_interface(bot, database)

        # Set up file watcher for external commands
        logger.info("📁 Setting up file watcher for external commands...")
        file_watcher = await create_file_watcher(console_interface.process_command)

        # Start the bot
        logger.info("🚀 Starting Discord bot...")
        discord_token = os.getenv("DISCORD_TOKEN")

        # Run the bot
        await bot.start(discord_token)

    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
        await cleanup_and_exit()
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}", exc_info=True)
        await cleanup_and_exit()


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    # Check if we're in the right directory
    if not os.path.exists("src/main.py"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)

    # Run the local development environment
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
