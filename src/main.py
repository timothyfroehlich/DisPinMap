import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from monitor import MachineMonitor
from commands import CommandHandler

# Test simulation removed - no longer supported

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True

# Custom Context for logging
class LoggingContext(commands.Context):
    async def send(self, content=None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None):
        if content: # Log only if there is text content
            print(f"BOT REPLY in #{self.channel} to {self.author}: {content}")
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
    print(f'{client.user} has connected to Discord!')
    # Start monitoring when bot is ready
    monitor.start_monitoring()

@client.event
async def on_command(ctx):
    """Logs incoming commands"""
    if ctx.command is None:
        return
    print(f"COMMAND RECEIVED from {ctx.author} in #{ctx.channel} (Guild: {ctx.guild}): {ctx.message.content}")

@client.event
async def on_command_error(ctx, error):
    """Logs command errors and informs the user."""
    if isinstance(error, commands.CommandNotFound):
        print(f"COMMAND NOT FOUND from {ctx.author} in #{ctx.channel}: {ctx.message.content}")
        # Optionally, send a message to the user, or just log it.
        # await ctx.send(f"❌ Command not found: `{ctx.invoked_with}`")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        # This is handled by specific command error handlers, but good to log here too.
        print(f"COMMAND ERROR (Missing Arg) from {ctx.author} for `!{ctx.command.qualified_name}`: {error}")
        # The specific command's error handler (e.g., add_location_error) will send the user-facing message.
    elif isinstance(error, commands.CommandInvokeError):
        print(f"COMMAND ERROR (Invoke) from {ctx.author} for `!{ctx.command.qualified_name}`: {error.original}")
        await ctx.send(f"❌ An unexpected error occurred while running `!{ctx.command.qualified_name}`. Please check the logs or contact the admin.")
    else:
        print(f"COMMAND ERROR (Unhandled) from {ctx.author} for `!{ctx.command.qualified_name}`: {error}")
        await ctx.send(f"❌ An unexpected error occurred: {error}")


# Region commands removed - no longer supported


@client.group(name='latlong')
async def latlong_group(ctx):
    """Manage lat/lon coordinate monitoring"""
    if ctx.invoked_subcommand is None:
        await command_handler.handle_latlong_list(ctx)


@latlong_group.command(name='add')
async def add_latlong(ctx, latitude: float, longitude: float, radius: int):
    """Add lat/lon coordinates to monitor"""
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




@client.command(name='interval')
async def set_poll_rate(ctx, minutes: int):
    """Set polling interval in minutes (minimum 15)"""
    if minutes < 15:
        await ctx.send("❌ Poll interval must be at least 15 minutes")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, poll_rate_minutes=minutes)
        await ctx.send(f"✅ Poll interval set to {minutes} minutes")
    except Exception as e:
        await ctx.send(f"❌ Error setting poll interval: {str(e)}")


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


# Test simulation command removed - no longer supported





def main():
    """Main function to start the bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
        print("Please create a .env file with your Discord bot token.")
        exit(1)

    client.run(token)

if __name__ == '__main__':
    main()
