"""
Command logic for Discord Pinball Map Bot
Extracted command handlers that can be used by both Discord bot and CLI test
"""

from typing import List, Dict, Any, Protocol
from database import Database
from api import fetch_submissions_for_location, fetch_submissions_for_coordinates, search_location_by_name


class MessageContext(Protocol):
    """Protocol for message context (Discord or CLI)"""
    channel: Any
    guild: Any
    
    async def send(self, message: str) -> None:
        """Send a message"""
        ...


class CommandHandler:
    def __init__(self, db: Database):
        self.db = db

    async def handle_latlong_add(self, ctx: MessageContext, lat: float, lon: float, radius: int):
        """Add coordinate monitoring"""
        try:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                await ctx.send("❌ Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180")
                return
            
            if radius < 1 or radius > 100:
                await ctx.send("❌ Radius must be between 1 and 100 miles")
                return
            
            target_name = f"{lat},{lon},{radius}"
            self.db.add_monitoring_target(ctx.channel.id, 'latlong', target_name)
            
            # Auto-start monitoring and fetch initial submissions
            self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
            
            # Fetch and post initial submissions
            submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
            await self._post_initial_submissions(ctx, submissions, "coordinate area")
            
            await ctx.send(f"✅ Added coordinates: **{lat}, {lon}** ({radius} mile radius) - Monitoring started!")
        except Exception as e:
            await ctx.send(f"❌ Error adding coordinates: {str(e)}")

    async def handle_latlong_remove(self, ctx: MessageContext, lat: float, lon: float):
        """Remove coordinate monitoring"""
        try:
            targets = self.db.get_monitoring_targets(ctx.channel.id)
            latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
            
            matching_target = None
            for target in latlong_targets:
                parts = target['target_name'].split(',')
                if len(parts) >= 2 and float(parts[0]) == lat and float(parts[1]) == lon:
                    matching_target = target
                    break
            
            if not matching_target:
                await ctx.send(f"❌ Coordinates {lat}, {lon} not found in monitoring list")
                return
            
            self.db.remove_monitoring_target(ctx.channel.id, 'latlong', matching_target['target_name'])
            await ctx.send(f"✅ Removed coordinates: **{lat}, {lon}**")
        except Exception as e:
            await ctx.send(f"❌ Error removing coordinates: {str(e)}")

    async def handle_latlong_list(self, ctx: MessageContext):
        """Show current coordinate targets"""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
        
        if latlong_targets:
            coords = [t['target_name'] for t in latlong_targets]
            await ctx.send(f"**Monitored coordinates:** {', '.join(coords)}\nUse `latlong add <lat> <lon> <radius>` or `latlong remove <lat> <lon>`")
        else:
            await ctx.send("No coordinates being monitored. Use `latlong add <lat> <lon> <radius>` to add some.")

    async def handle_location_add(self, ctx: MessageContext, location_input: str):
        """Add location monitoring (by ID or name)"""
        try:
            # Try as location ID first
            if location_input.isdigit():
                location_id = int(location_input)
                # Test if location exists by fetching submissions
                submissions = await fetch_submissions_for_location(location_id)
                if submissions:
                    location_name = submissions[0].get('location_name', f'Location {location_id}')
                    target_data = str(location_id)
                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, target_data)
                    
                    # Auto-start monitoring
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
                    
                    # Post initial submissions
                    await self._post_initial_submissions(ctx, submissions, f"location {location_name}")
                    
                    await ctx.send(f"✅ Added location: **{location_name}** (ID: {location_id}) - Monitoring started!")
                else:
                    await ctx.send(f"❌ No submissions found for location ID {location_id}")
            else:
                # Search by name
                matching_locations = await search_location_by_name(location_input)
                
                if not matching_locations:
                    await ctx.send(f"❌ No locations found matching '{location_input}'")
                    return
                
                if len(matching_locations) == 1:
                    location = matching_locations[0]
                    location_id = location['location_id']
                    location_name = location['location_name']
                    
                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, str(location_id))
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
                    
                    # Fetch and post initial submissions
                    submissions = await fetch_submissions_for_location(location_id)
                    await self._post_initial_submissions(ctx, submissions, f"location {location_name}")
                    
                    await ctx.send(f"✅ Added location: **{location_name}** (ID: {location_id}) - Monitoring started!")
                else:
                    # Multiple matches - show options
                    message = f"Multiple locations found for '{location_input}':\n"
                    for i, location in enumerate(matching_locations[:10]):
                        message += f"{i+1}. **{location['location_name']}** (ID: {location['location_id']}) in {location.get('city_name', 'Unknown')}\n"
                    
                    if len(matching_locations) > 10:
                        message += f"... and {len(matching_locations) - 10} more"
                    
                    message += "\nPlease be more specific or use the location ID."
                    await ctx.send(message)
                    
        except Exception as e:
            await ctx.send(f"❌ Error adding location: {str(e)}")

    async def handle_location_remove(self, ctx: MessageContext, location_input: str):
        """Remove location monitoring"""
        try:
            # Find matching target by ID or name
            targets = self.db.get_monitoring_targets(ctx.channel.id)
            location_targets = [t for t in targets if t['target_type'] == 'location']
            
            matching_target = None
            for target in location_targets:
                if (target['target_data'] == location_input or  # Match by ID
                    target['target_name'] == location_input):    # Match by name
                    matching_target = target
                    break
            
            if not matching_target:
                await ctx.send(f"❌ Location '{location_input}' not found in monitoring list")
                return
            
            self.db.remove_monitoring_target(ctx.channel.id, 'location', matching_target['target_name'])
            await ctx.send(f"✅ Removed location: **{matching_target['target_name']}**")
        except Exception as e:
            await ctx.send(f"❌ Error removing location: {str(e)}")

    async def handle_location_list(self, ctx: MessageContext):
        """Show current location targets"""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        location_targets = [t for t in targets if t['target_type'] == 'location']
        
        if location_targets:
            locations = []
            for t in location_targets:
                if t['target_data']:
                    locations.append(f"{t['target_name']} (ID: {t['target_data']})")
                else:
                    locations.append(t['target_name'])
            await ctx.send(f"**Monitored locations:** {', '.join(locations)}\nUse `location add <id_or_name>` or `location remove <id>`")
        else:
            await ctx.send("No individual locations being monitored. Use `location add <id_or_name>` to add one.")

    async def handle_status(self, ctx: MessageContext):
        """Show status"""
        config = self.db.get_channel_config(ctx.channel.id)
        targets = self.db.get_monitoring_targets(ctx.channel.id)

        if not config and not targets:
            await ctx.send("❌ No configuration found for this channel. Use `latlong add` or `location add` to set up monitoring.")
            return

        status_msg = "**Channel Configuration:**\n"
        
        # Show monitoring targets
        latlong_targets = [t for t in targets if t['target_type'] == 'latlong']
        location_targets = [t for t in targets if t['target_type'] == 'location']
        
        if latlong_targets:
            coords = []
            for target in latlong_targets:
                parts = target['target_name'].split(',')
                if len(parts) >= 3:
                    coords.append(f"{parts[0]}, {parts[1]} ({parts[2]}mi)")
            status_msg += f"📍 **Coordinates:** {', '.join(coords)}\n"
        
        if location_targets:
            locations = []
            for t in location_targets:
                if t['target_data']:
                    locations.append(f"{t['target_name']} (ID: {t['target_data']})")
                else:
                    locations.append(t['target_name'])
            status_msg += f"🏢 **Locations:** {', '.join(locations)}\n"
        
        if not (latlong_targets or location_targets):
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

    async def handle_check(self, ctx: MessageContext):
        """Check for new submissions"""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        
        if not targets:
            await ctx.send("❌ No monitoring targets configured. Use `latlong add` or `location add` to set up monitoring first.")
            return
        
        try:
            await ctx.send("🔍 Checking for new submissions across all targets...")
            
            all_submissions = []
            target_descriptions = []
            
            # Fetch from all targets
            for target in targets:
                if target['target_type'] == 'latlong':
                    parts = target['target_name'].split(',')
                    if len(parts) >= 3:
                        lat, lon, radius = float(parts[0]), float(parts[1]), int(parts[2])
                        submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
                        target_descriptions.append(f"coordinates **{lat}, {lon}** ({radius}mi)")
                        all_submissions.extend(submissions)
                        
                elif target['target_type'] == 'location':
                    if target['target_data']:
                        location_id = int(target['target_data'])
                        submissions = await fetch_submissions_for_location(location_id)
                        target_descriptions.append(f"location **{target['target_name']}**")
                        all_submissions.extend(submissions)
            
            # Filter out already seen submissions
            new_submissions = self.db.filter_new_submissions(ctx.channel.id, all_submissions)
            
            target_summary = f"{len(targets)} target(s): {', '.join(target_descriptions)}"
            
            if new_submissions:
                await self._post_submissions(ctx, new_submissions)
                # Mark as seen
                submission_ids = [s['id'] for s in new_submissions]
                self.db.mark_submissions_seen(ctx.channel.id, submission_ids)
                
                await ctx.send(f"✅ Found {len(all_submissions)} total submissions across {target_summary}. Posted {len(new_submissions)} new submissions!")
            else:
                await ctx.send(f"✅ Found {len(all_submissions)} submissions across {target_summary}. No new submissions since last check.")
            
        except Exception as e:
            await ctx.send(f"❌ Error checking for submissions: {str(e)}")

    async def _post_initial_submissions(self, ctx: MessageContext, submissions: List[Dict[str, Any]], target_type: str):
        """Post initial submissions when setting up monitoring"""
        if not submissions:
            await ctx.send(f"No recent submissions found for {target_type}")
            return
        
        # Post last 5 submissions
        recent_submissions = sorted(submissions, key=lambda x: x['created_at'], reverse=True)[:5]
        await ctx.send(f"**Last {len(recent_submissions)} submissions for {target_type}:**")
        await self._post_submissions(ctx, recent_submissions)
        
        # Mark ALL submissions as seen (not just the 5 we posted)
        all_submission_ids = [s['id'] for s in submissions]
        self.db.mark_submissions_seen(ctx.channel.id, all_submission_ids)

    async def _post_submissions(self, ctx: MessageContext, submissions: List[Dict[str, Any]]):
        """Post submissions to channel"""
        for submission in submissions:
            submission_type = submission.get('submission_type', 'unknown')
            location_name = submission.get('location_name', 'Unknown Location')
            machine_name = submission.get('machine_name', 'Unknown Machine')
            user_name = submission.get('user_name', 'Anonymous')
            created_at = submission.get('created_at', '')
            
            # Format the submission
            if submission_type == 'new_lmx':
                emoji = "🆕"
                action = "added"
            elif submission_type == 'remove_machine':
                emoji = "🗑️"
                action = "removed"
            elif submission_type == 'new_condition':
                emoji = "🔧"
                action = "updated"
            else:
                emoji = "📝"
                action = "changed"
            
            message = f"{emoji} **{machine_name}** {action} at **{location_name}** by {user_name}"
            if submission.get('comment'):
                message += f"\n💬 {submission['comment']}"
            
            await ctx.send(message)