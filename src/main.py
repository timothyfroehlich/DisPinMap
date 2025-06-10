import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from .database import Database
    from .monitor import MachineMonitor
    from .commands import CommandHandler
except ImportError:
    from database import Database
    from monitor import MachineMonitor
    from commands import CommandHandler


load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True

# Custom Context for logging
class LoggingContext(commands.Context):
    async def send(self, content=None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None):
        if content:
            logger.info(f"BOT REPLY in #{self.channel} to {self.author}: {content}")
        # Call the original send method
        return await super().send(content=content, tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce, allowed_mentions=allowed_mentions, reference=reference, mention_author=mention_author)

class LoggingBot(commands.Bot):
    async def get_context(self, message, *, cls=LoggingContext):
        return await super().get_context(message, cls=cls)

client = LoggingBot(command_prefix='!', intents=intents)
db = Database()
monitor = MachineMonitor(client, db)
command_handler = CommandHandler(db)


@client.event
async def on_ready():
    logger.info(f'{client.user} has connected to Discord!')
    # Start monitoring when bot is ready
    monitor.start_monitoring()

@client.event
async def on_message(message):
    """Log commands immediately when received, before processing"""
    if message.author == client.user:
        return

    # Check if it's a command and log it immediately
    if message.content.startswith('!'):
        logger.info(f"COMMAND RECEIVED from {message.author} in #{message.channel} (Guild: {message.guild}): {message.content}")

    # Process the command
    await client.process_commands(message)

@client.event
async def on_command(ctx):
    """Command event handler"""
    pass

@client.event
async def on_command_error(ctx, error):
    """Logs command errors and informs the user."""
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f"COMMAND NOT FOUND from {ctx.author} in #{ctx.channel}: {ctx.message.content}")
        # Optionally, send a message to the user, or just log it.
        # await ctx.send(f"❌ Command not found: `{ctx.invoked_with}`")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        # This is handled by specific command error handlers, but good to log here too.
        logger.warning(f"COMMAND ERROR (Missing Arg) from {ctx.author} for `!{ctx.command.qualified_name}`: {error}")
        # The specific command's error handler (e.g., add_location_error) will send the user-facing message.
    elif isinstance(error, commands.CommandInvokeError):
        logger.error(f"COMMAND ERROR (Invoke) from {ctx.author} for `!{ctx.command.qualified_name}`: {error.original}")
        await ctx.send(f"❌ An unexpected error occurred while running `!{ctx.command.qualified_name}`. Please check the logs or contact the admin.")
    else:
        logger.error(f"COMMAND ERROR (Unhandled) from {ctx.author} for `!{ctx.command.qualified_name}`: {error}")
        await ctx.send(f"❌ An unexpected error occurred: {error}")




@client.group(name='latlong')
async def latlong_group(ctx):
    """Manage lat/lon coordinate monitoring"""
    if ctx.invoked_subcommand is None:
        await command_handler.handle_latlong_list(ctx)


@latlong_group.command(name='add')
async def add_latlong(ctx, latitude: float, longitude: float, radius: int = None):
    """Add lat/lon coordinates to monitor (radius optional)"""
    await command_handler.handle_latlong_add(ctx, latitude, longitude, radius)


@latlong_group.command(name='remove')
async def remove_latlong(ctx, latitude: float, longitude: float):
    """Remove lat/lon coordinates from monitoring"""
    await command_handler.handle_latlong_remove(ctx, latitude, longitude)


@client.group(name='location')
async def location_group(ctx):
    """Manage individual pinball location monitoring"""
    if ctx.invoked_subcommand is None:
        await command_handler.handle_location_list(ctx)


@location_group.command(name='add')
async def add_location(ctx, *, location_input: str):
    """Add a specific pinball location to monitor (by ID or name)"""
    await command_handler.handle_location_add(ctx, location_input)

@add_location.error
async def add_location_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ You need to provide a location ID or name. Example: `!location add 1234` or `!location add \"Location Name\"`")
    else:
        await ctx.send(f"❌ An unexpected error occurred with `!location add`: {error}")


