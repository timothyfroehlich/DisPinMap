"""
Monitor module for Discord Pinball Map Bot
Handles background polling and notification sending
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from discord.ext import tasks
from database import Database
from api import fetch_machines_for_location, fetch_region_machines, fetch_location_machines


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
        async def monitor_machines():
            """Background task to monitor machine changes"""
            try:
                active_channels = self.db.get_active_channels()
                
                for config in active_channels:
                    # Check if it's time to poll this channel
                    if await self._should_poll_channel(config):
                        await self._poll_channel(config)
                        
            except Exception as e:
                print(f"Error in monitor_machines task: {e}")
        
        @monitor_machines.before_loop
        async def before_monitor():
            """Wait until bot is ready before starting monitoring"""
            await self.bot.wait_until_ready()
        
        return monitor_machines
    
    async def _should_poll_channel(self, config: Dict[str, Any]) -> bool:
        """Check if it's time to poll a channel based on its poll rate"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT last_poll_time FROM poll_history WHERE channel_id = ?", 
                             (config['channel_id'],))
                result = cursor.fetchone()
                
                if not result:
                    return True  # Never polled before
                
                last_poll = datetime.fromisoformat(result[0])
                now = datetime.now()
                poll_interval = timedelta(minutes=config['poll_rate_minutes'])
                
                return (now - last_poll) >= poll_interval
                
        except Exception as e:
            print(f"Error checking poll time for channel {config['channel_id']}: {e}")
            return False
    
    async def _poll_channel(self, config: Dict[str, Any]):
        """Poll a single channel for machine changes across all its targets"""
        try:
            channel_id = config['channel_id']
            targets = self.db.get_monitoring_targets(channel_id)
            
            if not targets:
                print(f"Channel {channel_id} has no monitoring targets")
                return
            
            all_machines = []
            
            # Fetch from all targets
            for target in targets:
                if target['target_type'] == 'region':
                    machines = await fetch_region_machines(target['target_name'])
                    all_machines.extend(machines)
                    
                elif target['target_type'] == 'latlong':
                    parts = target['target_name'].split(',')
                    if len(parts) >= 3:
                        lat, lon, radius = float(parts[0]), float(parts[1]), int(parts[2])
                        machines = await fetch_machines_for_location(lat, lon, radius)
                        all_machines.extend(machines)
                        
                elif target['target_type'] == 'location':
                    if target['target_data']:
                        location_id, region_name = target['target_data'].split(':')
                        machines = await fetch_location_machines(int(location_id), region_name)
                        all_machines.extend(machines)
            
            # Update tracking and detect changes
            self.db.update_machine_tracking(channel_id, all_machines)
            
            # Send notifications
            notifications = self.db.get_pending_notifications(channel_id)
            if notifications and config.get('notification_types', 'machines') in ['machines', 'all']:
                await self._send_notifications(channel_id, notifications)
                
        except Exception as e:
            print(f"Error polling channel {config['channel_id']}: {e}")
    
    async def _send_notifications(self, channel_id: int, notifications: List[Dict[str, Any]]):
        """Send machine change notifications to a channel"""
        if not notifications:
            return
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"Could not find channel {channel_id}")
                return
                
            # Group notifications by type
            added = [n for n in notifications if n['change_type'] == 'added']
            removed = [n for n in notifications if n['change_type'] == 'removed']
            
            # Send addition notifications
            if added:
                message = "⚡ **New Pinball Machines Added!**\n"
                for notification in added[:10]:  # Limit to prevent message length issues
                    message += f"• **{notification['machine_name']}** at {notification['location_name']}\n"
                
                if len(added) > 10:
                    message += f"... and {len(added) - 10} more machines"
                    
                await channel.send(message)
            
            # Send removal notifications
            if removed:
                message = "📤 **Pinball Machines Removed:**\n"
                for notification in removed[:10]:  # Limit to prevent message length issues
                    message += f"• **{notification['machine_name']}** from {notification['location_name']}\n"
                
                if len(removed) > 10:
                    message += f"... and {len(removed) - 10} more machines"
                    
                await channel.send(message)
                
            # Mark notifications as sent
            notification_ids = [n['id'] for n in notifications]
            self.db.mark_notifications_sent(notification_ids)
            
        except Exception as e:
            print(f"Error sending notifications to channel {channel_id}: {e}")