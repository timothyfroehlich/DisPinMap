"""
Command logic for Discord Pinball Map Bot
Extracted command handlers that can be used by both Discord bot and CLI test
"""

import asyncio # For TimeoutError in confirmation
from typing import List, Dict, Any, Protocol, Optional
try:
    from .database import Database
    from .api import fetch_submissions_for_location, fetch_submissions_for_coordinates, search_location_by_name, fetch_location_details
except ImportError:
    from database import Database
    from api import fetch_submissions_for_location, fetch_submissions_for_coordinates, search_location_by_name, fetch_location_details


class MessageContext(Protocol):
    """Protocol for message context (Discord or CLI)"""
    channel: Any
    guild: Any
    author: Any # Added for confirmation check
    bot: Any    # Added for wait_for (access to bot.wait_for)

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
            location_input_stripped = location_input.strip()
            # Try as location ID first
            if location_input_stripped.isdigit():
                location_id = int(location_input_stripped)
                location_details = await fetch_location_details(location_id) # Use new function

                if location_details and location_details.get('id'): # Check if details are valid
                    location_name = location_details.get('name', f'Location {location_id}')

                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, str(location_id))
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

                    submissions = await fetch_submissions_for_location(location_id)
                    await self._post_initial_submissions(ctx, submissions, f"location **{location_name}** (ID: {location_id})")

                    await ctx.send(f"✅ Added location: **{location_name}** (ID: {location_id}) - Monitoring started!")
                else:
                    await ctx.send(f"❌ Location ID {location_id} not found or no details available. Please check the ID on PinballMap.com.")
            else:
                # Search by name using the refactored search_location_by_name
                search_result = await search_location_by_name(location_input_stripped)
                status = search_result.get('status')
                data = search_result.get('data')

                if status == 'exact':
                    location_details = data
                    location_id = location_details['id']
                    location_name = location_details['name']

                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, str(location_id))
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

                    submissions = await fetch_submissions_for_location(location_id)
                    await self._post_initial_submissions(ctx, submissions, f"location **{location_name}** (ID: {location_id})")

                    await ctx.send(f"✅ Added location: **{location_name}** (ID: {location_id}) - Monitoring started!")

                elif status == 'suggestions':
                    suggestions = data
                    if suggestions:
                        message = f"Location '{location_input_stripped}' not found directly. Did you mean one of these? (Up to 5 shown)\n"
                        for i, loc in enumerate(suggestions):
                            message += f"{i+1}. **{loc['name']}** (ID: {loc['id']})\n"
                        message += "\nPlease use `!location add <ID>` with the ID of the correct location."
                        await ctx.send(message)
                    else: # Should ideally be caught by \'not_found\', but as a fallback
                        await ctx.send(f"❌ No locations found matching \'{location_input_stripped}\'.")

                elif status == 'not_found':
                    await ctx.send(f"❌ No locations found matching \'{location_input_stripped}\'.")

                else: # Should not happen with current search_location_by_name
                    await ctx.send(f"❌ An unexpected error occurred while searching for \'{location_input_stripped}\'.")

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
        """Show current monitoring status, including individual target poll rates."""
        config = self.db.get_channel_config(ctx.channel.id)
        targets = self.db.get_monitoring_targets(ctx.channel.id) # Fetches ordered by ID

        status_msg = "**Channel Monitoring Status:**\n"

        if config:
            status_msg += f"▶️ **Overall Status:** {'Active' if config.get('is_active') else 'Inactive'}\n"
            status_msg += f"🔔 **Notification Types:** {config.get('notification_types', 'machines (default)')}\n"
        else:
            status_msg += "▶️ **Overall Status:** Inactive (Channel not fully configured)\n"
            status_msg += "🔔 **Notification Types:** machines (default)\n"

        status_msg += f"\n**Monitoring Targets (Total: {len(targets)}):**\n"

        if not targets:
            status_msg += "No monitoring targets configured for this channel. Use `!location add` or `!latlong add` to start.\n"
        else:
            for i, target in enumerate(targets):
                target_id_display = i + 1
                target_type = target['target_type']
                target_name_db = target['target_name']
                target_data = target['target_data']
                poll_rate = target['poll_rate_minutes']
                
                display_name = ""
                if target_type == 'location':
                    display_name = f"{target_name_db} (ID: {target_data})"
                elif target_type == 'latlong':
                    parts = target_name_db.split(',')
                    if len(parts) == 3: # lat,lon,radius
                        display_name = f"Coordinates {parts[0]},{parts[1]} (Radius: {parts[2]}mi)"
                    else:
                        display_name = target_name_db # Fallback
                else:
                    display_name = target_name_db

                status_msg += f"{target_id_display}. {display_name} (Type: {target_type}, Poll: {poll_rate} min)\n"
        
        await ctx.send(status_msg)

    async def handle_poll_rate(self, ctx: MessageContext, minutes: int, target_selector: Optional[str] = None):
        """Handles the !poll_rate command logic."""
        if minutes < 15:
            await ctx.send("❌ Poll rate must be at least 15 minutes.")
            return

        targets = self.db.get_monitoring_targets(ctx.channel.id)
        # If target_selector is None (command was `!poll_rate <minutes>`), it defaults to "all"
        effective_selector = target_selector.lower() if target_selector is not None else "all"

        if effective_selector == "all":
            if not targets:
                # This matches the test case, though "No targets to update." might also be suitable.
                await ctx.send(f"✅ Poll rate for all 0 targets set to {minutes} minutes.")
                return

            if len(targets) >= 5:
                # Ensure bot and author are available on ctx for wait_for
                if not hasattr(ctx, 'bot') or not hasattr(ctx.bot, 'wait_for') or not hasattr(ctx, 'author'):
                    await ctx.send("⚠️ Cannot request confirmation due to a context issue. Update cancelled for safety.")
                    return

                await ctx.send(f"You are about to change the poll rate for {len(targets)} targets. Are you sure? (yes/no)")
                try:
                    def check(message):
                        return message.author == ctx.author and \
                               message.channel == ctx.channel and \
                               message.content.lower() in ['yes', 'y', 'no', 'n']

                    reply_message = await ctx.bot.wait_for('message', timeout=30.0, check=check)
                    
                    if reply_message.content.lower() in ['no', 'n']:
                        await ctx.send("Poll rate update cancelled.")
                        return
                    # If 'yes' or 'y', proceed
                except asyncio.TimeoutError:
                    await ctx.send("No confirmation received. Poll rate update cancelled.")
                    return
                except Exception as e: # Catch other potential errors with wait_for
                    await ctx.send(f"An error occurred during confirmation: {e}. Update cancelled.")
                    return
            
            num_updated = self.db.update_channel_monitoring_targets_poll_rate(ctx.channel.id, minutes)
            await ctx.send(f"✅ Poll rate for all {num_updated} targets set to {minutes} minutes.")

        elif effective_selector.isdigit():
            target_idx_one_based = int(effective_selector)
            if not (1 <= target_idx_one_based <= len(targets)):
                await ctx.send("❌ Invalid target ID. Please use a number from the `!status` list.")
                return
            
            selected_target_info = targets[target_idx_one_based - 1]
            actual_target_db_id = selected_target_info['id']
            
            target_display_name = ""
            ttype = selected_target_info['target_type']
            tname = selected_target_info['target_name']
            tdata = selected_target_info['target_data']

            if ttype == 'location':
                target_display_name = f"{tname} (ID: {tdata})"
            elif ttype == 'latlong':
                parts = tname.split(',')
                if len(parts) == 3: target_display_name = f"Coordinates {parts[0]},{parts[1]} (Radius: {parts[2]}mi)"
                else: target_display_name = tname
            else: target_display_name = tname

            if self.db.update_monitoring_target_poll_rate(actual_target_db_id, minutes):
                await ctx.send(f"✅ Poll rate for '{target_display_name}' set to {minutes} minutes.")
            else:
                # This might happen if the target was deleted between fetching and updating, though unlikely.
                await ctx.send(f"❌ Could not update poll rate for target ID {target_idx_one_based}. Target may no longer exist or no change was needed.")
        else:
            await ctx.send(f"❌ Invalid target selector '{target_selector}'. Must be a number (from `!status`) or 'all'.")

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
