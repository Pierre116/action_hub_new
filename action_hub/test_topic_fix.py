#!/usr/bin/env python3
"""Quick test to verify business-theme creation works with the correct payload key."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.conftest import AppTestCase

class TestBusinessThemeFix(AppTestCase):
    def test_create_business_theme_with_name_key(self):
        self.login_admin()
        # Test with correct key "name"
        resp = self.client.post('/api/admin/topics', json={
            'name': 'Test Business Theme'
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('data', data)
        self.assertEqual(data['data']['top_name'], 'Test Business Theme')
        
    def test_create_business_theme_accepts_top_name_key(self):
        self.login_admin()
        resp = self.client.post('/api/admin/topics', json={
            'top_name': 'Test Business Theme Wrong Key'
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('data', data)
        self.assertEqual(data['data']['top_name'], 'Test Business Theme Wrong Key')

if __name__ == '__main__':
    import unittest
    unittest.main()