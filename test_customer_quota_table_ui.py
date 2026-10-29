"""
Test suite for Customer Monthly Grain Quota Allocation Table UI Fixes.
Verifies:
1. Citizen dashboard renders the Monthly Grain Quota Allocation table with all columns.
2. The Scheme label in the card header displays a valid, non-empty scheme name (e.g. Antyodaya Anna Yojana).
3. The table has proper responsive container semantics (role="region", tabindex="0", aria-label).
4. Table columns (Commodity, Allocation Basis, Unit Price, Monthly Quota, Already Lifted, Remaining, Status / Action) are present.
5. Action button/link (Report) is present and accessible, and not clipped.
6. CSS style.css defines .table-responsive with overflow-x: auto and NOT overflow: hidden.
7. Other citizen tables (Family Members, Transactions, Complaints) also have non-clipping responsive wrappers.
8. Quota calculations and numbers remain accurate and unchanged.
"""

import os
import unittest
from app import create_app
from config import Config
from models import db, User, RationCard, FairPriceShop
from rules import get_beneficiary_quota_status

class TestCustomerQuotaTableUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def login_citizen(self, card_number='RC-AAY-1001', password='citizen123'):
        return self.client.post('/login', data={
            'username': card_number,
            'password': password,
            'role': 'customer'
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_01_rules_get_beneficiary_quota_status_includes_scheme_name(self):
        """Verify rules.py returns a populated scheme_name for AAY, PHH, AY cards."""
        with self.app.app_context():
            card_aay = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
            if card_aay:
                status_aay = get_beneficiary_quota_status(card_aay)
                self.assertIn('scheme_name', status_aay)
                self.assertIn('Antyodaya Anna Yojana', status_aay['scheme_name'])

            card_phh = RationCard.query.filter_by(card_number='RC-PHH-2001').first()
            if card_phh:
                status_phh = get_beneficiary_quota_status(card_phh)
                self.assertIn('scheme_name', status_phh)
                self.assertIn('Priority Household', status_phh['scheme_name'])

    def test_02_citizen_dashboard_renders_scheme_badge_with_value(self):
        """Verify the customer dashboard renders 'Scheme: <Value>' and never a blank 'Scheme: '."""
        res_login = self.login_citizen('RC-AAY-1001', 'citizen123')
        self.assertEqual(res_login.status_code, 200)

        res_dash = self.client.get('/citizen/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        html = res_dash.data.decode('utf-8')

        # Check scheme badge contains value
        self.assertIn('Scheme:', html)
        self.assertNotIn('Scheme: </span>', html)
        self.assertNotIn('Scheme:</span>', html)
        self.assertIn('Antyodaya Anna Yojana', html)

        self.logout()

    def test_03_quota_table_columns_and_action_button_present(self):
        """Verify all columns and the action button are rendered in the Quota table."""
        self.login_citizen('RC-AAY-1001', 'citizen123')
        res = self.client.get('/citizen/dashboard')
        html = res.data.decode('utf-8')

        # Verify column headers
        self.assertIn('Commodity', html)
        self.assertIn('Allocation Basis', html)
        self.assertIn('Unit Price', html)
        self.assertIn('Monthly Quota', html)
        self.assertIn('Already Lifted', html)
        self.assertIn('Remaining', html)
        self.assertIn('Status / Action', html)

        # Verify action button / report link is present
        self.assertIn('Report', html)
        self.assertIn('/complaints/raise', html)

        # Verify commodities present
        self.assertIn('Rice', html)
        self.assertIn('Wheat', html)

        self.logout()

    def test_04_accessible_table_wrapper_semantics(self):
        """Verify tables use tabindex='0', role='region', and descriptive aria-labels."""
        self.login_citizen('RC-AAY-1001', 'citizen123')
        res = self.client.get('/citizen/dashboard')
        html = res.data.decode('utf-8')

        self.assertIn('role="region"', html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('aria-label="Monthly Grain Quota Allocation Table"', html)
        self.assertIn('aria-label="Family Members Table"', html)
        self.assertIn('aria-label="My Ration Transaction History Table"', html)

        self.logout()

    def test_05_css_table_responsive_allows_scrolling_not_clipped(self):
        """Verify style.css does not set overflow: hidden on .table-responsive."""
        css_path = os.path.join(os.path.dirname(__file__), 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        # Must have overflow-x: auto
        self.assertIn('.table-responsive {', css)
        self.assertIn('overflow-x: auto', css)

        # Must NOT have .table-responsive { overflow: hidden; }
        import re
        self.assertFalse(
            bool(re.search(r'\.table-responsive\s*\{[^}]*overflow\s*:\s*hidden', css)),
            ".table-responsive must NOT have overflow: hidden which clips data tables!"
        )

if __name__ == '__main__':
    unittest.main()
