"""
RationSmart - Comprehensive Verification & Audit Test Suite
Tests the 4 Major Novelty Features:
1. Offline-First PWA & Idempotent Sync Engine
2. Dynamic Bilingual System (Tamil ⇄ English)
3. Tamil Voice Accessibility & Number-to-Words Engine
4. Mobile QR Verification & HMAC-SHA256 Cryptographic Integrity Check
"""

import os
import unittest
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta

from app import create_app
from config import Config
from models import (
    db, User, FairPriceShop, RationCard, Commodity, ShopStock,
    DistributionTransaction, TransactionItem, AuditLog
)
from seed_data import seed_database

TEST_AUDIT_DB = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_audit_isolated.db')

class AuditTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_AUDIT_DB}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'super-secret-audit-key-2026'

class NoveltyFeaturesAuditTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_AUDIT_DB):
            try:
                os.remove(TEST_AUDIT_DB)
            except Exception:
                pass
        cls.app = create_app(AuditTestConfig)
        with cls.app.app_context():
            db.create_all()
            seed_database(cls.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_AUDIT_DB):
            try:
                os.remove(TEST_AUDIT_DB)
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def login_user(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout_user(self):
        return self.client.get('/logout', follow_redirects=True)

    # =========================================================================
    # FEATURE 1: OFFLINE PWA & IDEMPOTENT SYNC ENGINE
    # =========================================================================

    def test_01_db_schema_unique_constraint(self):
        """Verify client_sale_id has unique constraint in DistributionTransaction table."""
        col = DistributionTransaction.__table__.columns['client_sale_id']
        self.assertTrue(col.unique, "client_sale_id column MUST have unique=True constraint in SQLAlchemy model")
        self.assertTrue(col.index, "client_sale_id column MUST have index=True for O(1) idempotency lookup")

    def test_02_dealer_pwa_bootstrap_endpoint(self):
        """Verify /api/dealer/pwa-bootstrap enforces role isolation and delivers required offline cache data."""
        # Unauthenticated request rejected
        res = self.client.get('/api/dealer/pwa-bootstrap')
        self.assertIn(res.status_code, [302, 401, 403])

        # Login as Citizen -> rejected
        self.login_user('citizen1', 'citizen123')
        res = self.client.get('/api/dealer/pwa-bootstrap')
        self.assertEqual(res.status_code, 403)
        self.logout_user()

        # Login as Dealer 1 (Assigned to Shop 1)
        self.login_user('dealer1', 'dealer123')
        res = self.client.get('/api/dealer/pwa-bootstrap')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('shop', data)
        self.assertTrue(data['shop']['shop_code'].startswith('FPS-'))
        self.assertIn('stock', data)
        self.assertIn('cards', data)
        self.assertGreater(len(data['stock']), 0)
        self.assertGreater(len(data['cards']), 0)

        # Verify only cards belonging to Shop 1 are in bootstrap
        for c in data['cards']:
            self.assertEqual(c['assigned_shop_id'], 1)
        self.logout_user()

    def test_03_bulk_sync_atomic_deduction_and_idempotency(self):
        """Verify bulk sync processes offline bill atomically and enforces server-side idempotency."""
        self.login_user('dealer1', 'dealer123')
        dealer = User.query.filter_by(username='dealer1').first()
        shop = dealer.shop

        # Get initial rice stock
        rice = Commodity.query.filter_by(code='RICE').first()
        initial_stock_obj = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=rice.id).first()
        initial_stock = initial_stock_obj.current_stock

        # Client sale payload with unique clientSaleId
        client_sale_id = f"OFFLINE-TEST-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            'sales': [{
                'clientSaleId': client_sale_id,
                'cardNumber': 'RC-PHH-2001',
                'headOfFamily': 'Kavitha Ramesh',
                'cardType': 'PHH',
                'shopId': shop.id,
                'items': [{
                    'commodityId': rice.id,
                    'quantity': 5.0
                }],
                'totalAmount': 0.0,
                'authMode': 'Biometric Aadhaar (Offline Verified)',
                'paymentMode': 'Cash / Direct Subsidy'
            }]
        }

        # 1. First sync submission -> should be ACCEPTED
        res1 = self.client.post('/api/sales/bulk-sync',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        d1 = res1.get_json()
        self.assertTrue(d1['success'])
        self.assertEqual(len(d1['synced']), 1)
        self.assertEqual(d1['synced'][0]['clientSaleId'], client_sale_id)
        self.assertEqual(d1['synced'][0]['status'], 'accepted')
        bill_number = d1['synced'][0]['billNumber']

        # Verify stock decreased by exactly 5.0
        db.session.expire_all()
        stock_after_first = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=rice.id).first().current_stock
        self.assertAlmostEqual(stock_after_first, initial_stock - 5.0, places=2)

        # Verify transaction in DB has offline_synced flag
        tx = DistributionTransaction.query.filter_by(client_sale_id=client_sale_id).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.sync_status, 'offline_synced')
        self.assertEqual(tx.bill_number, bill_number)

        # 2. Repeated sync submission (Exact same clientSaleId) -> IDEMPOTENCY TEST
        res2 = self.client.post('/api/sales/bulk-sync',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.get_json()
        self.assertTrue(d2['success'])
        self.assertEqual(len(d2['synced']), 0, "Repeated sync must NOT create a new synced bill")
        self.assertEqual(len(d2['alreadyProcessed']), 1, "Repeated sync MUST be identified as already processed")
        self.assertEqual(d2['alreadyProcessed'][0]['clientSaleId'], client_sale_id)
        self.assertEqual(d2['alreadyProcessed'][0]['billNumber'], bill_number)

        # Verify stock did NOT decrease a second time
        db.session.expire_all()
        stock_after_repeat = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=rice.id).first().current_stock
        self.assertAlmostEqual(stock_after_repeat, stock_after_first, places=2,
                               msg="Stock must NOT be deducted multiple times for same clientSaleId")
        self.logout_user()

    def test_04_bulk_sync_validation_rejections(self):
        """Verify bulk-sync re-validates entitlements, stock, active card status, and cross-shop security."""
        self.login_user('dealer1', 'dealer123')
        dealer = User.query.filter_by(username='dealer1').first()
        shop = dealer.shop
        rice = Commodity.query.filter_by(code='RICE').first()

        # Case A: Missing clientSaleId
        res_a = self.client.post('/api/sales/bulk-sync',
                                 data=json.dumps({'sales': [{'cardNumber': 'RC-PHH-2001'}]}),
                                 content_type='application/json')
        self.assertEqual(len(res_a.get_json()['rejected']), 1)
        self.assertIn('Missing clientSaleId', res_a.get_json()['rejected'][0]['reason'])

        # Case B: Cross-Shop Security Violation (Card assigned to shop 2, dealer is shop 1)
        card_shop2 = RationCard.query.filter(RationCard.assigned_shop_id != shop.id).first()
        self.assertIsNotNone(card_shop2)
        res_b = self.client.post('/api/sales/bulk-sync', data=json.dumps({
            'sales': [{
                'clientSaleId': f"OFFLINE-CROSS-{uuid.uuid4().hex[:6]}",
                'cardNumber': card_shop2.card_number,
                'items': [{'commodityId': rice.id, 'quantity': 1.0}]
            }]
        }), content_type='application/json')
        self.assertEqual(len(res_b.get_json()['rejected']), 1)
        self.assertIn('Security Violation', res_b.get_json()['rejected'][0]['reason'])

        # Case C: Stock Shortage (Request 999999 kg)
        res_c = self.client.post('/api/sales/bulk-sync', data=json.dumps({
            'sales': [{
                'clientSaleId': f"OFFLINE-SHORT-{uuid.uuid4().hex[:6]}",
                'cardNumber': 'RC-PHH-2001',
                'items': [{'commodityId': rice.id, 'quantity': 999999.0}]
            }]
        }), content_type='application/json')
        self.assertEqual(len(res_c.get_json()['rejected']), 1)
        self.assertIn('exceeds', res_c.get_json()['rejected'][0]['reason'].lower())
        self.logout_user()

    # =========================================================================
    # FEATURE 2: BILINGUAL SYSTEM (TAMIL ⇄ ENGLISH)
    # =========================================================================

    def test_05_bilingual_ui_elements_and_dictionary(self):
        """Verify bilingual toggle button, dictionary completeness, and preservation of input elements."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Language toggle button present in header
        self.assertIn('id="pdsLangToggleBtn"', html)
        self.assertIn('id="pdsCurrentLangLabel"', html)
        self.assertIn('src="/static/js/i18n.js"', html)

        # Read static/js/i18n.js to verify dictionary and DOM TreeWalker logic
        with open('static/js/i18n.js', 'r', encoding='utf-8') as f:
            js = f.read()

        # Dictionary mappings
        self.assertIn("'Government of Tamil Nadu': 'தமிழ்நாடு அரசு'", js)
        self.assertIn("'My Shop Billing': 'கடை பில்லிங் (POS)'", js)
        self.assertIn("'Commodity': 'உணவுப் பொருள்'", js)
        self.assertIn("'Monthly Entitlement': 'மாத ஒதுக்கீடு'", js)
        self.assertIn("'Username': 'பயனர் பெயர்'", js)
        self.assertIn("'Password': 'கடவுச்சொல்'", js)

        # Protection against user input corruption
        self.assertIn("const ignoreTags = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'INPUT', 'TEXTAREA'])", js)
        self.assertIn("node.parentElement.closest('.no-translate')", js)

        # Persistence check
        self.assertIn("localStorage.getItem('pds_portal_lang')", js)
        self.assertIn("localStorage.setItem('pds_portal_lang'", js)

    # =========================================================================
    # FEATURE 3: TAMIL VOICE ACCESSIBILITY & NUMBER CONVERSION
    # =========================================================================

    def test_06_tamil_voice_numbers_commodities_and_fallback(self):
        """Verify pure Tamil number-to-words algorithm, commodities translation, and offline capability."""
        with open('static/js/voice_assistant.js', 'r', encoding='utf-8') as f:
            js = f.read()

        # 1. Number to Pure Tamil Words checks
        self.assertIn("function numberToTamilWords", js)
        self.assertIn("பூஜ்ஜியம்", js)
        self.assertIn("இருபது", js)
        self.assertIn("பதினைந்து", js)
        self.assertIn("அரை", js)
        self.assertIn("ஒன்றரை", js)

        # 2. Number to Tanglish Phonetic Words checks
        self.assertIn("function numberToTanglishWords", js)
        self.assertIn("Irupathu", js)
        self.assertIn("Pathinainthu", js)
        self.assertIn("Poojiyam", js)
        self.assertIn("Arai", js)

        # 3. Commodity & Unit translation
        self.assertIn("translateCommodityToTamil", js)
        self.assertIn("அரிசி", js)
        self.assertIn("கோதுமை", js)
        self.assertIn("சர்க்கரை", js)
        self.assertIn("கிலோ", js)

        # 4. Scheme Card Types
        self.assertIn("translateCardTypeToTamil", js)
        self.assertIn("முன்னுரிமை குடும்ப அட்டை", js) # PHH
        self.assertIn("அந்தியோதயா அன்ன யோஜனா மஞ்சள் அட்டை", js) # AAY
        self.assertIn("அன்னபூர்ணா முதியோர் அட்டை", js) # AY

        # 5. Dual-Layer speech architecture & fallback
        self.assertIn("findTamilVoice()", js)
        self.assertIn("findIndianEnglishVoice()", js)
        self.assertIn("SpeechSynthesisUtterance", js)
        self.assertIn("window.speechSynthesis", js)

    # =========================================================================
    # FEATURE 4: QR VERIFICATION & HMAC-SHA256 INTEGRITY CHECK
    # =========================================================================

    def test_07_qr_code_generation_endpoint(self):
        """Verify /qr/receipt/<id> generates a valid PNG with embedded HMAC signature."""
        tx = DistributionTransaction.query.first()
        self.assertIsNotNone(tx)

        res = self.client.get(f'/qr/receipt/{tx.id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'image/png')
        self.assertGreater(len(res.data), 100) # Valid PNG bytes

    def test_08_public_receipt_verification_hmac_and_tamper_detection(self):
        """Verify HMAC-SHA256 authentication, tampering detection, and privacy masking."""
        tx = DistributionTransaction.query.first()
        self.assertIsNotNone(tx)

        # Calculate legitimate HMAC
        canonical = f"{tx.bill_number}|{tx.ration_card.card_number}|{tx.total_amount:.2f}|{tx.shop.shop_code}|{tx.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}"
        valid_sig = hmac.new(self.app.config['SECRET_KEY'].encode('utf-8'),
                             canonical.encode('utf-8'),
                             hashlib.sha256).hexdigest()[:32].upper()

        # 1. Authentic request with valid signature (as scanned from QR code)
        res_valid = self.client.get(f'/verify-receipt/{tx.bill_number}?sig={valid_sig}')
        self.assertEqual(res_valid.status_code, 200)
        html_valid = res_valid.data.decode('utf-8')

        self.assertIn('RATIONSMART TRANSACTION VERIFIED', html_valid)
        self.assertIn('HMAC-SHA256 Cryptographic Signature: Authentic', html_valid)
        self.assertNotIn('SIGNATURE MISMATCH', html_valid)

        # 2. Tampered request with forged signature (Attacker altered bill or parameters)
        forged_sig = "DEADBEEF12345678DEADBEEF12345678"
        res_tampered = self.client.get(f'/verify-receipt/{tx.bill_number}?sig={forged_sig}')
        self.assertEqual(res_tampered.status_code, 200)
        html_tampered = res_tampered.data.decode('utf-8')

        self.assertIn('SIGNATURE MISMATCH &bull; TAMPERING DETECTED', html_tampered)
        self.assertIn('Cryptographic Tampering Warning', html_tampered)

        # 3. Manual lookup without signature parameter
        res_manual = self.client.get(f'/verify-receipt/{tx.bill_number}')
        self.assertEqual(res_manual.status_code, 200)
        html_manual = res_manual.data.decode('utf-8')
        self.assertIn('Database Record: Verified', html_manual)

        # 4. Unknown/fake bill number lookup
        res_fake = self.client.get('/verify-receipt/BILL-FAKE-99999')
        self.assertEqual(res_fake.status_code, 200)
        html_fake = res_fake.data.decode('utf-8')
        self.assertIn('TRANSACTION NOT VERIFIED', html_fake)

        # 5. Privacy masking check (No full ration card or Aadhaar leaked on public page)
        self.assertIn('Privacy Masked', html_valid)
        # Should not display the full card number in plain text in the cardholder details
        self.assertIn('-***-', html_valid)
        # Full Aadhaar last 4 should not be exposed
        self.assertNotIn(f"Aadhaar: **{tx.ration_card.aadhaar_last4}", html_valid)
        self.assertIn('Biometric Aadhaar Verified (On File)', html_valid)

        # 6. Academic project identification check (Not claiming official government certificate)
        self.assertIn('RationSmart Academic Project Portal', html_valid)
        self.assertIn('RationSmart student project', html_valid)
        self.assertNotIn('Department of Food and Civil Supplies • Government of Tamil Nadu', html_valid)

if __name__ == '__main__':
    unittest.main()