@location_group.command(name='remove')
async def remove_location(ctx, *, location_input: str):
    """Remove a specific pinball location from monitoring"""
    await command_handler.handle_location_remove(ctx, location_input)


@client.command(name='city')
async def add_city(ctx, *, city_name: str):
    """Add a city to monitor by name (e.g., "Austin, TX" or "Philadelphia, PA")"""
    await command_handler.handle_city_add(ctx, city_name)

@add_city.error
async def add_city_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ You need to provide a city name.\n\n**Examples:**\n• `!city Austin, TX`\n• `!city Philadelphia, PA`\n• `!city London, UK`")
    else:
        await ctx.send(f"❌ An unexpected error occurred with `!city`: {error}")


@client.command(name='poll_rate')
async def set_poll_rate(ctx, minutes: int, target_selector: str = None):
    """Set polling rate for monitoring targets
    
    Usage:
    !poll_rate 30           - Set all targets to 30 minutes
    !poll_rate 30 all       - Set all targets to 30 minutes  
    !poll_rate 45 3         - Set target #3 to 45 minutes
    
    Use !status to see target numbers"""
    await command_handler.handle_poll_rate(ctx, minutes, target_selector)


@client.command(name='notifications')
async def set_notifications(ctx, notification_type: str):
    """Set notification types

    Examples:
    !notifications machines   (machine additions/removals only)
    !notifications comments   (condition updates only)
    !notifications all        (everything)"""
    valid_types = ['machines', 'comments', 'all']
    if notification_type not in valid_types:
        await ctx.send(f"❌ Invalid notification type. Choose from: {', '.join(valid_types)}")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, notification_types=notification_type)
        await ctx.send(f"✅ Notifications set to: **{notification_type}**")
    except Exception as e:
        await ctx.send(f"❌ Error setting notifications: {str(e)}")

@set_notifications.error
async def set_notifications_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ You need to specify a notification type.\n\n**Examples:**\n• `!notifications machines` - machine additions/removals only\n• `!notifications comments` - condition updates only\n• `!notifications all` - everything")
    else:
        await ctx.send(f"❌ An unexpected error occurred with `!notifications`: {error}")


@client.command(name='status')
async def status(ctx):
    """Show current channel configuration and monitoring targets"""
    await command_handler.handle_status(ctx)


@client.command(name='start')
async def start_monitoring(ctx):
    """Start monitoring pinball machines for this channel"""
    targets = db.get_monitoring_targets(ctx.channel.id)

    if not targets:
        await ctx.send("❌ No monitoring targets configured. Use `!latlong add` or `!location add` to set up monitoring first.")
        return

    config = db.get_channel_config(ctx.channel.id)
    if config and config['is_active']:
        await ctx.send("✅ Monitoring is already active for this channel.")
        return

    try:
        # Create config if it doesn't exist
        if not config:
            db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
            poll_rate = 60  # default
        else:
            db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
            poll_rate = config['poll_rate_minutes']

        target_count = len(targets)
        await ctx.send(f"✅ Started monitoring {target_count} target(s)! I'll check for changes every {poll_rate} minutes.")
    except Exception as e:
        await ctx.send(f"❌ Error starting monitoring: {str(e)}")


@client.command(name='stop')
async def stop_monitoring(ctx):
    """Stop monitoring pinball machines for this channel"""
    config = db.get_channel_config(ctx.channel.id)

    if not config or not config['is_active']:
        await ctx.send("❌ Monitoring is not active for this channel.")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=False)
        await ctx.send("⏹️ Stopped monitoring pinball machines for this channel.")
    except Exception as e:
        await ctx.send(f"❌ Error stopping monitoring: {str(e)}")


@client.command(name='check')
async def check_now(ctx):
    """Immediately check for new submissions across all monitoring targets"""
    await command_handler.handle_check(ctx)







def main():
    """Main function to start the bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("Error: DISCORD_BOT_TOKEN not found in environment variables.")
        logger.error("Please create a .env file with your Discord bot token.")
        exit(1)

    client.run(token)

if __name__ == '__main__':
    main()
