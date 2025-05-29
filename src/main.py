import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from monitor import MachineMonitor
from api import fetch_austin_machines, get_all_regions, find_region_by_name, fetch_region_machines, search_location_by_name, fetch_location_machines

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


@client.group(name='region')
async def region_group(ctx):
    """Manage region monitoring"""
    if ctx.invoked_subcommand is None:
        targets = db.get_monitoring_targets(ctx.channel.id)
        region_targets = [t for t in targets if t['target_type'] == 'region']
        
        if region_targets:
            regions = [t['target_name'] for t in region_targets]
            await ctx.send(f"**Monitored regions:** {', '.join(regions)}\nUse `!region add <name>` or `!region remove <name>`")
        else:
            await ctx.send("No regions being monitored. Use `!region add <name>` to add one.")


@region_group.command(name='add')
async def add_region(ctx, region_name: str):
    """Add a region to monitor"""
    try:
        region = await find_region_by_name(region_name)
        db.add_monitoring_target(ctx.channel.id, 'region', region['name'])
        
        # Auto-start monitoring
        db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
        
        await ctx.send(f"✅ Added region: **{region['name']}** - Monitoring started!")
    except Exception as e:
        await ctx.send(f"❌ Error adding region: {str(e)}")


@region_group.command(name='remove')
async def remove_region(ctx, region_name: str):
    """Remove a region from monitoring"""
    try:
        region = await find_region_by_name(region_name)
        db.remove_monitoring_target(ctx.channel.id, 'region', region['name'])
        await ctx.send(f"✅ Removed region: **{region['name']}**")
    except Exception as e:
        await ctx.send(f"❌ Error removing region: {str(e)}")


@client.group(name='latlong')
async def latlong_group(ctx):
    """Manage lat/lon coordinate monitoring"""
    if ctx.invoked_subcommand is None:
        targets = db.get_monitoring_targets(ctx.channel.id)
        latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
        
        if latlong_targets:
            coords = [t['target_name'] for t in latlong_targets]
            await ctx.send(f"**Monitored coordinates:** {', '.join(coords)}\nUse `!latlong add <lat> <lon> <radius>` or `!latlong remove <lat> <lon>`")
        else:
            await ctx.send("No coordinates being monitored. Use `!latlong add <lat> <lon> <radius>` to add some.")


@latlong_group.command(name='add')
async def add_latlong(ctx, latitude: float, longitude: float, radius: int):
    """Add lat/lon coordinates to monitor"""
    try:
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            await ctx.send("❌ Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180")
            return
        
        if radius < 1 or radius > 100:
            await ctx.send("❌ Radius must be between 1 and 100 miles")
            return
        
        target_name = f"{latitude},{longitude},{radius}"
        db.add_monitoring_target(ctx.channel.id, 'latlong', target_name)
        
        # Auto-start monitoring
        db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
        
        await ctx.send(f"✅ Added coordinates: **{latitude}, {longitude}** ({radius} mile radius) - Monitoring started!")
    except Exception as e:
        await ctx.send(f"❌ Error adding coordinates: {str(e)}")


@latlong_group.command(name='remove')
async def remove_latlong(ctx, latitude: float, longitude: float):
    """Remove lat/lon coordinates from monitoring"""
    try:
        # Find matching target (any radius)
        targets = db.get_monitoring_targets(ctx.channel.id)
        latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
        
        matching_target = None
        for target in latlong_targets:
            parts = target['target_name'].split(',')
            if len(parts) >= 2 and float(parts[0]) == latitude and float(parts[1]) == longitude:
                matching_target = target
                break
        
        if not matching_target:
            await ctx.send(f"❌ Coordinates {latitude}, {longitude} not found in monitoring list")
            return
        
        db.remove_monitoring_target(ctx.channel.id, 'latlong', matching_target['target_name'])
        await ctx.send(f"✅ Removed coordinates: **{latitude}, {longitude}**")
    except Exception as e:
        await ctx.send(f"❌ Error removing coordinates: {str(e)}")


@client.group(name='location')
async def location_group(ctx):
    """Manage individual pinball location monitoring"""
    if ctx.invoked_subcommand is None:
        targets = db.get_monitoring_targets(ctx.channel.id)
        location_targets = [t for t in targets if t['target_type'] == 'location']
        
        if location_targets:
            locations = [t['target_name'] for t in location_targets]
            await ctx.send(f"**Monitored locations:** {', '.join(locations)}\nUse `!location add <name>` or `!location remove <name>`")
        else:
            await ctx.send("No individual locations being monitored. Use `!location add <name>` to add one.")


@location_group.command(name='add')
async def add_location(ctx, *, location_name: str):
    """Add a specific pinball location to monitor"""
    try:
        # Search for the location
        matching_locations = await search_location_by_name(location_name)
        
        if not matching_locations:
            await ctx.send(f"❌ No locations found matching '{location_name}'")
            return
        
        if len(matching_locations) == 1:
            location = matching_locations[0]
            target_data = f"{location['id']}:{location['region_name']}"
            db.add_monitoring_target(ctx.channel.id, 'location', location['name'], target_data)
            
            # Auto-start monitoring
            db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
            
            await ctx.send(f"✅ Added location: **{location['name']}** (in {location['region_name']}) - Monitoring started!")
        else:
            # Multiple matches - show options
            message = f"Multiple locations found for '{location_name}':\n"
            for i, location in enumerate(matching_locations[:10]):
                message += f"{i+1}. **{location['name']}** (in {location['region_name']})\n"
            
            if len(matching_locations) > 10:
                message += f"... and {len(matching_locations) - 10} more"
            
            message += "\nPlease be more specific with the location name."
            await ctx.send(message)
            
    except Exception as e:
        await ctx.send(f"❌ Error adding location: {str(e)}")


