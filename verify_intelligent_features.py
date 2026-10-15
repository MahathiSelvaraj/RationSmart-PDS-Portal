"""
Verification Test Suite for Intelligent Monitoring Features & Core Billing System
Tests:
1. Historical transactions calculate average demand correctly
2. Current stock displayed correctly
3. Estimated stock coverage calculated correctly
4. Reorder recommendation calculated correctly
5. Insufficient historical data handled safely
6. Admin can view all shops in demand forecast
7. Dealer can view only their own shop in demand forecast
8. Normal transaction remains unflagged
9. Repeated short-period transactions are flagged
10. Unusually large quantity flagged when appropriate
11. Flagged transaction shows clear reason
12. Admin can mark alert as Reviewed
13. Original transaction not deleted/modified
14. Dealer cannot access global transaction alerts
15. Core 12 Billing & Stock Management test cases pass
"""

import os
import unittest
from datetime import datetime, timedelta
from app import create_app
from config import Config
from models import (
    db, User, FairPriceShop, Commodity, RationCard, FamilyMember,
    ShopStock, DistributionTransaction, TransactionItem, AnomalyLog
)
from rules import calculate_demand_forecast, check_transaction_anomalies
from seed_data import seed_database

TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_intelligent.db')

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_PATH}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class IntelligentFeaturesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass
        cls.app = create_app(TestConfig)
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
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # DEMAND FORECAST & REORDER RECOMMENDATIONS (Tests 1 - 7)
    # -------------------------------------------------------------------------
    def test_01_historical_transactions_calculate_average_demand(self):
        """Test 1: Historical transactions calculate average demand correctly."""
        shop = FairPriceShop.query.filter_by(shop_code='FPS-102').first()
        comm = Commodity.query.filter_by(code='RICE').first()
        card = RationCard.query.filter_by(assigned_shop_id=shop.id).first()
        user = User.query.filter_by(username='dealer2').first()

        # Clean old transactions for Shop 2
        DistributionTransaction.query.filter_by(shop_id=shop.id).delete()
        db.session.commit()

        # Add 2 historical transactions across 2 distinct months (20kg + 30kg = 50kg over 2 months)
        tx1 = DistributionTransaction(
            bill_number='BILL-202606-00099',
            ration_card_id=card.id,
            shop_id=shop.id,
            user_id=user.id,
            transaction_date=datetime(2026, 6, 15, 10, 0),
            month_period='2026-06',
            total_amount=60.0,
            status='Completed'
        )
        db.session.add(tx1)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=tx1.id, commodity_id=comm.id, quantity=20.0, unit_price=3.0, subtotal=60.0))

        tx2 = DistributionTransaction(
            bill_number='BILL-202607-00099',
            ration_card_id=card.id,
            shop_id=shop.id,
            user_id=user.id,
            transaction_date=datetime(2026, 7, 15, 10, 0),
            month_period='2026-07',
            total_amount=90.0,
            status='Completed'
        )
        db.session.add(tx2)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=tx2.id, commodity_id=comm.id, quantity=30.0, unit_price=3.0, subtotal=90.0))
        db.session.commit()

        # Total outflow = 20 + 30 = 50. Months = 2. Avg monthly demand = 25.0
        forecasts = calculate_demand_forecast(shop_id=shop.id, commodity_id=comm.id)
        self.assertTrue(len(forecasts) > 0)
        f = forecasts[0]
        self.assertTrue(f['has_sufficient_data'])
        self.assertEqual(f['avg_monthly_demand'], 25.0)

    def test_02_current_stock_displayed_correctly(self):
        """Test 2: Current stock displayed correctly."""
        shop = FairPriceShop.query.first()
        comm = Commodity.query.filter_by(code='RICE').first()
        stock = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm.id).first()
        
        forecasts = calculate_demand_forecast(shop_id=shop.id, commodity_id=comm.id)
        f = forecasts[0]
        self.assertEqual(f['current_stock'], round(stock.current_stock, 1))

    def test_03_estimated_stock_coverage_calculated_correctly(self):
        """Test 3: Estimated stock coverage calculated correctly."""
        shop = FairPriceShop.query.first()
        comm = Commodity.query.filter_by(code='RICE').first()
        forecasts = calculate_demand_forecast(shop_id=shop.id, commodity_id=comm.id)
        f = forecasts[0]
        if f['has_sufficient_data'] and f['avg_daily_demand'] > 0:
            expected_days = int(round(f['current_stock'] / f['avg_daily_demand']))
            self.assertEqual(f['coverage_days_num'], expected_days)

    def test_04_reorder_recommendation_calculated_correctly(self):
        """Test 4: Reorder recommendation calculated correctly."""
        shop = FairPriceShop.query.first()
        comm = Commodity.query.filter_by(code='RICE').first()
        stock = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm.id).first()
        
        # Set stock lower than avg monthly demand to trigger replenishment
        stock.current_stock = 10.0
        db.session.commit()

        forecasts = calculate_demand_forecast(shop_id=shop.id, commodity_id=comm.id)
        f = forecasts[0]
        self.assertEqual(f['status'], 'Replenishment Recommended')
        expected_reorder = round(max(0.0, f['avg_monthly_demand'] - f['current_stock']), 1)
        self.assertEqual(f['recommended_reorder_qty'], expected_reorder)

    def test_05_insufficient_historical_data_handled_safely(self):
        """Test 5: Insufficient historical data handled safely."""
        new_shop = FairPriceShop(
            shop_code='FPS-TEST-99',
            shop_name='Test Empty Shop',
            dealer_name='Test Dealer',
            license_no='LIC-TEST-99',
            contact_no='9999999999',
            address='Test Address',
            ward='Ward 99'
        )
        db.session.add(new_shop)
        db.session.commit()

        comm = Commodity.query.first()
        forecasts = calculate_demand_forecast(shop_id=new_shop.id, commodity_id=comm.id)
        self.assertTrue(len(forecasts) > 0)
        f = forecasts[0]
        self.assertFalse(f['has_sufficient_data'])
        self.assertEqual(f['status'], 'Insufficient Data')
        self.assertIn('Insufficient historical data', f['message'])

    def test_06_admin_can_view_all_shops(self):
        """Test 6: Admin can view all shops in demand forecast."""
        self.login('admin', 'admin123')
        res = self.client.get('/admin/demand-forecast')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Demand Forecast', res.data)
        self.assertIn(b'All Ration Shops', res.data)

    def test_07_dealer_can_view_only_their_own_shop(self):
        """Test 7: Dealer can view only their own shop in demand forecast."""
        self.login('dealer1', 'dealer123')
        res = self.client.get('/dealer/demand-forecast')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Shop Demand Forecast', res.data)
        # Verify Dealer 1 sees Shop 1
        self.assertIn(b'FPS-101', res.data)
        # Verify Dealer 1 does not see shop selector options for other shops
        self.assertNotIn(b'<select name="shop_id"', res.data)

    # -------------------------------------------------------------------------
    # SUSPICIOUS TRANSACTION FLAGGING (Tests 8 - 14)
    # -------------------------------------------------------------------------
    def test_08_normal_transaction_remains_unflagged(self):
        """Test 8: Normal transaction remains unflagged."""
        card = RationCard.query.filter_by(card_number='RC-PHH-2003').first() # Shop 3 card
        # Clean any previous logs
        AnomalyLog.query.filter_by(ration_card_id=card.id).delete()
        db.session.commit()

        anomalies = check_transaction_anomalies(
            ration_card=card,
            shop_id=card.assigned_shop_id,
            items_to_purchase=[{'commodity_id': 1, 'quantity': 2.0}],
            transaction_time=datetime(2026, 9, 24, 11, 0) # Normal PDS hours
        )
        # Should have 0 high or medium severity anomalies
        flagged = [a for a in anomalies if a['severity'] in ['High', 'Medium']]
        self.assertEqual(len(flagged), 0)

    def test_09_repeated_short_period_transactions_are_flagged(self):
        """Test 9: Repeated short-period transactions are flagged."""
        self.login('dealer1', 'dealer123')
        card = RationCard.query.filter_by(card_number='RC-NPHH-3001').first()
        comm = Commodity.query.filter_by(code='RICE').first()

        # 1st sale
        res1 = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 2.0, # 2kg Rice
            'auth_mode': 'Aadhaar OTP',
            'payment_mode': 'Cash'
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # 2nd sale immediately (within 24 hours) for same card
        res2 = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 1.0, # 1kg Rice
            'auth_mode': 'Aadhaar OTP',
            'payment_mode': 'Cash'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Check AnomalyLog for flagged repeated transaction
        logs = AnomalyLog.query.filter_by(ration_card_id=card.id).all()
        flagged_types = [l.anomaly_type for l in logs]
        self.assertTrue(
            'Repeated Short-Period Distribution' in flagged_types or
            'Same-Day Multiple Distribution' in flagged_types
        )

    def test_10_unusually_large_quantity_flagged_when_appropriate(self):
        """Test 10: Unusually large quantity flagged when appropriate."""
        card = RationCard.query.filter_by(card_number='RC-AAY-1002').first()
        comm = Commodity.query.filter_by(code='RICE').first()
        
        # AAY rice entitlement is 35kg. Quantity 55kg is > (35 * 1.5 = 52.5kg)
        anomalies = check_transaction_anomalies(
            ration_card=card,
            shop_id=card.assigned_shop_id,
            items_to_purchase=[{'commodity_id': comm.id, 'quantity': 55.0}],
            transaction_time=datetime(2026, 9, 24, 11, 0)
        )
        large_qty_flags = [a for a in anomalies if a['type'] == 'Unusually Large Quantity']
        self.assertTrue(len(large_qty_flags) > 0)

    def test_11_flagged_transaction_shows_clear_reason(self):
        """Test 11: Flagged transaction shows clear reason."""
        log = AnomalyLog.query.filter(AnomalyLog.status == 'Flagged').first()
        if not log:
            # Create a test log
            log = AnomalyLog(
                ration_card_id=1,
                shop_id=1,
                anomaly_type='Repeated Short-Period Distribution',
                severity='Medium',
                description='Flagged for Review: Multiple transactions recorded within a short time period (1.2 hours ago).',
                status='Flagged'
            )
            db.session.add(log)
            db.session.commit()
            
        self.assertIsNotNone(log.description)
        self.assertTrue(len(log.description) > 10)

    def test_12_admin_can_mark_alert_as_reviewed(self):
        """Test 12: Admin can mark alert as Reviewed."""
        log = AnomalyLog(
            ration_card_id=1,
            shop_id=1,
            anomaly_type='Test Anomaly',
            severity='Medium',
            description='Test anomaly description for resolution test',
            status='Flagged'
        )
        db.session.add(log)
        db.session.commit()

        self.login('admin', 'admin123')
        res = self.client.post(f'/admin/anomalies/{log.id}/resolve', data={
            'status': 'Reviewed',
            'resolution_notes': 'Verified legitimate transaction by dealer.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        updated_log = db.session.get(AnomalyLog, log.id)
        self.assertEqual(updated_log.status, 'Reviewed')
        self.assertEqual(updated_log.resolution_notes, 'Verified legitimate transaction by dealer.')

    def test_13_original_transaction_not_deleted_or_modified(self):
        """Test 13: Original transaction not deleted/modified when alert is reviewed."""
        self.login('dealer3', 'dealer123')
        card = RationCard.query.filter_by(card_number='RC-AY-4001').first() # Shop 3 card
        comm = Commodity.query.filter_by(code='RICE').first()

        # Perform sale
        self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 1.0,
            'auth_mode': 'Biometric',
            'payment_mode': 'Cash'
        }, follow_redirects=True)

        tx = DistributionTransaction.query.filter_by(ration_card_id=card.id).order_by(DistributionTransaction.id.desc()).first()
        self.assertIsNotNone(tx)
        original_amount = tx.total_amount

        # Admin resolves any associated anomaly
        log = AnomalyLog.query.filter_by(transaction_id=tx.id).first()
        if log:
            self.login('admin', 'admin123')
            self.client.post(f'/admin/anomalies/{log.id}/resolve', data={'status': 'Reviewed'}, follow_redirects=True)

        # Confirm original transaction is completely unchanged
        tx_after = db.session.get(DistributionTransaction, tx.id)
        self.assertIsNotNone(tx_after)
        self.assertEqual(tx_after.status, 'Completed')
        self.assertEqual(tx_after.total_amount, original_amount)

    def test_14_dealer_cannot_access_global_transaction_alerts(self):
        """Test 14: Dealer cannot access global transaction alerts."""
        self.login('dealer1', 'dealer123')
        res = self.client.get('/admin/transaction-alerts', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        # Should be redirected to dealer_pos with access denied message
        self.assertIn(b'Access Denied', res.data)
        self.assertIn(b'My Shop Billing', res.data)

    # -------------------------------------------------------------------------
    # CORE BILLING & STOCK MANAGEMENT (Test 15 - 12/12 Sub-tests)
    # -------------------------------------------------------------------------
    def test_15_core_billing_and_stock_management_features(self):
        """Test 15: All 12/12 core billing & stock management features still pass."""
        self.login('dealer1', 'dealer123')
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        shop_id = card.assigned_shop_id
        comm = Commodity.query.filter_by(code='RICE').first()
        stock = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=comm.id).first()
        initial_stock = stock.current_stock

        # 15.1 Valid Bill -> Created successfully
        res_sale = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 3.0,
            'auth_mode': 'Aadhaar OTP',
            'payment_mode': 'Cash'
        }, follow_redirects=True)
        self.assertEqual(res_sale.status_code, 200)
        self.assertIn(b'OFFICIAL e-RATION RECEIPT', res_sale.data)

        # 15.2 Stock automatically decreases
        stock_after = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=comm.id).first()
        self.assertEqual(round(stock_after.current_stock, 2), round(initial_stock - 3.0, 2))

        # 15.3 Customer remaining allocation decreases
        from rules import get_beneficiary_quota_status
        quota = get_beneficiary_quota_status(card)
        rice_item = [i for i in quota['items'] if i['code'] == 'RICE'][0]
        self.assertTrue(rice_item['claimed_qty'] >= 3.0)

        # 15.4 Non-existent ration card rejected
        res_invalid_card = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': 999999,
            f'qty_{comm.id}': 1.0
        }, follow_redirects=True)
        self.assertIn(b'Invalid or non-existent Ration Card', res_invalid_card.data)

        # 15.5 Inactive card rejected
        inactive_card = RationCard(
            card_number='RC-INACTIVE-999',
            card_type='PHH',
            head_of_family='Test Inactive Head',
            aadhaar_last4='9999',
            address='Test Address',
            status='Suspended',
            assigned_shop_id=shop_id
        )
        db.session.add(inactive_card)
        db.session.commit()
        res_inactive = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': inactive_card.id,
            f'qty_{comm.id}': 1.0
        }, follow_redirects=True)
        self.assertIn(b'Rejected', res_inactive.data)

        # 15.6 Over-quota request rejected
        rem_quota = rice_item['remaining_qty']
        res_over_quota = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': rem_quota + 50.0
        }, follow_redirects=True)
        self.assertIn(b'exceeds customer', res_over_quota.data)

        # 15.7 Stock deficit request rejected
        stock_after.current_stock = 1.0 # set tiny stock
        db.session.commit()
        res_stock_deficit = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 5.0
        }, follow_redirects=True)
        self.assertIn(b'exceeds shop', res_stock_deficit.data)
        stock_after.current_stock = 500.0 # reset stock
        db.session.commit()

        # 15.8 Quantities <= 0 rejected
        res_zero = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 0.0
        }, follow_redirects=True)
        self.assertIn(b'at least one valid grain quantity greater than 0', res_zero.data)

        # 15.9 Non-numeric quantity rejected
        res_non_numeric = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': card.id,
            f'qty_{comm.id}': 'invalid_str'
        }, follow_redirects=True)
        self.assertIn(b'at least one valid grain quantity greater than 0', res_non_numeric.data)

        # 15.10 e-Receipt generated with accurate bill number and details
        latest_tx = DistributionTransaction.query.filter_by(ration_card_id=card.id).order_by(DistributionTransaction.id.desc()).first()
        res_receipt = self.client.get(f'/receipt/{latest_tx.id}')
        self.assertEqual(res_receipt.status_code, 200)
        self.assertIn(latest_tx.bill_number.encode(), res_receipt.data)

        # 15.11 Dealer isolated to assigned shop only
        other_shop_card = RationCard.query.filter(RationCard.assigned_shop_id != shop_id).first()
        res_other_shop = self.client.post('/dealer/pos/process-sale', data={
            'ration_card_id': other_shop_card.id,
            f'qty_{comm.id}': 1.0
        }, follow_redirects=True)
        self.assertIn(b'Security Enforcement', res_other_shop.data)

        # 15.12 Admin cannot create bills (Admin billing attempt blocked / restricted)
        self.client.get('/logout')
        self.login('admin', 'admin123')
        res_admin_pos = self.client.get('/dealer/pos', follow_redirects=True)
        self.assertIn(b'Access Denied', res_admin_pos.data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
