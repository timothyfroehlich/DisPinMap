"""
Unit test for location add command with actual PinballMap API calls
"""

import asyncio
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api import search_location_by_name


class TestLocationAdd(unittest.TestCase):
    def test_austin_pinball_collective_search(self):
        """Test that searching for Austin Pinball Collective returns valid location ID"""
        async def run_test():
            result = await search_location_by_name("Austin Pinball Collective")
            
            # Should return either exact match or single suggestion with exact name match
            if result['status'] == 'exact':
                location_data = result['data']
            elif result['status'] == 'suggestions' and len(result['data']) == 1:
                location_data = result['data'][0]
            else:
                self.fail(f"Unexpected result: {result}")
            
            self.assertEqual(location_data['id'], 26454)  # Known ID from API
            self.assertIn('austin pinball collective', location_data['name'].lower())
        
        asyncio.run(run_test())

    def test_lyon_fuzzy_search(self):
        """Test that searching for Lyon returns fuzzy match suggestions including Lyons Classic Pinball"""
        async def run_test():
            result = await search_location_by_name("Lyon")
            
            self.assertEqual(result['status'], 'suggestions')
            suggestions = result['data']
            self.assertIsInstance(suggestions, list)
            self.assertGreater(len(suggestions), 0)
            
            # Should include Lyons Classic Pinball (ID: 2477)
            found_lyons = False
            for suggestion in suggestions:
                if suggestion['id'] == 2477:
                    found_lyons = True
                    self.assertEqual(suggestion['name'], 'Lyons Classic Pinball')
                    break
            
            self.assertTrue(found_lyons, "Should find Lyons Classic Pinball in suggestions")
        
        asyncio.run(run_test())

    def test_district_multiple_results(self):
        """Test that searching for District returns multiple suggestions including District 82 Pinball"""
        async def run_test():
            result = await search_location_by_name("District")
            
            self.assertEqual(result['status'], 'suggestions')
            suggestions = result['data']
            self.assertIsInstance(suggestions, list)
            self.assertGreaterEqual(len(suggestions), 5, "Should return at least 5 results for District search")
            
            # Should include District 82 Pinball (ID: 10406)
            found_district82 = False
            for suggestion in suggestions:
                if suggestion['id'] == 10406:
                    found_district82 = True
                    self.assertEqual(suggestion['name'], 'District 82 Pinball')
                    break
            
            self.assertTrue(found_district82, "Should find District 82 Pinball in suggestions")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()