@location_group.command(name='remove')
async def remove_location(ctx, *, location_name: str):
    """Remove a specific pinball location from monitoring"""
    try:
        db.remove_monitoring_target(ctx.channel.id, 'location', location_name)
        await ctx.send(f"✅ Removed location: **{location_name}**")
    except Exception as e:
        await ctx.send(f"❌ Error removing location: {str(e)}")




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
    config = db.get_channel_config(ctx.channel.id)
    targets = db.get_monitoring_targets(ctx.channel.id)

    if not config and not targets:
        await ctx.send("❌ No configuration found for this channel. Use `!region add`, `!latlong add`, or `!location add` to set up monitoring.")
        return

    status_msg = "**Channel Configuration:**\n"
    
    # Show monitoring targets
    region_targets = [t for t in targets if t['target_type'] == 'region']
    latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
    location_targets = [t for t in targets if t['target_type'] == 'location']
    
    if region_targets:
        regions = [t['target_name'] for t in region_targets]
        status_msg += f"🌍 **Regions:** {', '.join(regions)}\n"
    
    if latlong_targets:
        coords = []
        for target in latlong_targets:
            parts = target['target_name'].split(',')
            if len(parts) >= 3:
                coords.append(f"{parts[0]}, {parts[1]} ({parts[2]}mi)")
        status_msg += f"📍 **Coordinates:** {', '.join(coords)}\n"
    
    if location_targets:
        locations = [t['target_name'] for t in location_targets]
        status_msg += f"🏢 **Locations:** {', '.join(locations)}\n"
    
    if not (region_targets or latlong_targets or location_targets):
        status_msg += "📍 **Monitoring:** Nothing configured\n"
    
    # Show general settings
    if config:
        status_msg += f"⏱️ **Poll Interval:** {config['poll_rate_minutes']} minutes\n"
        status_msg += f"🔔 **Notifications:** {config['notification_types']}\n"
        status_msg += f"▶️ **Status:** {'Active' if config['is_active'] else 'Inactive'}\n"
    else:
        status_msg += f"⏱️ **Poll Interval:** 60 minutes (default)\n"
        status_msg += f"🔔 **Notifications:** machines (default)\n"
        status_msg += f"▶️ **Status:** Inactive\n"

    await ctx.send(status_msg)


@client.command(name='start')
async def start_monitoring(ctx):
    """Start monitoring pinball machines for this channel"""
    targets = db.get_monitoring_targets(ctx.channel.id)
    
    if not targets:
        await ctx.send("❌ No monitoring targets configured. Use `!region add`, `!latlong add`, or `!location add` to set up monitoring first.")
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
    """Immediately check for machine changes across all monitoring targets"""
    targets = db.get_monitoring_targets(ctx.channel.id)
    
    if not targets:
        await ctx.send("❌ No monitoring targets configured. Use `!region add`, `!latlong add`, or `!location add` to set up monitoring first.")
        return
    
    try:
        await ctx.send("🔍 Checking for machine changes across all targets...")
        
        # Import the functions we need
        from api import fetch_region_machines, fetch_machines_for_location, fetch_location_machines
        
        all_machines = []
        target_descriptions = []
        
        # Fetch from all targets
        for target in targets:
            if target['target_type'] == 'region':
                machines = await fetch_region_machines(target['target_name'])
                target_descriptions.append(f"region **{target['target_name']}**")
                all_machines.extend(machines)
                
            elif target['target_type'] == 'latlong':
                parts = target['target_name'].split(',')
                if len(parts) >= 3:
                    lat, lon, radius = float(parts[0]), float(parts[1]), int(parts[2])
                    machines = await fetch_machines_for_location(lat, lon, radius)
                    target_descriptions.append(f"coordinates **{lat}, {lon}** ({radius}mi)")
                    all_machines.extend(machines)
                    
            elif target['target_type'] == 'location':
                if target['target_data']:
                    location_id, region_name = target['target_data'].split(':')
                    machines = await fetch_location_machines(int(location_id), region_name)
                    target_descriptions.append(f"location **{target['target_name']}**")
                    all_machines.extend(machines)
        
        # Update tracking and detect changes
        db.update_machine_tracking(ctx.channel.id, all_machines)
        
        # Check for notifications
        notifications = db.get_pending_notifications(ctx.channel.id)
        
        target_summary = f"{len(targets)} target(s): {', '.join(target_descriptions)}"
        
        if notifications:
            # Send the notifications using monitor's logic
            await monitor._send_notifications(ctx.channel.id, notifications)
            
            added_count = len([n for n in notifications if n['change_type'] == 'added'])
            removed_count = len([n for n in notifications if n['change_type'] == 'removed'])
            
            summary = f"✅ Found {len(all_machines)} machines across {target_summary}. "
            if added_count or removed_count:
                changes = []
                if added_count:
                    changes.append(f"{added_count} added")
                if removed_count:
                    changes.append(f"{removed_count} removed")
                summary += f"**Changes detected:** {', '.join(changes)}!"
            else:
                summary += "No changes since last check."
            
            await ctx.send(summary)
        else:
            await ctx.send(f"✅ Found {len(all_machines)} machines across {target_summary}. No changes since last check.")
        
    except Exception as e:
        await ctx.send(f"❌ Error checking for changes: {str(e)}")


@client.command(name='test')
async def test_simulation(ctx):
    """Run a 30-second simulation of machine changes for testing"""
    config = db.get_channel_config(ctx.channel.id)

    if not config:
        await ctx.send("❌ No configuration found. Set up monitoring first with `!region add <name>`.")
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
