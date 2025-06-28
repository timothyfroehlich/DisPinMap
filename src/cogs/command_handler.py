"""
Cog for all user-facing commands
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import List, Optional

import discord
from discord.ext import commands

from src.api import (
    fetch_location_details,
    geocode_city_name,
    search_location_by_name,
)
from src.database import Database
from src.messages import Messages
from src.notifier import Notifier

logger = logging.getLogger(__name__)


class CommandHandler(commands.Cog, name="CommandHandler"):
    def __init__(self, bot, db: Database, notifier: Notifier):
        self.bot = bot
        self.db = db
        self.notifier = notifier

    # Help Command
    @commands.command(
        name="help",
        help="!help [command] - Shows this help message.",
        aliases=["h"],
    )
    async def help_command(self, ctx, *, command_name: Optional[str] = None):
        """Shows a list of all commands or help for a specific command."""
        if command_name:
            command = self.bot.get_command(command_name)
            if command and command.help:
                await ctx.send(f"```\n{command.help}\n```")
            else:
                await ctx.send(f"❌ Command `{command_name}` not found.")
        else:
            embed = discord.Embed(
                title="DisPinMap Bot Help",
                description="I monitor pinball locations from PinballMap.com. Here are my commands:",
                color=discord.Color.blue(),
            )
            cogs = self.bot.cogs.values()
            all_commands = []
            for cog in cogs:
                all_commands.extend(cog.get_commands())

            for command in sorted(all_commands, key=lambda c: c.name):
                if command.name != "help" and command.help and not command.hidden:
                    summary = command.help.splitlines()[0]
                    embed.add_field(name=command.name, value=summary, inline=False)
            await ctx.send(embed=embed)

    # Monitoring Commands
    @commands.command(
        name="add",
        help='!add <location|city|coordinates> ... - Adds a new target to monitor.\\n\\nMonitors a specific location, city, or geographic area for new machine or condition submissions on PinballMap.com.\\n\\n**Usage:**\\n• `!add location "My Favorite Arcade"`\\n• `!add city "Portland, OR" [radius]`\\n• `!add coordinates 45.52 -122.67 [radius]`',
    )
    async def add(self, ctx, target_type: str, *args):
        """Add a new monitoring target. Usage: /add <location|coordinates|city> <args>"""
        try:
            if target_type == "location":
                if not args:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Add.MISSING_LOCATION
                    )
                    return
                await self._handle_location_add(ctx, " ".join(args))
            elif target_type == "coordinates":
                if len(args) < 2:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Add.MISSING_COORDS
                    )
                    return
                try:
                    lat, lon = float(args[0]), float(args[1])
                    radius = int(args[2]) if len(args) > 2 else None
                    await self._handle_coordinates_add(ctx, lat, lon, radius)
                except ValueError:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Add.INVALID_COORDS_FORMAT
                    )
            elif target_type == "city":
                if not args:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Add.MISSING_CITY
                    )
                    return

                city_name_parts: List[str] = []
                radius = None

                if len(args) > 1 and args[-1].isdigit():
                    radius = int(args[-1])
                    city_name_parts = list(args[:-1])
                else:
                    city_name_parts = list(args)

                city_name = " ".join(city_name_parts)
                await self._handle_city_add(ctx, city_name, radius)
            else:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Add.INVALID_SUBCOMMAND
                )
        except Exception as e:
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Add.ERROR.format(
                    target_type=target_type, error_message=str(e)
                ),
            )

    @commands.command(
        name="rm",
        aliases=["remove"],
        help="!rm <index> - Removes a monitoring target.\\n\\nRemoves a target from the monitoring list using its index number from the `!list` command.",
    )
    async def remove(self, ctx, index: str):
        """Remove a monitoring target by its index from the list."""
        try:
            targets = self.db.get_monitoring_targets(ctx.channel.id)

            if not targets:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.NO_TARGETS
                )
                return

            index_int = int(index)
            if not 1 <= index_int <= len(targets):
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.Shared.INVALID_INDEX.format(
                        max_index=len(targets)
                    ),
                )
                return

            target = targets[index_int - 1]
            self.db.remove_monitoring_target(
                ctx.channel.id, target["target_type"], target["target_name"]
            )

            if target["target_type"] == "latlong":
                coords = target["target_name"].split(",")
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.Remove.SUCCESS.format(
                        target_type="coordinates",
                        target_name=f"{coords[0]}, {coords[1]}",
                    ),
                )
            else:
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.Remove.SUCCESS.format(
                        target_type=target["target_type"],
                        target_name=target["target_name"],
                    ),
                )

        except ValueError:
            await self.notifier.log_and_send(
                ctx, Messages.Command.Shared.INVALID_INDEX_NUMBER
            )

    @commands.command(
        name="list",
        aliases=["ls", "status"],
        help="!list - Shows all monitored targets.\\n\\nDisplays a detailed table of all active monitoring targets in the current channel, including their index, poll rate, and notification settings.",
    )
    async def list_targets(self, ctx):
        """Show all monitored targets in a formatted table."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        channel_config = self.db.get_channel_config(ctx.channel.id)

        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.Shared.NO_TARGETS)
            return

        headers = ["Index", "Target", "Poll (min)", "Notifications", "Last Checked"]
        rows = []

        for i, target in enumerate(targets, 1):
            if target["target_type"] == "latlong":
                coords = target["target_name"].split(",")
                target_name = f"Coords: {coords[0]}, {coords[1]}"
                if len(coords) > 2:
                    target_name += f" ({coords[2]}mi)"
            else:
                target_name = (
                    f"{target['target_type'].title()}: {target['target_name']}"
                )

            poll_rate = target.get(
                "poll_rate_minutes",
                channel_config.get("poll_rate_minutes") if channel_config else 60,
            )
            notifications = target.get(
                "notification_types",
                channel_config.get("notification_types") if channel_config else "all",
            )
            last_checked = "Never"
            if target.get("last_checked_at"):
                last_checked_dt = target["last_checked_at"]
                if last_checked_dt.tzinfo is None:
                    last_checked_dt = last_checked_dt.replace(tzinfo=timezone.utc)
                last_checked = self._format_relative_time(last_checked_dt)

            rows.append(
                [str(i), target_name, str(poll_rate), notifications, last_checked]
            )

        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if len(cell) > widths[i]:
                    widths[i] = len(cell)

        header_line = " | ".join(
            headers[i].ljust(widths[i]) for i in range(len(headers))
        )
        separator_line = "-|-".join("-" * widths[i] for i in range(len(headers)))
        table_rows = "\\n".join(
            " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
            for row in rows
        )

        message = (
            f"```\\n{header_line}\\n{separator_line}\\n{table_rows}\\n```\\n\\n"
            f"Channel defaults: Poll rate: {channel_config.get('poll_rate_minutes') if channel_config else 60} minutes, "
            f"Notifications: {channel_config.get('notification_types') if channel_config else 'all'}\\n\\n"
            "Use `!rm <index>` to remove a target"
        )
        await self.notifier.log_and_send(ctx, message)

    @commands.command(
        name="export",
        help="!export - Exports the channel's configuration.\\n\\nGenerates a copy-pasteable list of commands to replicate the channel's entire monitoring configuration.",
    )
    async def export(self, ctx):
        """Export channel configuration as copy-pasteable commands."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        channel_config = self.db.get_channel_config(ctx.channel.id)

        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.Export.NO_TARGETS)
            return

        commands_list = []
        if channel_config:
            if channel_config.get("poll_rate_minutes"):
                commands_list.append(
                    f"!poll_rate {channel_config['poll_rate_minutes']}"
                )
            if channel_config.get("notification_types"):
                commands_list.append(
                    f"!notifications {channel_config['notification_types']}"
                )

        target_commands = []
        for i, target in enumerate(targets, 1):
            if target["target_type"] == "location":
                target_commands.append(f"!add location {target['location_id']}")
            elif target["target_type"] == "city":
                target_commands.append(f"!add city \"{target['target_name']}\"")
            elif target["target_type"] == "latlong":
                lat, lon, *rest = target["target_name"].split(",")
                radius_str = f" {rest[0]}" if rest else ""
                target_commands.append(f"!add coordinates {lat} {lon}{radius_str}")

            if target.get("poll_rate_minutes"):
                target_commands.append(f"!poll_rate {target['poll_rate_minutes']} {i}")
            if target.get("notification_types"):
                target_commands.append(
                    f"!notifications {target['notification_types']} {i}"
                )

        channel_config_str = "\\n".join(commands_list)
        targets_str = "\\n".join(target_commands)

        message = Messages.Command.Export.CONFIGURATION.format(
            channel_config=channel_config_str, targets=targets_str
        )
        await self.notifier.log_and_send(ctx, message)

    @commands.command(
        name="check",
        help="!check - Manually checks for new submissions.\\n\\nTriggers an immediate check for new submissions across all active targets in the channel.",
    )
    async def check(self, ctx):
        """Manually check for new submissions across all targets."""
        runner_cog = self.bot.get_cog("Runner")
        if not runner_cog:
            await self.notifier.log_and_send(
                ctx, "❌ Monitoring service is not available. Please try again later."
            )
            return

        channel_config = self.db.get_channel_config(ctx.channel.id)
        if not channel_config:
            await self.notifier.log_and_send(ctx, Messages.Command.Shared.NO_TARGETS)
            return

        await self.notifier.log_and_send(ctx, "Manual check initiated...")
        await runner_cog.run_checks_for_channel(
            ctx.channel.id, channel_config, is_manual_check=True
        )

    @commands.command(name="monitor_health")
    async def monitor_health(self, ctx):
        """Get health status of the monitoring service."""
        runner_cog = self.bot.get_cog("Runner")
        if runner_cog:
            health_status = await runner_cog.manual_health_check()
            await self.notifier.log_and_send(ctx, health_status)
        else:
            await self.notifier.log_and_send(
                ctx, "❌ Monitoring service is not running."
            )

    # Config Commands
    @commands.command(
        name="poll_rate",
        help="!poll_rate <minutes> [index] - Sets the poll rate.\n\nSets how frequently (in minutes) the bot checks for updates.\nCan be set for the whole channel or for a specific target by its index.",
    )
    async def poll_rate(self, ctx, minutes: str, target_selector: Optional[str] = None):
        """Set poll rate for channel or specific target."""
        try:
            minutes_int = int(minutes)
            if minutes_int < 1:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.PollRate.INVALID_RATE
                )
                return

            if target_selector:
                try:
                    target_id = int(target_selector)
                    targets = self.db.get_monitoring_targets(ctx.channel.id)
                    if not 1 <= target_id <= len(targets):
                        await self.notifier.log_and_send(
                            ctx,
                            Messages.Command.Shared.INVALID_INDEX.format(
                                max_index=len(targets)
                            ),
                        )
                        return
                    target = targets[target_id - 1]
                    self.db.update_monitoring_target(
                        ctx.channel.id,
                        target["target_type"],
                        target["target_name"],
                        poll_rate_minutes=minutes_int,
                    )
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.PollRate.SUCCESS_TARGET.format(
                            minutes=minutes_int, target_id=target_id
                        ),
                    )
                except ValueError:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Shared.INVALID_INDEX_NUMBER
                    )
            else:
                self.db.update_channel_config(
                    ctx.channel.id, ctx.guild.id, poll_rate_minutes=minutes_int
                )
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.PollRate.SUCCESS_CHANNEL.format(
                        minutes=minutes_int
                    ),
                )
        except ValueError:
            await self.notifier.log_and_send(ctx, Messages.Command.PollRate.ERROR)

    @commands.command(
        name="notifications",
        help="!notifications <type> [index] - Sets notification types.\n\nSets the type of notifications (machines, comments, all).\nCan be set for the whole channel or for a specific target by its index.",
    )
    async def notifications(
        self, ctx, notification_type: str, target_selector: Optional[str] = None
    ):
        """Set notification type for channel or specific target."""
        valid_types = ["machines", "comments", "all"]
        if notification_type not in valid_types:
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Notifications.ERROR.format(
                    valid_types=", ".join(valid_types)
                ),
            )
            return

        if target_selector:
            try:
                target_id = int(target_selector)
                targets = self.db.get_monitoring_targets(ctx.channel.id)
                if not 1 <= target_id <= len(targets):
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.Shared.INVALID_INDEX.format(
                            max_index=len(targets)
                        ),
                    )
                    return
                target = targets[target_id - 1]
                self.db.update_monitoring_target(
                    ctx.channel.id,
                    target["target_type"],
                    target["target_name"],
                    notification_types=notification_type,
                )
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.Notifications.SUCCESS_TARGET.format(
                        notification_type=notification_type, target_id=target_id
                    ),
                )
            except ValueError:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.INVALID_INDEX_NUMBER
                )
        else:
            self.db.update_channel_config(
                ctx.channel.id, ctx.guild.id, notification_types=notification_type
            )
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Notifications.SUCCESS_CHANNEL.format(
                    notification_type=notification_type
                ),
            )

    # Helper methods
    def _format_relative_time(self, dt: datetime) -> str:
        """Format a datetime as a human-readable relative time string."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff.total_seconds() < 604800:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"
        else:
            return dt.strftime("%b %d")

    async def _add_target_and_notify(
        self,
        ctx,
        target_type: str,
        target_name: str,
        target_data: str,
        target_details: Optional[dict] = None,
    ):
        """Helper to add a target to DB and send initial notifications."""
        self.db.add_monitoring_target(
            ctx.channel.id, target_type, target_name, target_data
        )
        self.db.update_channel_config(ctx.channel.id, ctx.guild.id, is_active=True)
        await self.notifier.send_initial_notifications(
            ctx, target_name, target_data, target_type, target_details
        )
        self.db.update_channel_last_poll_time(
            ctx.channel.id, datetime.now(timezone.utc)
        )

    async def _handle_location_add(self, ctx, location_input: str):
        """Handle adding a location, including searching and selection."""
        try:
            location_input_stripped = location_input.strip()
            if location_input_stripped.isdigit():
                location_id = int(location_input_stripped)
                location_details = await fetch_location_details(location_id)

                if not location_details:
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.Add.LOCATION_NOT_FOUND.format(
                            location_id=location_id
                        ),
                    )
                    return

                await self._add_target_and_notify(
                    ctx,
                    "location",
                    location_details["name"],
                    str(location_id),
                    location_details,
                )
            else:
                search_result = await search_location_by_name(location_input_stripped)
                status = search_result.get("status")
                data = search_result.get("data")

                if status == "success" and data and len(data) > 0:
                    if len(data) == 1:
                        location_id = data[0]["id"]
                        location_details = await fetch_location_details(location_id)
                        await self._add_target_and_notify(
                            ctx,
                            "location",
                            location_details["name"],
                            str(location_id),
                            location_details,
                        )
                    else:
                        suggestions = [f"`{loc['id']}` - {loc['name']}" for loc in data]
                        await self.notifier.log_and_send(
                            ctx,
                            Messages.Command.Add.SUGGESTIONS.format(
                                search_term=location_input_stripped,
                                suggestions="\\n".join(suggestions),
                            ),
                        )
                else:
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.Add.NO_LOCATIONS.format(
                            search_term=location_input_stripped
                        ),
                    )
        except Exception as e:
            logger.error(f"Error handling location add for '{location_input}': {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Add.ERROR.format(
                    target_type="location", error_message=str(e)
                ),
            )

    async def _handle_coordinates_add(
        self, ctx, lat: float, lon: float, radius: Optional[int] = None
    ):
        """Handle adding a coordinate-based monitoring target."""
        try:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.INVALID_COORDS
                )
                return

            if radius is not None and not 1 <= radius <= 100:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.INVALID_RADIUS
                )
                return

            target_name = f"{lat},{lon}"
            target_data = target_name
            if radius:
                target_data += f",{radius}"

            await self._add_target_and_notify(ctx, "latlong", target_name, target_data)
        except Exception as e:
            logger.error(
                f"Error handling coordinates add for '{lat}, {lon}, {radius}': {e}"
            )
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Add.ERROR.format(
                    target_type="coordinates", error_message=str(e)
                ),
            )

    async def _handle_city_add(self, ctx, city_name: str, radius: Optional[int] = None):
        """Handle adding a city-based monitoring target."""
        result = await geocode_city_name(city_name)
        status = result.get("status")

        if status == "success":
            location = result["data"][0]
            lat = location["lat"]
            lon = location["lon"]

            target_name = f"{city_name}"
            target_data = f"{lat},{lon}"
            if radius:
                target_data += f",{radius}"

            await self._add_target_and_notify(ctx, "city", target_name, target_data)

        elif status == "multiple":
            suggestions = [loc["display_name"] for loc in result["data"]]
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Add.CITY_SUGGESTIONS.format(
                    city_name=city_name, suggestions="\\n".join(suggestions)
                ),
            )
        else:
            await self.notifier.log_and_send(
                ctx, Messages.Command.Add.CITY_NOT_FOUND.format(city_name=city_name)
            )


async def setup(bot):
    """Setup function for Discord.py extension loading"""
    database = getattr(bot, "database", None)
    notifier = getattr(bot, "notifier", None)

    if database is None or notifier is None:
        raise RuntimeError(
            "Database and Notifier must be initialized on bot before loading cogs"
        )

    await bot.add_cog(CommandHandler(bot, database, notifier))
