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
            
            # Channel configurations table (general settings only)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channel_configs (
                    channel_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    poll_rate_minutes INTEGER DEFAULT 60,
                    notification_types TEXT DEFAULT 'machines',
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Monitoring targets table - supports coordinate and location targets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    target_type TEXT NOT NULL, -- 'latlong', 'location'
                    target_name TEXT NOT NULL, -- "lat,lon,radius" or location name
                    target_data TEXT, -- location_id for location targets
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id),
                    UNIQUE (channel_id, target_type, target_name)
                )
            """)
            
            # Seen submissions table - tracks which submissions we've already posted
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    submission_id INTEGER NOT NULL,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id),
                    UNIQUE (channel_id, submission_id)
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
                    INSERT INTO channel_configs (channel_id, guild_id, poll_rate_minutes, notification_types, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    channel_id, guild_id,
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
                SELECT cc.* FROM channel_configs cc
                WHERE cc.is_active = TRUE
                AND EXISTS (
                    SELECT 1 FROM monitoring_targets mt 
                    WHERE mt.channel_id = cc.channel_id
                )
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_submissions_seen(self, channel_id: int, submission_ids: List[int]):
        """Mark submissions as seen for a channel"""
        if not submission_ids:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for submission_id in submission_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO seen_submissions (channel_id, submission_id)
                    VALUES (?, ?)
                """, (channel_id, submission_id))
            
            conn.commit()
    
    def filter_new_submissions(self, channel_id: int, submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out submissions we've already seen"""
        if not submissions:
            return []
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get seen submission IDs
            submission_ids = [s['id'] for s in submissions]
            placeholders = ','.join('?' * len(submission_ids))
            
            cursor.execute(f"""
                SELECT submission_id FROM seen_submissions 
                WHERE channel_id = ? AND submission_id IN ({placeholders})
            """, [channel_id] + submission_ids)
            
            seen_ids = {row[0] for row in cursor.fetchall()}
            
            # Return only unseen submissions
            return [s for s in submissions if s['id'] not in seen_ids]
    
    def get_seen_submissions(self, channel_id: int) -> List[int]:
        """Get list of seen submission IDs for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT submission_id FROM seen_submissions 
                WHERE channel_id = ?
            """, (channel_id,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def add_monitoring_target(self, channel_id: int, target_type: str, target_name: str, target_data: str = None):
        """Add a monitoring target for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO monitoring_targets (channel_id, target_type, target_name, target_data)
                    VALUES (?, ?, ?, ?)
                """, (channel_id, target_type, target_name, target_data))
                conn.commit()
            except sqlite3.IntegrityError:
                # Target already exists
                raise Exception(f"Target '{target_name}' of type '{target_type}' is already being monitored")
    
    def remove_monitoring_target(self, channel_id: int, target_type: str, target_name: str):
        """Remove a monitoring target for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM monitoring_targets 
                WHERE channel_id = ? AND target_type = ? AND target_name = ?
            """, (channel_id, target_type, target_name))
            
            if cursor.rowcount == 0:
                raise Exception(f"Target '{target_name}' of type '{target_type}' not found")
            
            conn.commit()
    
    def get_monitoring_targets(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get all monitoring targets for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM monitoring_targets WHERE channel_id = ? ORDER BY target_type, target_name
            """, (channel_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_monitoring_targets(self, channel_id: int):
        """Remove all monitoring targets for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monitoring_targets WHERE channel_id = ?", (channel_id,))
            conn.commit()
    
    def clear_seen_submissions(self, channel_id: int):
        """Clear seen submissions for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM seen_submissions WHERE channel_id = ?", (channel_id,))
            conn.commit()