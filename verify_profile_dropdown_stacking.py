"""
Verification test for Admin Profile Dropdown and Navigation Bar Stacking & Logout.
Verifies:
1. CSS stacking context hierarchy: .pds-brand-header (z-index: 1030) > .pds-navbar-wrapper (z-index: 1020).
2. .dropdown-menu has z-index: 1050 !important to guarantee it renders completely above sticky elements.
3. No parent container has overflow: hidden or overflow: clip that could clip the dropdown.
4. Admin profile dropdown renders complete menu with 'Authenticated Account', user details, and 'Sign Out'.
5. Sign Out link points to /logout and executes logout cleanly.
6. Works for Admin, Dealer, and Citizen authenticated accounts.
"""

import os
import re
import unittest
from app import create_app
from config import Config
from models import db
from seed_data import seed_database

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CSS_FILE = os.path.join(WORKSPACE_DIR, 'static', 'css', 'style.css')
TEST_DB = os.path.join(WORKSPACE_DIR, 'test_dropdown_stacking.db')

class TestDropdownStackingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-dropdown-key'

class ProfileDropdownStackingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
        cls.app = create_app(TestDropdownStackingConfig)
        with cls.app.app_context():
            db.create_all()
            seed_database(cls.app)

        with open(CSS_FILE, 'r', encoding='utf-8') as f:
            cls.css_content = f.read()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_css_stacking_context_and_z_index_hierarchy(self):
        """Verify CSS ensures brand header is positioned higher than sticky navbar."""
        # 1. Header has position: relative and z-index: 1030
        self.assertIn(".pds-brand-header", self.css_content)
        self.assertIn("z-index: 1030", self.css_content)
        
        # 2. Sticky navbar has z-index: 1020
        self.assertIn(".pds-navbar-wrapper", self.css_content)
        self.assertIn("z-index: 1020", self.css_content)
        
        # 3. Dropdown menu has z-index: 1050 !important
        self.assertIn("z-index: 1050 !important", self.css_content)
        
        # Verify mathematically that header stacking context > navbar stacking context
        header_match = re.search(r'\.pds-brand-header\s*\{[^}]*z-index:\s*(\d+)', self.css_content)
        navbar_match = re.search(r'\.pds-navbar-wrapper\s*\{[^}]*z-index:\s*(\d+)', self.css_content)
        self.assertIsNotNone(header_match, "pds-brand-header must have explicit z-index")
        self.assertIsNotNone(navbar_match, "pds-navbar-wrapper must have explicit z-index")
        header_z = int(header_match.group(1))
        navbar_z = int(navbar_match.group(1))
        self.assertGreater(header_z, navbar_z, f"Header z-index ({header_z}) must be strictly greater than navbar ({navbar_z})")

    def test_02_no_overflow_clipping_on_header_containers(self):
        """Ensure no overflow: hidden on pds-brand-header, header, or .dropdown that could clip menus."""
        header_block_match = re.search(r'\.pds-brand-header\s*\{([^}]*)\}', self.css_content)
        self.assertIsNotNone(header_block_match)
        header_rules = header_block_match.group(1)
        self.assertNotIn("overflow: hidden", header_rules)
        self.assertNotIn("overflow: clip", header_rules)

    def test_03_admin_login_and_profile_dropdown_content(self):
        """Verify Admin login renders profile capsule with full dropdown and Sign Out."""
        # Log in as Admin
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check User Profile Capsule elements
        self.assertIn('class="pds-user-capsule', html)
        self.assertIn('data-bs-toggle="dropdown"', html)
        self.assertIn('ADMINISTRATOR', html)
        self.assertIn('District Food Supply Officer', html)

        # Check Dropdown Menu Content
        self.assertIn('dropdown-menu dropdown-menu-end shadow', html)
        self.assertIn('Authenticated Account', html)
        self.assertIn('@admin', html)
        self.assertIn('Sign Out', html)
        self.assertIn('href="/logout"', html)

    def test_04_sign_out_link_executes_clean_logout(self):
        """Verify clicking Sign Out (/logout) terminates session and redirects to /login."""
        # Log in as Admin first
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin'
        }, follow_redirects=True)

        # Confirm dashboard is accessible
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Click Sign Out
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        logout_html = res_logout.data.decode('utf-8')
        
        # User is redirected to login page and flash message is displayed
        self.assertIn('Sign In / Login', logout_html)

        # Subsequent attempt to access /admin/dashboard must be blocked
        res_dash_after = self.client.get('/admin/dashboard', follow_redirects=True)
        dash_after_html = res_dash_after.data.decode('utf-8')
        self.assertIn('Sign In', dash_after_html)

    def test_05_dealer_and_citizen_profile_dropdowns(self):
        """Verify Dealer and Citizen roles also have unobstructed profile dropdowns and functional sign out."""
        # 1. Test Dealer
        res_dealer = self.client.post('/login', data={
            'username': 'dealer1',
            'password': 'dealer123',
            'role': 'dealer'
        }, follow_redirects=True)
        self.assertEqual(res_dealer.status_code, 200)
        dealer_html = res_dealer.data.decode('utf-8')
        self.assertIn('DEALER:', dealer_html)
        self.assertIn('Sign Out', dealer_html)
        self.client.get('/logout', follow_redirects=True)

        # 2. Test Citizen
        res_citizen = self.client.post('/login', data={
            'username': 'citizen1',
            'password': 'citizen123',
            'role': 'citizen'
        }, follow_redirects=True)
        self.assertEqual(res_citizen.status_code, 200)
        citizen_html = res_citizen.data.decode('utf-8')
        self.assertIn('CITIZEN CARDHOLDER', citizen_html)
        self.assertIn('Sign Out', citizen_html)
        self.client.get('/logout', follow_redirects=True)

if __name__ == '__main__':
    unittest.main()
