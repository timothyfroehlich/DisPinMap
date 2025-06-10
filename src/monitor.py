"""
Monitor module for Discord Pinball Map Bot
Handles background polling and notification sending using the new submission-based approach
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from discord.ext import tasks
try:
    from .database import Database
    from .api import fetch_submissions_for_coordinates, fetch_submissions_for_location
except ImportError:
    from database import Database
    from api import fetch_submissions_for_coordinates, fetch_submissions_for_location


class MachineMonitor:
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database
        self.monitor_task = None
    
    def start_monitoring(self):
        """Start the background monitoring task"""
        if self.monitor_task is None or not self.monitor_task.is_running():
            self.monitor_task = self._create_monitor_task()
            self.monitor_task.start()
    
    def stop_monitoring(self):
        """Stop the background monitoring task"""
        if self.monitor_task and self.monitor_task.is_running():
            self.monitor_task.cancel()
    
    def _create_monitor_task(self):
        """Create the monitoring task"""
        @tasks.loop(minutes=5)  # Check every 5 minutes, but respect individual channel poll rates
        async def monitor_submissions():
            """Background task to monitor new submissions"""
            try:
                active_channels = self.db.get_active_channels()
                
                for config in active_channels:
                    # Check if it's time to poll this channel
                    if await self._should_poll_channel(config):
                        await self._poll_channel(config)
                        
            except Exception as e:
                print(f"Error in monitor_submissions task: {e}")
        
        @monitor_submissions.before_loop
        async def before_monitor():
            """Wait until bot is ready before starting monitoring"""
            await self.bot.wait_until_ready()
        
        return monitor_submissions
    
    async def _should_poll_channel(self, config: Dict[str, Any]) -> bool:
        """Check if it's time to poll a channel based on its poll rate"""
        try:
            # Simple approach: check if enough time has passed since last poll
            # We'll store last poll time in a simple table or just use interval
            poll_interval_minutes = config.get('poll_rate_minutes', 60)
            
            # For simplicity, we can store the last poll time in memory or database
            # For now, let's use a basic time-based approach
            # In a real implementation, you'd want to track this per channel
            
            # This is a simplified version - poll every interval
            return True  # For now, always poll (the task loop handles timing)
                
        except Exception as e:
            print(f"Error checking poll time for channel {config['channel_id']}: {e}")
            return False
    
    async def _poll_channel(self, config: Dict[str, Any]):
        """Poll a single channel for new submissions across all its targets"""
        try:
            channel_id = config['channel_id']
            targets = self.db.get_monitoring_targets(channel_id)
            
            if not targets:
                print(f"Channel {channel_id} has no monitoring targets")
                return
            
            all_submissions = []
            
            # Fetch from all targets
            for target in targets:
                if target['target_type'] == 'latlong':
                    parts = target['target_name'].split(',')
                    if len(parts) >= 3:
                        lat, lon, radius = float(parts[0]), float(parts[1]), int(parts[2])
                        submissions = await fetch_submissions_for_coordinates(lat, lon, radius)
                        all_submissions.extend(submissions)
                    elif len(parts) == 2:
                        lat, lon = float(parts[0]), float(parts[1])
                        submissions = await fetch_submissions_for_coordinates(lat, lon)  # No radius (use API default)
                        all_submissions.extend(submissions)
                        
                elif target['target_type'] == 'location':
                    if target['target_data']:
                        location_id = int(target['target_data'])
                        submissions = await fetch_submissions_for_location(location_id)
                        all_submissions.extend(submissions)
            
            # Filter out submissions we've already seen
            new_submissions = self.db.filter_new_submissions(channel_id, all_submissions)
            
            # Send notifications for new submissions
            if new_submissions and config.get('notification_types', 'machines') in ['machines', 'all']:
                await self._send_notifications(channel_id, new_submissions)
                
                # Mark submissions as seen
                submission_ids = [s['id'] for s in new_submissions]
                self.db.mark_submissions_seen(channel_id, submission_ids)
                
        except Exception as e:
            print(f"Error polling channel {config['channel_id']}: {e}")
    
    async def _send_notifications(self, channel_id: int, submissions: List[Dict[str, Any]]):
        """Send submission notifications to a channel"""
        if not submissions:
            return
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"Could not find channel {channel_id}")
                return
            
            # Group submissions by type
            additions = [s for s in submissions if s.get('submission_type') == 'new_lmx']
            removals = [s for s in submissions if s.get('submission_type') == 'remove_machine']
            conditions = [s for s in submissions if s.get('submission_type') == 'new_condition']
            
            # Send addition notifications
            if additions:
                if len(additions) == 1:
                    submission = additions[0]
                    message = f"🆕 **{submission.get('machine_name', 'Unknown Machine')}** added at **{submission.get('location_name', 'Unknown Location')}** by {submission.get('user_name', 'Anonymous')}"
                    await channel.send(message)
                else:
                    message = f"🆕 **{len(additions)} New Pinball Machines Added!**\n"
                    for submission in additions[:10]:  # Limit to prevent message length issues
                        message += f"• **{submission.get('machine_name', 'Unknown')}** at {submission.get('location_name', 'Unknown')}\n"
                    
                    if len(additions) > 10:
                        message += f"... and {len(additions) - 10} more machines"
                        
                    await channel.send(message)
            
            # Send removal notifications
            if removals:
                if len(removals) == 1:
                    submission = removals[0]
                    message = f"🗑️ **{submission.get('machine_name', 'Unknown Machine')}** removed from **{submission.get('location_name', 'Unknown Location')}** by {submission.get('user_name', 'Anonymous')}"
                    await channel.send(message)
                else:
                    message = f"🗑️ **{len(removals)} Pinball Machines Removed:**\n"
                    for submission in removals[:10]:  # Limit to prevent message length issues
                        message += f"• **{submission.get('machine_name', 'Unknown')}** from {submission.get('location_name', 'Unknown')}\n"
                    
                    if len(removals) > 10:
                        message += f"... and {len(removals) - 10} more machines"
                        
                    await channel.send(message)
            
            # Send condition update notifications
            if conditions:
                for submission in conditions[:5]:  # Limit condition updates
                    message = f"🔧 **{submission.get('machine_name', 'Unknown Machine')}** at **{submission.get('location_name', 'Unknown Location')}**"
                    if submission.get('comment'):
                        message += f"\n💬 {submission['comment']}"
                    message += f" - by {submission.get('user_name', 'Anonymous')}"
                    await channel.send(message)
            
        except Exception as e:
            print(f"Error sending notifications to channel {channel_id}: {e}")