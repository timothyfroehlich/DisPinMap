"""
Cog for monitoring-related commands
"""
import logging
from typing import Optional
from datetime import datetime, timezone
from discord.ext import commands
from src.database import Database
from src.api import fetch_submissions_for_location, fetch_submissions_for_coordinates, search_location_by_name, fetch_location_details, geocode_city_name
from src.messages import Messages
from src.notifier import Notifier

logger = logging.getLogger(__name__)

class MonitoringCog(commands.Cog, name="Monitoring"):
    def __init__(self, bot, db: Database, notifier: Notifier):
        self.bot = bot
        self.db = db
        self.notifier = notifier

    def _sort_submissions(self, submissions: list) -> list:
        """Sorts submissions by date and returns the most recent ones."""
        if not submissions:
            return []

        # Sort by 'created_at' descending (newest first)
        # Handles potential parsing errors gracefully
        def sort_key(s):
            try:
                return datetime.fromisoformat(s['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError, KeyError):
                return datetime.min

        sorted_submissions = sorted(submissions, key=sort_key, reverse=True)
        return sorted_submissions

    def _format_relative_time(self, dt: datetime) -> str:
        """Format a datetime as a human-readable relative time string."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:  # Less than 1 hour
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:  # Less than 1 day
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff.total_seconds() < 604800:  # Less than 1 week
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"
        else:
            return dt.strftime("%b %d")  # e.g., "Dec 17"

    @commands.command(name='add')
    async def add(self, ctx, target_type: str, *args):
        """Add a new monitoring target. Usage: !add <location|coordinates|city> <args>"""
        try:
            if target_type == 'location':
                if not args:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.MISSING_LOCATION)
                    return
                await self._handle_location_add(ctx, " ".join(args))
            elif target_type == 'coordinates':
                if len(args) < 2:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.MISSING_COORDS)
                    return
                try:
                    lat, lon = float(args[0]), float(args[1])
                    radius = int(args[2]) if len(args) > 2 else None
                    await self._handle_coordinates_add(ctx, lat, lon, radius)
                except ValueError:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.INVALID_COORDS_FORMAT)
            elif target_type == 'city':
                if not args:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.MISSING_CITY)
                    return

                city_name_parts = []
                radius = None

                if len(args) > 1 and args[-1].isdigit():
                    radius = int(args[-1])
                    city_name_parts = args[:-1]
                else:
                    city_name_parts = args

                city_name = " ".join(city_name_parts)
                await self._handle_city_add(ctx, city_name, radius)
            else:
                await self.notifier.log_and_send(ctx, Messages.Command.Add.INVALID_TYPE)
        except Exception as e:
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type=target_type,
                error_message=str(e)
            ))

    @commands.command(name='rm')
    async def remove(self, ctx, index: str):
        """Remove a monitoring target by its index from the list."""
        try:
            targets = self.db.get_monitoring_targets(ctx.channel.id)

            if not targets:
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.NO_TARGETS)
                return

            index_int = int(index)
            if index_int < 1 or index_int > len(targets):
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_INDEX.format(max_index=len(targets)))
                return

            target = targets[index_int - 1]
            self.db.remove_monitoring_target(ctx.channel.id, target['target_type'], target['target_name'])

            if target['target_type'] == 'latlong':
                coords = target['target_name'].split(',')
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.SUCCESS.format(
                    target_type="coordinates",
                    name=f"{coords[0]}, {coords[1]}"
                ))
            else:
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.SUCCESS.format(
                    target_type=target['target_type'],
                    name=target['target_name']
                ))

        except ValueError:
            await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_INDEX_NUMBER)

    @commands.command(name='list', aliases=['ls', 'status'])
    async def list_targets(self, ctx):
        """Show all monitored targets in a formatted table."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        channel_config = self.db.get_channel_config(ctx.channel.id)

        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.List.NO_TARGETS)
            return

        headers = ["Index", "Target", "Poll (min)", "Notifications", "Last Checked"]
        rows = []

        for i, target in enumerate(targets, 1):
            # Target Name
            if target['target_type'] == 'latlong':
                coords = target['target_name'].split(',')
                target_name = f"Coords: {coords[0]}, {coords[1]}"
                if len(coords) > 2:
                    target_name += f" ({coords[2]}mi)"
            else:
                target_name = f"{target['target_type'].title()}: {target['target_name']}"

            # Poll Rate
            poll_rate = target.get('poll_rate_minutes', channel_config['poll_rate_minutes'])

            # Notifications
            notifications = target.get('notification_types', channel_config['notification_types'])

            # Last Checked
            last_checked = "Never"
            if target.get('last_checked_at'):
                last_checked_dt = target['last_checked_at']
                if last_checked_dt.tzinfo is None:
                    last_checked_dt = last_checked_dt.replace(tzinfo=timezone.utc)
                last_checked = self._format_relative_time(last_checked_dt)


            rows.append([
                str(i),
                target_name,
                str(poll_rate),
                notifications,
                last_checked
            ])

        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if len(cell) > widths[i]:
                    widths[i] = len(cell)

        # Build table
        header_line = " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
        separator_line = "-|-".join("-" * widths[i] for i in range(len(headers)))
        table_rows = "\n".join(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows)

        message = f"```\n{header_line}\n{separator_line}\n{table_rows}\n```"
        await self.notifier.log_and_send(ctx, message)

    @commands.command(name='export')
    async def export(self, ctx):
        """Export channel configuration as copy-pasteable commands."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        channel_config = self.db.get_channel_config(ctx.channel.id)

        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.Export.NO_TARGETS)
            return

        commands = []
        commands.append(f"!poll_rate {channel_config['poll_rate_minutes']}")
        commands.append(f"!notifications {channel_config['notification_types']}")
        commands.append("")

        for i, target in enumerate(targets, 1):
            if target['target_type'] == 'latlong':
                coords = target['target_name'].split(',')
                cmd = f"!add coordinates {coords[0]} {coords[1]}"
                if len(coords) > 2:
                    cmd += f" {coords[2]}"
            elif target['target_type'] == 'location':
                cmd = f"!add location {target['target_name']}"
            else:
                cmd = f"!add city {target['target_name']}"

            if target['poll_rate_minutes'] != channel_config['poll_rate_minutes']:
                cmd += f"\n!poll_rate {target['poll_rate_minutes']} {i}"
            if target['notification_types'] != channel_config['notification_types']:
                cmd += f"\n!notifications {target['notification_types']} {i}"

            commands.append(cmd)

        await self.notifier.log_and_send(ctx, Messages.Command.Export.HEADER.format(commands="\n".join(commands)))

    @commands.command(name='check')
    async def check(self, ctx):
        """Immediately check for new submissions."""
        # Get the monitor cog and channel config
        monitor_cog = self.bot.get_cog('MachineMonitor')
        if monitor_cog:
            config = self.db.get_channel_config(ctx.channel.id)
            await monitor_cog.run_checks_for_channel(ctx.channel.id, config, is_manual_check=True)
        else:
            await self.notifier.log_and_send(ctx, "Error: Could not find the monitor.")

    async def _handle_location_add(self, ctx, location_input: str):
        try:
            location_input_stripped = location_input.strip()
            if location_input_stripped.isdigit():
                location_id = int(location_input_stripped)
                location_details = await fetch_location_details(location_id)

                if location_details and location_details.get('id'):
                    location_name = location_details.get('name', f'Location {location_id}')
                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, str(location_id))
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

                    submissions = await fetch_submissions_for_location(location_id, use_min_date=False)
                    sorted_submissions = self._sort_submissions(submissions)
                    await self.notifier.post_initial_submissions(ctx, sorted_submissions, f"location **{location_name}** (ID: {location_id})")
                    
                    # Update timestamp to reflect successful add target check
                    from datetime import datetime, timezone
                    self.db.update_channel_last_poll_time(ctx.channel.id, datetime.now(timezone.utc))
                else:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.LOCATION_NOT_FOUND.format(
                        location_id=location_id
                    ))
            else:
                search_result = await search_location_by_name(location_input_stripped)
                status = search_result.get('status')
                data = search_result.get('data')

                if status == 'exact':
                    location_details = data
                    location_id = location_details['id']
                    location_name = location_details['name']

                    self.db.add_monitoring_target(ctx.channel.id, 'location', location_name, str(location_id))
                    self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

                    submissions = await fetch_submissions_for_location(location_id, use_min_date=False)
                    sorted_submissions = self._sort_submissions(submissions)
                    await self.notifier.post_initial_submissions(ctx, sorted_submissions, f"location **{location_name}** (ID: {location_id})")
                    
                    # Update timestamp to reflect successful add target check
                    from datetime import datetime, timezone
                    self.db.update_channel_last_poll_time(ctx.channel.id, datetime.now(timezone.utc))
                elif status == 'suggestions':
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.LOCATION_SUGGESTIONS.format(
                        search_term=location_input_stripped,
                        suggestions="\n".join([f"• {loc['name']} (ID: {loc['id']})" for loc in data])
                    ))
                else: # not_found or error
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.NO_LOCATIONS.format(
                        search_term=location_input_stripped
                    ))
        except Exception as e:
            logger.error(f"Error handling location add for '{location_input}': {e}")
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type='location',
                error_message=str(e)
            ))

    async def _handle_coordinates_add(self, ctx, lat: float, lon: float, radius: Optional[int] = None):
        """Handle adding a coordinate-based monitoring target."""
        try:
            target_name = f"{lat},{lon}"
            if radius:
                target_name += f",{radius}"

            self.db.add_monitoring_target(ctx.channel.id, 'latlong', target_name)
            self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

            submissions = await fetch_submissions_for_coordinates(lat, lon, radius, use_min_date=False)
            sorted_submissions = self._sort_submissions(submissions)
            await self.notifier.post_initial_submissions(ctx, sorted_submissions, f"coordinates **{lat}, {lon}**")
            
            # Update timestamp to reflect successful add target check
            from datetime import datetime, timezone
            self.db.update_channel_last_poll_time(ctx.channel.id, datetime.now(timezone.utc))

            radius_info = f" with a {radius} mile radius" if radius else ""
            await self.notifier.log_and_send(ctx, Messages.Command.Add.SUCCESS.format(
                target_type="coordinates",
                name=f"{lat}, {lon}{radius_info}"
            ))
        except Exception as e:
            logger.error(f"Error handling coordinates add for '{lat}, {lon}': {e}")
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type='coordinates',
                error_message=str(e)
            ))

    async def _handle_city_add(self, ctx, city_name: str, radius: Optional[int] = None):
        """Handle adding a city-based monitoring target."""
        result = await geocode_city_name(city_name)
        status = result.get('status')

        if status == 'success':
            lat = result['lat']
            lon = result['lon']
            display_name = result['display_name']

            target_name = display_name
            target_data = f"{lat},{lon}"
            if radius:
                target_name += f" ({radius} miles)"
                target_data += f",{radius}"

            self.db.add_monitoring_target(ctx.channel.id, 'city', target_name, target_data)
            self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

            submissions = await fetch_submissions_for_coordinates(lat, lon, radius, use_min_date=False)
            sorted_submissions = self._sort_submissions(submissions)
            await self.notifier.post_initial_submissions(ctx, sorted_submissions, f"city **{display_name}**")
            
            # Update timestamp to reflect successful add target check
            from datetime import datetime, timezone
            self.db.update_channel_last_poll_time(ctx.channel.id, datetime.now(timezone.utc))

        elif status == 'multiple':
            await self.notifier.log_and_send(ctx, Messages.Command.Add.CITY_SUGGESTIONS.format(
                city_name=city_name,
                suggestions="\n".join([f"• {name}" for name in result['suggestions']])
            ))
        else: # error
            await self.notifier.log_and_send(ctx, Messages.Command.Add.CITY_NOT_FOUND.format(
                city_name=city_name
            ))

async def setup(bot):
    """Setup function for Discord.py extension loading"""
    # Get shared instances from bot
    database = getattr(bot, 'database', None)
    notifier = getattr(bot, 'notifier', None)

    if database is None or notifier is None:
        raise RuntimeError("Database and Notifier must be initialized on bot before loading cogs")

    await bot.add_cog(MonitoringCog(bot, database, notifier))
