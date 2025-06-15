"""
Cog for monitoring-related commands
"""
import logging
from typing import Optional
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

    @commands.command(name='add')
    async def add(self, ctx, target_type: str, *args):
        """Add a new monitoring target. Usage: !add <location|coordinates|city> <args>"""
        try:
            if target_type == 'location':
                if not args:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.MISSING_LOCATION)
                    return
                await self._handle_location_add(ctx, args[0])
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
    async def remove(self, ctx, index: int):
        """Remove a monitoring target by its index from the list."""
        try:
            targets = self.db.get_monitoring_targets(ctx.channel.id)

            if not targets:
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.NO_TARGETS)
                return

            if index < 1 or index > len(targets):
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_INDEX.format(max_index=len(targets)))
                return

            target = targets[index - 1]
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

    @commands.command(name='list')
    async def list_targets(self, ctx):
        """Show all monitored targets with index numbers."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        channel_config = self.db.get_channel_config(ctx.channel.id)

        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.List.NO_TARGETS)
            return

        targets_list = []
        for i, target in enumerate(targets, 1):
            if target['target_type'] == 'latlong':
                coords = target['target_name'].split(',')
                target_info = f"Coordinates: {coords[0]}, {coords[1]}"
                if len(coords) > 2:
                    target_info += f" ({coords[2]} miles)"
            else:
                target_info = f"{target['target_type'].title()}: {target['target_name']}"
                if target['target_data']:
                    target_info += f" (ID: {target['target_data']})"

            if target['poll_rate_minutes'] != channel_config['poll_rate_minutes']:
                target_info += f" [Poll: {target['poll_rate_minutes']}m]"
            if target['notification_types'] != channel_config['notification_types']:
                target_info += f" [Notify: {target['notification_types']}]"

            targets_list.append(f"{i}. {target_info}")

        await self.notifier.log_and_send(ctx, Messages.Command.List.HEADER.format(
            targets="\n".join(targets_list),
            poll_rate=channel_config['poll_rate_minutes'],
            notification_types=channel_config['notification_types']
        ))

    @commands.command(name='status')
    async def status(self, ctx):
        """Show bot status and monitoring information."""
        try:
            targets = self.db.get_monitoring_targets(ctx.channel.id)
            channel_config = self.db.get_channel_config(ctx.channel.id)

            if not targets:
                await self.notifier.log_and_send(ctx, Messages.Command.Status.NO_TARGETS)
                return

            status_lines = [
                f"**Bot Status**",
                f"• Poll Rate: {channel_config['poll_rate_minutes']} minutes",
                f"• Notification Types: {channel_config['notification_types']}",
                f"• Active Targets: {len(targets)}",
                "",
                "**Active Monitoring Targets:**"
            ]

            for i, target in enumerate(targets, 1):
                if target['target_type'] == 'latlong':
                    coords = target['target_name'].split(',')
                    target_info = f"Coordinates: {coords[0]}, {coords[1]}"
                    if len(coords) > 2:
                        target_info += f" ({coords[2]} miles)"
                else:
                    target_info = f"{target['target_type'].title()}: {target['target_name']}"
                    if target['target_data']:
                        target_info += f" (ID: {target['target_data']})"

                if target['poll_rate_minutes'] != channel_config['poll_rate_minutes']:
                    target_info += f" [Poll: {target['poll_rate_minutes']}m]"
                if target['notification_types'] != channel_config['notification_types']:
                    target_info += f" [Notify: {target['notification_types']}]"

                status_lines.append(f"{i}. {target_info}")

            await self.notifier.log_and_send(ctx, "\n".join(status_lines))
        except Exception as e:
            await self.notifier.log_and_send(ctx, Messages.Command.Error.GENERAL.format(error=str(e)))
            logger.error(f'Error in status command: {str(e)}')

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
            await monitor_cog.run_checks_for_channel(ctx.channel.id, config)
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

                    submissions = await fetch_submissions_for_location(location_id)
                    await self.notifier.post_initial_submissions(ctx, submissions, f"location **{location_name}** (ID: {location_id})")

                    await self.notifier.log_and_send(ctx, Messages.Command.Add.SUCCESS.format(
                        target_type="location",
                        name=f"{location_name} (ID: {location_id})"
                    ))
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

                    submissions = await fetch_submissions_for_location(location_id)
                    await self.notifier.post_initial_submissions(ctx, submissions, f"location **{location_name}** (ID: {location_id})")

                    await self.notifier.log_and_send(ctx, Messages.Command.Add.SUCCESS.format(
                        target_type="location",
                        name=f"{location_name} (ID: {location_id})"
                    ))
                elif status == 'suggestions':
                    suggestions = data
                    if suggestions:
                        suggestions_text = "\n".join(
                            f"{i}. **{loc['name']}** (ID: {loc['id']})"
                            for i, loc in enumerate(suggestions[:5], 1)
                        )
                        await self.notifier.log_and_send(ctx, Messages.Command.Add.SUGGESTIONS.format(
                            search_term=location_input_stripped,
                            suggestions=suggestions_text
                        ))
                    else:
                        await self.notifier.log_and_send(ctx, Messages.Command.Add.NO_LOCATIONS.format(search_term=location_input_stripped))
                else:
                    await self.notifier.log_and_send(ctx, Messages.Command.Add.NO_LOCATIONS.format(search_term=location_input_stripped))
        except Exception as e:
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type="location",
                error_message=str(e)
            ))

    async def _handle_coordinates_add(self, ctx, lat: float, lon: float, radius: Optional[int] = None):
        try:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                await self.notifier.log_and_send(ctx, Messages.Command.Add.INVALID_COORDS)
                return

            if radius is not None and (radius < 1 or radius > 100):
                await self.notifier.log_and_send(ctx, Messages.Command.Add.INVALID_RADIUS)
                return

            target_name = f"{lat},{lon},{radius}" if radius else f"{lat},{lon}"
            self.db.add_monitoring_target(ctx.channel.id, 'latlong', target_name)
            self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

            submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
            await self.notifier.post_initial_submissions(ctx, submissions, "coordinate area")

            radius_display = f"{radius} miles" if radius else "default"
            await self.notifier.log_and_send(ctx, Messages.Command.Add.SUCCESS.format(
                target_type="coordinates",
                name=f"{lat}, {lon} ({radius_display} radius)"
            ))
        except Exception as e:
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type="coordinates",
                error_message=str(e)
            ))

    async def _handle_city_add(self, ctx, city_name: str, radius: Optional[int] = None):
        try:
            if radius is not None and (radius < 1 or radius > 100):
                await self.notifier.log_and_send(ctx, Messages.Command.Add.INVALID_RADIUS)
                return

            coords = await geocode_city_name(city_name)
            if coords.get('status') != 'success':
                await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                    target_type="city",
                    error_message=coords.get('message', 'Could not find coordinates for city')
                ))
                return

            lat, lon = coords['lat'], coords['lon']
            target_name = f"{lat},{lon},{radius}" if radius else f"{lat},{lon}"
            self.db.add_monitoring_target(ctx.channel.id, 'latlong', target_name)
            self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)

            submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
            await self.notifier.post_initial_submissions(ctx, submissions, f"city **{city_name}**")

            radius_display = f"{radius} miles" if radius else "default"
            await self.notifier.log_and_send(ctx, Messages.Command.Add.SUCCESS.format(
                target_type="city",
                name=f"{city_name} ({radius_display} radius)"
            ))
        except Exception as e:
            await self.notifier.log_and_send(ctx, Messages.Command.Add.ERROR.format(
                target_type="city",
                error_message=str(e)
            ))

async def setup(bot):
    """Setup function for Discord.py extension loading"""
    # Get shared instances from bot
    database = getattr(bot, 'database', None)
    notifier = getattr(bot, 'notifier', None)
    
    if database is None or notifier is None:
        raise RuntimeError("Database and Notifier must be initialized on bot before loading cogs")

    await bot.add_cog(MonitoringCog(bot, database, notifier))
