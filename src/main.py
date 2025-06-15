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
    if isinstance(error, commands.MissingRequiredArgument):
        command_name = ctx.command.name
        message = ""
        if command_name == 'add':
            message = "❌ Please specify a target type (location, coordinates, or city). Usage: `!add <type> [...]`"
        elif command_name == 'rm':
            message = "❌ Please specify the index of the target to remove. Usage: `!rm <index>`"
        elif command_name == 'poll_rate':
            message = "❌ Please specify the poll rate in minutes. Usage: `!poll_rate <minutes> [target_index]`"
        elif command_name == 'notifications':
            message = "❌ Please specify the notification type. Usage: `!notifications <type> [target_index]`\nValid types are: `machines`, `comments`, `all`"

        if message:
            await ctx.send(message)
        else:
            await ctx.send(f"❌ Missing argument: `{error.param.name}`. Please check the command's usage.")

    elif isinstance(error, commands.CommandInvokeError):
        if ctx.command:
            await ctx.send(Messages.Command.Error.COMMAND.format(command=ctx.command.qualified_name))
        else:
            await ctx.send(Messages.Command.Error.GENERAL.format(error=str(error)))
    else:
        await ctx.send(Messages.Command.Error.GENERAL.format(error=str(error)))

async def main():
    """Async entry point for the bot"""
    # Create shared instances (not cogs)
    database = Database()

    # Import notifier after other imports
    try:
        from .notifier import Notifier
    except ImportError:
        from notifier import Notifier

    notifier = Notifier(database)

    # Store shared instances on bot for cogs to access
    bot.database = database
    bot.notifier = notifier

    # Load command cogs
    for filename in os.listdir('./src/cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            await bot.load_extension(f'src.cogs.{filename[:-3]}')

    # Load monitor cog
    await bot.load_extension('src.monitor')

    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.critical("DISCORD_TOKEN environment variable not set.")
        sys.exit(1)

    await bot.start(token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down.")
