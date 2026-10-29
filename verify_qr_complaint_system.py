"""
Comprehensive Verification Test Suite for QR Code-Based Complaint Management System
Tests all 12 key requirements on an isolated test database.
"""

import os
import io
import unittest
from datetime import datetime, timedelta
from PIL import Image

# Use isolated test database
os.environ['DATABASE_URL'] = 'sqlite:///test_complaint_system.db'
os.environ['SECRET_KEY'] = 'test-secret-key-123'

from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_complaint_system.db'
    WTF_CSRF_ENABLED = False

from app import create_app
from models import (
    db, User, FairPriceShop, Commodity, RationCard, FamilyMember,
    Grievance, ComplaintAuditLog
)
from seed_data import seed_database


class QRComplaintSystemTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Remove old test DB if exists
        if os.path.exists('test_complaint_system.db'):
            try:
                os.remove('test_complaint_system.db')
            except Exception:
                pass

        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()
            seed_database(cls.app)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists('test_complaint_system.db'):
            try:
                os.remove('test_complaint_system.db')
            except Exception:
                pass

    def login(self, username, password, role='customer'):
        return self.client.post('/login', data={
            'username': username,
            'password': password,
            'role': role
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # -------------------------------------------------------------------------
    # Test 1: QR Code Generation & Correct Shop Mapping
    # -------------------------------------------------------------------------
    def test_01_qr_code_generation_and_shop_mapping(self):
        with self.app.app_context():
            shop = FairPriceShop.query.first()
            self.assertIsNotNone(shop)
            shop_id = shop.id
            shop_code = shop.shop_code

        # Request QR code
        res = self.client.get(f'/qr/shop/{shop_id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'image/png')
        self.assertGreater(len(res.data), 100)

        # Verify QR image is valid PNG
        img = Image.open(io.BytesIO(res.data))
        self.assertEqual(img.format, 'PNG')

        # Download version
        res_dl = self.client.get(f'/qr/shop/{shop_id}?download=1')
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn('attachment', res_dl.headers.get('Content-Disposition', ''))

        # Non-existent shop returns 404
        res_404 = self.client.get('/qr/shop/999999')
        self.assertEqual(res_404.status_code, 404)

    # -------------------------------------------------------------------------
    # Test 2: Valid Complaint Submission with Dynamic Reference Code
    # -------------------------------------------------------------------------
    def test_02_valid_complaint_submission(self):
        # Login as customer RC-AAY-1001 (Shop 1)
        res_login = self.login('RC-AAY-1001', 'citizen123', role='customer')
        self.assertIn(b'Welcome back', res_login.data)

        with self.app.app_context():
            card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
            self.assertIsNotNone(card)
            shop = card.assigned_shop
            self.assertIsNotNone(shop)
            comm = Commodity.query.first()

        # Submit complaint
        payload = {
            'shop_id': str(shop.id),
            'category': 'Grain/product quality',
            'commodity_id': str(comm.id),
            'subject': 'Poor quality rice with excessive husk',
            'description': 'The rice supplied during October collection contained significant grit, stones, and black particles.'
        }
        res = self.client.post('/complaints/raise', data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Complaint registered successfully', res.data)
        self.assertIn(b'CMP-', res.data)

        # Verify in database
        with self.app.app_context():
            cmp = Grievance.query.filter_by(subject='Poor quality rice with excessive husk').first()
            self.assertIsNotNone(cmp)
            self.assertTrue(cmp.grievance_code.startswith('CMP-'))
            self.assertEqual(cmp.ration_card_number, 'RC-AAY-1001')
            self.assertEqual(cmp.status, 'Pending')
            self.assertEqual(cmp.category, 'Grain/product quality')
            self.assertEqual(cmp.shop_id, shop.id)
            self.assertEqual(cmp.commodity_id, comm.id)

            # Verify initial audit trail
            audit = ComplaintAuditLog.query.filter_by(complaint_id=cmp.id).first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.new_status, 'Pending')

        self.logout()

    # -------------------------------------------------------------------------
    # Test 3: Invalid Form Submission Validation
    # -------------------------------------------------------------------------
    def test_03_invalid_complaint_submission(self):
        self.login('RC-AAY-1001', 'citizen123', role='customer')

        with self.app.app_context():
            shop = FairPriceShop.query.first()

        # Case A: Invalid Category
        res = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Bogus Fake Category',
            'subject': 'Valid subject here',
            'description': 'Valid description with sufficient characters.'
        }, follow_redirects=True)
        self.assertIn(b'Invalid complaint category selected', res.data)

        # Case B: Too Short Subject (< 5 chars)
        res = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Other',
            'subject': 'Bad',
            'description': 'Valid description with sufficient characters.'
        }, follow_redirects=True)
        self.assertIn(b'Complaint subject must be between 5 and 150 characters', res.data)

        # Case C: Too Short Description (< 10 chars)
        res = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Other',
            'subject': 'Valid subject here',
            'description': 'Too short'
        }, follow_redirects=True)
        self.assertIn(b'Detailed description must be between 10 and 2000 characters', res.data)

        # Case D: Non-existent shop
        res = self.client.post('/complaints/raise', data={
            'shop_id': '88888',
            'category': 'Other',
            'subject': 'Valid subject here',
            'description': 'Valid description with sufficient characters.'
        }, follow_redirects=True)
        self.assertIn(b'Please select a valid Fair Price Shop', res.data)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 4: Complaint Appears in Admin Dashboard & Filterable
    # -------------------------------------------------------------------------
    def test_04_admin_dashboard_visibility_and_filters(self):
        # Login as admin
        self.login('admin', 'admin123', role='admin')

        res = self.client.get('/admin/complaints')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'PDS Grievance Redressal Center', res.data)
        self.assertIn(b'Poor quality rice with excessive husk', res.data)
        self.assertIn(b'RC-AAY-1001', res.data)

        # Test filter by status
        res_filter = self.client.get('/admin/complaints?status=Pending')
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn(b'Poor quality rice with excessive husk', res_filter.data)

        # Test filter by category
        res_cat = self.client.get('/admin/complaints?category=Grain/product+quality')
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b'Poor quality rice with excessive husk', res_cat.data)

        # Alias /admin/grievances works
        res_alias = self.client.get('/admin/grievances')
        self.assertEqual(res_alias.status_code, 200)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 5: Complaint Appears Only for Assigned Dealer
    # -------------------------------------------------------------------------
    def test_05_complaint_assigned_dealer_visibility(self):
        # Dealer 1 is linked to Shop 1
        self.login('dealer1', 'dealer123', role='dealer')

        res = self.client.get('/dealer/complaints')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Shop Complaints', res.data)
        # Should see the complaint created for Shop 1
        self.assertIn(b'Poor quality rice with excessive husk', res.data)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 6: Cross-Shop Isolation / IDOR Protection for Dealers
    # -------------------------------------------------------------------------
    def test_06_dealer_cross_shop_idor_protection(self):
        # Create a complaint specifically against Shop 2
        with self.app.app_context():
            shop2 = FairPriceShop.query.filter_by(shop_code='FPS-102').first()
            self.assertIsNotNone(shop2)
            c2 = Grievance(
                grievance_code='CMP-TEST-SHOP2-01',
                ration_card_number='RC-AAY-1003',
                citizen_name='Basheer Ahmed',
                citizen_phone='9867112233',
                shop_id=shop2.id,
                category='Dealer behaviour',
                subject='Rude behaviour by dealer staff',
                description='Staff refused to provide receipt and used discourteous language.',
                status='Pending',
                created_at=datetime.utcnow()
            )
            db.session.add(c2)
            db.session.commit()
            c2_id = c2.id

        # Dealer 1 (Shop 1) logs in
        self.login('dealer1', 'dealer123', role='dealer')

        # Dealer 1's dashboard should NOT show Shop 2's complaint
        res = self.client.get('/dealer/complaints')
        self.assertNotIn(b'CMP-TEST-SHOP2-01', res.data)
        self.assertNotIn(b'Rude behaviour by dealer staff', res.data)

        # Dealer 1 tries to POST an update to Shop 2's complaint (IDOR attempt)
        res_hack = self.client.post(f'/dealer/complaints/{c2_id}/update', data={
            'status': 'Resolved',
            'response_text': 'Malicious attempt to close another shop complaint.'
        })
        # Backend MUST reject with 403 Forbidden
        self.assertEqual(res_hack.status_code, 403)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 7: Citizen Can View Only Their Own Complaints (Cross-Citizen Isolation)
    # -------------------------------------------------------------------------
    def test_07_citizen_cross_customer_isolation(self):
        # Customer 2 (RC-AAY-1003) logs in
        self.login('RC-AAY-1003', 'citizen123', role='customer')

        res = self.client.get('/citizen/dashboard')
        self.assertEqual(res.status_code, 200)
        # Should see their own complaint (CMP-TEST-SHOP2-01)
        self.assertIn(b'CMP-TEST-SHOP2-01', res.data)
        # Should NOT see Customer 1's complaint
        self.assertNotIn(b'Poor quality rice with excessive husk', res.data)

        # Customer 2 tries to access Customer 1's confirmation slip directly
        with self.app.app_context():
            c1 = Grievance.query.filter_by(subject='Poor quality rice with excessive husk').first()
            c1_code = c1.grievance_code
            c1_id = c1.id

        res_slip = self.client.get(f'/complaints/confirmation/{c1_code}')
        self.assertEqual(res_slip.status_code, 403)

        # Customer 2 tries to call JSON API for Customer 1's complaint
        res_json = self.client.get(f'/citizen/complaints/{c1_id}')
        self.assertEqual(res_json.status_code, 403)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 8: Unauthenticated & Unauthorized Requests Rejected Appropriately
    # -------------------------------------------------------------------------
    def test_08_unauthenticated_and_unauthorized_rejections(self):
        # Ensure logged out
        self.logout()

        # Unauthenticated user visiting /complaints/raise redirects to login
        res = self.client.get('/complaints/raise')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Unauthenticated user attempting to post a complaint redirects to login
        res_post = self.client.post('/complaints/raise', data={
            'category': 'Other',
            'subject': 'Unauthorized submit',
            'description': 'Should be rejected without login.'
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertIn('/login', res_post.headers['Location'])

        # Unauthenticated user attempting to view dealer complaints redirects to login
        res_dealer = self.client.get('/dealer/complaints')
        self.assertEqual(res_dealer.status_code, 302)
        self.assertIn('/login', res_dealer.headers['Location'])

        # Unauthenticated user attempting to view admin grievances redirects to login
        res_admin = self.client.get('/admin/grievances')
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn('/login', res_admin.headers['Location'])

        # Citizen attempting to view /admin/grievances gets redirected with Access Denied
        self.login('RC-AAY-1001', 'citizen123', role='customer')
        res_denied = self.client.get('/admin/grievances', follow_redirects=True)
        self.assertIn(b'Access Denied', res_denied.data)
        self.logout()

    # -------------------------------------------------------------------------
    # Test 9: Valid and Invalid Status Transitions
    # -------------------------------------------------------------------------
    def test_09_status_transitions_and_rules(self):
        with self.app.app_context():
            cmp = Grievance.query.filter_by(subject='Poor quality rice with excessive husk').first()
            self.assertIsNotNone(cmp)
            c_id = cmp.id

        # Dealer 1 logs in
        self.login('dealer1', 'dealer123', role='dealer')

        # Dealer tries to reject a complaint (Dealer cannot reject; only In Progress or Resolved)
        res_bad_status = self.client.post(f'/dealer/complaints/{c_id}/update', data={
            'status': 'Rejected',
            'response_text': 'I reject this.'
        }, follow_redirects=True)
        self.assertIn(b'Invalid status change', res_bad_status.data)

        # Dealer validly transitions Pending -> In Progress
        res_valid = self.client.post(f'/dealer/complaints/{c_id}/update', data={
            'status': 'In Progress',
            'response_text': 'Initiating warehouse grain batch verification.'
        }, follow_redirects=True)
        self.assertEqual(res_valid.status_code, 200)

        with self.app.app_context():
            updated = db.session.get(Grievance, c_id)
            self.assertEqual(updated.status, 'In Progress')

        # Dealer tries to resolve without remarks (should be rejected)
        res_no_rem = self.client.post(f'/dealer/complaints/{c_id}/update', data={
            'status': 'Resolved',
            'response_text': '   '
        }, follow_redirects=True)
        self.assertIn(b'Resolution remarks are required', res_no_rem.data)

        # Dealer resolves with remarks
        res_res = self.client.post(f'/dealer/complaints/{c_id}/update', data={
            'status': 'Resolved',
            'response_text': 'Grain bag replaced with grade-A certified rice. Beneficiary verified satisfaction.'
        }, follow_redirects=True)
        self.assertEqual(res_res.status_code, 200)

        with self.app.app_context():
            updated = db.session.get(Grievance, c_id)
            self.assertEqual(updated.status, 'Resolved')
            self.assertIsNotNone(updated.resolved_at)

        # Dealer tries to modify already resolved complaint -> forbidden
        res_remod = self.client.post(f'/dealer/complaints/{c_id}/update', data={
            'status': 'In Progress',
            'response_text': 'Re-opening attempt.'
        }, follow_redirects=True)
        self.assertIn(b'already been concluded', res_remod.data)

        self.logout()

    # -------------------------------------------------------------------------
    # Test 10: Resolution Remarks and Audit Trail Log
    # -------------------------------------------------------------------------
    def test_10_audit_trail_and_resolution_remarks(self):
        with self.app.app_context():
            cmp = Grievance.query.filter_by(subject='Poor quality rice with excessive husk').first()
            self.assertIsNotNone(cmp)
            logs = ComplaintAuditLog.query.filter_by(complaint_id=cmp.id).order_by(ComplaintAuditLog.created_at.asc()).all()

            # Should have at least 3 audit entries:
            # 1. Initial citizen registration (Pending)
            # 2. Dealer set to In Progress
            # 3. Dealer set to Resolved
            self.assertGreaterEqual(len(logs), 3)

            # Initial
            self.assertEqual(logs[0].new_status, 'Pending')
            # Middle
            self.assertEqual(logs[1].old_status, 'Pending')
            self.assertEqual(logs[1].new_status, 'In Progress')
            self.assertIn('warehouse', logs[1].remarks)
            # Concluded
            self.assertEqual(logs[2].old_status, 'In Progress')
            self.assertEqual(logs[2].new_status, 'Resolved')
            self.assertIn('grade-A certified rice', logs[2].remarks)

    # -------------------------------------------------------------------------
    # Test 11: Invalid or Oversized Attachment Rejection
    # -------------------------------------------------------------------------
    def test_11_attachment_validation_and_security(self):
        self.login('RC-AAY-1001', 'citizen123', role='customer')

        with self.app.app_context():
            shop = FairPriceShop.query.first()

        # Case A: Invalid extension (.exe)
        fake_exe = (io.BytesIO(b'MZ executable header content'), 'exploit.exe')
        res_exe = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Other',
            'subject': 'Malicious file upload attempt',
            'description': 'Attempting to upload executable payload.',
            'attachment': fake_exe
        }, follow_redirects=True)
        self.assertIn(b'Attachment must be an image file', res_exe.data)

        # Case B: Fake image (extension .png but invalid byte content)
        fake_img = (io.BytesIO(b'NOT A REAL PNG FILE'), 'fake.png')
        res_fake = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Other',
            'subject': 'Corrupted image upload attempt',
            'description': 'Attempting to upload invalid image data.',
            'attachment': fake_img
        }, follow_redirects=True)
        self.assertIn(b'Uploaded file is not a valid image', res_fake.data)

        # Case C: Oversized image (> 3MB)
        oversized_data = (io.BytesIO(b'A' * (3 * 1024 * 1024 + 1024)), 'huge.png')
        res_over = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Other',
            'subject': 'Oversized file upload attempt',
            'description': 'Attempting to upload file larger than limit.',
            'attachment': oversized_data
        }, follow_redirects=True)
        self.assertIn(b'Attachment file size must not exceed 3 MB', res_over.data)

        # Case D: Valid image upload (.png)
        img_buffer = io.BytesIO()
        valid_pil_img = Image.new('RGB', (100, 100), color='green')
        valid_pil_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        res_valid_img = self.client.post('/complaints/raise', data={
            'shop_id': str(shop.id),
            'category': 'Stock unavailability',
            'subject': 'Wheat stock depleted in morning',
            'description': 'Arrived at 9am but told wheat is fully out of stock.',
            'attachment': (img_buffer, 'stock_notice.png')
        }, follow_redirects=True)
        self.assertIn(b'Complaint registered successfully', res_valid_img.data)

        with self.app.app_context():
            cmp_img = Grievance.query.filter_by(subject='Wheat stock depleted in morning').first()
            self.assertIsNotNone(cmp_img)
            self.assertIsNotNone(cmp_img.attachment_path)
            cmp_img_id = cmp_img.id

        # Verify secure attachment serving:
        # Customer 1 who uploaded it CAN view it:
        res_att = self.client.get(f'/complaints/attachment/{cmp_img_id}')
        self.assertEqual(res_att.status_code, 200)

        self.logout()

        # Customer 2 CANNOT view Customer 1's attachment:
        self.login('RC-AAY-1003', 'citizen123', role='customer')
        res_att_idor = self.client.get(f'/complaints/attachment/{cmp_img_id}')
        self.assertEqual(res_att_idor.status_code, 403)
        self.logout()

    # -------------------------------------------------------------------------
    # Test 12: Admin Remains Unable to Create Bills
    # -------------------------------------------------------------------------
    def test_12_admin_cannot_create_bills(self):
        self.login('admin', 'admin123', role='admin')

        # Admin attempting to access dealer POS
        res_pos = self.client.get('/dealer/pos', follow_redirects=True)
        self.assertIn(b'Access Denied', res_pos.data)

        # Admin attempting to create a bill
        res_bill = self.client.post('/dealer/pos', data={
            'card_id': '1',
            'items': '[]'
        }, follow_redirects=True)
        self.assertIn(b'Access Denied', res_bill.data)

        self.logout()


if __name__ == '__main__':
    unittest.main()
