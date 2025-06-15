"""
Monitor module for Discord Pinball Map Bot
Handles background polling and notification sending using the new submission-based approach
"""

from datetime import datetime
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
    def __init__(self, bot, database: Database, notifier: Notifier, start_task: bool = True):
        self.bot = bot
        self.db = database
        self.notifier = notifier
        if start_task:
            self.monitor_task_loop.start()

    def cog_unload(self):
        self.monitor_task_loop.cancel()

    @tasks.loop(minutes=1)
    async def monitor_task_loop(self):
        """Main monitoring loop"""
        active_channel_configs = self.db.get_active_channels()
        for config in active_channel_configs:
            if await self._should_poll_channel(config):
                await self.run_checks_for_channel(config['channel_id'], config)

    async def run_checks_for_channel(self, channel_id: int, config: Dict[str, Any]):
        """Poll a channel for new submissions based on its monitoring targets"""
        logger.info(f"Polling channel {channel_id}...")
        try:
            # Update last poll time before checking to prevent race conditions on long polls
            self.db.update_channel_last_poll_time(channel_id, datetime.now())

            targets = self.db.get_monitoring_targets(channel_id)
            if not targets:
                logger.info(f"No targets for channel {channel_id}, skipping.")
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.notifier.log_and_send(channel, Messages.Command.Status.NO_TARGETS_TO_CHECK)
                return

            all_submissions = []
            for target in targets:
                if target['target_type'] == 'latlong':
                    parts = target['target_name'].split(',')
                    if len(parts) >= 3:
                        lat, lon, radius = float(parts[0]), float(parts[1]), int(parts[2])
                        submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
                        all_submissions.extend(submissions)
                    elif len(parts) == 2:
                        lat, lon = float(parts[0]), float(parts[1])
                        submissions = await fetch_submissions_for_coordinates(lat, lon)
                        all_submissions.extend(submissions)
                elif target['target_type'] == 'location' and target['target_data']:
                    location_id = int(target['target_data'])
                    submissions = await fetch_submissions_for_location(location_id)
                    all_submissions.extend(submissions)

            new_submissions = self.db.filter_new_submissions(channel_id, all_submissions)

            if new_submissions:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.notifier.post_submissions(channel, new_submissions, config)
                    self.db.mark_submissions_seen(channel_id, [s['id'] for s in new_submissions])
                else:
                    logger.warning(f"Could not find channel {channel_id} to send notifications")

        except Exception as e:
            logger.error(f"Error polling channel {channel_id}: {e}")

    async def _should_poll_channel(self, config: Dict[str, Any]) -> bool:
        """Check if it's time to poll a channel based on its poll rate"""
        try:
            poll_interval_minutes = config.get('poll_rate_minutes', 60)
            last_poll = config.get('last_poll_at')

            if last_poll is None:
                return True

            time_since_last_poll = datetime.now() - last_poll
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
