import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from monitor import MachineMonitor
from api import fetch_austin_machines

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


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # Start monitoring when bot is ready
    monitor.start_monitoring()


@client.group(name='configure')
async def configure(ctx):
    """Configure monitoring settings for this channel"""
    if ctx.invoked_subcommand is None:
        await ctx.send("Available configuration options: `location`, `radius`, `poll_rate`, `notifications`\n"
                      "Use `!configure <option> <value>` to set configuration.")


@configure.command(name='location')
async def configure_location(ctx, latitude: float, longitude: float):
    """Set the center point for machine searches"""
    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, latitude=latitude, longitude=longitude)
        await ctx.send(f"✅ Location set to {latitude}, {longitude}")
    except Exception as e:
        await ctx.send(f"❌ Error setting location: {str(e)}")


@configure.command(name='radius')
async def configure_radius(ctx, miles: int):
    """Set search radius in miles"""
    if miles < 1 or miles > 100:
        await ctx.send("❌ Radius must be between 1 and 100 miles")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, radius_miles=miles)
        await ctx.send(f"✅ Search radius set to {miles} miles")
    except Exception as e:
        await ctx.send(f"❌ Error setting radius: {str(e)}")


@configure.command(name='poll_rate')
async def configure_poll_rate(ctx, minutes: int):
    """Set polling interval in minutes (minimum 15)"""
    if minutes < 15:
        await ctx.send("❌ Poll rate must be at least 15 minutes")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, poll_rate_minutes=minutes)
        await ctx.send(f"✅ Poll rate set to {minutes} minutes")
    except Exception as e:
        await ctx.send(f"❌ Error setting poll rate: {str(e)}")


@configure.command(name='notifications')
async def configure_notifications(ctx, notification_type: str):
    """Set notification types: machines, comments, or all"""
    valid_types = ['machines', 'comments', 'all']
    if notification_type not in valid_types:
        await ctx.send(f"❌ Invalid notification type. Choose from: {', '.join(valid_types)}")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, notification_types=notification_type)
        await ctx.send(f"✅ Notifications set to: {notification_type}")
    except Exception as e:
        await ctx.send(f"❌ Error setting notifications: {str(e)}")


@client.command(name='status')
async def status(ctx):
    """Show current channel configuration"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found for this channel. Use `!configure` commands to set up monitoring.")
        return

    status_msg = "**Channel Configuration:**\n"
    status_msg += f"📍 Location: {config['latitude']}, {config['longitude']}\n" if config['latitude'] else "📍 Location: Not set\n"
    status_msg += f"📏 Radius: {config['radius_miles']} miles\n"
    status_msg += f"⏱️ Poll Rate: {config['poll_rate_minutes']} minutes\n"
    status_msg += f"🔔 Notifications: {config['notification_types']}\n"
    status_msg += f"▶️ Status: {'Active' if config['is_active'] else 'Inactive'}\n"

    await ctx.send(status_msg)


@client.command(name='start')
async def start_monitoring(ctx):
    """Start monitoring pinball machines for this channel"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found. Use `!configure location <lat> <lon>` to set up monitoring first.")
        return

    if not config['latitude'] or not config['longitude']:
        await ctx.send("❌ Location not configured. Use `!configure location <lat> <lon>` first.")
        return

    if config['is_active']:
        await ctx.send("✅ Monitoring is already active for this channel.")
        return

    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
        await ctx.send("✅ Started monitoring pinball machines! I'll check for changes every "
                      f"{config['poll_rate_minutes']} minutes.")
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


@client.command(name='test')
async def test_simulation(ctx):
    """Run a 30-second simulation of machine changes for testing"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found. Set up monitoring first with `!configure location <lat> <lon>`.")
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




@client.command(name='hello')
async def hello(ctx):
    """Simple hello command"""
    await ctx.send('Hello! I\'m the Pinball Map Bot!')


@client.command(name='ping')
async def ping(ctx):
    """Ping command to test bot responsiveness"""
    await ctx.send(f'Pong! Latency: {round(client.latency * 1000)}ms')


@client.command(name='machines')
async def machines(ctx):
    """List all pinball machines in Austin, TX"""
    try:
        # Fetch locations from Austin region
        data = await fetch_austin_machines()
        locations = data['locations']

        # Count total machines and create summary
        total_machines = sum(location.get('machine_count', 0) for location in locations)
        total_locations = len(locations)

        message = f"**Pinball Machines in Austin, TX**\n"
        message += f"Found {total_machines} machines across {total_locations} locations\n\n"

        # List first few locations with machines
        for i, location in enumerate(locations[:5]):
            if location.get('machine_count', 0) > 0:
                name = location.get('name', 'Unknown')
                machine_count = location.get('machine_count', 0)
                message += f"• **{name}** - {machine_count} machine(s)\n"

        if len(locations) > 5:
            message += f"\n... and {len(locations) - 5} more locations"

        await ctx.send(message)

    except Exception as e:
        await ctx.send(f"Sorry, I couldn't fetch the pinball data right now. Error: {str(e)}")

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
