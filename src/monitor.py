"""
Monitor module for Discord Pinball Map Bot
Handles background polling and notification sending using the new submission-based approach
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
from discord.ext import tasks, commands
import logging

logger = logging.getLogger(__name__)
try:
    from .database import Database
    from .api import fetch_submissions_for_coordinates, fetch_submissions_for_location
    from .notifier import Notifier
    from .messages import Messages
except ImportError:
    from database import Database
    from api import fetch_submissions_for_coordinates, fetch_submissions_for_location
    from notifier import Notifier
    from messages import Messages


class MachineMonitor(commands.Cog, name="MachineMonitor"):
    def __init__(self, bot, database: Database, notifier: Notifier):
        self.bot = bot
        self.db = database
        self.notifier = notifier

    def cog_load(self):
        """Starts the monitoring task when the cog is loaded."""
        self.monitor_task_loop.start()

    def cog_unload(self):
        """Cancels the monitoring task when the cog is unloaded."""
        self.monitor_task_loop.cancel()

    @tasks.loop(minutes=1)
    async def monitor_task_loop(self):
        """Main monitoring loop"""
        active_channel_configs = self.db.get_active_channels()
        for config in active_channel_configs:
            if await self._should_poll_channel(config):
                await self.run_checks_for_channel(config['channel_id'], config)

    async def run_checks_for_channel(self, channel_id: int, config: Dict[str, Any], is_manual_check: bool = False):
        """Poll a channel for new submissions based on its monitoring targets

        Args:
            channel_id: Discord channel ID
            config: Channel configuration
            is_manual_check: Whether this is a manual check (via !check command)

        Returns:
            bool: True if new submissions were found and posted, False otherwise
        """
        logger.info(f"{'Manual check' if is_manual_check else 'Polling'} channel {channel_id}...")
        try:
            targets = self.db.get_monitoring_targets(channel_id)
            if not targets:
                return await self._handle_no_targets(channel_id, is_manual_check)

            all_submissions = []
            for target in targets:
                submissions = await self._process_target(target, is_manual_check)
                all_submissions.extend(submissions)

            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id} to send results")
                return False

            if is_manual_check:
                return await self._handle_manual_check_results(channel, all_submissions, config)
            else:
                result = await self._handle_automatic_poll_results(channel, all_submissions, config)
                self.db.update_channel_last_poll_time(channel_id, datetime.now(timezone.utc))
                return result

        except Exception as e:
            logger.error(f"Error {'in manual check' if is_manual_check else 'polling'} for channel {channel_id}: {e}")
            if is_manual_check:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.notifier.log_and_send(channel, f"❌ **Error during manual check:** {str(e)}")
            return False

    async def _process_target(self, target: Dict[str, Any], is_manual_check: bool) -> List[Dict[str, Any]]:
        """Fetch submissions for a single monitoring target and update its timestamp."""
        try:
            submissions = []
            target_id = target['id']
            target_type = target['target_type']

            if target_type in ('latlong', 'city'):
                source_data = target['target_name'] if target_type == 'latlong' else target['target_data']
                if not source_data:
                    logger.warning(f"Skipping target with missing data: id={target_id}, type={target_type}")
                    return []
                parts = source_data.split(',')
                if len(parts) < 2:
                    logger.warning(f"Skipping target with malformed data: id={target_id}, type={target_type}, data={source_data}")
                    return []
                lat, lon = float(parts[0]), float(parts[1])
                radius = int(parts[2]) if len(parts) >= 3 else None
                submissions = await fetch_submissions_for_coordinates(lat, lon, radius, use_min_date=not is_manual_check)
            elif target_type == 'location' and target['target_data']:
                location_id = int(target['target_data'])
                submissions = await fetch_submissions_for_location(location_id, use_min_date=not is_manual_check)
            else:
                logger.warning(f"Skipping unhandled target: id={target_id}, type={target_type}")
                return []

            self.db.update_target_last_checked_time(target_id, datetime.now(timezone.utc))
            return submissions
        except Exception as e:
            logger.error(f"Failed to fetch for target {target['id']}: {e}")
            return []

    async def _handle_no_targets(self, channel_id: int, is_manual_check: bool) -> bool:
        """Handle the case where a channel has no monitoring targets."""
        logger.info(f"No targets for channel {channel_id}, skipping.")
        if is_manual_check:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await self.notifier.log_and_send(channel, Messages.Command.Status.NO_TARGETS_TO_CHECK)
        return False

    async def _handle_manual_check_results(self, channel, submissions: List[Dict[str, Any]], config: Dict[str, Any]) -> bool:
        """Process and send results for a manual check."""
        sorted_submissions = sorted(submissions, key=lambda x: x.get('created_at', ''), reverse=True)
        submissions_to_show = sorted_submissions[:5]

        if submissions_to_show:
            await self.notifier.log_and_send(channel, "📋 **Last 5 submissions across all monitored targets:**")
            await self.notifier.post_submissions(channel, submissions_to_show, config)
            return True
        else:
            last_poll = config.get('last_poll_at')
            if last_poll:
                time_since_poll = datetime.now(timezone.utc) - last_poll
                minutes_ago = int(time_since_poll.total_seconds() / 60)
                if minutes_ago < 60:
                    await self.notifier.log_and_send(channel, f"📋 **Nothing new since {minutes_ago} minutes ago.**")
                else:
                    hours_ago = minutes_ago // 60
                    await self.notifier.log_and_send(channel, f"📋 **Nothing new since {hours_ago} hours ago.**")
            else:
                await self.notifier.log_and_send(channel, "📋 **No submissions found for any monitored targets.**")
            return False

    async def _handle_automatic_poll_results(self, channel, submissions: List[Dict[str, Any]], config: Dict[str, Any]) -> bool:
        """Filter and send notifications for an automatic poll."""
        new_submissions = self.db.filter_new_submissions(channel.id, submissions)

        if new_submissions:
            await self.notifier.post_submissions(channel, new_submissions, config)
            self.db.mark_submissions_seen(channel.id, [s['id'] for s in new_submissions])
            return True
        return False

    async def _should_poll_channel(self, config: Dict[str, Any]) -> bool:
        """Check if it's time to poll a channel based on its poll rate"""
        try:
            poll_interval_minutes = config.get('poll_rate_minutes', 60)
            last_poll = config.get('last_poll_at')

            if last_poll is None:
                return True

            time_since_last_poll = datetime.now(timezone.utc) - last_poll
            minutes_since_last_poll = time_since_last_poll.total_seconds() / 60

            return minutes_since_last_poll >= poll_interval_minutes
        except Exception as e:
            logger.error(f"Error checking poll time for channel {config.get('channel_id')}: {e}")
            return False

    @monitor_task_loop.before_loop
    async def before_monitor_task_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    """Setup function for Discord.py extension loading"""
    # Get shared instances from bot
    database = getattr(bot, 'database', None)
    notifier = getattr(bot, 'notifier', None)

    if database is None or notifier is None:
        raise RuntimeError("Database and Notifier must be initialized on bot before loading cogs")

    await bot.add_cog(MachineMonitor(bot, database, notifier))
