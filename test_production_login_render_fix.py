"""
Test suite for Render production login failure root-cause and fix.
Verifies:
1. Gunicorn factory `create_app()` automatically initializes a fresh database when empty.
2. `admin`, `dealer1`, and citizen demo accounts are created and can successfully authenticate.
3. Login POST requests return HTTP 302 redirect (successful login) instead of HTTP 200 with error.
4. Non-destructive safety: Existing custom passwords and records are NEVER overwritten.
5. `config.py` correctly parses and normalizes `DATABASE_URL` (including `postgres://` to `postgresql://`).
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from config import Config
from models import db, User, FairPriceShop, RationCard
from seed_data import seed_database, ensure_essential_accounts

class TestProductionLoginRenderFix(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.temp_db_fd)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_01_gunicorn_create_app_initializes_empty_db_and_allows_login(self):
        """Simulate Gunicorn starting a fresh container on Render."""
        class RenderFreshConfig(Config):
            TESTING = False # Simulate production where TESTING is False
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.temp_db_path}"
            WTF_CSRF_ENABLED = False
            AUTO_SEED_IF_EMPTY = True

        # Gunicorn calls app:create_app()
        app = create_app(RenderFreshConfig)
        client = app.test_client()

        with app.app_context():
            # 1. Verify accounts exist now
            user_count = User.query.count()
            self.assertGreater(user_count, 0, "Users table must be automatically seeded on fresh DB")

            admin_user = User.query.filter_by(username='admin').first()
            self.assertIsNotNone(admin_user, "Admin user must exist")
            self.assertTrue(admin_user.check_password('admin123'), "Admin password must verify")

            dealer_user = User.query.filter_by(username='dealer1').first()
            self.assertIsNotNone(dealer_user, "Dealer1 user must exist")
            self.assertTrue(dealer_user.check_password('dealer123'), "Dealer1 password must verify")

        # 2. Test Admin login via POST - must redirect (302) to dashboard, NOT return 200 with error
        res_admin = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin'
        }, follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302, "Admin login must redirect (302) on success")
        self.assertIn('/admin/dashboard', res_admin.headers.get('Location', ''))

        # Logout
        client.get('/logout')

        # 3. Test Dealer login via POST - must redirect (302) to POS
        res_dealer = client.post('/login', data={
            'username': 'dealer1',
            'password': 'dealer123',
            'role': 'dealer'
        }, follow_redirects=False)
        self.assertEqual(res_dealer.status_code, 302, "Dealer login must redirect (302) on success")
        self.assertIn('/dealer/pos', res_dealer.headers.get('Location', ''))

    def test_02_non_destructive_safety_preserves_custom_passwords(self):
        """Verify that re-running seeding or ensure_essential_accounts never overwrites existing passwords."""
        class ExistingDataConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.temp_db_path}"
            WTF_CSRF_ENABLED = False

        app = create_app(ExistingDataConfig)
        with app.app_context():
            db.create_all()
            seed_database(app)

            # Change admin password to a custom production password
            admin = User.query.filter_by(username='admin').first()
            admin.set_password('ProductionCustomSecretPass@2026')
            db.session.commit()

            # Verify changed password
            self.assertTrue(admin.check_password('ProductionCustomSecretPass@2026'))
            self.assertFalse(admin.check_password('admin123'))

            # Run ensure_essential_accounts again
            created = ensure_essential_accounts(app)
            self.assertNotIn('admin', created, "Existing admin should not be re-created")

            # Check that custom password was PRESERVED
            admin_after = User.query.filter_by(username='admin').first()
            self.assertTrue(admin_after.check_password('ProductionCustomSecretPass@2026'), "Custom password must be preserved!")
            self.assertFalse(admin_after.check_password('admin123'), "Default password must NOT have overwritten custom password!")

    def test_03_config_normalizes_postgres_database_url(self):
        """Verify config handles Render postgres:// URL rewriting to postgresql://."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgres://user:secret123@dpg-render-host.com/pds_db'}):
            # Re-read Config
            import importlib
            import config
            importlib.reload(config)

            self.assertTrue(
                config.Config.SQLALCHEMY_DATABASE_URI.startswith('postgresql://'),
                f"DATABASE_URL must be normalized to postgresql://, got: {config.Config.SQLALCHEMY_DATABASE_URI}"
            )
            self.assertIn('user:secret123@dpg-render-host.com/pds_db', config.Config.SQLALCHEMY_DATABASE_URI)

        # Restore default config without DATABASE_URL
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(config)

    def test_04_init_db_script_runs_safely(self):
        """Verify init_db script executes and verifies database health."""
        import subprocess
        env = os.environ.copy()
        env['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{self.temp_db_path}"
        env['TESTING'] = '0'

        # Run init_db.py as a separate subprocess
        result = subprocess.run(
            ['python', 'init_db.py'],
            capture_output=True,
            text=True,
            env=env
        )
        self.assertEqual(result.returncode, 0, f"init_db.py failed with: {result.stderr}")
        self.assertIn("Database is ready for production login requests", result.stdout)

if __name__ == '__main__':
    unittest.main()
