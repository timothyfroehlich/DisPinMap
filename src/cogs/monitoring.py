"""
Cog for monitoring-related commands
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import List, Optional

from discord.ext import commands

from src.api import (
    fetch_location_details,
    fetch_submissions_for_coordinates,
    fetch_submissions_for_location,
    geocode_city_name,
    search_location_by_name,
)
from src.database import Database
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
                return datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
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
            # Target Name
            if target["target_type"] == "latlong":
                coords = target["target_name"].split(",")
                target_name = f"Coords: {coords[0]}, {coords[1]}"
                if len(coords) > 2:
                    target_name += f" ({coords[2]}mi)"
            else:
                target_name = (
                    f"{target['target_type'].title()}: {target['target_name']}"
                )

            # Poll Rate
            poll_rate = target.get(
                "poll_rate_minutes",
                channel_config.get("poll_rate_minutes") if channel_config else 60,
            )

            # Notifications
            notifications = target.get(
                "notification_types",
                channel_config.get("notification_types") if channel_config else "all",
            )

            # Last Checked
            last_checked = "Never"
            if target.get("last_checked_at"):
                last_checked_dt = target["last_checked_at"]
                if last_checked_dt.tzinfo is None:
                    last_checked_dt = last_checked_dt.replace(tzinfo=timezone.utc)
                last_checked = self._format_relative_time(last_checked_dt)

            rows.append(
                [str(i), target_name, str(poll_rate), notifications, last_checked]
            )

        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if len(cell) > widths[i]:
                    widths[i] = len(cell)

        # Build table
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

    async def list(self, ctx):
        """Alias for list_targets to maintain compatibility."""
        await self.list_targets(ctx)

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
                target_commands.append(f"!add location {target['target_data']}")
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

    @commands.command(name="monitor_health")
    async def monitor_health(self, ctx):
        """Send a health check message to the channel."""
        await ctx.send("Monitoring service is up and running!")

    @commands.command(
        name="check",
        help="!check - Manually checks for new submissions.\\n\\nTriggers an immediate check for new submissions across all active targets in the channel.",
    )
    async def check(self, ctx):
        """Manually check for new submissions across all targets."""
        targets = self.db.get_monitoring_targets(ctx.channel.id)
        if not targets:
            await self.notifier.log_and_send(ctx, Messages.Command.Shared.NO_TARGETS)
            return

        all_new_submissions = []
        for target in targets:
            try:
                last_checked_at = target.get("last_checked_at")
                submissions = []
                if target["target_type"] == "location":
                    target_id = int(target["target_data"])
                    submissions = await fetch_submissions_for_location(
                        target_id, use_min_date=True, last_check_time=last_checked_at
                    )
                elif target["target_type"] == "latlong":
                    lat, lon, *rest = target["target_name"].split(",")
                    radius = rest[0] if rest else None
                    submissions = await fetch_submissions_for_coordinates(
                        lat,
                        lon,
                        radius,
                        use_min_date=True,
                        last_check_time=last_checked_at,
                    )
                else:  # city
                    continue

                if submissions:
                    all_new_submissions.extend(submissions)

            except Exception as e:
                logger.error(
                    f"Error checking target {target['target_name']}: {e}", exc_info=True
                )

        if not all_new_submissions:
            # NOTE: Reverted to old message temporarily, pending new implementation.
            await self.notifier.log_and_send(
                ctx, "No new submissions found. All targets are up to date."
            )
            return

        # Sort and format submissions for display
        sorted_submissions = self._sort_submissions(all_new_submissions)
        formatted_submissions = await self.notifier.format_submissions(
            sorted_submissions
        )

        # NOTE: Reverted to old message temporarily, pending new implementation.
        await self.notifier.log_and_send(
            ctx,
            f"Found {len(sorted_submissions)} new submissions:\\n{formatted_submissions}",
        )

        # Update last checked timestamp for all targets
        self.db.update_channel_last_poll_time(
            ctx.channel.id, datetime.now(timezone.utc)
        )

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

        # Update timestamp to reflect successful add target check
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
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.INVALID_COORDS
                )
                return

            # Validate radius if provided
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
        else:  # error
            await self.notifier.log_and_send(
                ctx, Messages.Command.Add.CITY_NOT_FOUND.format(city_name=city_name)
            )


async def setup(bot):
    """Setup function for Discord.py extension loading"""
    # Get shared instances from bot
    database = getattr(bot, "database", None)
    notifier = getattr(bot, "notifier", None)

    if database is None or notifier is None:
        raise RuntimeError(
            "Database and Notifier must be initialized on bot before loading cogs"
        )

    await bot.add_cog(MonitoringCog(bot, database, notifier))
