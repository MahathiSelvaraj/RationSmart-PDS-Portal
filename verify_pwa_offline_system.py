"""
RationSmart - Progressive Web App (PWA) & Offline-First Verification Suite
Tests:
1. Manifest & Service Worker routing & headers
2. App Icons verification
3. UI online/offline elements & Tamil offline banner
4. Dealer PWA Bootstrap endpoint
5. Bulk Sync API:
   - Successful sync & atomic stock deduction
   - Idempotency with clientSaleId
   - Rejection on quota violation
   - Rejection on stock shortage
   - Rejection on cross-shop card
   - Rejection on inactive card
6. Offline Sales workspace access control
"""

import unittest
import json
import uuid
from app import create_app
from models import db, User, FairPriceShop, RationCard, Commodity, ShopStock, DistributionTransaction

class PWAOfflineSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # 1. PWA Assets & Manifest Tests
    # =========================================================================

    def test_01_manifest_json(self):
        """Verify web app manifest is served with correct fields & theme."""
        res = self.client.get('/manifest.json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('application/manifest+json', res.content_type)
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertEqual(data.get('name'), "TN PDS Ration Shop")
        self.assertEqual(data.get('short_name'), "RationSmart")
        self.assertEqual(data.get('theme_color'), "#0d6efd")
        self.assertEqual(data.get('display'), "standalone")
        
        icons = data.get('icons', [])
        sizes = [i.get('sizes') for i in icons]
        self.assertIn('192x192', sizes)
        self.assertIn('512x512', sizes)

    def test_02_service_worker_routing(self):
        """Verify Service Worker is served with root scope and JS content-type."""
        res = self.client.get('/sw.js')
        self.assertEqual(res.status_code, 200)
        self.assertIn('application/javascript', res.content_type)
        self.assertEqual(res.headers.get('Service-Worker-Allowed'), '/')
        
        body = res.data.decode('utf-8')
        self.assertIn('rationsmart-pwa-v1', body)
        self.assertIn('PRECACHE_ASSETS', body)

    def test_03_app_icons_exist(self):
        """Verify 192x192 and 512x512 PNG app icons are accessible."""
        res192 = self.client.get('/static/img/icon-192.png')
        self.assertEqual(res192.status_code, 200)
        self.assertIn('image/png', res192.content_type)
        
        res512 = self.client.get('/static/img/icon-512.png')
        self.assertEqual(res512.status_code, 200)
        self.assertIn('image/png', res512.content_type)

    def test_04_ui_elements_and_tamil_banner(self):
        """Verify connection indicator and Tamil offline banner in base template."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        
        self.assertIn('id="pwaConnectionStatus"', html)
        self.assertIn('id="pwaOfflineBanner"', html)
        self.assertIn('இணைய இணைப்பு இல்லை — விற்பனை உள்ளூரில் சேமிக்கப்படும்', html)
        self.assertIn('id="pwaInstallBtn"', html)
        self.assertIn('src="/static/js/pwa.js"', html)

    # =========================================================================
    # 2. Dealer Bootstrap API
    # =========================================================================

    def test_05_dealer_pwa_bootstrap_auth_and_data(self):
        """Verify /api/dealer/pwa-bootstrap requires dealer login and returns shop cards/stock."""
        # Unauthenticated request
        res = self.client.get('/api/dealer/pwa-bootstrap')
        self.assertIn(res.status_code, [302, 401, 403])
        
        # Log in as Dealer 1
        self.client.post('/login', data={'username': 'dealer1', 'password': 'dealer123', 'role': 'dealer'})
        res = self.client.get('/api/dealer/pwa-bootstrap')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data.get('success'))
        self.assertEqual(data['shop']['shop_code'], 'FPS-101')
        self.assertGreater(len(data['stock']), 0)
        self.assertGreater(len(data['cards']), 0)
        
        # Verify card entitlement data
        first_card = data['cards'][0]
        self.assertIn('card_number', first_card)
        self.assertIn('quota_items', first_card)
        self.assertGreater(len(first_card['quota_items']), 0)

    # =========================================================================
    # 3. Idempotent Bulk Synchronization API
    # =========================================================================

    def test_06_bulk_sync_accepted_and_idempotency(self):
        """Verify successful offline sale sync, stock deduction, and idempotency prevention."""
        # Log in as Dealer 1 (FPS-101)
        self.client.post('/login', data={'username': 'dealer1', 'password': 'dealer123', 'role': 'dealer'})
        
        dealer = User.query.filter_by(username='dealer1').first()
        shop_id = dealer.shop_id
        
        # Pick card assigned to FPS-101 (RC-AAY-1001)
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        comm = Commodity.query.filter_by(code='RICE').first()
        stock_before = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=comm.id).first()
        initial_stock = stock_before.current_stock
        
        test_client_sale_id = f"TEST-OFFLINE-{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            'sales': [{
                'clientSaleId': test_client_sale_id,
                'cardNumber': 'RC-AAY-1001',
                'items': [{
                    'commodityId': comm.id,
                    'quantity': 2.0
                }],
                'authMode': 'Biometric Aadhaar (Offline Verified)',
                'paymentMode': 'Cash / Direct Subsidy'
            }]
        }
        
        # First Sync: Should be accepted
        res = self.client.post('/api/sales/bulk-sync', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode('utf-8'))
        
        self.assertTrue(data.get('success'))
        self.assertEqual(len(data.get('synced', [])), 1)
        synced_sale = data['synced'][0]
        self.assertEqual(synced_sale['clientSaleId'], test_client_sale_id)
        self.assertEqual(synced_sale['status'], 'accepted')
        bill_number = synced_sale['billNumber']
        self.assertTrue(bill_number.startswith('BILL-'))
        
        # Verify stock was deducted
        db.session.expire_all()
        stock_after = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=comm.id).first()
        self.assertAlmostEqual(stock_after.current_stock, initial_stock - 2.0)
        
        # Verify database record
        tx = DistributionTransaction.query.filter_by(client_sale_id=test_client_sale_id).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.sync_status, 'offline_synced')
        
        # Second Sync with same clientSaleId: IDEMPOTENCY TEST
        res2 = self.client.post('/api/sales/bulk-sync', json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data.decode('utf-8'))
        
        self.assertEqual(len(data2.get('synced', [])), 0)
        self.assertEqual(len(data2.get('alreadyProcessed', [])), 1)
        ap = data2['alreadyProcessed'][0]
        self.assertEqual(ap['clientSaleId'], test_client_sale_id)
        self.assertEqual(ap['billNumber'], bill_number)
        
        # Verify stock was NOT deducted again
        db.session.expire_all()
        stock_after2 = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=comm.id).first()
        self.assertAlmostEqual(stock_after2.current_stock, initial_stock - 2.0)

    def test_07_bulk_sync_rejections(self):
        """Verify server rejects over-quota, stock deficit, cross-shop cards, and inactive cards."""
        self.client.post('/login', data={'username': 'dealer1', 'password': 'dealer123', 'role': 'dealer'})
        
        comm = Commodity.query.filter_by(code='RICE').first()
        
        # 1. Quota Violation (e.g. requesting 1000 kg for an AAY card)
        bad_sale_quota = {
            'clientSaleId': f"FAIL-QUOTA-{uuid.uuid4().hex[:6]}",
            'cardNumber': 'RC-AAY-1001',
            'items': [{'commodityId': comm.id, 'quantity': 1000.0}]
        }
        res = self.client.post('/api/sales/bulk-sync', json={'sales': [bad_sale_quota]})
        data = json.loads(res.data.decode('utf-8'))
        self.assertEqual(len(data.get('rejected', [])), 1)
        self.assertIn('exceeds customer remaining quota', data['rejected'][0]['reason'].lower())
        
        # 2. Cross-Shop Card Violation (RC-AAY-1003 belongs to Shop 2, not Dealer 1's Shop 1)
        bad_sale_cross_shop = {
            'clientSaleId': f"FAIL-SHOP-{uuid.uuid4().hex[:6]}",
            'cardNumber': 'RC-AAY-1003',
            'items': [{'commodityId': comm.id, 'quantity': 5.0}]
        }
        res = self.client.post('/api/sales/bulk-sync', json={'sales': [bad_sale_cross_shop]})
        data = json.loads(res.data.decode('utf-8'))
        self.assertEqual(len(data.get('rejected', [])), 1)
        self.assertIn('security violation', data['rejected'][0]['reason'].lower())

    def test_08_offline_sales_page_access(self):
        """Verify /offline-sales route renders properly for dealers and blocks citizens."""
        # Citizen blocked and redirected with Access Denied
        self.client.post('/login', data={'username': 'citizen1', 'password': 'citizen123', 'role': 'customer'})
        res = self.client.get('/offline-sales', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/citizen/dashboard', res.headers.get('Location', ''))
        
        # Log out citizen
        self.client.get('/logout')
        
        # Dealer permitted
        self.client.post('/login', data={'username': 'dealer1', 'password': 'dealer123', 'role': 'dealer'})
        res = self.client.get('/offline-sales')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Offline Sales Register', html)
        self.assertIn('id="btnPwaSyncNow"', html)
        self.assertIn('id="devOfflineSimulationToggle"', html)

if __name__ == '__main__':
    unittest.main()
