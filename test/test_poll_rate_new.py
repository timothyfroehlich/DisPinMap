"""
Unit tests for the new poll_rate command functionality
Tests individual target poll rate features following TDD approach
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import List, Dict, Any

from src.commands import CommandHandler
from src.database import Database


class MockMessageContext:
    """Mock message context for testing"""
    def __init__(self, channel_id=12345, guild_id=67890, author_id=11111):
        self.channel = MagicMock()
        self.channel.id = channel_id
        self.guild = MagicMock()
        self.guild.id = guild_id
        self.author = MagicMock()
        self.author.id = author_id
        self.bot = MagicMock()
        self.sent_messages = []
        
    async def send(self, message: str):
        self.sent_messages.append(message)


class TestNewPollRateCommand(unittest.TestCase):
    """Test cases for new poll_rate command functionality"""
    
    def setUp(self):
        """Set up test database and command handler"""
        self.db = Database(":memory:")
        self.handler = CommandHandler(self.db)
        self.ctx = MockMessageContext()
        
    def tearDown(self):
        """Clean up database"""
        self.db.close()
        
    def _create_test_targets(self, count: int = 3) -> List[Dict[str, Any]]:
        """Helper to create test monitoring targets"""
        targets = []
        for i in range(count):
            if i % 2 == 0:
                # Create coordinate targets
                self.db.add_monitoring_target(
                    self.ctx.channel.id, 
                    'latlong', 
                    f"40.{i},74.{i},5"
                )
            else:
                # Create location targets
                self.db.add_monitoring_target(
                    self.ctx.channel.id, 
                    'location', 
                    f"Test Location {i}",
                    str(100 + i)
                )
        return self.db.get_monitoring_targets(self.ctx.channel.id)
        
    def test_poll_rate_minimum_value(self):
        """Test that poll rate must be at least 15 minutes"""
        async def run_test():
            await self.handler.handle_poll_rate(self.ctx, 10)
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("❌ Poll rate must be at least 15 minutes", self.ctx.sent_messages[0])
            
        asyncio.run(run_test())
        
    def test_poll_rate_all_no_targets(self):
        """Test poll_rate with 'all' when no targets exist"""
        async def run_test():
            await self.handler.handle_poll_rate(self.ctx, 30, "all")
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("✅ Poll rate for all 0 targets set to 30 minutes", self.ctx.sent_messages[0])
            
        asyncio.run(run_test())
        
    def test_poll_rate_all_with_targets(self):
        """Test poll_rate with 'all' when targets exist (less than 5)"""
        async def run_test():
            self._create_test_targets(3)
            
            with patch.object(self.db, 'update_channel_monitoring_targets_poll_rate', return_value=3) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 45, "all")
                
                mock_update.assert_called_once_with(self.ctx.channel.id, 45)
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for all 3 targets set to 45 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())
        
    def test_poll_rate_specific_target_valid(self):
        """Test poll_rate with specific valid target ID"""
        async def run_test():
            targets = self._create_test_targets(3)
            
            with patch.object(self.db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 30, "2")
                
                # Should update the second target (index 1, ID from database)
                expected_target_db_id = targets[1]['id']
                mock_update.assert_called_once_with(expected_target_db_id, 30)
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("set to 30 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())
        
    def test_poll_rate_specific_target_invalid_id(self):
        """Test poll_rate with invalid target ID"""
        async def run_test():
            self._create_test_targets(3)
            
            await self.handler.handle_poll_rate(self.ctx, 30, "5")  # Only 3 targets exist
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("❌ Invalid target ID", self.ctx.sent_messages[0])
            
        asyncio.run(run_test())
        
    def test_poll_rate_invalid_selector(self):
        """Test poll_rate with invalid selector"""
        async def run_test():
            self._create_test_targets(3)
            
            await self.handler.handle_poll_rate(self.ctx, 30, "invalid")
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("❌ Invalid target selector", self.ctx.sent_messages[0])
            
        asyncio.run(run_test())
        
    def test_poll_rate_no_selector_defaults_to_all(self):
        """Test poll_rate without selector defaults to affecting all targets"""
        async def run_test():
            self._create_test_targets(2)
            
            with patch.object(self.db, 'update_channel_monitoring_targets_poll_rate', return_value=2) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 60)  # No target_selector
                
                mock_update.assert_called_once_with(self.ctx.channel.id, 60)
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for all 2 targets set to 60 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())


class TestPollRateConfirmation(unittest.TestCase):
    """Test cases for poll_rate confirmation logic with 5+ targets"""
    
    def setUp(self):
        """Set up test database and command handler"""
        self.db = Database(":memory:")
        self.handler = CommandHandler(self.db)
        self.ctx = MockMessageContext()
        
    def tearDown(self):
        """Clean up database"""
        self.db.close()
        
    def _create_test_targets(self, count: int = 6) -> List[Dict[str, Any]]:
        """Helper to create test monitoring targets"""
        for i in range(count):
            self.db.add_monitoring_target(
                self.ctx.channel.id, 
                'location', 
                f"Test Location {i}",
                str(100 + i)
            )
        return self.db.get_monitoring_targets(self.ctx.channel.id)
        
    def test_poll_rate_confirmation_yes(self):
        """Test poll_rate confirmation with 'yes' response"""
        async def run_test():
            self._create_test_targets(6)
            
            # Mock the wait_for to return 'yes'
            mock_reply = MagicMock()
            mock_reply.content = "yes"
            mock_reply.author = self.ctx.author
            mock_reply.channel = self.ctx.channel
            self.ctx.bot.wait_for = AsyncMock(return_value=mock_reply)
            
            with patch.object(self.db, 'update_channel_monitoring_targets_poll_rate', return_value=6) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 30, "all")
                
                # Should ask for confirmation and then proceed
                self.assertEqual(len(self.ctx.sent_messages), 2)
                self.assertIn("change the poll rate for 6 targets", self.ctx.sent_messages[0])
                self.assertIn("✅ Poll rate for all 6 targets set to 30 minutes", self.ctx.sent_messages[1])
                mock_update.assert_called_once_with(self.ctx.channel.id, 30)
                
        asyncio.run(run_test())
        
    def test_poll_rate_confirmation_no(self):
        """Test poll_rate confirmation with 'no' response"""
        async def run_test():
            self._create_test_targets(6)
            
            # Mock the wait_for to return 'no'
            mock_reply = MagicMock()
            mock_reply.content = "no"
            mock_reply.author = self.ctx.author
            mock_reply.channel = self.ctx.channel
            self.ctx.bot.wait_for = AsyncMock(return_value=mock_reply)
            
            with patch.object(self.db, 'update_channel_monitoring_targets_poll_rate', return_value=6) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 30, "all")
                
                # Should ask for confirmation and then cancel
                self.assertEqual(len(self.ctx.sent_messages), 2)
                self.assertIn("change the poll rate for 6 targets", self.ctx.sent_messages[0])
                self.assertIn("Poll rate update cancelled", self.ctx.sent_messages[1])
                mock_update.assert_not_called()
                
        asyncio.run(run_test())
        
    def test_poll_rate_confirmation_timeout(self):
        """Test poll_rate confirmation with timeout"""
        async def run_test():
            self._create_test_targets(6)
            
            # Mock the wait_for to timeout
            self.ctx.bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError())
            
            with patch.object(self.db, 'update_channel_monitoring_targets_poll_rate', return_value=6) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 30, "all")
                
                # Should ask for confirmation and then timeout
                self.assertEqual(len(self.ctx.sent_messages), 2)
                self.assertIn("change the poll rate for 6 targets", self.ctx.sent_messages[0])
                self.assertIn("No confirmation received", self.ctx.sent_messages[1])
                mock_update.assert_not_called()
                
        asyncio.run(run_test())


class TestStatusCommandChanges(unittest.TestCase):
    """Test cases for status command changes to show numbered IDs"""
    
    def setUp(self):
        """Set up test database and command handler"""
        self.db = Database(":memory:")
        self.handler = CommandHandler(self.db)
        self.ctx = MockMessageContext()
        
    def tearDown(self):
        """Clean up database"""
        self.db.close()
        
    def test_status_shows_numbered_targets(self):
        """Test that status command shows numbered target IDs"""
        async def run_test():
            # Create a few targets with different poll rates
            self.db.add_monitoring_target(self.ctx.channel.id, 'location', 'Location A', '123')
            self.db.add_monitoring_target(self.ctx.channel.id, 'latlong', '40.1,74.1,5')
            self.db.add_monitoring_target(self.ctx.channel.id, 'location', 'Location B', '456')
            
            await self.handler.handle_status(self.ctx)
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            status_message = self.ctx.sent_messages[0]
            
            # Should show numbered targets
            self.assertIn("1.", status_message)
            self.assertIn("2.", status_message)
            self.assertIn("3.", status_message)
            
            # Should show target types and poll rates
            self.assertIn("Type:", status_message)
            self.assertIn("Poll:", status_message)
            
        asyncio.run(run_test())
        

if __name__ == '__main__':
    unittest.main()