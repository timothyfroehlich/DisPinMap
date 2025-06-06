"""
Unit test for location add command with actual PinballMap API calls
"""

import unittest
from test_utils import run_async_test, find_location_in_suggestions

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
        
        run_async_test(run_test)

    def test_lyon_fuzzy_search(self):
        """Test that searching for Lyon returns fuzzy match suggestions including Lyons Classic Pinball"""
        async def run_test():
            result = await search_location_by_name("Lyon")
            
            self.assertEqual(result['status'], 'suggestions')
            suggestions = result['data']
            self.assertIsInstance(suggestions, list)
            self.assertGreater(len(suggestions), 0)
            
            # Should include Lyons Classic Pinball (ID: 2477)
            found_lyons = find_location_in_suggestions(suggestions, 2477, 'Lyons Classic Pinball')
            self.assertTrue(found_lyons, "Should find Lyons Classic Pinball in suggestions")
        
        run_async_test(run_test)

    def test_district_multiple_results(self):
        """Test that searching for District returns multiple suggestions including District 82 Pinball"""
        async def run_test():
            result = await search_location_by_name("District")
            
            self.assertEqual(result['status'], 'suggestions')
            suggestions = result['data']
            self.assertIsInstance(suggestions, list)
            self.assertGreaterEqual(len(suggestions), 5, "Should return at least 5 results for District search")
            
            # Should include District 82 Pinball (ID: 10406)
            found_district82 = find_location_in_suggestions(suggestions, 10406, 'District 82 Pinball')
            self.assertTrue(found_district82, "Should find District 82 Pinball in suggestions")
        
        run_async_test(run_test)


if __name__ == '__main__':
    unittest.main()