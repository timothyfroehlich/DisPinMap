"""
Test simulation module for Discord Pinball Map Bot
Simulates machine changes over time using Austin data for testing
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import Database
from api import fetch_austin_machines


class TestSimulation:
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database
        self.simulation_running = False
    
    async def run_test_simulation(self, channel_id: int, duration_seconds: int = 30):
        """Run a 30-second simulation of machine changes"""
        if self.simulation_running:
            return "❌ Simulation already running"
        
        self.simulation_running = True
        
        try:
            # Fetch real Austin data
            austin_data = await fetch_austin_machines()
            locations = austin_data['locations']
            
            # Filter to locations with machines
            locations_with_machines = [loc for loc in locations if loc.get('machine_count', 0) > 0]
            
            if len(locations_with_machines) < 10:
                return "❌ Not enough Austin locations for simulation"
            
            # Create initial state with subset of machines
            initial_machines = await self._create_initial_state(locations_with_machines[:5])
            
            # Create changes to simulate over 30 seconds
            changes = await self._create_simulated_changes(locations_with_machines[5:10], duration_seconds)
            
            # Apply initial state
            self.db.update_machine_tracking(channel_id, initial_machines)
            
            channel = self.bot.get_channel(channel_id)
            await channel.send("🧪 **Test Simulation Started!** Watch for machine changes over the next 30 seconds...")
            
            # Apply changes over time
            start_time = datetime.now()
            for change in changes:
                # Wait until it's time for this change
                target_time = start_time + timedelta(seconds=change['delay'])
                now = datetime.now()
                if target_time > now:
                    await asyncio.sleep((target_time - now).total_seconds())
                
                # Apply the change
                if change['type'] == 'add':
                    await self._simulate_machine_addition(channel_id, change['data'])
                elif change['type'] == 'remove':
                    await self._simulate_machine_removal(channel_id, change['data'])
                
                # Send notifications immediately
                notifications = self.db.get_pending_notifications(channel_id)
                if notifications:
                    await self._send_test_notifications(channel_id, notifications)
            
            await channel.send("🏁 **Test Simulation Complete!** All changes have been processed.")
            
        except Exception as e:
            print(f"Error in test simulation: {e}")
            return f"❌ Simulation failed: {str(e)}"
        finally:
            self.simulation_running = False
        
        return "✅ Test simulation completed successfully"
    
    async def _create_initial_state(self, locations: List[Dict]) -> List[Dict[str, Any]]:
        """Create initial machine state from location data"""
        machines = []
        
        for location in locations:
            # Create 1-3 fake machines per location
            machine_count = random.randint(1, 3)
            for i in range(machine_count):
                machines.append({
                    'location_id': location['id'],
                    'location_name': location['name'],
                    'machine_id': random.randint(10000, 99999),
                    'machine_name': random.choice([
                        'Medieval Madness', 'Attack from Mars', 'The Twilight Zone',
                        'Indiana Jones', 'Star Trek: The Next Generation', 'Theatre of Magic',
                        'White Water', 'Fish Tales', 'Cirqus Voltaire', 'Tales of the Arabian Nights'
                    ]),
                    'manufacturer': random.choice(['Williams', 'Bally', 'Stern', 'Gottlieb']),
                    'year': random.randint(1990, 2023)
                })
        
        return machines
    
    async def _create_simulated_changes(self, locations: List[Dict], duration_seconds: int) -> List[Dict]:
        """Create a sequence of machine additions and removals over time"""
        changes = []
        
        # Create 5-8 changes spread over the duration
        num_changes = random.randint(5, 8)
        
        for i in range(num_changes):
            delay = (duration_seconds / num_changes) * i + random.uniform(1, 3)
            
            location = random.choice(locations)
            change_type = 'add' if i % 2 == 0 else 'remove'
            
            if change_type == 'add':
                machine_data = {
                    'location_id': location['id'],
                    'location_name': location['name'],
                    'machine_id': random.randint(10000, 99999),
                    'machine_name': random.choice([
                        'Monster Bash', 'Scared Stiff', 'Creature from the Black Lagoon',
                        'The Addams Family', 'Terminator 2', 'The Machine: Bride of Pin*Bot',
                        'Black Knight 2000', 'High Speed', 'Pin*Bot', 'Funhouse'
                    ]),
                    'manufacturer': random.choice(['Williams', 'Bally', 'Stern', 'Gottlieb']),
                    'year': random.randint(1990, 2023)
                }
            else:
                # For removal, we'll pick from existing machines during simulation
                machine_data = {
                    'location_id': location['id'],
                    'location_name': location['name']
                }
            
            changes.append({
                'type': change_type,
                'delay': delay,
                'data': machine_data
            })
        
        return sorted(changes, key=lambda x: x['delay'])
    
    async def _simulate_machine_addition(self, channel_id: int, machine_data: Dict):
        """Simulate adding a machine"""
        # Get current machines and add the new one
        current_machines = []
        
        # Fetch existing machines from database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT location_id, location_name, machine_id, machine_name, manufacturer, year
                FROM machine_tracking WHERE channel_id = ? AND is_active = TRUE
            """, (channel_id,))
            
            for row in cursor.fetchall():
                current_machines.append({
                    'location_id': row[0],
                    'location_name': row[1],
                    'machine_id': row[2],
                    'machine_name': row[3],
                    'manufacturer': row[4],
                    'year': row[5]
                })
        
        # Add the new machine
        current_machines.append(machine_data)
        
        # Update tracking (this will detect the addition)
        self.db.update_machine_tracking(channel_id, current_machines)
    
    async def _simulate_machine_removal(self, channel_id: int, location_data: Dict):
        """Simulate removing a machine from a location"""
        # Get current machines and remove one from the specified location
        current_machines = []
        removed_machine = None
        
        # Fetch existing machines from database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT location_id, location_name, machine_id, machine_name, manufacturer, year
                FROM machine_tracking WHERE channel_id = ? AND is_active = TRUE
            """, (channel_id,))
            
            for row in cursor.fetchall():
                machine = {
                    'location_id': row[0],
                    'location_name': row[1],
                    'machine_id': row[2],
                    'machine_name': row[3],
                    'manufacturer': row[4],
                    'year': row[5]
                }
                
                # Remove first machine from target location
                if (machine['location_id'] == location_data['location_id'] and 
                    removed_machine is None):
                    removed_machine = machine
                    continue
                
                current_machines.append(machine)
        
        if removed_machine:
            # Update tracking (this will detect the removal)
            self.db.update_machine_tracking(channel_id, current_machines)
    
    async def _send_test_notifications(self, channel_id: int, notifications: List[Dict[str, Any]]):
        """Send notifications immediately for testing"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
                
            # Group notifications by type
            added = [n for n in notifications if n['change_type'] == 'added']
            removed = [n for n in notifications if n['change_type'] == 'removed']
            
            # Send addition notifications
            if added:
                message = "⚡ **New Pinball Machine Added!**\n"
                for notification in added:
                    message += f"• **{notification['machine_name']}** at {notification['location_name']}\n"
                await channel.send(message)
            
            # Send removal notifications
            if removed:
                message = "📤 **Pinball Machine Removed:**\n"
                for notification in removed:
                    message += f"• **{notification['machine_name']}** from {notification['location_name']}\n"
                await channel.send(message)
                
            # Mark notifications as sent
            notification_ids = [n['id'] for n in notifications]
            self.db.mark_notifications_sent(notification_ids)
            
        except Exception as e:
            print(f"Error sending test notifications: {e}")