"""
RationSmart - Production Database Initialization & Health Verification
======================================================================
Safe, explicit, non-destructive database initializer for Render / production deployments.

Safety Guarantees:
1. NEVER drops, truncates, or resets existing database tables.
2. NEVER overwrites existing user accounts, passwords, or transaction records.
3. Automatically creates missing tables via db.create_all().
4. If the database is completely empty (0 users), seeds initial baseline PDS entities.
5. If the database is partially populated, verifies and creates ONLY missing accounts.

Usage:
    python init_db.py
Or in Render Build / Pre-Deploy Command:
    pip install -r requirements.txt && python init_db.py
"""

import os
import sys

def mask_connection_uri(uri: str) -> str:
    """Mask password in connection URI for safe log output."""
    if not uri:
        return "(empty)"
    try:
        if '@' in uri and '://' in uri:
            scheme_and_auth, host_and_db = uri.split('@', 1)
            scheme, auth = scheme_and_auth.split('://', 1)
            if ':' in auth:
                user = auth.split(':', 1)[0]
                return f"{scheme}://{user}:****@{host_and_db}"
        return uri
    except Exception:
        return "configured-database-uri"

def init_production_db():
    print("=" * 70)
    print(" [RationSmart] Production Database Initialization & Verification")
    print("=" * 70)

    from app import create_app
    from models import db, User, FairPriceShop, Commodity, RationCard, FamilyMember
    from seed_data import seed_database, ensure_essential_accounts

    app = create_app()
    with app.app_context():
        raw_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print(f">> Target Database: {mask_connection_uri(raw_uri)}")

        # 1. Ensure all database tables exist
        print(">> Verifying database schema tables...")
        try:
            db.create_all()
            print("   [OK] Tables verified successfully.")
        except Exception as e:
            print(f"   [ERROR] Schema verification failed: {e}")
            sys.exit(1)

        # 2. Check current state of records
        user_count = User.query.count()
        shop_count = FairPriceShop.query.count()
        card_count = RationCard.query.count()
        comm_count = Commodity.query.count()

        print(f">> Existing Records:")
        print(f"   - Users:        {user_count}")
        print(f"   - Ration Shops: {shop_count}")
        print(f"   - Ration Cards: {card_count}")
        print(f"   - Commodities:  {comm_count}")

        # 3. Handle initialization safely
        if user_count == 0 or shop_count == 0:
            print("\n>> Database is uninitialized or missing essential entities.")
            print(">> Running baseline seeding (safe one-time initialization)...")
            seed_database(app)
            print("   [OK] Baseline PDS entities and initial accounts seeded successfully.")
        else:
            print("\n>> Database already contains records. Preserving all existing data.")
            print(">> Checking for any missing essential accounts (non-destructive)...")
            created_accounts = ensure_essential_accounts(app)
            if created_accounts:
                print(f"   [OK] Created missing account(s): {', '.join(created_accounts)}")
            else:
                print("   [OK] All expected baseline accounts already exist. Zero modifications made.")

        # 4. Final verification of baseline accounts
        admin_user = User.query.filter_by(username='admin').first()
        dealer_user = User.query.filter_by(username='dealer1').first()

        print("\n>> Account Verification Status:")
        print(f"   - Admin Account ('admin'):      {'Present & Active' if admin_user and admin_user.is_active else 'MISSING'}")
        print(f"   - Dealer Account ('dealer1'):   {'Present & Active' if dealer_user and dealer_user.is_active else 'MISSING'}")
        print(f"   - Total Users in Database:      {User.query.count()}")
        print("=" * 70)
        print(" [RationSmart] Database is ready for production login requests.")
        print("=" * 70 + "\n")

if __name__ == '__main__':
    init_production_db()
