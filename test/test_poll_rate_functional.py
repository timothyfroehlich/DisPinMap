"""
Functional tests for poll_rate command with preconfigured database
Tests realistic scenarios with 10 monitoring targets
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestPollRateFunctional(unittest.TestCase):
    """Functional tests with preconfigured 10-target database"""
    
    @classmethod
    def setUpClass(cls):
        """Set up shared test database with 10 targets - reused across tests"""
        cls.shared_db = Database(":memory:")
        cls.channel_id = 12345
        cls.guild_id = 67890
        
        # Set up channel config
        cls.shared_db.update_channel_config(cls.channel_id, cls.guild_id, is_active=True)
        
        # Create 10 diverse monitoring targets
        cls.test_targets = [
            ('location', 'Arcade Palace', '1001'),
            ('latlong', '40.7589,-73.9851,10', None),  # NYC coordinates  
            ('location', 'GameZone Central', '1002'),
            ('latlong', '34.0522,-118.2437,5', None),  # LA coordinates
            ('location', 'Retro Game Bar', '1003'),
            ('location', 'Pinball Paradise', '1004'),
            ('latlong', '41.8781,-87.6298,8', None),   # Chicago coordinates
            ('location', 'The Flipper House', '1005'),
            ('location', 'Classic Games Cafe', '1006'),
            ('latlong', '47.6062,-122.3321,12', None), # Seattle coordinates
        ]
        
        for target_type, target_name, target_data in cls.test_targets:
            if target_type == 'latlong':
                cls.shared_db.add_monitoring_target(cls.channel_id, target_type, target_name)
            else:
                cls.shared_db.add_monitoring_target(cls.channel_id, target_type, target_name, target_data)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up shared database"""
        cls.shared_db.close()
        
    def setUp(self):
        """Set up test handler and context for each test"""
        self.handler = CommandHandler(self.shared_db)
        self.ctx = MockMessageContext(self.channel_id, self.guild_id)
        
    def test_status_shows_all_ten_targets_with_numbers(self):
        """Test that status command shows all 10 targets with sequential numbers"""
        async def run_test():
            await self.handler.handle_status(self.ctx)
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            status_message = self.ctx.sent_messages[0]
            
            # Should show all 10 targets with numbers
            for i in range(1, 11):
                self.assertIn(f"{i}.", status_message)
            
            # Should show target count
            self.assertIn("Total: 10", status_message)
            
            # Check specific targets are listed
            self.assertIn("Arcade Palace", status_message)
            self.assertIn("GameZone Central", status_message)
            self.assertIn("40.7589,-73.9851", status_message)  # NYC coords
            
        asyncio.run(run_test())
        
    def test_poll_rate_specific_target_from_status_list(self):
        """Test setting poll rate for specific target using ID from status"""
        async def run_test():
            # First get status to see the targets
            await self.handler.handle_status(self.ctx)
            self.ctx.sent_messages.clear()
            
            # Update target #3 (GameZone Central) to 25 minutes
            with patch.object(self.shared_db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 25, "3")
                
                # Should call update with correct target DB ID
                targets = self.shared_db.get_monitoring_targets(self.channel_id)
                expected_db_id = targets[2]['id']  # 3rd target (index 2)
                mock_update.assert_called_once_with(expected_db_id, 25)
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("GameZone Central", self.ctx.sent_messages[0])
                self.assertIn("25 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())
        
    def test_poll_rate_all_targets_with_confirmation(self):
        """Test updating all 10 targets requires confirmation"""
        async def run_test():
            # Mock user confirming with 'yes'
            mock_reply = MagicMock()
            mock_reply.content = "yes"
            mock_reply.author = self.ctx.author
            mock_reply.channel = self.ctx.channel
            self.ctx.bot.wait_for = AsyncMock(return_value=mock_reply)
            
            with patch.object(self.shared_db, 'update_channel_monitoring_targets_poll_rate', return_value=10) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 45)  # No selector = all
                
                # Should ask for confirmation first
                self.assertEqual(len(self.ctx.sent_messages), 2)
                self.assertIn("change the poll rate for 10 targets", self.ctx.sent_messages[0])
                self.assertIn("Are you sure?", self.ctx.sent_messages[0])
                
                # Then confirm success
                self.assertIn("✅ Poll rate for all 10 targets set to 45 minutes", self.ctx.sent_messages[1])
                mock_update.assert_called_once_with(self.channel_id, 45)
                
        asyncio.run(run_test())
        
    def test_poll_rate_all_targets_declined(self):
        """Test declining to update all 10 targets"""
        async def run_test():
            # Mock user declining with 'no'
            mock_reply = MagicMock()
            mock_reply.content = "no"
            mock_reply.author = self.ctx.author
            mock_reply.channel = self.ctx.channel
            self.ctx.bot.wait_for = AsyncMock(return_value=mock_reply)
            
            with patch.object(self.shared_db, 'update_channel_monitoring_targets_poll_rate', return_value=10) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 45, "all")
                
                # Should ask for confirmation then cancel
                self.assertEqual(len(self.ctx.sent_messages), 2)
                self.assertIn("change the poll rate for 10 targets", self.ctx.sent_messages[0])
                self.assertIn("Poll rate update cancelled", self.ctx.sent_messages[1])
                mock_update.assert_not_called()
                
        asyncio.run(run_test())
        
    def test_poll_rate_invalid_target_id_with_ten_targets(self):
        """Test invalid target ID when 10 targets exist"""
        async def run_test():
            # Try target ID 11 (out of range)
            await self.handler.handle_poll_rate(self.ctx, 30, "11")
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("❌ Invalid target ID", self.ctx.sent_messages[0])
            
            # Try target ID 0 (out of range low)
            self.ctx.sent_messages.clear()
            await self.handler.handle_poll_rate(self.ctx, 30, "0")
            
            self.assertEqual(len(self.ctx.sent_messages), 1)
            self.assertIn("❌ Invalid target ID", self.ctx.sent_messages[0])
            
        asyncio.run(run_test())
        
    def test_poll_rate_edge_case_target_boundaries(self):
        """Test poll rate on first and last targets"""
        async def run_test():
            # Test first target (ID 1)
            with patch.object(self.shared_db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 20, "1")
                
                targets = self.shared_db.get_monitoring_targets(self.channel_id)
                expected_db_id = targets[0]['id']  # First target
                mock_update.assert_called_with(expected_db_id, 20)
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("20 minutes", self.ctx.sent_messages[0])
                
            self.ctx.sent_messages.clear()
            
            # Test last target (ID 10)
            with patch.object(self.shared_db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 90, "10")
                
                targets = self.shared_db.get_monitoring_targets(self.channel_id)
                expected_db_id = targets[9]['id']  # Last target (index 9)
                mock_update.assert_called_with(expected_db_id, 90)
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("90 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())
        
    def test_poll_rate_coordinate_vs_location_targets(self):
        """Test poll rate updates work for both coordinate and location targets"""
        async def run_test():
            # Update a coordinate target (target #2 - NYC coordinates)
            with patch.object(self.shared_db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 35, "2")
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("Coordinates 40.7589,-73.9851", self.ctx.sent_messages[0])
                self.assertIn("35 minutes", self.ctx.sent_messages[0])
                
            self.ctx.sent_messages.clear()
            
            # Update a location target (target #1 - Arcade Palace)
            with patch.object(self.shared_db, 'update_monitoring_target_poll_rate', return_value=True) as mock_update:
                await self.handler.handle_poll_rate(self.ctx, 50, "1")
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("Arcade Palace", self.ctx.sent_messages[0])
                self.assertIn("50 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())


class TestPollRateIntegration(unittest.TestCase):
    """Integration tests showing complete workflow"""
    
    def setUp(self):
        """Set up fresh database for each integration test"""
        self.db = Database(":memory:")
        self.handler = CommandHandler(self.db)
        self.ctx = MockMessageContext()
        
        # Set up channel and add a few targets
        self.db.update_channel_config(self.ctx.channel.id, self.ctx.guild.id, is_active=True)
        
    def tearDown(self):
        """Clean up database"""
        self.db.close()
        
    def test_complete_workflow_status_then_poll_rate(self):
        """Test complete workflow: add targets, check status, update poll rates"""
        async def run_test():
            # Add some targets
            self.db.add_monitoring_target(self.ctx.channel.id, 'location', 'Test Arcade', '123')
            self.db.add_monitoring_target(self.ctx.channel.id, 'latlong', '40.0,74.0,5')
            self.db.add_monitoring_target(self.ctx.channel.id, 'location', 'Game Center', '456')
            
            # Check status shows numbered targets
            await self.handler.handle_status(self.ctx)
            status_message = self.ctx.sent_messages[0]
            
            self.assertIn("1.", status_message)
            self.assertIn("2.", status_message)
            self.assertIn("3.", status_message)
            self.assertIn("Total: 3", status_message)
            
            self.ctx.sent_messages.clear()
            
            # Update poll rate for target #2
            with patch.object(self.db, 'update_monitoring_target_poll_rate', return_value=True):
                await self.handler.handle_poll_rate(self.ctx, 30, "2")
                
                self.assertEqual(len(self.ctx.sent_messages), 1)
                self.assertIn("✅ Poll rate for", self.ctx.sent_messages[0])
                self.assertIn("30 minutes", self.ctx.sent_messages[0])
                
        asyncio.run(run_test())


if __name__ == '__main__':
    # Run functional tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPollRateFunctional)
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Run integration tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPollRateIntegration)
    unittest.TextTestRunner(verbosity=2).run(suite)