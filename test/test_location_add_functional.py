"""
Functional tests for the full !location add command flow
Tests the complete command handling including bot responses
"""

import unittest
from src.commands import CommandHandler
from src.database import Database
from .test_utils import MockContext, run_async_test, verify_database_targets, count_suggestion_lines


class TestLocationAddFunctional(unittest.TestCase):
    def setUp(self):
        """Set up test database and handler for each test"""
        # Use in-memory database for testing
        self.db = Database(':memory:')
        self.handler = CommandHandler(self.db)
        self.ctx = MockContext()

    def test_exact_match_austin_pinball_collective(self):
        """Test adding Austin Pinball Collective with an exact name match"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "Austin Pinball Collective")
            
            # Verify bot response
            self.assertIn("Exact match found for Austin Pinball Collective", self.ctx.sent_messages[0])
            self.assertIn("Now monitoring Austin Pinball Collective", self.ctx.sent_messages[1])
            
            # Verify database state
            verify_database_targets(self.db, self.ctx.channel.id, 1, "26454")

        run_async_test(run_test)

    def test_suggestion_flow_austin(self):
        """Test adding a location that results in suggestions (e.g., Austin)"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "Austin")
            
            # Verify bot response indicates suggestions
            self.assertIn("Multiple locations found for 'Austin'. Please specify with !location add <id>:", self.ctx.sent_messages[0])
            
            # Count suggestion lines (example: Austin Pinball Collective, Austin Beerworks)
            # This count might vary based on actual API response, adjust if needed
            suggestion_lines = count_suggestion_lines(self.ctx.messages[0])
            self.assertGreaterEqual(suggestion_lines, 2, "Expected at least 2 suggestions for Austin")
            
            # Verify database state (no new targets should be added yet)
            verify_database_targets(self.db, self.ctx.channel.id, 0)

        run_async_test(run_test)