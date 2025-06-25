"""
Monitor module for Discord Pinball Map Bot
Handles background polling and notification sending using the new submission-based approach
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List

from discord.ext import commands, tasks

logger = logging.getLogger(__name__)
try:
    from ..api import fetch_submissions_for_coordinates, fetch_submissions_for_location
    from ..database import Database
    from ..messages import Messages
    from ..notifier import Notifier
except ImportError:
    from src.api import (
        fetch_submissions_for_coordinates,
        fetch_submissions_for_location,
    )
    from src.database import Database
    from src.messages import Messages
    from src.notifier import Notifier


class MachineMonitor(commands.Cog, name="MachineMonitor"):
    def __init__(self, bot, database: Database, notifier: Notifier):
        self.bot = bot
        self.db = database
        self.notifier = notifier

        # Health monitoring attributes
        self.loop_iteration_count = 0
        self.last_successful_run = None
        self.last_error_count = 0
        self.total_error_count = 0
        self.monitor_start_time = None

    async def cog_load(self):
        """Starts the monitoring task when the cog is loaded."""
        logger.info("🔄 Starting MachineMonitor task loop")
        self.monitor_start_time = datetime.now(timezone.utc)
        try:
            self.monitor_task_loop.start()
            logger.info("✅ MachineMonitor task loop started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start MachineMonitor task loop: {e}")
            raise

    async def cog_unload(self):
        """Cancels the monitoring task when the cog is unloaded."""
        logger.info("⏹️ Stopping MachineMonitor task loop")
        uptime = None
        if self.monitor_start_time:
            uptime = datetime.now(timezone.utc) - self.monitor_start_time
            logger.info(
                f"📊 Monitor uptime: {uptime}, iterations: {self.loop_iteration_count}, total errors: {self.total_error_count}"
            )
        if self.monitor_task_loop.is_running():
            self.monitor_task_loop.cancel()
            logger.info("✅ MachineMonitor task loop cancelled")

    @tasks.loop(minutes=1)
    async def monitor_task_loop(self):
        """Main monitoring loop with comprehensive logging and error handling"""
        loop_start_time = datetime.now(timezone.utc)
        self.loop_iteration_count += 1

        logger.info(
            f"🔄 Monitor loop iteration #{self.loop_iteration_count} starting at {loop_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        # Debug: Log that we're actually inside the loop
        logger.info(
            f"🔍 Inside monitor_task_loop, bot user: {self.bot.user.name if self.bot.user else 'None'}"
        )
        logger.info(f"🔍 Loop is running: {self.monitor_task_loop.is_running()}")
        logger.info(f"🔍 Loop next iteration: {self.monitor_task_loop.next_iteration}")

        try:
            # Get active channels with error handling
            try:
                active_channel_configs = self.db.get_active_channels()
                logger.info(
                    f"📋 Found {len(active_channel_configs)} active channels with monitoring targets"
                )
            except Exception as e:
                logger.error(f"❌ Database error getting active channels: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                self.total_error_count += 1
                return  # Skip this iteration but don't crash the loop

            if not active_channel_configs:
                logger.info("😴 No active channels to monitor, skipping iteration")
                return

            # Process each channel
            channels_polled = 0
            channels_skipped = 0

            for config in active_channel_configs:
                channel_id = config["channel_id"]

                try:
                    # Check if it's time to poll this channel
                    should_poll = await self._should_poll_channel(config)

                    if should_poll:
                        logger.info(
                            f"📞 Polling channel {channel_id} (poll rate: {config.get('poll_rate_minutes', 60)} min)"
                        )

                        # Track performance
                        channel_start_time = datetime.now(timezone.utc)
                        result = await self.run_checks_for_channel(channel_id, config)
                        channel_duration = (
                            datetime.now(timezone.utc) - channel_start_time
                        ).total_seconds()

                        logger.info(
                            f"✅ Channel {channel_id} polling completed in {channel_duration:.2f}s, result: {result}"
                        )
                        channels_polled += 1
                    else:
                        last_poll = config.get("last_poll_at")
                        if last_poll:
                            minutes_since = int(
                                (datetime.now(timezone.utc) - last_poll).total_seconds()
                                / 60
                            )
                            logger.debug(
                                f"⏰ Skipping channel {channel_id} (last polled {minutes_since} min ago)"
                            )
                        else:
                            logger.debug(
                                f"⏰ Skipping channel {channel_id} (never polled, but poll conditions not met)"
                            )
                        channels_skipped += 1

                except Exception as e:
                    logger.error(f"❌ Error processing channel {channel_id}: {e}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    self.total_error_count += 1
                    # Continue with other channels even if one fails
                    continue

            # Log iteration summary
            loop_duration = (
                datetime.now(timezone.utc) - loop_start_time
            ).total_seconds()
            logger.info(
                f"✅ Monitor loop iteration #{self.loop_iteration_count} completed in {loop_duration:.2f}s: {channels_polled} polled, {channels_skipped} skipped"
            )

            # Update health monitoring
            self.last_successful_run = datetime.now(timezone.utc)
            self.last_error_count = 0  # Reset error counter on successful run

        except Exception as e:
            # Catch-all for any unexpected errors in the main loop
            logger.error(f"❌ CRITICAL: Unexpected error in monitor task loop: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.total_error_count += 1
            self.last_error_count += 1

            # If we have too many consecutive errors, log a warning but keep running
            if self.last_error_count >= 5:
                logger.warning(
                    f"⚠️ Monitor loop has had {self.last_error_count} consecutive errors. System may need attention."
                )

        finally:
            # Always log the end of the loop iteration
            total_duration = (
                datetime.now(timezone.utc) - loop_start_time
            ).total_seconds()
            logger.debug(
                f"🏁 Monitor loop iteration #{self.loop_iteration_count} finished (total time: {total_duration:.2f}s)"
            )

    async def run_checks_for_channel(
        self, channel_id: int, config: Dict[str, Any], is_manual_check: bool = False
    ):
        """Poll a channel for new submissions based on its monitoring targets

        Args:
            channel_id: Discord channel ID
            config: Channel configuration
            is_manual_check: Whether this is a manual check (via !check command)

        Returns:
            bool: True if new submissions were found and posted, False otherwise
        """
        logger.info(
            f"{'Manual check' if is_manual_check else 'Polling'} channel {channel_id}..."
        )
        try:
            targets = self.db.get_monitoring_targets(channel_id)
            if not targets:
                return await self._handle_no_targets(channel_id, is_manual_check)

            all_submissions = []
            api_failures = False
            for target in targets:
                submissions, failed = await self._process_target(
                    target, is_manual_check
                )
                all_submissions.extend(submissions)
                if failed:
                    api_failures = True

            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id} to send results")
                return False

            if is_manual_check:
                result = await self._handle_manual_check_results(
                    channel, all_submissions, config
                )
                # Update timestamp on successful manual checks (no API failures)
                if not api_failures:
                    self.db.update_channel_last_poll_time(
                        channel_id, datetime.now(timezone.utc)
                    )
                return result
            else:
                result = await self._handle_automatic_poll_results(
                    channel, all_submissions, config
                )
                # Only update timestamp on successful automatic polls (no API failures)
                if not api_failures:
                    self.db.update_channel_last_poll_time(
                        channel_id, datetime.now(timezone.utc)
                    )
                return result

        except Exception as e:
            logger.error(
                f"❌ Error {'in manual check' if is_manual_check else 'polling'} for channel {channel_id}: {e}"
            )
            logger.error(f"Full traceback: {traceback.format_exc()}")

            if is_manual_check:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.notifier.log_and_send(
                        channel, f"❌ **Error during manual check:** {str(e)}"
                    )
            return False

    async def _process_target(
        self, target: Dict[str, Any], is_manual_check: bool
    ) -> tuple[List[Dict[str, Any]], bool]:
        """Fetch submissions for a single monitoring target and update its timestamp.

        Returns:
            tuple: (submissions, failed) where failed is True if API call failed
        """
        try:
            submissions = []
            target_id = target["id"]
            target_type = target["target_type"]

            if target_type in ("latlong", "city"):
                source_data = (
                    target["target_name"]
                    if target_type == "latlong"
                    else target["target_data"]
                )
                if not source_data:
                    logger.warning(
                        f"Skipping target with missing data: id={target_id}, type={target_type}"
                    )
                    return [], False  # Not an API failure, just invalid config
                parts = source_data.split(",")
                if len(parts) < 2:
                    logger.warning(
                        f"Skipping target with malformed data: id={target_id}, type={target_type}, data={source_data}"
                    )
                    return [], False  # Not an API failure, just invalid config
                lat, lon = float(parts[0]), float(parts[1])
                radius = int(parts[2]) if len(parts) >= 3 else None
                submissions = await fetch_submissions_for_coordinates(
                    lat, lon, radius, use_min_date=not is_manual_check
                )
            elif target_type == "location" and target["target_data"]:
                location_id = int(target["target_data"])
                submissions = await fetch_submissions_for_location(
                    location_id, use_min_date=not is_manual_check
                )
            else:
                logger.warning(
                    f"Skipping unhandled target: id={target_id}, type={target_type}"
                )
                return [], False  # Not an API failure, just invalid config

            self.db.update_target_last_checked_time(
                target_id, datetime.now(timezone.utc)
            )
            return submissions, False  # Success
        except Exception as e:
            logger.error(f"Failed to fetch for target {target['id']}: {e}")
            if is_manual_check:
                # For manual checks, allow the error to propagate up
                raise
            else:
                # For automatic polls, catch and mark as failed
                return [], True  # Failed

    async def _handle_no_targets(self, channel_id: int, is_manual_check: bool) -> bool:
        """Handle the case where a channel has no monitoring targets."""
        logger.info(f"No targets for channel {channel_id}, skipping.")
        if is_manual_check:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await self.notifier.log_and_send(
                    channel, Messages.Command.Status.NO_TARGETS_TO_CHECK
                )
        return False

    async def _handle_manual_check_results(
        self, channel, submissions: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> bool:
        """Process and send results for a manual check."""
        sorted_submissions = sorted(
            submissions, key=lambda x: x.get("created_at", ""), reverse=True
        )
        submissions_to_show = sorted_submissions[:5]

        if submissions_to_show:
            await self.notifier.log_and_send(
                channel, "📋 **Last 5 submissions across all monitored targets:**"
            )
            await self.notifier.post_submissions(channel, submissions_to_show, config)
            return True
        else:
            last_poll = config.get("last_poll_at")
            if last_poll:
                time_since_poll = datetime.now(timezone.utc) - last_poll
                minutes_ago = int(time_since_poll.total_seconds() / 60)
                if minutes_ago < 60:
                    await self.notifier.log_and_send(
                        channel, f"📋 **Nothing new since {minutes_ago} minutes ago.**"
                    )
                else:
                    hours_ago = minutes_ago // 60
                    await self.notifier.log_and_send(
                        channel, f"📋 **Nothing new since {hours_ago} hours ago.**"
                    )
            else:
                await self.notifier.log_and_send(
                    channel, "📋 **No submissions found for any monitored targets.**"
                )
            return False

    async def _handle_automatic_poll_results(
        self, channel, submissions: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> bool:
        """Filter and send notifications for an automatic poll."""
        new_submissions = self.db.filter_new_submissions(channel.id, submissions)

        if new_submissions:
            await self.notifier.post_submissions(channel, new_submissions, config)
            self.db.mark_submissions_seen(
                channel.id, [s["id"] for s in new_submissions]
            )
            return True
        return False

    async def _should_poll_channel(self, config: Dict[str, Any]) -> bool:
        """Check if it's time to poll a channel based on its poll rate with detailed logging"""
        try:
            channel_id = config.get("channel_id", "unknown")
            poll_interval_minutes = config.get("poll_rate_minutes", 60)
            last_poll = config.get("last_poll_at")

            if last_poll is None:
                logger.debug(
                    f"🔄 Channel {channel_id}: First poll (no previous poll time)"
                )
                return True

            time_since_last_poll = datetime.now(timezone.utc) - last_poll
            minutes_since_last_poll = time_since_last_poll.total_seconds() / 60

            should_poll = minutes_since_last_poll >= poll_interval_minutes

            if should_poll:
                logger.debug(
                    f"✅ Channel {channel_id}: Ready to poll ({minutes_since_last_poll:.1f} min >= {poll_interval_minutes} min)"
                )
            else:
                logger.debug(
                    f"⏰ Channel {channel_id}: Not ready ({minutes_since_last_poll:.1f} min < {poll_interval_minutes} min)"
                )

            return should_poll

        except Exception as e:
            logger.error(
                f"❌ Error checking poll time for channel {config.get('channel_id')}: {e}"
            )
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    @monitor_task_loop.before_loop
    async def before_monitor_task_loop(self):
        """Setup before starting the monitor loop"""
        logger.info("⏳ Waiting for bot to be ready before starting monitor loop...")
        await self.bot.wait_until_ready()
        logger.info("✅ Bot ready, monitor loop will start shortly")

        # Additional debug info
        logger.info(f"🔍 Bot user: {self.bot.user}")
        logger.info(f"🔍 Bot guilds: {len(self.bot.guilds)} guilds")
        logger.info(
            f"🔍 Task loop current iteration: {self.monitor_task_loop.current_loop}"
        )
        logger.info(f"🔍 Task loop is running: {self.monitor_task_loop.is_running()}")

    def get_monitor_health_status(self) -> Dict[str, Any]:
        """Get health status information for the monitor loop"""
        from datetime import timedelta
        from typing import Optional

        now = datetime.now(timezone.utc)
        uptime: Optional[timedelta] = None
        last_run_ago: Optional[timedelta] = None

        if self.monitor_start_time:
            uptime = now - self.monitor_start_time

        if self.last_successful_run:
            last_run_ago = now - self.last_successful_run

        try:
            next_iteration_seconds = None
            if self.monitor_task_loop.next_iteration:
                next_iteration_seconds = (
                    self.monitor_task_loop.next_iteration.timestamp() - now.timestamp()
                )
        except Exception as e:
            logger.warning(f"Could not calculate next iteration time: {e}")
            next_iteration_seconds = None

        return {
            "is_running": not self.monitor_task_loop.is_being_cancelled()
            and self.monitor_task_loop.is_running(),
            "iteration_count": self.loop_iteration_count,
            "uptime_seconds": uptime.total_seconds() if uptime else None,
            "last_successful_run_ago_seconds": (
                last_run_ago.total_seconds() if last_run_ago else None
            ),
            "consecutive_errors": self.last_error_count,
            "total_errors": self.total_error_count,
            "next_iteration_in_seconds": next_iteration_seconds,
        }

    async def manual_health_check(self) -> str:
        """Manual health check that can be called from commands"""
        status = self.get_monitor_health_status()

        lines = [
            "🌡️ **Monitor Loop Health Status**",
            f"Running: {'✅ Yes' if status['is_running'] else '❌ No'}",
            f"Iterations: {status['iteration_count']}",
        ]

        if status["uptime_seconds"] is not None:
            uptime_str = self._format_duration(status["uptime_seconds"])
            lines.append(f"Uptime: {uptime_str}")

        if status["last_successful_run_ago_seconds"] is not None:
            last_run_str = self._format_duration(
                status["last_successful_run_ago_seconds"]
            )
            lines.append(f"Last successful run: {last_run_str} ago")
        else:
            lines.append("Last successful run: Never")

        lines.append(f"Total errors: {status['total_errors']}")

        if status["consecutive_errors"] > 0:
            lines.append(f"⚠️ Consecutive errors: {status['consecutive_errors']}")

        if status["next_iteration_in_seconds"] is not None:
            next_str = self._format_duration(status["next_iteration_in_seconds"])
            lines.append(f"Next iteration: in {next_str}")

        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable string"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


async def setup(bot):
    """Setup function for Discord.py extension loading"""
    logger.info("🔧 Setting up MachineMonitor cog...")

    # Get shared instances from bot
    database = getattr(bot, "database", None)
    notifier = getattr(bot, "notifier", None)

    if database is None or notifier is None:
        error_msg = (
            "Database and Notifier must be initialized on bot before loading cogs"
        )
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

    logger.info("✅ Database and Notifier instances found, creating MachineMonitor cog")
    monitor_cog = MachineMonitor(bot, database, notifier)

    try:
        await bot.add_cog(monitor_cog)
        logger.info("✅ MachineMonitor cog added to bot successfully")
    except Exception as e:
        logger.error(f"❌ Failed to add MachineMonitor cog to bot: {e}")
        raise
