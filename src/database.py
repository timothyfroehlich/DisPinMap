"""
Database module for Discord Pinball Map Bot
Handles SQLite database operations for channel configurations and machine tracking
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    def __init__(self, db_path: str = "pinball_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def _get_connection(self):
        """Get a database connection (for context manager use)"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Channel configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channel_configs (
                    channel_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    radius_miles INTEGER DEFAULT 25,
                    poll_rate_minutes INTEGER DEFAULT 60,
                    notification_types TEXT DEFAULT 'machines',
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Machine tracking table - stores current state of machines
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS machine_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    location_name TEXT NOT NULL,
                    machine_id INTEGER NOT NULL,
                    machine_name TEXT NOT NULL,
                    manufacturer TEXT,
                    year INTEGER,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id),
                    UNIQUE (channel_id, location_id, machine_id)
                )
            """)
            
            # Poll history table - tracks when each channel was last polled
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS poll_history (
                    channel_id INTEGER PRIMARY KEY,
                    last_poll_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    machines_found INTEGER DEFAULT 0,
                    locations_found INTEGER DEFAULT 0,
                    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id)
                )
            """)
            
            # Machine changes log - tracks additions/removals for notifications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS machine_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    location_name TEXT NOT NULL,
                    machine_id INTEGER NOT NULL,
                    machine_name TEXT NOT NULL,
                    change_type TEXT NOT NULL, -- 'added' or 'removed'
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id)
                )
            """)
            
            conn.commit()
    
    def get_channel_config(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific channel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM channel_configs WHERE channel_id = ?
            """, (channel_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_channel_config(self, channel_id: int, guild_id: int, **kwargs):
        """Update or create channel configuration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if config exists
            cursor.execute("SELECT channel_id FROM channel_configs WHERE channel_id = ?", (channel_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing config
                set_clauses = []
                values = []
                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                
                if set_clauses:
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(channel_id)
                    
                    query = f"UPDATE channel_configs SET {', '.join(set_clauses)} WHERE channel_id = ?"
                    cursor.execute(query, values)
            else:
                # Create new config
                cursor.execute("""
                    INSERT INTO channel_configs (channel_id, guild_id, latitude, longitude, 
                                               radius_miles, poll_rate_minutes, notification_types, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    channel_id, guild_id,
                    kwargs.get('latitude'),
                    kwargs.get('longitude'),
                    kwargs.get('radius_miles', 25),
                    kwargs.get('poll_rate_minutes', 60),
                    kwargs.get('notification_types', 'machines'),
                    kwargs.get('is_active', False)
                ))
            
            conn.commit()
    
    def get_active_channels(self) -> List[Dict[str, Any]]:
        """Get all channels that are actively monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM channel_configs WHERE is_active = TRUE
                AND latitude IS NOT NULL AND longitude IS NOT NULL
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_machine_tracking(self, channel_id: int, machines_data: List[Dict[str, Any]]):
        """Update machine tracking for a channel and detect changes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current machines for this channel
            cursor.execute("""
                SELECT location_id, machine_id FROM machine_tracking 
                WHERE channel_id = ? AND is_active = TRUE
            """, (channel_id,))
            
            current_machines = {(row[0], row[1]) for row in cursor.fetchall()}
            new_machines = {(m['location_id'], m['machine_id']) for m in machines_data}
            
            # Detect additions
            added_machines = new_machines - current_machines
            for machine_data in machines_data:
                key = (machine_data['location_id'], machine_data['machine_id'])
                if key in added_machines:
                    # Log the addition
                    cursor.execute("""
                        INSERT INTO machine_changes 
                        (channel_id, location_id, location_name, machine_id, machine_name, change_type)
                        VALUES (?, ?, ?, ?, ?, 'added')
                    """, (
                        channel_id,
                        machine_data['location_id'],
                        machine_data['location_name'],
                        machine_data['machine_id'],
                        machine_data['machine_name']
                    ))
            
            # Detect removals
            removed_machines = current_machines - new_machines
            for location_id, machine_id in removed_machines:
                # Get machine info for logging
                cursor.execute("""
                    SELECT location_name, machine_name FROM machine_tracking
                    WHERE channel_id = ? AND location_id = ? AND machine_id = ?
                """, (channel_id, location_id, machine_id))
                
                row = cursor.fetchone()
                if row:
                    location_name, machine_name = row
                    cursor.execute("""
                        INSERT INTO machine_changes 
                        (channel_id, location_id, location_name, machine_id, machine_name, change_type)
                        VALUES (?, ?, ?, ?, ?, 'removed')
                    """, (channel_id, location_id, location_name, machine_id, machine_name))
                
                # Mark as inactive
                cursor.execute("""
                    UPDATE machine_tracking SET is_active = FALSE, last_seen = CURRENT_TIMESTAMP
                    WHERE channel_id = ? AND location_id = ? AND machine_id = ?
                """, (channel_id, location_id, machine_id))
            
            # Update/insert current machines
            for machine_data in machines_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO machine_tracking 
                    (channel_id, location_id, location_name, machine_id, machine_name, 
                     manufacturer, year, last_seen, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, TRUE)
                """, (
                    channel_id,
                    machine_data['location_id'],
                    machine_data['location_name'],
                    machine_data['machine_id'],
                    machine_data['machine_name'],
                    machine_data.get('manufacturer'),
                    machine_data.get('year')
                ))
            
            # Update poll history
            cursor.execute("""
                INSERT OR REPLACE INTO poll_history 
                (channel_id, last_poll_time, machines_found, locations_found)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            """, (channel_id, len(machines_data), len(set(m['location_id'] for m in machines_data))))
            
            conn.commit()
    
    def get_pending_notifications(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get unnotified machine changes for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM machine_changes 
                WHERE channel_id = ? AND notified = FALSE
                ORDER BY detected_at ASC
            """, (channel_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_notifications_sent(self, change_ids: List[int]):
        """Mark machine change notifications as sent"""
        if not change_ids:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(change_ids))
            cursor.execute(f"""
                UPDATE machine_changes SET notified = TRUE 
                WHERE id IN ({placeholders})
            """, change_ids)
            
            conn.commit()