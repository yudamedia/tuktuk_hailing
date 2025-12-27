#!/usr/bin/env python3
"""
Unit tests for Hailing Places System

Run with:
    bench run-tests --app tuktuk_hailing --module test_places
    
Or run specific test:
    bench run-tests --app tuktuk_hailing --module test_places --test test_search_exact_match
"""

import frappe
import unittest
from tuktuk_hailing.api.places import (
    search_places,
    search_local_places,
    get_place_suggestions,
    format_display_name
)

class TestHailingPlaces(unittest.TestCase):
    """Test suite for Hailing Places functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests"""
        
        # Create test category
        if not frappe.db.exists("Hailing Place Category", "Test Category"):
            frappe.get_doc({
                "doctype": "Hailing Place Category",
                "category_name": "Test Category",
                "icon": "fa-test"
            }).insert(ignore_permissions=True)
        
        # Create test places
        cls.test_places = []
        
        test_data = [
            {
                "place_name": "Test Beach Resort",
                "category": "Test Category",
                "latitude": -4.283,
                "longitude": 39.567,
                "aliases": "Beach, Resort, Test",
                "description": "A test resort on the beach"
            },
            {
                "place_name": "Test Hotel Paradise",
                "category": "Test Category",
                "latitude": -4.290,
                "longitude": 39.570,
                "aliases": "Hotel, Paradise",
                "description": "A test hotel"
            },
            {
                "place_name": "Beach Cafe Test",
                "category": "Test Category",
                "latitude": -4.285,
                "longitude": 39.568,
                "aliases": "Cafe, Beach",
                "description": "A test cafe"
            }
        ]
        
        for data in test_data:
            if not frappe.db.exists("Hailing Place", data["place_name"]):
                place = frappe.get_doc({
                    "doctype": "Hailing Place",
                    **data,
                    "is_active": 1
                })
                place.insert(ignore_permissions=True)
                cls.test_places.append(place.name)
        
        frappe.db.commit()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data after all tests"""
        
        # Delete test places
        for place_name in cls.test_places:
            try:
                frappe.delete_doc("Hailing Place", place_name, force=1)
            except:
                pass
        
        # Delete test category
        try:
            frappe.delete_doc("Hailing Place Category", "Test Category", force=1)
        except:
            pass
        
        frappe.db.commit()
    
    def test_search_exact_match(self):
        """Test exact name match returns correct result"""
        
        result = search_places("Test Beach Resort", limit=5)
        
        self.assertEqual(result['source'], 'local')
        self.assertGreater(len(result['results']), 0)
        self.assertEqual(result['results'][0]['place_name'], 'Test Beach Resort')
    
    def test_search_partial_match(self):
        """Test partial name match"""
        
        result = search_places("Beach", limit=5)
        
        self.assertEqual(result['source'], 'local')
        self.assertGreater(len(result['results']), 0)
        
        # Should find at least the test beach places
        found_names = [r['place_name'] for r in result['results']]
        self.assertTrue(
            'Test Beach Resort' in found_names or 'Beach Cafe Test' in found_names
        )
    
    def test_search_by_alias(self):
        """Test search by alias"""
        
        result = search_places("Resort", limit=5)
        
        self.assertEqual(result['source'], 'local')
        found = any(r['place_name'] == 'Test Beach Resort' for r in result.get('results', []))
        self.assertTrue(found, "Should find place by alias")
    
    def test_search_by_category(self):
        """Test search by category"""
        
        result = search_places("Test Category", limit=5)
        
        self.assertEqual(result['source'], 'local')
        self.assertGreater(len(result['results']), 0)
    
    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        
        result1 = search_places("test beach", limit=5)
        result2 = search_places("TEST BEACH", limit=5)
        result3 = search_places("Test Beach", limit=5)
        
        # All should return results
        self.assertGreater(len(result1['results']), 0)
        self.assertGreater(len(result2['results']), 0)
        self.assertGreater(len(result3['results']), 0)
    
    def test_search_min_characters(self):
        """Test minimum character requirement"""
        
        result = search_places("T", limit=5)
        
        # Should return empty results for single character
        self.assertEqual(len(result['results']), 0)
    
    def test_search_empty_query(self):
        """Test empty query returns empty results"""
        
        result = search_places("", limit=5)
        
        self.assertEqual(len(result['results']), 0)
    
    def test_inactive_places_excluded(self):
        """Test that inactive places are not returned"""
        
        # Create an inactive place
        inactive_place = frappe.get_doc({
            "doctype": "Hailing Place",
            "place_name": "Inactive Test Place",
            "category": "Test Category",
            "latitude": -4.300,
            "longitude": 39.600,
            "is_active": 0
        })
        inactive_place.insert(ignore_permissions=True)
        frappe.db.commit()
        
        try:
            result = search_places("Inactive Test Place", limit=5)
            
            # Should not find the inactive place
            found = any(r['place_name'] == 'Inactive Test Place' for r in result.get('results', []))
            self.assertFalse(found, "Inactive places should not be returned")
        
        finally:
            # Clean up
            frappe.delete_doc("Hailing Place", "Inactive Test Place", force=1)
            frappe.db.commit()
    
    def test_search_with_distance(self):
        """Test search with user location for distance sorting"""
        
        # Search near Test Beach Resort location
        result = search_places(
            "Test", 
            limit=5,
            user_lat=-4.283,
            user_lng=39.567
        )
        
        self.assertEqual(result['source'], 'local')
        self.assertGreater(len(result['results']), 0)
        
        # First result should have distance
        if len(result['results']) > 0:
            first_result = result['results'][0]
            # Distance should be present and close to 0 (same location)
            if 'distance_km' in first_result:
                self.assertLess(first_result['distance_km'], 1.0)
    
    def test_search_with_bounds(self):
        """Test search with geographic bounds filtering"""
        
        # Define bounds around test locations
        bounds = {
            'min_lat': -4.295,
            'max_lat': -4.280,
            'min_lng': 39.565,
            'max_lng': 39.575
        }
        
        result = search_places("Test", limit=10, bounds=bounds)
        
        self.assertEqual(result['source'], 'local')
        
        # All results should be within bounds
        for place in result['results']:
            self.assertGreaterEqual(place['lat'], bounds['min_lat'])
            self.assertLessEqual(place['lat'], bounds['max_lat'])
            self.assertGreaterEqual(place['lon'], bounds['min_lng'])
            self.assertLessEqual(place['lon'], bounds['max_lng'])
    
    def test_get_place_suggestions(self):
        """Test autocomplete suggestions"""
        
        suggestions = get_place_suggestions("Beach", limit=10)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Check suggestion structure
        if len(suggestions) > 0:
            first = suggestions[0]
            self.assertIn('label', first)
            self.assertIn('value', first)
            self.assertIn('lat', first)
            self.assertIn('lon', first)
    
    def test_suggestions_min_characters(self):
        """Test suggestions minimum character requirement"""
        
        suggestions = get_place_suggestions("T", limit=10)
        
        # Should return empty list for single character
        self.assertEqual(len(suggestions), 0)
    
    def test_format_display_name(self):
        """Test display name formatting"""
        
        result = {
            'place_name': 'Test Place',
            'category': 'Hotel',
            'latitude': -4.283,
            'longitude': 39.567
        }
        
        display_name = format_display_name(result)
        
        self.assertIn('Test Place', display_name)
        self.assertIn('Hotel', display_name)
        self.assertIn('Diani Beach', display_name)
        self.assertIn('Kenya', display_name)
    
    def test_search_special_characters(self):
        """Test that special characters are properly escaped"""
        
        # These should not cause SQL errors
        special_queries = [
            "Test's Place",
            "Test & Place",
            "Test%Place",
            "Test_Place"
        ]
        
        for query in special_queries:
            try:
                result = search_places(query, limit=5)
                # Should not raise exception
                self.assertIsInstance(result, dict)
            except Exception as e:
                self.fail(f"Special character query failed: {query} - {str(e)}")
    
    def test_search_limit_respected(self):
        """Test that result limit is respected"""
        
        result = search_places("Test", limit=2)
        
        # Should return at most 2 results
        self.assertLessEqual(len(result['results']), 2)
    
    def test_search_priority_ordering(self):
        """Test that results are ordered by match priority"""
        
        # Exact match should come first
        result = search_places("Test Beach Resort", limit=10)
        
        if len(result['results']) > 0:
            # First result should be the exact match
            self.assertEqual(result['results'][0]['place_name'], 'Test Beach Resort')
    
    def test_cache_functionality(self):
        """Test that caching works for suggestions"""
        
        # First call - will cache
        suggestions1 = get_place_suggestions("Beach", limit=5)
        
        # Second call - should use cache
        suggestions2 = get_place_suggestions("Beach", limit=5)
        
        # Results should be identical
        self.assertEqual(len(suggestions1), len(suggestions2))
        
        if len(suggestions1) > 0 and len(suggestions2) > 0:
            self.assertEqual(suggestions1[0]['value'], suggestions2[0]['value'])


class TestHailingPlaceDocType(unittest.TestCase):
    """Test Hailing Place DocType operations"""
    
    def test_create_place(self):
        """Test creating a new place"""
        
        place = frappe.get_doc({
            "doctype": "Hailing Place",
            "place_name": "Test Create Place",
            "latitude": -4.300,
            "longitude": 39.600,
            "is_active": 1
        })
        
        place.insert(ignore_permissions=True)
        
        try:
            self.assertTrue(frappe.db.exists("Hailing Place", "Test Create Place"))
        finally:
            frappe.delete_doc("Hailing Place", "Test Create Place", force=1)
    
    def test_unique_place_name(self):
        """Test that place names must be unique"""
        
        place1 = frappe.get_doc({
            "doctype": "Hailing Place",
            "place_name": "Test Unique Place",
            "latitude": -4.300,
            "longitude": 39.600,
            "is_active": 1
        })
        place1.insert(ignore_permissions=True)
        
        try:
            # Try to create duplicate
            place2 = frappe.get_doc({
                "doctype": "Hailing Place",
                "place_name": "Test Unique Place",
                "latitude": -4.301,
                "longitude": 39.601,
                "is_active": 1
            })
            
            with self.assertRaises(Exception):
                place2.insert(ignore_permissions=True)
        
        finally:
            frappe.delete_doc("Hailing Place", "Test Unique Place", force=1)
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        
        # Missing place_name
        with self.assertRaises(Exception):
            place = frappe.get_doc({
                "doctype": "Hailing Place",
                "latitude": -4.300,
                "longitude": 39.600
            })
            place.insert(ignore_permissions=True)
        
        # Missing coordinates
        with self.assertRaises(Exception):
            place = frappe.get_doc({
                "doctype": "Hailing Place",
                "place_name": "Test Place"
            })
            place.insert(ignore_permissions=True)


def run_tests():
    """
    Helper function to run tests
    Usage: bench execute tuktuk_hailing.tests.test_places.run_tests
    """
    
    import sys
    from io import StringIO
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestHailingPlaces))
    suite.addTests(loader.loadTestsFromTestCase(TestHailingPlaceDocType))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()

