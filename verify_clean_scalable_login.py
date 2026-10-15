"""
Verification Script for Clean, Scalable Login & Dynamic Shop/Dealer Registration.
Verifies all 11 user requirements.
"""

import unittest
from app import create_app
from models import db, User, FairPriceShop, RationCard

class TestCleanScalableLogin(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    # -------------------------------------------------------------------------
    # UI Verification: No Quick Logins or Demo Buttons on /login (Points 8, 9, 10)
    # -------------------------------------------------------------------------
    def test_01_login_page_has_no_demo_quick_logins_or_dealer_buttons(self):
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        # Check that Demo Quick Logins section and individual buttons are removed
        self.assertNotIn(b'Demo Quick Logins', res.data)
        self.assertNotIn(b'fillCredentials', res.data)
        self.assertNotIn(b'Dealer 1', res.data)
        self.assertNotIn(b'Dealer 2', res.data)
        self.assertNotIn(b'Dealer 3', res.data)
        self.assertNotIn(b'Dealer 4', res.data)
        self.assertNotIn(b'Citizen 1', res.data)
        self.assertNotIn(b'Citizen 2', res.data)
        self.assertNotIn(b'Citizen 3', res.data)
        # Ensure standard form fields are present
        self.assertIn(b'Username / Login ID', res.data)
        self.assertIn(b'Password', res.data)
        self.assertIn(b'Sign In', res.data)

    # -------------------------------------------------------------------------
    # Manual Credentials Login Tests (Points 1-6)
    # -------------------------------------------------------------------------
    def test_02_admin_login_manually(self):
        res = self.login('admin', 'admin123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'District Admin Monitoring Dashboard', res.data)

    def test_03_dealer1_login_manually_mapped_to_shop1(self):
        res = self.login('dealer1', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FPS-101', res.data)
        self.assertIn(b'Central Ward Fair Price Shop #101', res.data)

    def test_04_dealer2_login_manually_mapped_to_shop2(self):
        res = self.login('dealer2', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FPS-102', res.data)
        self.assertIn(b'Gandhi Chowk PDS Distribution Center #102', res.data)

    def test_05_dealer3_login_manually_mapped_to_shop3(self):
        res = self.login('dealer3', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FPS-103', res.data)
        self.assertIn(b'Market Road Public Ration Store #103', res.data)

    def test_06_dealer4_login_manually_mapped_to_shop4(self):
        res = self.login('dealer4', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'FPS-104', res.data)
        self.assertIn(b'Railway Colony Ration Depot #104', res.data)

    def test_07_customer_login_manually(self):
        res = self.login('citizen1', 'citizen123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Ration Portal', res.data)
        self.assertIn(b'Munna Lal', res.data)

    # -------------------------------------------------------------------------
    # Scalability & Dynamic Future Shop Creation (Point 11)
    # -------------------------------------------------------------------------
    def test_08_dynamic_shop5_dealer5_creation_and_auto_login(self):
        # 1. Admin logs in
        self.login('admin', 'admin123')
        
        # 2. Admin creates Shop 5 + Dealer 5 dynamically
        res_create = self.client.post('/admin/shops', data=dict(
            shop_code='FPS-105',
            license_no='LIC-PDS-2026-0505',
            shop_name='New Suburb Ration Depot #105',
            dealer_name='Rajesh Gupta',
            contact_no='9899112233',
            ward='Ward 25',
            district='Metro Central',
            address='Plot 10, New Suburb Road',
            dealer_username='dealer5',
            dealer_password='dealer123'
        ), follow_redirects=True)
        self.assertIn(b'FPS-105', res_create.data)
        
        # 3. Log out admin
        self.client.get('/logout')
        
        # 4. Verify login page remains identical (no dealer5 button rendered)
        res_login_page = self.client.get('/login')
        self.assertNotIn(b'dealer5', res_login_page.data)
        self.assertNotIn(b'Dealer 5', res_login_page.data)
        
        # 5. Dealer 5 logs in via standard form
        res_d5 = self.login('dealer5', 'dealer123')
        self.assertEqual(res_d5.status_code, 200)
        self.assertIn(b'FPS-105', res_d5.data)
        self.assertIn(b'New Suburb Ration Depot #105', res_d5.data)

if __name__ == '__main__':
    unittest.main()
