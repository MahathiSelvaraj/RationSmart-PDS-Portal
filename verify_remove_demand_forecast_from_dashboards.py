"""
Verification script for:
Removal of Demand Forecast from Admin and Dealer Dashboards.

Verifies:
1. Admin Dashboard does not render Demand Forecast navigation link or any forecast widgets.
2. Dealer Dashboard / Billing does not render Demand Forecast navigation link or any forecast widgets.
3. Neither role's layout presents Demand Forecast options in navigation or dashboard headers/cards.
4. Stock and inventory monitoring, low-stock alerts, transactions, billing, allocations, complaints remain intact.
"""

import unittest
from app import create_app
from models import db, User

class TestRemoveDemandForecast(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def login(self, username, password, role=None):
        data = {'username': username, 'password': password}
        if role:
            data['role'] = role
        return self.client.post('/login', data=data, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_01_admin_dashboard_no_demand_forecast(self):
        """Verify Admin Dashboard contains no Demand Forecast link, card, or widget."""
        res_login = self.login('admin', 'admin123', role='admin')
        self.assertEqual(res_login.status_code, 200)

        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        content = res_dash.data.decode('utf-8')

        # Verify NO Demand Forecast link in navigation or page body
        self.assertNotIn('Demand Forecast', content)
        self.assertNotIn('admin_demand_forecast', content)
        self.assertNotIn('/admin/demand-forecast', content)

        # Verify other essential dashboard monitoring sections are preserved
        self.assertIn('District Admin Monitoring Dashboard', content)
        self.assertIn('Total Shops', content)
        self.assertIn('Active Dealers', content)
        self.assertIn('Total Cardholders', content)
        self.assertIn('Overall Stock Balance', content)
        self.assertIn('Recent System Distribution Transactions', content)
        self.assertIn('Low-Stock Warnings', content)
        self.assertIn('Monthly Grain Outflow Distribution', content)

        self.logout()

    def test_02_dealer_dashboard_no_demand_forecast(self):
        """Verify Dealer Dashboard / POS contains no Demand Forecast link, card, or widget."""
        res_login = self.login('dealer1', 'dealer123', role='dealer')
        self.assertEqual(res_login.status_code, 200)

        # Dealer landing / dashboard is dealer_pos
        res_dash = self.client.get('/dealer/pos')
        self.assertEqual(res_dash.status_code, 200)
        content = res_dash.data.decode('utf-8')

        # Verify NO Demand Forecast link in navigation or page body
        self.assertNotIn('Demand Forecast', content)
        self.assertNotIn('dealer_demand_forecast', content)
        self.assertNotIn('/dealer/demand-forecast', content)

        # Verify other essential dealer operations are preserved
        self.assertIn('My Shop Billing', content)
        self.assertIn('My Stock', content)
        self.assertIn('My Transactions', content)
        self.assertIn('Shop Complaints', content)
        self.assertIn('Step 1: Authenticate Beneficiary', content)

        self.logout()

    def test_03_dealer_stock_and_transactions_no_demand_forecast_nav(self):
        """Verify dealer stock and sales history pages also have no Demand Forecast nav."""
        self.login('dealer1', 'dealer123', role='dealer')

        res_stock = self.client.get('/dealer/stock')
        self.assertEqual(res_stock.status_code, 200)
        self.assertNotIn('Demand Forecast', res_stock.data.decode('utf-8'))

        res_history = self.client.get('/dealer/sales-history')
        self.assertEqual(res_history.status_code, 200)
        self.assertNotIn('Demand Forecast', res_history.data.decode('utf-8'))

        res_complaints = self.client.get('/dealer/complaints')
        self.assertEqual(res_complaints.status_code, 200)
        self.assertNotIn('Demand Forecast', res_complaints.data.decode('utf-8'))

        self.logout()

    def test_04_admin_management_pages_no_demand_forecast_nav(self):
        """Verify admin pages also do not display Demand Forecast in their navigation bar."""
        self.login('admin', 'admin123', role='admin')

        pages_to_check = [
            '/admin/shops',
            '/admin/beneficiaries',
            '/admin/allocations',
            '/admin/stock',
            '/admin/transactions',
            '/admin/anomalies',
            '/admin/reports',
            '/admin/grievances'
        ]

        for p in pages_to_check:
            res = self.client.get(p)
            self.assertEqual(res.status_code, 200, f"Page {p} returned status {res.status_code}")
            content = res.data.decode('utf-8')
            # The navigation bar should not have Demand Forecast
            self.assertNotIn('Demand Forecast</a>', content, f"Demand Forecast nav link found on {p}")
            self.assertNotIn('<i class="bi bi-graph-up-arrow me-1"></i> Demand Forecast', content)

        self.logout()

if __name__ == '__main__':
    unittest.main()
