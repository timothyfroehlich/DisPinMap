import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from monitor import MachineMonitor
from commands import CommandHandler

# Add test directory to path for test_simulation import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'test'))
from test_simulation import TestSimulation

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)
db = Database()
monitor = MachineMonitor(client, db)
test_sim = TestSimulation(client, db)
command_handler = CommandHandler(db)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # Start monitoring when bot is ready
    monitor.start_monitoring()


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


@client.command(name='test')
async def test_simulation(ctx):
    """Run a 30-second simulation of machine changes for testing"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found. Set up monitoring first with `!latlong add` or `!location add`.")
        return

    try:
        # Temporarily ensure the channel is active for testing
        original_status = config['is_active']
        if not original_status:
            db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

        await ctx.send("🧪 Starting test simulation... This will run for 30 seconds!")
        result = await test_sim.run_test_simulation(ctx.channel.id, 30)

        # Restore original status
        if not original_status:
            db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=original_status)

        print(result)  # Log the result

    except Exception as e:
        await ctx.send(f"❌ Test simulation failed: {str(e)}")





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
