"""
RationSmart - Isolated End-to-End Verification Test Suite
Executes all 15 real application workflows in an isolated test database.
"""

import os
import unittest
from datetime import datetime, timedelta
from app import create_app
from config import Config
from models import (
    db, User, FairPriceShop, Commodity, RationCard, FamilyMember,
    GrainAllocation, ShopStock, DistributionTransaction, TransactionItem,
    AnomalyLog, AllocationRule
)
from rules import (
    get_monthly_entitlements, get_beneficiary_quota_status,
    calculate_demand_forecast, check_transaction_anomalies
)
from seed_data import seed_database

TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_e2e_verification.db')

class TestE2EConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_PATH}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-e2e-secret-key'

class E2EComprehensiveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass
        cls.app = create_app(TestE2EConfig)
        with cls.app.app_context():
            db.create_all()
            seed_database(cls.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def login(self, username, password, role=None):
        data = {'username': username, 'password': password}
        if role:
            data['role'] = role
        return self.client.post('/login', data=data, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # =========================================================================
    # WORKFLOW 1: Admin login and access to authorized management pages
    # =========================================================================
    def test_workflow_01_admin_login_and_management_pages(self):
        res = self.login('admin', 'admin123', role='admin')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Dashboard', res.data)
        
        pages = [
            ('/admin/dashboard', 'District Admin Monitoring Dashboard'),
            ('/admin/shops', 'Fair Price Shops'),
            ('/admin/beneficiaries', 'Beneficiary & Ration Card Registry'),
            ('/admin/allocations', 'Allocations'),
            ('/admin/stock', 'Shop Stock'),
            ('/admin/transactions', 'Transactions'),
            ('/admin/demand-forecast', 'Demand Forecast'),
            ('/admin/reports', 'System Reports')
        ]
        for url, expected_text in pages:
            page_res = self.client.get(url)
            self.assertEqual(page_res.status_code, 200, f"Failed on {url}")
            self.assertIn(expected_text.encode('utf-8'), page_res.data, f"Missing {expected_text} on {url}")
        self.logout()

    # =========================================================================
    # WORKFLOW 2: Dealer login and automatic access to assigned shop only
    # =========================================================================
    def test_workflow_02_dealer_login_and_assigned_shop_access(self):
        res = self.login('dealer1', 'dealer123', role='dealer')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Shop Billing', res.data)
        self.assertIn(b'FPS-101', res.data)

        # Dealer cannot access admin dashboard
        res_admin = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Access Denied', res_admin.data)
        self.assertIn(b'My Shop Billing', res_admin.data)
        self.logout()

    # =========================================================================
    # WORKFLOW 3: Customer search using a valid ration card
    # =========================================================================
    def test_workflow_03_customer_search_valid_card(self):
        self.login('dealer1', 'dealer123', role='dealer')
        res = self.client.get('/dealer/pos?card_number=RC-AAY-1001')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Munna Lal', res.data)
        self.assertIn(b'RC-AAY-1001', res.data)
        self.assertIn(b'Yellow', res.data)
        self.assertIn(b'4512', res.data) # Aadhaar last 4
        self.logout()

    # =========================================================================
    # WORKFLOW 4: Current-month allocation calculation
    # =========================================================================
    def test_workflow_04_current_month_allocation_calculation(self):
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        quota = get_beneficiary_quota_status(card)
        quota_items = {item['code']: item for item in quota['quota_items']}
        
        # AAY in TN PDS is PER_CARD 35kg total grains (e.g. 35.0 kg Rice, 15.0 kg Wheat, 1.0 kg Sugar)
        self.assertIn('RICE', quota_items)
        self.assertEqual(quota_items['RICE']['entitled_qty'], 35.0)
        self.assertEqual(quota_items['RICE']['allocation_basis'], 'PER_CARD')
        self.assertEqual(quota_items['SUGAR']['entitled_qty'], 1.0)
        self.assertGreater(quota_items['RICE']['remaining_qty'], 0.0)

    # =========================================================================
    # WORKFLOW 5 & 6: Billing with valid commodity & exactly-once stock deduction
    # =========================================================================
    def test_workflow_05_06_billing_and_stock_deduction(self):
        self.login('dealer1', 'dealer123', role='dealer')
        shop = FairPriceShop.query.filter_by(shop_code='FPS-101').first()
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        comm_rice = Commodity.query.filter_by(code='RICE').first()
        
        stock_before = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm_rice.id).first().current_stock
        quota_before = get_beneficiary_quota_status(card)
        rice_quota_before = next(i for i in quota_before['quota_items'] if i['code'] == 'RICE')['remaining_qty']

        bill_qty = 10.0
        self.assertGreaterEqual(rice_quota_before, bill_qty)
        self.assertGreaterEqual(stock_before, bill_qty)

        res = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            'shop_id': shop.id,
            f'qty_{comm_rice.id}': str(bill_qty),
            'payment_mode': 'Cash / Direct Subsidy',
            'auth_mode': 'Biometric Aadhaar Fingerprint (Simulated Verification Passed)'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'e-Ration Receipt', res.data)

        # Verify stock decreased by EXACTLY 10.0
        stock_after = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm_rice.id).first().current_stock
        self.assertEqual(round(stock_before - stock_after, 2), bill_qty)

        # Verify other shops' stocks remain untouched
        shop2 = FairPriceShop.query.filter_by(shop_code='FPS-102').first()
        stock_shop2 = ShopStock.query.filter_by(shop_id=shop2.id, commodity_id=comm_rice.id).first().current_stock
        self.assertEqual(stock_shop2, 500.0)
        self.logout()

    # =========================================================================
    # WORKFLOW 7: Correct customer allocation update
    # =========================================================================
    def test_workflow_07_customer_allocation_update(self):
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        quota = get_beneficiary_quota_status(card)
        rice_item = next(i for i in quota['quota_items'] if i['code'] == 'RICE')
        
        # Customer claimed 10.0 kg in previous test
        self.assertGreaterEqual(rice_item['claimed_qty'], 10.0)
        self.assertEqual(rice_item['remaining_qty'], round(rice_item['entitled_qty'] - rice_item['claimed_qty'], 2))

    # =========================================================================
    # WORKFLOW 8: E-receipt generation and retrieval
    # =========================================================================
    def test_workflow_08_receipt_generation_and_retrieval(self):
        self.login('dealer1', 'dealer123', role='dealer')
        tx = DistributionTransaction.query.filter_by(status='Completed').order_by(DistributionTransaction.id.desc()).first()
        self.assertIsNotNone(tx)

        res = self.client.get(f'/receipt/{tx.id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(tx.bill_number.encode('utf-8'), res.data)
        self.assertIn(b'OFFICIAL e-RATION RECEIPT', res.data)
        self.assertIn(b'PUBLIC DISTRIBUTION SYSTEM', res.data)
        self.logout()

    # =========================================================================
    # WORKFLOW 9: Transaction history updates for the correct customer
    # =========================================================================
    def test_workflow_09_transaction_history_customer_isolation(self):
        card1 = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        card2 = RationCard.query.filter_by(card_number='RC-PHH-2001').first()
        
        txs_card1 = DistributionTransaction.query.filter_by(ration_card_id=card1.id).all()
        txs_card2 = DistributionTransaction.query.filter_by(ration_card_id=card2.id).all()
        
        bill_nums_card1 = {t.bill_number for t in txs_card1}
        bill_nums_card2 = {t.bill_number for t in txs_card2}
        
        # Verify no cross contamination
        self.assertTrue(bill_nums_card1.isdisjoint(bill_nums_card2))

    # =========================================================================
    # WORKFLOW 10: Customer login and display of only own information
    # =========================================================================
    def test_workflow_10_customer_login_own_info_only(self):
        res = self.login('RC-AAY-1001', 'citizen123', role='customer')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Munna Lal', res.data)
        self.assertIn(b'RC-AAY-1001', res.data)
        self.assertNotIn(b'Suresh Babu', res.data)
        self.assertNotIn(b'RC-PHH-2001', res.data)
        self.logout()

    # =========================================================================
    # WORKFLOW 11: Rejection of unauthorized cross-shop and cross-customer requests
    # =========================================================================
    def test_workflow_11_cross_shop_and_cross_customer_protection(self):
        # 1. Dealer 1 attempts to search or bill card of Shop 2
        self.login('dealer1', 'dealer123', role='dealer')
        card_shop2 = RationCard.query.filter_by(card_number='RC-AAY-1003').first() # Shop 2
        res = self.client.get(f'/dealer/pos?card_number={card_shop2.card_number}')
        self.assertIn(b'Access Restriction', res.data)
        
        # Attempt to bill shop 2 card
        comm_rice = Commodity.query.filter_by(code='RICE').first()
        res_post = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card_shop2.id,
            'shop_id': 1,
            f'qty_{comm_rice.id}': '5.0'
        }, follow_redirects=True)
        self.assertIn(b'Security Enforcement', res_post.data)
        self.logout()

        # 2. Customer 1 attempts to view receipt of Customer 2
        self.login('RC-AAY-1001', 'citizen123', role='customer')
        tx_card2 = DistributionTransaction.query.filter_by(ration_card_id=card_shop2.id).first()
        if tx_card2:
            res_receipt = self.client.get(f'/receipt/{tx_card2.id}', follow_redirects=True)
            self.assertIn(b'Access Denied', res_receipt.data)
        self.logout()

    # =========================================================================
    # WORKFLOW 12: Insufficient stock, allocation, invalid card handling
    # =========================================================================
    def test_workflow_12_insufficient_stock_and_allocation_validation(self):
        self.login('dealer1', 'dealer123', role='dealer')
        shop = FairPriceShop.query.filter_by(shop_code='FPS-101').first()
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        comm_rice = Commodity.query.filter_by(code='RICE').first()
        stock_orig = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm_rice.id).first().current_stock

        # Quantity > remaining quota
        res_over_quota = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            'shop_id': shop.id,
            f'qty_{comm_rice.id}': '9999.0'
        }, follow_redirects=True)
        self.assertIn(b'Distribution Rejected', res_over_quota.data)
        self.assertIn(b'exceeds', res_over_quota.data)

        # Negative quantity
        res_neg = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            'shop_id': shop.id,
            f'qty_{comm_rice.id}': '-5.0'
        }, follow_redirects=True)
        self.assertIn(b'cannot be negative', res_neg.data)

        # Invalid card ID
        res_inv = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': 999999,
            'shop_id': shop.id,
            f'qty_{comm_rice.id}': '5.0'
        }, follow_redirects=True)
        self.assertIn(b'Invalid or non-existent', res_inv.data)

        # Stock is unchanged after failures
        stock_after = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm_rice.id).first().current_stock
        self.assertEqual(stock_orig, stock_after)
        self.logout()

    # =========================================================================
    # WORKFLOW 13: Admin remains unable to create bills
    # =========================================================================
    def test_workflow_13_admin_unable_to_create_bills(self):
        self.login('admin', 'admin123', role='admin')
        card = RationCard.query.first()
        comm = Commodity.query.first()
        
        res = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            'shop_id': 1,
            f'qty_{comm.id}': '5.0'
        }, follow_redirects=True)
        self.assertIn(b'Admin Dashboard', res.data)
        self.assertIn(b'Access Denied', res.data)
        self.logout()

    # =========================================================================
    # WORKFLOW 14: Monthly reports and demand forecasting use actual database records
    # =========================================================================
    def test_workflow_14_reports_and_demand_forecast_use_real_db(self):
        self.login('admin', 'admin123', role='admin')
        res_report = self.client.get('/admin/reports')
        self.assertEqual(res_report.status_code, 200)
        self.assertIn(b'System Reports', res_report.data)
        self.assertIn(b'Sales Report by Grain', res_report.data)

        res_forecast = self.client.get('/admin/demand-forecast')
        self.assertEqual(res_forecast.status_code, 200)
        self.assertIn(b'Demand Forecast & Reorder Recommendations', res_forecast.data)

        # Demand forecast function returns actual calculated records
        shop1 = FairPriceShop.query.first()
        fc = calculate_demand_forecast(shop_id=shop1.id)
        self.assertIsInstance(fc, list)
        self.assertGreater(len(fc), 0)
        # Check first commodity forecast record structure
        first_item = fc[0]
        self.assertIn('commodity', first_item)
        self.assertIn('avg_monthly_demand', first_item)
        self.assertIn('status', first_item)
        self.logout()

    # =========================================================================
    # WORKFLOW 15: Empty or insufficient historical data handled honestly
    # =========================================================================
    def test_workflow_15_insufficient_historical_data_handled_honestly(self):
        # Create a new shop with no transactions
        with self.app.app_context():
            new_shop = FairPriceShop(
                shop_code='FPS-999',
                shop_name='Empty Test Shop #999',
                dealer_name='Test Operator',
                license_no='LIC-TEST-999',
                contact_no='9000000000',
                address='Test Lane',
                ward='Ward 99'
            )
            db.session.add(new_shop)
            db.session.commit()
            
            fc = calculate_demand_forecast(shop_id=new_shop.id)
            self.assertIsInstance(fc, list)
            for item in fc:
                self.assertFalse(item['has_sufficient_data'])
                self.assertEqual(item['status'], 'Insufficient Data')
                self.assertIn('Insufficient historical data', item['message'])
                self.assertEqual(item['avg_monthly_demand'], 0.0)
                self.assertEqual(item['total_outflow'], 0.0)

if __name__ == '__main__':
    unittest.main()
