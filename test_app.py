"""
RationSmart - Automated Verification Test Suite
Tests authentication, Flask-Login, role redirections, family members, and database models.
"""

import os
import unittest
from datetime import datetime, timedelta
from app import create_app
from config import Config
from models import (
    db, User, FairPriceShop, RationShop, Commodity, RationCard, FamilyMember,
    GrainAllocation, ShopStock, DistributionTransaction, TransactionItem,
    AnomalyLog, Grievance
)
from rules import (
    get_monthly_entitlements, get_beneficiary_quota_status,
    estimate_stock_depletion, check_transaction_anomalies
)
from seed_data import seed_database

TEST_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_digital_ration.db')

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_PATH}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class RationSmartTestCase(unittest.TestCase):
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

    def test_01_user_roles_and_password_hashing(self):
        """Test User model, password hashing, and role helper methods."""
        admin = User.query.filter_by(username='admin').first()
        self.assertIsNotNone(admin)
        self.assertTrue(admin.check_password('admin123'))
        self.assertFalse(admin.check_password('wrongpass'))
        self.assertTrue(admin.is_admin())
        self.assertFalse(admin.is_dealer())
        self.assertFalse(admin.is_citizen())

        dealer = User.query.filter_by(username='dealer1').first()
        self.assertIsNotNone(dealer)
        self.assertTrue(dealer.check_password('dealer123'))
        self.assertTrue(dealer.is_dealer())

        citizen = User.query.filter_by(username='citizen1').first()
        self.assertIsNotNone(citizen)
        self.assertTrue(citizen.check_password('citizen123'))
        self.assertTrue(citizen.is_citizen())
        self.assertEqual(citizen.ration_card.card_number, 'RC-AAY-1001')

    def test_02_family_members_relationship(self):
        """Test family_members table and relationship with ration_cards."""
        card = RationCard.query.filter_by(card_number='RC-AAY-1001').first()
        self.assertIsNotNone(card)
        members = FamilyMember.query.filter_by(ration_card_id=card.id).all()
        self.assertEqual(len(members), 4)
        names = [m.full_name for m in members]
        self.assertIn('Munna Lal', names)
        self.assertIn('Shanti Devi', names)
        self.assertIn('Rahul Kumar', names)
        self.assertIn('Priya Kumari', names)

    def test_03_admin_login_and_redirection(self):
        """Test Admin login redirecting to /admin/dashboard."""
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Dashboard', res.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'Sign In', res_logout.data)

    def test_04_dealer_login_and_redirection(self):
        """Test Dealer login redirecting to /dealer/pos."""
        res = self.client.post('/login', data={
            'username': 'dealer1',
            'password': 'dealer123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Shop Billing', res.data)

        # Dealer accessing POS sale form for Devaki Ammal
        res_pos = self.client.get('/dealer/pos?card_number=RC-AAY-1002&shop_id=1')
        self.assertEqual(res_pos.status_code, 200)
        self.assertIn(b'Devaki Ammal', res_pos.data)

        # Logout
        self.client.get('/logout')

    def test_05_citizen_login_and_dashboard(self):
        """Test Citizen login redirecting to /citizen/dashboard."""
        res = self.client.post('/login', data={
            'username': 'citizen1',
            'password': 'citizen123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Ration Portal', res.data)
        self.assertIn(b'Munna Lal', res.data)
        self.assertIn(b'Family Members', res.data)
        self.assertIn(b'Shanti Devi', res.data)

        # Logout
        self.client.get('/logout')

    def test_06_role_access_control(self):
        """Test access control preventing citizen from accessing admin modules."""
        # Login as Citizen
        self.client.post('/login', data={
            'username': 'citizen1',
            'password': 'citizen123'
        }, follow_redirects=True)

        # Try to access Admin Dashboard
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        # Should be redirected back to citizen dashboard with access denied
        self.assertIn(b'Access Denied', res.data)
        self.assertIn(b'My Ration Portal', res.data)

        self.client.get('/logout')

if __name__ == '__main__':
    unittest.main(verbosity=2)
