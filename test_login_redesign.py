import unittest
from app import create_app
from config import Config
from models import db, User, RationCard
from seed_data import seed_database
import os

TEST_DB = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_login_redesign.db')

class TestLoginRedesignConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB}"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-login-key'

class LoginRedesignTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
        cls.app = create_app(TestLoginRedesignConfig)
        with cls.app.app_context():
            db.create_all()
            seed_database(cls.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_login_page_renders_redesigned_ui(self):
        """Verify the redesigned split-screen login page structure, labels, and styles."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        
        # Check Design Identity elements
        self.assertIn("PUBLIC DISTRIBUTION SYSTEM", html)
        self.assertIn("Digital Ration Shop", html)
        self.assertIn("Transparent distribution. Reliable records. Better public service.", html)
        self.assertIn("Welcome Back", html)
        self.assertIn("Sign in to access your portal.", html)
        
        # Check Color palette & Typography in CSS
        self.assertIn("#F8F7F2", html) # Warm ivory / cream
        self.assertIn("#244A36", html) # Forest green
        self.assertIn("#C5A15A", html) # Muted gold
        self.assertIn("#202820", html) # Dark charcoal
        self.assertIn("#626B64", html) # Readable grey
        self.assertIn("Times New Roman", html) # Formal serif typography
        
        # Check Form Controls and Toggle Elements
        self.assertIn('id="tabCustomer"', html)
        self.assertIn('id="tabDealer"', html)
        self.assertIn('id="tabAdmin"', html)
        self.assertIn('id="usernameInput"', html)
        self.assertIn('id="passwordInput"', html)
        self.assertIn('id="togglePasswordBtn"', html)
        self.assertIn('id="togglePasswordIcon"', html)
        self.assertIn('id="selectedRoleInput"', html)
        self.assertIn("Digital Ration Shop Management Portal", html)

    def test_02_admin_login_with_role(self):
        """Admin login using role='admin' redirects to /admin/dashboard."""
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Dashboard', res.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'Welcome Back', res_logout.data)

    def test_03_dealer_login_with_role(self):
        """Dealer login using role='dealer' redirects to /dealer/pos."""
        res = self.client.post('/login', data={
            'username': 'dealer1',
            'password': 'dealer123',
            'role': 'dealer'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Shop Billing', res.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'Welcome Back', res_logout.data)

    def test_04_customer_login_using_ration_card_number(self):
        """Customer login using Ration Card Number and password redirects to customer dashboard."""
        res = self.client.post('/login', data={
            'username': 'RC-AAY-1001',
            'password': 'citizen123',
            'role': 'customer'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Munna Lal', res.data)
        self.assertIn(b'RC-AAY-1001', res.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'Welcome Back', res_logout.data)

    def test_05_invalid_password_shows_clear_error(self):
        """Invalid credentials stay on login page and display clear error message."""
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid username or password', res.data)
        self.assertIn(b'Welcome Back', res.data)

    def test_06_role_mismatch_prevents_unauthorized_access(self):
        """Selecting Customer role while entering Admin credentials rejects access."""
        res = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'customer'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Access Denied: The provided account is not a Customer', res.data)

    def test_07_unauthenticated_protected_route_access(self):
        """Unauthenticated access to protected routes redirects to /login."""
        for path in ['/admin/dashboard', '/dealer/pos', '/citizen/dashboard']:
            res = self.client.get(path, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login', res.headers.get('Location', ''))

if __name__ == '__main__':
    unittest.main()
