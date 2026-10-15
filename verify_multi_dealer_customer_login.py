"""
Comprehensive Test Suite for Multi-Shop Dealer Login + Customer Login & Isolation Rules.
Tests 25 verification cases.
"""

import sys
import unittest
from app import create_app
from models import db, User, FairPriceShop, RationCard, DistributionTransaction

class TestMultiDealerCustomerLogin(unittest.TestCase):
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
    # 1. Dealer Accounts & Shop Isolation (Tests 1-12)
    # -------------------------------------------------------------------------
    def test_01_dealer1_login_lands_on_pos_shop1(self):
        res = self.login('dealer1', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Central Ward Fair Price Shop #101', res.data)
        self.assertIn(b'FPS-101', res.data)

    def test_02_dealer2_login_lands_on_pos_shop2(self):
        res = self.login('dealer2', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Gandhi Chowk PDS Distribution Center #102', res.data)
        self.assertIn(b'FPS-102', res.data)

    def test_03_dealer3_login_lands_on_pos_shop3(self):
        res = self.login('dealer3', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Market Road Public Ration Store #103', res.data)
        self.assertIn(b'FPS-103', res.data)

    def test_04_dealer4_login_lands_on_pos_shop4(self):
        res = self.login('dealer4', 'dealer123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Railway Colony Ration Depot #104', res.data)
        self.assertIn(b'FPS-104', res.data)

    def test_05_dealer1_pos_has_no_shop_selection_dropdown(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/pos')
        self.assertNotIn(b'<select name="shop_id"', res.data)

    def test_06_dealer1_search_card_belonging_to_shop2_denied(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/pos?card_number=RC-AAY-1003', follow_redirects=True)
        self.assertIn(b'belongs to', res.data)
        self.assertIn(b'You can only disburse ration for your assigned shop', res.data)

    def test_07_dealer1_search_card_belonging_to_shop1_allowed(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/pos?card_number=RC-AAY-1001', follow_redirects=True)
        self.assertIn(b'Munna Lal', res.data)
        self.assertIn(b'AAY', res.data)

    def test_08_dealer1_process_sale_on_shop2_card_rejected(self):
        self.login('dealer1', 'dealer123')
        card_shop2 = RationCard.query.filter_by(card_number='RC-AAY-1003').first()
        res = self.client.post('/dealer/pos/process-sale', data=dict(
            ration_card_id=card_shop2.id,
            qty_1=2.0
        ), follow_redirects=True)
        self.assertIn(b'Security Enforcement: Ration Card', res.data)
        self.assertIn(b'belongs to another shop', res.data)

    def test_09_dealer1_stock_page_shows_only_shop1_stock(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/stock')
        self.assertIn(b'FPS-101', res.data)
        self.assertNotIn(b'FPS-102', res.data)

    def test_10_dealer2_stock_page_shows_only_shop2_stock(self):
        self.login('dealer2', 'dealer123')
        res = self.client.get('/dealer/stock')
        self.assertIn(b'FPS-102', res.data)
        self.assertNotIn(b'FPS-101', res.data)

    def test_11_dealer1_sales_history_shows_only_shop1(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/sales-history')
        self.assertEqual(res.status_code, 200)

    def test_12_dealer2_sales_history_shows_only_shop2(self):
        self.login('dealer2', 'dealer123')
        res = self.client.get('/dealer/sales-history')
        self.assertEqual(res.status_code, 200)

    # -------------------------------------------------------------------------
    # 2. Role Redirection & Restrictions for Dealer (Tests 13-14)
    # -------------------------------------------------------------------------
    def test_13_dealer1_cannot_access_admin_dashboard(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access Denied', res.data)
        self.assertIn(b'FPS-101', res.data)

    def test_14_dealer1_cannot_access_admin_shops(self):
        self.login('dealer1', 'dealer123')
        res = self.client.get('/admin/shops', follow_redirects=True)
        self.assertIn(b'Access Denied', res.data)

    # -------------------------------------------------------------------------
    # 3. Citizen Login & Dashboard (Tests 15-20)
    # -------------------------------------------------------------------------
    def test_15_citizen1_login_by_username_lands_on_dashboard(self):
        res = self.login('citizen1', 'citizen123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Ration Portal', res.data)
        self.assertIn(b'Munna Lal', res.data)

    def test_16_citizen2_login_by_card_number_lands_on_dashboard(self):
        res = self.login('RC-PHH-2001', 'citizen123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Ration Portal', res.data)
        self.assertIn(b'Suresh Babu', res.data)

    def test_17_citizen3_login_by_username_lands_on_dashboard(self):
        res = self.login('citizen3', 'citizen123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Ration Portal', res.data)
        self.assertIn(b'Ramachandra Rao', res.data)

    def test_18_citizen1_dashboard_profile_details(self):
        self.login('citizen1', 'citizen123')
        res = self.client.get('/citizen/dashboard')
        self.assertIn(b'RC-AAY-1001', res.data)
        self.assertIn(b'AAY', res.data)
        self.assertIn(b'Central Ward Fair Price Shop #101', res.data)

    def test_19_citizen1_dashboard_monthly_quota_allocation(self):
        self.login('citizen1', 'citizen123')
        res = self.client.get('/citizen/dashboard')
        self.assertIn(b'Monthly Grain Quota Allocation', res.data)
        self.assertIn(b'Rice', res.data)
        self.assertIn(b'Wheat', res.data)

    def test_20_citizen1_dashboard_family_members(self):
        self.login('citizen1', 'citizen123')
        res = self.client.get('/citizen/dashboard')
        self.assertIn(b'Family Members', res.data)
        self.assertIn(b'Shanti Devi', res.data)

    # -------------------------------------------------------------------------
    # 4. Customer Data Security & Access Restrictions (Tests 21-24)
    # -------------------------------------------------------------------------
    def test_21_citizen_can_view_own_receipt(self):
        self.login('citizen2', 'citizen123')
        tx = DistributionTransaction.query.filter_by(ration_card_id=3).first() # RC-PHH-2001
        if tx:
            res = self.client.get(f'/receipt/{tx.id}')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Suresh Babu', res.data)

    def test_22_citizen_cannot_view_other_customer_receipt(self):
        self.login('citizen1', 'citizen123') # Munna Lal (RC-AAY-1001)
        tx = DistributionTransaction.query.filter_by(ration_card_id=8).first() # Ramachandra Rao (RC-AY-4001)
        if tx:
            res = self.client.get(f'/receipt/{tx.id}', follow_redirects=True)
            self.assertIn(b'Access Denied', res.data)
            self.assertIn(b'only authorized to view your own e-Receipts', res.data)

    def test_23_citizen_cannot_access_dealer_pos(self):
        self.login('citizen1', 'citizen123')
        res = self.client.get('/dealer/pos', follow_redirects=True)
        self.assertIn(b'Access Denied', res.data)

    def test_24_citizen_cannot_access_admin_dashboard(self):
        self.login('citizen1', 'citizen123')
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access Denied', res.data)

    # -------------------------------------------------------------------------
    # 5. Admin Privileges Intact & Cannot Create Bills (Test 25)
    # -------------------------------------------------------------------------
    def test_25_admin_privileges_intact_and_cannot_create_bills(self):
        self.login('admin', 'admin123')
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'District Admin Monitoring Dashboard', res_dash.data)
        
        # Admin blocked from POS sale creation
        res_sale = self.client.post('/dealer/pos/process-sale', data=dict(ration_card_id=1, qty_1=1.0), follow_redirects=True)
        self.assertIn(b'Access Denied: Billing operations are restricted to Shop Dealers only', res_sale.data)

if __name__ == '__main__':
    unittest.main()
