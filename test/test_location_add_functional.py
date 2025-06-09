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
            
            # The command handler posts initial submissions first, then success message
            # Look for the success message (should be the last message)
            success_message = self.ctx.sent_messages[-1]
            self.assertIn("✅ Added location:", success_message)
            self.assertIn("Austin Pinball Collective", success_message)
            self.assertIn("Monitoring started!", success_message)
            
            # Verify database state
            verify_database_targets(self.db, self.ctx.channel.id, 1, "26454")

        run_async_test(run_test)

    def test_suggestion_flow_austin(self):
        """Test adding a location that results in suggestions (e.g., Austin)"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "Austin")
            
            # Verify bot response indicates suggestions (should be first/only message)
            response_message = self.ctx.sent_messages[0]
            self.assertIn("not found directly", response_message)
            self.assertIn("Did you mean one of these?", response_message)
            
            # Count suggestion lines (example: Austin Pinball Collective, Austin Beerworks)
            # This count might vary based on actual API response, adjust if needed
            suggestion_lines = count_suggestion_lines(response_message)
            self.assertGreaterEqual(suggestion_lines, 2, "Expected at least 2 suggestions for Austin")
            
            # Verify database state (no new targets should be added yet)
            verify_database_targets(self.db, self.ctx.channel.id, 0)

        run_async_test(run_test)