import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from monitor import MachineMonitor
from api import fetch_austin_machines, get_all_regions, find_region_by_name, fetch_region_machines

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


@client.command(name='regions')
async def list_regions(ctx):
    """List all available pinball regions"""
    try:
        regions = await get_all_regions()
        
        # Group regions for better display
        region_list = sorted([region['name'] for region in regions])
        
        # Split into chunks of 20 for readability
        chunk_size = 20
        chunks = [region_list[i:i + chunk_size] for i in range(0, len(region_list), chunk_size)]
        
        message = f"**Available Pinball Regions ({len(region_list)} total):**\n"
        
        for i, chunk in enumerate(chunks):
            message += f"\n**Page {i+1}/{len(chunks)}:**\n"
            message += ", ".join(chunk)
            
            # Send message if it's getting long
            if len(message) > 1500:
                await ctx.send(message)
                message = ""
        
        if message:  # Send any remaining content
            await ctx.send(message)
            
    except Exception as e:
        await ctx.send(f"❌ Error fetching regions: {str(e)}")


@client.command(name='location')
async def set_location(ctx, *args):
    """Set monitoring location
    
    Examples:
    !location austin          (region name)
    !location 30.27 -97.74    (latitude longitude)"""
    if not args:
        await ctx.send("❌ Please specify a location. Examples:\n"
                      "`!location austin` (region name)\n"
                      "`!location 30.2672 -97.7431` (latitude longitude)")
        return
    
    try:
        if len(args) == 1:
            # Region name
            region_name = args[0]
            region = await find_region_by_name(region_name)
            
            # Clear lat/lon and set region
            db.update_channel_config(ctx.channel.id, ctx.guild.id, 
                                   region_name=region['name'], 
                                   latitude=None, longitude=None)
            await ctx.send(f"✅ Location set to region: **{region['name']}**")
            
        elif len(args) == 2:
            # Lat/lon coordinates
            try:
                latitude = float(args[0])
                longitude = float(args[1])
                
                if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                    await ctx.send("❌ Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180")
                    return
                
                # Clear region and set lat/lon
                db.update_channel_config(ctx.channel.id, ctx.guild.id,
                                       region_name=None,
                                       latitude=latitude, longitude=longitude)
                await ctx.send(f"✅ Location set to coordinates: **{latitude}, {longitude}**")
                
            except ValueError:
                await ctx.send("❌ Invalid coordinates. Please use numbers for latitude and longitude.")
                return
        else:
            await ctx.send("❌ Invalid format. Use either:\n"
                          "`!location <region_name>` or `!location <latitude> <longitude>`")
            
    except Exception as e:
        await ctx.send(f"❌ Error setting location: {str(e)}")


@client.command(name='radius')
async def set_radius(ctx, miles: int):
    """Set search radius in miles (only used with lat/lon coordinates)"""
    if miles < 1 or miles > 100:
        await ctx.send("❌ Radius must be between 1 and 100 miles")
        return
    
    try:
        db.update_channel_config(ctx.channel.id, ctx.guild.id, radius_miles=miles)
        await ctx.send(f"✅ Search radius set to {miles} miles")
    except Exception as e:
        await ctx.send(f"❌ Error setting radius: {str(e)}")


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
    """Show current channel configuration"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found for this channel. Use `!location` to set up monitoring.")
        return

    status_msg = "**Channel Configuration:**\n"
    
    # Show location info
    if config.get('region_name'):
        status_msg += f"📍 Region: **{config['region_name']}**\n"
    elif config.get('latitude') and config.get('longitude'):
        status_msg += f"📍 Coordinates: **{config['latitude']}, {config['longitude']}**\n"
        status_msg += f"📏 Radius: {config['radius_miles']} miles\n"
    else:
        status_msg += "📍 Location: Not set\n"
    
    status_msg += f"⏱️ Poll Interval: {config['poll_rate_minutes']} minutes\n"
    status_msg += f"🔔 Notifications: {config['notification_types']}\n"
    status_msg += f"▶️ Status: {'Active' if config['is_active'] else 'Inactive'}\n"

    await ctx.send(status_msg)


@client.command(name='start')
async def start_monitoring(ctx):
    """Start monitoring pinball machines for this channel"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found. Use `!location <region_name>` to set up monitoring first.")
        return

    # Check if we have either a region or valid coordinates
    has_region = config.get('region_name') is not None
    has_coords = (config.get('latitude') is not None and config.get('longitude') is not None)
    
    if not has_region and not has_coords:
        await ctx.send("❌ Location not configured. Use `!location <region_name>` or `!location <lat> <lon>` first.")
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
