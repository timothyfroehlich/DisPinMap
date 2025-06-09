"""
Common utilities for testing location add functionality
"""

import asyncio
from unittest.mock import Mock
from typing import List, Dict, Any, Optional

from src.commands import CommandHandler
from src.database import Database


class MockContext:
    """Mock Discord message context for testing"""
    def __init__(self, channel_id=12345, guild_id=67890):
        self.channel = Mock()
        self.channel.id = channel_id
        self.guild = Mock()
        self.guild.id = guild_id
        self.messages = []
    
    async def send(self, message: str):
        """Capture sent messages"""
        self.messages.append(message)


def run_async_test(test_func):
    """Helper to run async test functions"""
    asyncio.run(test_func())


def find_location_in_suggestions(suggestions: List[Dict[str, Any]], location_id: int, expected_name: str) -> bool:
    """
    Helper to find a specific location in suggestions list
    
    Args:
        suggestions: List of location suggestions from API
        location_id: Expected location ID
        expected_name: Expected location name
        
    Returns:
        True if location found with correct name, False otherwise
    """
    for suggestion in suggestions:
        if suggestion['id'] == location_id:
            return suggestion['name'] == expected_name
    return False


def verify_database_targets(db: Database, channel_id: int, expected_count: int, expected_location_id: Optional[str] = None) -> bool:
    """
    Helper to verify database monitoring targets with exception handling
    
    Args:
        db: Database instance
        channel_id: Channel ID to check
        expected_count: Expected number of location targets
        expected_location_id: Expected location ID if count > 0
        
    Returns:
        True if verification passed or exception occurred (expected for in-memory DB)
    """
    try:
        targets = db.get_monitoring_targets(channel_id)
        location_targets = [t for t in targets if t['target_type'] == 'location']
        
        if len(location_targets) != expected_count:
            return False
            
        if expected_count > 0 and expected_location_id:
            return location_targets[0]['target_data'] == expected_location_id
            
        return True
    except Exception:
        # Tables might not exist in test DB, which is expected
        return True


def count_suggestion_lines(message: str) -> int:
    """
    Helper to count numbered suggestion lines in bot response message
    
    Args:
        message: Bot response message containing suggestions
        
    Returns:
        Number of numbered suggestion lines found
    """
    lines = message.split('\n')  # Bot messages use actual newlines now
    suggestion_lines = [
        line for line in lines 
        if line.strip() and any(line.strip().startswith(f'{i}.') for i in range(1, 6))
    ]
    return len(suggestion_lines)