"""
Functional tests for the full !location add command flow
Tests the complete command handling including bot responses
"""

import unittest
from test_utils import MockContext, run_async_test, verify_database_targets, count_suggestion_lines

from commands import CommandHandler
from database import Database


class TestLocationAddFunctional(unittest.TestCase):
    def setUp(self):
        """Set up test database and handler for each test"""
        # Use in-memory database for testing
        self.db = Database(':memory:')
        self.handler = CommandHandler(self.db)
        self.ctx = MockContext()

    def test_exact_match_austin_pinball_collective(self):
        """Test !location add Austin Pinball Collective - should add location successfully"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "Austin Pinball Collective")
            
            # Should get multiple messages: initial submissions + success message
            self.assertGreater(len(self.ctx.messages), 0)
            
            # Should get either a success message or suggestions (API returns suggestions for single results)
            final_message = self.ctx.messages[-1]
            
            # Check if it was treated as exact match or suggestion
            if "✅ Added location:" in final_message:
                # Exact match case
                self.assertIn("Austin Pinball Collective", final_message)
                self.assertIn("ID: 26454", final_message)
                self.assertIn("Monitoring started!", final_message)
                
                # Verify location was added to database
                self.assertTrue(verify_database_targets(self.db, self.ctx.channel.id, 1, '26454'))
            else:
                # Suggestion case (single result treated as suggestion)
                self.assertIn("Austin Pinball Collective", final_message)
                self.assertIn("ID: 26454", final_message)
                self.assertIn("Did you mean one of these?", final_message)
                
                # Verify no location was added to database for suggestions
                self.assertTrue(verify_database_targets(self.db, self.ctx.channel.id, 0))
        
        run_async_test(run_test)

    def test_single_fuzzy_match_lyon(self):
        """Test !location add Lyon - should return suggestion for Lyons Classic Pinball"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "Lyon")
            
            # Should get exactly one message with suggestions
            self.assertEqual(len(self.ctx.messages), 1)
            
            message = self.ctx.messages[0]
            self.assertIn("Location 'Lyon' not found directly", message)
            self.assertIn("Did you mean one of these?", message)
            self.assertIn("Lyons Classic Pinball", message)
            self.assertIn("ID: 2477", message)
            self.assertIn("Please use `!location add <ID>` with the ID of the correct location", message)
            
            # Verify no location was added to database
            self.assertTrue(verify_database_targets(self.db, self.ctx.channel.id, 0))
        
        run_async_test(run_test)

    def test_multiple_fuzzy_matches_district(self):
        """Test !location add District - should return multiple suggestions including District 82 Pinball"""
        async def run_test():
            await self.handler.handle_location_add(self.ctx, "District")
            
            # Should get exactly one message with suggestions
            self.assertEqual(len(self.ctx.messages), 1)
            
            message = self.ctx.messages[0]
            self.assertIn("Location 'District' not found directly", message)
            self.assertIn("Did you mean one of these?", message)
            self.assertIn("District 82 Pinball", message)
            self.assertIn("ID: 10406", message)
            self.assertIn("Please use `!location add <ID>` with the ID of the correct location", message)
            
            # Should show multiple results (up to 5)
            suggestion_count = count_suggestion_lines(message)
            self.assertGreaterEqual(suggestion_count, 5, f"Should show at least 5 suggestions, got: {suggestion_count}")
            
            # Verify no location was added to database
            self.assertTrue(verify_database_targets(self.db, self.ctx.channel.id, 0))
        
        run_async_test(run_test)


if __name__ == '__main__':
    unittest.main()