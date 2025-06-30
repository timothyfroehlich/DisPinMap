"""
Runner module for Discord Pinball Map Bot
Handles background polling and notification sending. This cog runs the task loop.
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


class Runner(commands.Cog, name="Runner"):
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
        """Prepare the monitoring task when the cog is loaded (task will start when bot is ready)."""
        logger.info("🔄 Preparing Runner task loop")
        self.monitor_start_time = datetime.now(timezone.utc)
        # Start the task loop - it will wait for bot to be ready via before_loop
        self.monitor_task_loop.start()
        logger.info("✅ Runner cog loaded, task loop will start when bot is ready")

    async def cog_unload(self):
        """Cancels the monitoring task when the cog is unloaded."""
        logger.info("⏹️ Stopping Runner task loop")
        uptime = None
        if self.monitor_start_time:
            uptime = datetime.now(timezone.utc) - self.monitor_start_time
            logger.info(
                f"📊 Monitor uptime: {uptime}, iterations: {self.loop_iteration_count}, total errors: {self.total_error_count}"
            )
        if self.monitor_task_loop.is_running():
            self.monitor_task_loop.cancel()
            logger.info("✅ Runner task loop cancelled")

    @tasks.loop(minutes=1)
    async def monitor_task_loop(self):
        """Main monitoring loop with comprehensive logging and error handling"""
        loop_start_time = datetime.now(timezone.utc)
        self.loop_iteration_count += 1

        await self._log_loop_startup(loop_start_time)

        try:
            active_channel_configs = (
                await self._get_active_channels_with_error_handling()
            )
            if not active_channel_configs:
                logger.info("😴 No active channels to monitor, skipping iteration")
                return

            channels_polled, channels_skipped = await self._process_all_channels(
                active_channel_configs
            )
            await self._log_iteration_summary(
                loop_start_time, channels_polled, channels_skipped
            )

            # Update health monitoring
            self.last_successful_run = datetime.now(timezone.utc)
            self.last_error_count = 0  # Reset error counter on successful run

        except Exception as e:
            await self._handle_critical_loop_error(e)

        finally:
            await self._log_loop_completion(loop_start_time)

    async def _log_loop_startup(self, loop_start_time: datetime) -> None:
        """Log the startup of a monitor loop iteration with debug information"""
        logger.info(
            f"🔄 Monitor loop iteration #{self.loop_iteration_count} starting at {loop_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        # Debug: Log that we're actually inside the loop
        logger.info(
            f"🔍 Inside monitor_task_loop, bot user: {self.bot.user.name if self.bot.user else 'None'}"
        )
        logger.info(f"🔍 Loop is running: {self.monitor_task_loop.is_running()}")
        logger.info(f"🔍 Loop next iteration: {self.monitor_task_loop.next_iteration}")

    async def _get_active_channels_with_error_handling(self) -> List[Dict[str, Any]]:
        """Get active channels with comprehensive error handling"""
        try:
            active_channel_configs = self.db.get_active_channels()
            logger.info(
                f"📋 Found {len(active_channel_configs)} active channels with monitoring targets"
            )
            return active_channel_configs
        except Exception as e:
            logger.error(f"❌ Database error getting active channels: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.total_error_count += 1
            return []  # Return empty list to skip iteration but don't crash the loop

    async def _process_all_channels(
        self, active_channel_configs: List[Dict[str, Any]]
    ) -> tuple[int, int]:
        """Process all active channels and return polling statistics"""
        channels_polled = 0
        channels_skipped = 0

        for config in active_channel_configs:
            channel_id = config["channel_id"]

            try:
                should_poll = await self._should_poll_channel(config)

                if should_poll:
                    await self._poll_single_channel(channel_id, config)
                    channels_polled += 1
                else:
                    await self._skip_channel_with_logging(channel_id, config)
                    channels_skipped += 1

            except Exception as e:
                logger.error(f"❌ Error processing channel {channel_id}: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                self.total_error_count += 1
                # Continue with other channels even if one fails
                continue

        return channels_polled, channels_skipped

    async def _poll_single_channel(
        self, channel_id: int, config: Dict[str, Any]
    ) -> None:
        """Poll a single channel with performance tracking"""
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

    async def _skip_channel_with_logging(
        self, channel_id: int, config: Dict[str, Any]
    ) -> None:
        """Skip a channel with appropriate logging based on last poll time"""
        last_poll = config.get("last_poll_at")
        if last_poll:
            minutes_since = int(
                (datetime.now(timezone.utc) - last_poll).total_seconds() / 60
            )
            logger.debug(
                f"⏰ Skipping channel {channel_id} (last polled {minutes_since} min ago)"
            )
        else:
            logger.debug(
                f"⏰ Skipping channel {channel_id} (never polled, but poll conditions not met)"
            )

    async def _log_iteration_summary(
        self, loop_start_time: datetime, channels_polled: int, channels_skipped: int
    ) -> None:
        """Log a summary of the completed monitor loop iteration"""
        loop_duration = (datetime.now(timezone.utc) - loop_start_time).total_seconds()
        logger.info(
            f"✅ Monitor loop iteration #{self.loop_iteration_count} completed in {loop_duration:.2f}s: {channels_polled} polled, {channels_skipped} skipped"
        )

    async def _handle_critical_loop_error(self, e: Exception) -> None:
        """Handle critical errors in the main loop with appropriate logging and error tracking"""
        logger.error(f"❌ CRITICAL: Unexpected error in monitor task loop: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        self.total_error_count += 1
        self.last_error_count += 1

        # If we have too many consecutive errors, log a warning but keep running
        if self.last_error_count >= 5:
            logger.warning(
                f"⚠️ Monitor loop has had {self.last_error_count} consecutive errors. System may need attention."
            )

    async def _log_loop_completion(self, loop_start_time: datetime) -> None:
        """Log the completion of a monitor loop iteration"""
        total_duration = (datetime.now(timezone.utc) - loop_start_time).total_seconds()
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

            if target_type == "city":
                logger.error(
                    f"Skipping target with unsupported type 'city': id={target_id}. "
                    f"This target should be re-added using the add command to geocode it correctly."
                )
                return [], True  # Mark as failed to prevent silent failures

            if target_type in ("latlong"):
                source_data = target.get("target_name")
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
            elif target_type == "location" and target["location_id"]:
                location_id = int(target["location_id"])
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
                    channel, Messages.Command.Shared.NO_TARGETS
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

        # Run immediate first check to avoid waiting 60 minutes on startup
        await self._run_startup_checks()

    async def _run_startup_checks(self) -> None:
        """Run immediate startup checks to avoid waiting for the first loop iteration"""
        logger.info("🚀 Running immediate first check to avoid startup delay...")
        try:
            # Get active channels with error handling - reuse the same helper method
            active_channel_configs = (
                await self._get_active_channels_with_error_handling()
            )
            logger.info(
                f"📋 Found {len(active_channel_configs)} active channels for immediate startup check"
            )

            if active_channel_configs:
                startup_checks = await self._process_startup_channels(
                    active_channel_configs
                )
                logger.info(
                    f"✅ Completed {startup_checks} startup checks. Regular 1-minute loop will begin now."
                )
            else:
                logger.info(
                    "😴 No active channels for startup check, regular loop will begin now."
                )

        except Exception as e:
            logger.error(f"❌ Error during startup check: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.info(
                "Regular monitor loop will still start despite startup check error."
            )

    async def _process_startup_channels(
        self, active_channel_configs: List[Dict[str, Any]]
    ) -> int:
        """Process channels during startup and return the number of successful checks"""
        startup_checks = 0
        for config in active_channel_configs:
            channel_id = config["channel_id"]
            try:
                logger.info(f"📞 Running startup check for channel {channel_id}")
                result = await self.run_checks_for_channel(channel_id, config)
                logger.info(
                    f"✅ Startup check for channel {channel_id} completed, result: {result}"
                )
                startup_checks += 1
            except Exception as e:
                logger.error(f"❌ Error in startup check for channel {channel_id}: {e}")
                continue
        return startup_checks

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
    logger.info("🔧 Setting up Runner cog...")

    # Get shared instances from bot
    database = getattr(bot, "database", None)
    notifier = getattr(bot, "notifier", None)

    if database is None or notifier is None:
        error_msg = (
            "Database and Notifier must be initialized on bot before loading cogs"
        )
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

    logger.info("✅ Database and Notifier instances found, creating Runner cog")
    cog = Runner(bot, database, notifier)

    try:
        await bot.add_cog(cog)
        logger.info("✅ Runner cog added to bot successfully")
    except Exception as e:
        logger.error(f"❌ Failed to add Runner cog to bot: {e}")
        raise
