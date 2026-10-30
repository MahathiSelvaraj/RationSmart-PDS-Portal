"""
RationSmart: Intelligent PDS Distribution & Beneficiary Transparency Platform
Project Startup File
"""

import os
from app import create_app
from models import db, User
from seed_data import seed_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables exist
        db.create_all()
        # Seed initial sample data if empty
        if not User.query.first():
            print("Populating initial sample data...")
            seed_database(app)

    print("\n" + "="*70)
    print(" [RationSmart] Intelligent PDS Platform is Running!")
    print("="*70)
    print(" >> Access URL:          http://127.0.0.1:5000")
    print(" >> Citizen Portal:      http://127.0.0.1:5000/citizen/portal")
    print(" >> Admin Login:         Username: admin      | Password: admin123")
    print(" >> Dealer Login:        Username: dealer1    | Password: dealer123")
    print(" >> Inspector Login:     Username: inspector1 | Password: inspector123")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
