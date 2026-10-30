"""
RationSmart - Database Seeder
Populates initial commodities, admin/dealers/citizens, Fair Price Shops, Ration Cards,
Family Members, Allocations, Stocks, and Sample Transactions.
"""

from datetime import datetime, timedelta, date
from models import (
    db, User, FairPriceShop, Commodity, RationCard, FamilyMember,
    GrainAllocation, ShopStock, DistributionTransaction, TransactionItem,
    AnomalyLog, Grievance
)

def seed_database(app=None):
    if app is None:
        from app import create_app
        app = create_app()
        
    with app.app_context():
        # Create all tables if not exist
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(username='admin').first():
            if not User.query.filter_by(username='dealer4').first():
                shop4 = FairPriceShop.query.filter_by(shop_code='FPS-104').first()
                if shop4:
                    d4 = User(
                        username='dealer4',
                        full_name='Manish Sharma',
                        email='dealer4@rationsmart.gov.in',
                        phone='9812345678',
                        role='dealer',
                        shop_id=shop4.id
                    )
                    d4.set_password('dealer123')
                    db.session.add(d4)
                    db.session.commit()
                    print("Added missing dealer4 account for FPS-104.")
            
            # Ensure additional demo customers exist for live review / billing demo
            fresh_review_cards = [
                {'card_number': 'RC-AAY-1005', 'card_type': 'AAY', 'head_of_family': 'Murugan K', 'family_members_count': 4, 'aadhaar_last4': '5512', 'mobile': '9894100001', 'address': 'No 5, Kamaraj Nagar, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-PHH-2007', 'card_type': 'PHH', 'head_of_family': 'Selvi Ramesh', 'family_members_count': 4, 'aadhaar_last4': '3381', 'mobile': '9894100002', 'address': 'No 18, Bharathiyar St, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-PHH-2008', 'card_type': 'PHH', 'head_of_family': 'Arunachalam V', 'family_members_count': 3, 'aadhaar_last4': '7744', 'mobile': '9894100003', 'address': 'Plot 42, Cross Road, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-PHH-2009', 'card_type': 'PHH', 'head_of_family': 'Fathima Banu', 'family_members_count': 5, 'aadhaar_last4': '6618', 'mobile': '9894100004', 'address': 'No 9, Mosque St, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-NPHH-3004', 'card_type': 'NPHH', 'head_of_family': 'Venkatesh S', 'family_members_count': 3, 'aadhaar_last4': '4491', 'mobile': '9894100005', 'address': 'Flat 3A, Green Park, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-NPHH-3005', 'card_type': 'NPHH', 'head_of_family': 'Karpagam Sundar', 'family_members_count': 4, 'aadhaar_last4': '8820', 'mobile': '9894100006', 'address': 'No 21, New Colony, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-AY-4002', 'card_type': 'AY', 'head_of_family': 'Palaniammal (Elderly)', 'family_members_count': 1, 'aadhaar_last4': '2299', 'mobile': '9894100007', 'address': 'Govt Old Age Home, Anna Nagar', 'shop_code': 'FPS-101'},
                {'card_number': 'RC-AAY-1006', 'card_type': 'AAY', 'head_of_family': 'Muthukumar P', 'family_members_count': 4, 'aadhaar_last4': '1108', 'mobile': '9894100008', 'address': 'No 14, Slum Board, Anna Nagar', 'shop_code': 'FPS-101'},
            ]
            shop1 = FairPriceShop.query.filter_by(shop_code='FPS-101').first()
            if shop1:
                for c_data in fresh_review_cards:
                    if not RationCard.query.filter_by(card_number=c_data['card_number']).first():
                        new_rc = RationCard(
                            card_number=c_data['card_number'],
                            card_type=c_data['card_type'],
                            head_of_family=c_data['head_of_family'],
                            family_members_count=c_data['family_members_count'],
                            aadhaar_last4=c_data['aadhaar_last4'],
                            mobile=c_data['mobile'],
                            address=c_data['address'],
                            assigned_shop_id=shop1.id
                        )
                        db.session.add(new_rc)
                        db.session.flush()
                        fm = FamilyMember(
                            ration_card_id=new_rc.id,
                            full_name=new_rc.head_of_family,
                            relationship='Self (Head)',
                            age=45,
                            gender='Male' if 'Elderly' not in new_rc.head_of_family and 'Selvi' not in new_rc.head_of_family and 'Fathima' not in new_rc.head_of_family and 'Karpagam' not in new_rc.head_of_family else 'Female',
                            aadhaar_last4=new_rc.aadhaar_last4
                        )
                        db.session.add(fm)

            # Ensure every Ration Card has a citizen user account
            for rc in RationCard.query.all():
                u = User.query.filter_by(ration_card_id=rc.id, role='citizen').first()
                if not u:
                    new_u = User(
                        username=rc.card_number,
                        full_name=rc.head_of_family,
                        email=f"card_{rc.id}@citizen.gov.in",
                        phone=rc.mobile or '9800000000',
                        role='citizen',
                        ration_card_id=rc.id
                    )
                    new_u.set_password('citizen123')
                    db.session.add(new_u)
            db.session.commit()
            return

        print("Seeding initial data into RationSmart Database...")
        
        # 1. Commodities
        commodities_data = [
            {'code': 'RICE', 'name': 'Rice (NFSA Grade A)', 'unit': 'kg', 'price_per_unit': 2.00},
            {'code': 'WHEAT', 'name': 'Wheat (Fortified Atta)', 'unit': 'kg', 'price_per_unit': 3.00},
            {'code': 'SUGAR', 'name': 'Refined Sugar', 'unit': 'kg', 'price_per_unit': 13.50},
            {'code': 'KEROSENE', 'name': 'Subsidized Kerosene', 'unit': 'liter', 'price_per_unit': 25.00},
            {'code': 'DAL', 'name': 'Tur Dal / Pulses', 'unit': 'kg', 'price_per_unit': 35.00},
        ]
        
        comm_objs = {}
        for c in commodities_data:
            comm = Commodity(
                code=c['code'],
                name=c['name'],
                unit=c['unit'],
                price_per_unit=c['price_per_unit'],
                is_active=True
            )
            db.session.add(comm)
            comm_objs[c['code']] = comm
        db.session.flush()

        # 2. Fair Price Shops (Ration Shops)
        shops_data = [
            {
                'shop_code': 'FPS-101',
                'shop_name': 'Central Ward Fair Price Shop #101',
                'dealer_name': 'Ramesh Kumar Verma',
                'license_no': 'LIC-PDS-2024-0089',
                'contact_no': '9876543210',
                'address': 'Shop 12, Main Bazaar, Anna Nagar',
                'ward': 'Ward 12',
                'district': 'Metro Central'
            },
            {
                'shop_code': 'FPS-102',
                'shop_name': 'Gandhi Chowk PDS Distribution Center #102',
                'dealer_name': 'Sunita Devi',
                'license_no': 'LIC-PDS-2023-0145',
                'contact_no': '9876501234',
                'address': 'Plot 45, Near Post Office, Gandhi Nagar',
                'ward': 'Ward 15',
                'district': 'Metro Central'
            },
            {
                'shop_code': 'FPS-103',
                'shop_name': 'Market Road Public Ration Store #103',
                'dealer_name': 'Abdul Razak',
                'license_no': 'LIC-PDS-2022-0312',
                'contact_no': '9845123456',
                'address': 'Shop 3B, Old Vegetable Market, Sector 4',
                'ward': 'Ward 21',
                'district': 'Metro Central'
            },
            {
                'shop_code': 'FPS-104',
                'shop_name': 'Railway Colony Ration Depot #104',
                'dealer_name': 'Manish Sharma',
                'license_no': 'LIC-PDS-2025-0077',
                'contact_no': '9812345678',
                'address': 'Platform Road, Near Gate 2, Railway Colony',
                'ward': 'Ward 08',
                'district': 'Metro Central'
            }
        ]

        shop_objs = []
        for s in shops_data:
            fps = FairPriceShop(**s)
            db.session.add(fps)
            shop_objs.append(fps)
        db.session.flush()

        # 3. Ration Cards (Beneficiaries)
        cards_data = [
            # AAY Cards (Yellow) - Shop 1
            {'card_number': 'RC-AAY-1001', 'card_type': 'AAY', 'head_of_family': 'Munna Lal', 'family_members_count': 4, 'aadhaar_last4': '4512', 'mobile': '9823112233', 'address': 'House 14, Slum Colony, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            {'card_number': 'RC-AAY-1002', 'card_type': 'AAY', 'head_of_family': 'Devaki Ammal', 'family_members_count': 3, 'aadhaar_last4': '7821', 'mobile': '9823223344', 'address': 'Hut 8, Canal Road, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            
            # PHH Cards (Pink) - Shop 1
            {'card_number': 'RC-PHH-2001', 'card_type': 'PHH', 'head_of_family': 'Suresh Babu', 'family_members_count': 4, 'aadhaar_last4': '9034', 'mobile': '9834112233', 'address': '12/4, Gandhi Street, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            {'card_number': 'RC-PHH-2002', 'card_type': 'PHH', 'head_of_family': 'Lakshmi Narayan', 'family_members_count': 5, 'aadhaar_last4': '1129', 'mobile': '9834223344', 'address': '45, Market Lane, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            {'card_number': 'RC-PHH-2003', 'card_type': 'PHH', 'head_of_family': 'Meenakshi Sundaram', 'family_members_count': 2, 'aadhaar_last4': '6643', 'mobile': '9834334455', 'address': '89/1, 2nd Cross, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            
            # NPHH Cards (White) - Shop 1
            {'card_number': 'RC-NPHH-3001', 'card_type': 'NPHH', 'head_of_family': 'Anand Joshi', 'family_members_count': 3, 'aadhaar_last4': '5521', 'mobile': '9845112233', 'address': 'Flat 202, Surya Apts, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},
            {'card_number': 'RC-NPHH-3002', 'card_type': 'NPHH', 'head_of_family': 'Pooja Agarwal', 'family_members_count': 4, 'aadhaar_last4': '8872', 'mobile': '9845223344', 'address': '104, Green Avenue, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},

            # AY Cards (Green) - Shop 1
            {'card_number': 'RC-AY-4001', 'card_type': 'AY', 'head_of_family': 'Ramachandra Rao (Sr. Citizen)', 'family_members_count': 1, 'aadhaar_last4': '3310', 'mobile': '9856112233', 'address': 'Old Age Quarters, Block C, Anna Nagar', 'assigned_shop_id': shop_objs[0].id},

            # Shop 2 Cards
            {'card_number': 'RC-AAY-1003', 'card_type': 'AAY', 'head_of_family': 'Basheer Ahmed', 'family_members_count': 5, 'aadhaar_last4': '4490', 'mobile': '9867112233', 'address': '7/A, Old Fort Road, Gandhi Nagar', 'assigned_shop_id': shop_objs[1].id},
            {'card_number': 'RC-PHH-2004', 'card_type': 'PHH', 'head_of_family': 'Kavita Rathore', 'family_members_count': 4, 'aadhaar_last4': '7712', 'mobile': '9867223344', 'address': '62, Nehru Road, Gandhi Nagar', 'assigned_shop_id': shop_objs[1].id},
            {'card_number': 'RC-PHH-2005', 'card_type': 'PHH', 'head_of_family': 'Gurpreet Singh', 'family_members_count': 6, 'aadhaar_last4': '9931', 'mobile': '9867334455', 'address': '19, Gurdwara Lane, Gandhi Nagar', 'assigned_shop_id': shop_objs[1].id},
            {'card_number': 'RC-NPHH-3003', 'card_type': 'NPHH', 'head_of_family': 'Vikram Patel', 'family_members_count': 3, 'aadhaar_last4': '2214', 'mobile': '9867445566', 'address': '55, Commercial Street, Gandhi Nagar', 'assigned_shop_id': shop_objs[1].id},

            # Shop 3 Cards
            {'card_number': 'RC-AAY-1004', 'card_type': 'AAY', 'head_of_family': 'Chhotu Ram', 'family_members_count': 4, 'aadhaar_last4': '6619', 'mobile': '9878112233', 'address': 'Jhuggi 44, Sector 4, Market Road', 'assigned_shop_id': shop_objs[2].id},
            {'card_number': 'RC-PHH-2006', 'card_type': 'PHH', 'head_of_family': 'Kalyan Sen', 'family_members_count': 3, 'aadhaar_last4': '8841', 'mobile': '9878223344', 'address': '33, Mandi Road, Sector 4', 'assigned_shop_id': shop_objs[2].id},
        ]

        card_objs = []
        for c in cards_data:
            rc = RationCard(**c)
            db.session.add(rc)
            card_objs.append(rc)
        db.session.flush()

        # 4. Family Members
        members_data = [
            # Munna Lal Family (RC-AAY-1001)
            {'ration_card_id': card_objs[0].id, 'full_name': 'Munna Lal', 'relationship': 'Self (Head)', 'age': 46, 'gender': 'Male', 'aadhaar_last4': '4512'},
            {'ration_card_id': card_objs[0].id, 'full_name': 'Shanti Devi', 'relationship': 'Spouse', 'age': 42, 'gender': 'Female', 'aadhaar_last4': '7819'},
            {'ration_card_id': card_objs[0].id, 'full_name': 'Rahul Kumar', 'relationship': 'Son', 'age': 19, 'gender': 'Male', 'aadhaar_last4': '2314'},
            {'ration_card_id': card_objs[0].id, 'full_name': 'Priya Kumari', 'relationship': 'Daughter', 'age': 16, 'gender': 'Female', 'aadhaar_last4': '6690'},

            # Suresh Babu Family (RC-PHH-2001)
            {'ration_card_id': card_objs[2].id, 'full_name': 'Suresh Babu', 'relationship': 'Self (Head)', 'age': 40, 'gender': 'Male', 'aadhaar_last4': '9034'},
            {'ration_card_id': card_objs[2].id, 'full_name': 'Radha Suresh', 'relationship': 'Spouse', 'age': 36, 'gender': 'Female', 'aadhaar_last4': '5543'},
            {'ration_card_id': card_objs[2].id, 'full_name': 'Ananya Suresh', 'relationship': 'Daughter', 'age': 14, 'gender': 'Female', 'aadhaar_last4': '8812'},
            {'ration_card_id': card_objs[2].id, 'full_name': 'Karthik Suresh', 'relationship': 'Son', 'age': 11, 'gender': 'Male', 'aadhaar_last4': '4421'},

            # Ramachandra Rao (RC-AY-4001)
            {'ration_card_id': card_objs[7].id, 'full_name': 'Ramachandra Rao', 'relationship': 'Self (Head)', 'age': 68, 'gender': 'Male', 'aadhaar_last4': '3310'},
        ]

        for m in members_data:
            fm = FamilyMember(**m)
            db.session.add(fm)
        db.session.flush()

        # 5. Users (Admin, Inspector, Dealers, Citizens)
        admin = User(
            username='admin',
            full_name='District Food Supply Officer (Admin)',
            email='admin@rationsmart.gov.in',
            phone='9900011223',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        inspector = User(
            username='inspector1',
            full_name='Rajesh Nair (Vigilance Inspector)',
            email='inspector@rationsmart.gov.in',
            phone='9900099887',
            role='admin'
        )
        inspector.set_password('inspector123')
        db.session.add(inspector)

        # Dealer accounts
        dealer1 = User(
            username='dealer1',
            full_name='Ramesh Kumar Verma',
            email='dealer1@rationsmart.gov.in',
            phone='9876543210',
            role='dealer',
            shop_id=shop_objs[0].id
        )
        dealer1.set_password('dealer123')
        db.session.add(dealer1)

        dealer2 = User(
            username='dealer2',
            full_name='Sunita Devi',
            email='dealer2@rationsmart.gov.in',
            phone='9876501234',
            role='dealer',
            shop_id=shop_objs[1].id
        )
        dealer2.set_password('dealer123')
        db.session.add(dealer2)

        dealer3 = User(
            username='dealer3',
            full_name='Abdul Razak',
            email='dealer3@rationsmart.gov.in',
            phone='9845123456',
            role='dealer',
            shop_id=shop_objs[2].id
        )
        dealer3.set_password('dealer123')
        db.session.add(dealer3)

        dealer4 = User(
            username='dealer4',
            full_name='Manish Sharma',
            email='dealer4@rationsmart.gov.in',
            phone='9812345678',
            role='dealer',
            shop_id=shop_objs[3].id
        )
        dealer4.set_password('dealer123')
        db.session.add(dealer4)

        # Citizen Accounts (Linked to Ration Cards)
        citizen1 = User(
            username='citizen1',
            full_name='Munna Lal',
            email='munnalal@citizen.gov.in',
            phone='9823112233',
            role='citizen',
            ration_card_id=card_objs[0].id # RC-AAY-1001
        )
        citizen1.set_password('citizen123')
        db.session.add(citizen1)

        citizen2 = User(
            username='citizen2',
            full_name='Suresh Babu',
            email='sureshbabu@citizen.gov.in',
            phone='9834112233',
            role='citizen',
            ration_card_id=card_objs[2].id # RC-PHH-2001
        )
        citizen2.set_password('citizen123')
        db.session.add(citizen2)

        citizen3 = User(
            username='citizen3',
            full_name='Ramachandra Rao',
            email='ramachandra@citizen.gov.in',
            phone='9856112233',
            role='citizen',
            ration_card_id=card_objs[7].id # RC-AY-4001
        )
        citizen3.set_password('citizen123')
        db.session.add(citizen3)

        # Create user accounts for all remaining cards as well
        for rc_obj in card_objs:
            user_exists = User.query.filter_by(ration_card_id=rc_obj.id, role='citizen').first()
            if not user_exists:
                cit_u = User(
                    username=rc_obj.card_number,
                    full_name=rc_obj.head_of_family,
                    email=f"card_{rc_obj.id}@citizen.gov.in",
                    phone=rc_obj.mobile or '9800000000',
                    role='citizen',
                    ration_card_id=rc_obj.id
                )
                cit_u.set_password('citizen123')
                db.session.add(cit_u)

        db.session.flush()

        # 6. Shop Stocks
        stock_matrix = [
            # Shop 1 (FPS-101)
            (shop_objs[0].id, comm_objs['RICE'].id, 850.0, 150.0),
            (shop_objs[0].id, comm_objs['WHEAT'].id, 620.0, 150.0),
            (shop_objs[0].id, comm_objs['SUGAR'].id, 180.0, 50.0),
            (shop_objs[0].id, comm_objs['KEROSENE'].id, 120.0, 40.0),
            (shop_objs[0].id, comm_objs['DAL'].id, 210.0, 50.0),

            # Shop 2 (FPS-102) - Wheat is Low (< min_threshold)
            (shop_objs[1].id, comm_objs['RICE'].id, 500.0, 150.0),
            (shop_objs[1].id, comm_objs['WHEAT'].id, 85.0, 150.0),
            (shop_objs[1].id, comm_objs['SUGAR'].id, 95.0, 50.0),
            (shop_objs[1].id, comm_objs['KEROSENE'].id, 30.0, 40.0),
            (shop_objs[1].id, comm_objs['DAL'].id, 140.0, 50.0),

            # Shop 3 (FPS-103) - Rice is Low
            (shop_objs[2].id, comm_objs['RICE'].id, 90.0, 150.0),
            (shop_objs[2].id, comm_objs['WHEAT'].id, 450.0, 150.0),
            (shop_objs[2].id, comm_objs['SUGAR'].id, 75.0, 50.0),
            (shop_objs[2].id, comm_objs['KEROSENE'].id, 80.0, 40.0),
            (shop_objs[2].id, comm_objs['DAL'].id, 110.0, 50.0),

            # Shop 4 (FPS-104)
            (shop_objs[3].id, comm_objs['RICE'].id, 600.0, 150.0),
            (shop_objs[3].id, comm_objs['WHEAT'].id, 500.0, 150.0),
            (shop_objs[3].id, comm_objs['SUGAR'].id, 120.0, 50.0),
            (shop_objs[3].id, comm_objs['KEROSENE'].id, 90.0, 40.0),
            (shop_objs[3].id, comm_objs['DAL'].id, 150.0, 50.0),
        ]

        for s_id, c_id, curr, thresh in stock_matrix:
            stk = ShopStock(
                shop_id=s_id,
                commodity_id=c_id,
                current_stock=curr,
                min_threshold=thresh,
                last_replenished_at=datetime.utcnow() - timedelta(days=5)
            )
            db.session.add(stk)
        db.session.flush()

        # 7. Central Godown Grain Allocations (Current & Previous month)
        current_month = datetime.utcnow().strftime('%Y-%m')
        allocations_data = [
            {'code': f'ALC-{current_month}-01', 'shop_id': shop_objs[0].id, 'comm': comm_objs['RICE'].id, 'qty': 1000.0, 'status': 'Received'},
            {'code': f'ALC-{current_month}-02', 'shop_id': shop_objs[0].id, 'comm': comm_objs['WHEAT'].id, 'qty': 800.0, 'status': 'Received'},
            {'code': f'ALC-{current_month}-03', 'shop_id': shop_objs[0].id, 'comm': comm_objs['SUGAR'].id, 'qty': 200.0, 'status': 'Received'},
            {'code': f'ALC-{current_month}-04', 'shop_id': shop_objs[1].id, 'comm': comm_objs['RICE'].id, 'qty': 900.0, 'status': 'Received'},
            {'code': f'ALC-{current_month}-05', 'shop_id': shop_objs[1].id, 'comm': comm_objs['WHEAT'].id, 'qty': 700.0, 'status': 'Received'},
            {'code': f'ALC-{current_month}-06', 'shop_id': shop_objs[2].id, 'comm': comm_objs['RICE'].id, 'qty': 600.0, 'status': 'Dispatched'},
        ]

        for a in allocations_data:
            ga = GrainAllocation(
                allocation_code=a['code'],
                shop_id=a['shop_id'],
                commodity_id=a['comm'],
                allocated_qty=a['qty'],
                allocation_month=current_month,
                dispatch_date=date.today() - timedelta(days=7),
                status=a['status']
            )
            db.session.add(ga)
        db.session.flush()

        # 8. Distribution Transactions (Sample completed sales)
        tx1 = DistributionTransaction(
            bill_number=f"BILL-{datetime.utcnow().strftime('%Y%m')}-00101",
            ration_card_id=card_objs[2].id, # Suresh Babu (PHH)
            shop_id=shop_objs[0].id,
            user_id=dealer1.id,
            transaction_date=datetime.utcnow() - timedelta(days=3),
            month_period=current_month,
            total_amount=57.50,
            payment_mode='Direct Benefit / Cash',
            auth_mode='Biometric Aadhaar Authentication (Simulated)',
            status='Completed'
        )
        db.session.add(tx1)
        db.session.flush()

        db.session.add(TransactionItem(transaction_id=tx1.id, commodity_id=comm_objs['RICE'].id, quantity=12.0, unit_price=2.0, subtotal=24.0))
        db.session.add(TransactionItem(transaction_id=tx1.id, commodity_id=comm_objs['WHEAT'].id, quantity=8.0, unit_price=3.0, subtotal=24.0))
        db.session.add(TransactionItem(transaction_id=tx1.id, commodity_id=comm_objs['SUGAR'].id, quantity=1.0, unit_price=13.50, subtotal=13.50))

        tx2 = DistributionTransaction(
            bill_number=f"BILL-{datetime.utcnow().strftime('%Y%m')}-00102",
            ration_card_id=card_objs[7].id, # Ramachandra Rao (AY)
            shop_id=shop_objs[0].id,
            user_id=dealer1.id,
            transaction_date=datetime.utcnow() - timedelta(days=2),
            month_period=current_month,
            total_amount=0.0,
            payment_mode='Free (Annapurna Scheme)',
            auth_mode='Biometric Aadhaar Authentication (Simulated)',
            status='Completed'
        )
        db.session.add(tx2)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=tx2.id, commodity_id=comm_objs['RICE'].id, quantity=7.0, unit_price=0.0, subtotal=0.0))
        db.session.add(TransactionItem(transaction_id=tx2.id, commodity_id=comm_objs['WHEAT'].id, quantity=3.0, unit_price=0.0, subtotal=0.0))

        # 9. Anomaly Logs
        anomaly1 = AnomalyLog(
            transaction_id=tx1.id,
            ration_card_id=card_objs[2].id,
            shop_id=shop_objs[0].id,
            anomaly_type='Off-Hours Distribution',
            severity='Low',
            description='Transaction recorded at 08:35 PM, slightly after regular PDS counter closure.',
            status='Reviewed',
            resolution_notes='Verified with dealer log. Power failure delayed evening distribution.'
        )
        db.session.add(anomaly1)

        anomaly2 = AnomalyLog(
            ration_card_id=card_objs[0].id,
            shop_id=shop_objs[0].id,
            anomaly_type='Over-Quota Attempt',
            severity='High',
            description='Citizen attempted to claim 40 kg Rice (Permitted monthly AAY ceiling is 20 kg). POS rejected excess claim.',
            status='Flagged'
        )
        db.session.add(anomaly2)

        anomaly3 = AnomalyLog(
            shop_id=shop_objs[1].id,
            anomaly_type='Stock Inconsistency',
            severity='Medium',
            description='Fair Price Shop #102 recorded higher wheat outflow rate than registered cardholder count in Ward 15.',
            status='Flagged'
        )
        db.session.add(anomaly3)

        # 10. Grievances
        g1 = Grievance(
            grievance_code='GRV-1001',
            ration_card_number='RC-AAY-1001',
            citizen_name='Munna Lal',
            citizen_phone='9823112233',
            shop_id=shop_objs[0].id,
            subject='Delay in Kerosene Distribution',
            description='The shop dealer mentioned kerosene stock had not arrived on the 1st of the month.',
            status='Resolved',
            response_text='Godown replenishment completed on 5th of this month. Stock is now available for collection.'
        )
        db.session.add(g1)

        g2 = Grievance(
            grievance_code='GRV-1002',
            ration_card_number='RC-PHH-2004',
            citizen_name='Kavita Rathore',
            citizen_phone='9867223344',
            shop_id=shop_objs[1].id,
            subject='E-POS Biometric Scanner Slow',
            description='Faced biometric scanning difficulty during peak evening hours at Shop #102.',
            status='In Progress',
            response_text='Technical team has scheduled a scanner calibration visit.'
        )
        db.session.add(g2)

        db.session.commit()
        print("Database successfully initialized with full sample PDS datasets and family members!")

def ensure_essential_accounts(app=None):
    """
    Safely ensures essential accounts exist (admin, inspector, dealers, cardholders).
    NEVER drops tables, and NEVER overwrites or resets existing users or passwords.
    Returns a list of newly created usernames (if any).
    """
    if app is None:
        from app import create_app
        app = create_app()

    created = []
    with app.app_context():
        # 1. Admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                full_name='District Food Supply Officer (Admin)',
                email='admin@rationsmart.gov.in',
                phone='9900011223',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            created.append('admin')

        # 2. Inspector
        inspector = User.query.filter_by(username='inspector1').first()
        if not inspector:
            inspector = User(
                username='inspector1',
                full_name='Rajesh Nair (Vigilance Inspector)',
                email='inspector@rationsmart.gov.in',
                phone='9900099887',
                role='admin'
            )
            inspector.set_password('inspector123')
            db.session.add(inspector)
            created.append('inspector1')

        # 3. Dealers
        dealer_configs = [
            ('dealer1', 'Ramesh Kumar Verma', 'dealer1@rationsmart.gov.in', '9876543210', 'FPS-101', 'dealer123'),
            ('dealer2', 'Sunita Devi', 'dealer2@rationsmart.gov.in', '9876501234', 'FPS-102', 'dealer123'),
            ('dealer3', 'Abdul Razak', 'dealer3@rationsmart.gov.in', '9845123456', 'FPS-103', 'dealer123'),
            ('dealer4', 'Manish Sharma', 'dealer4@rationsmart.gov.in', '9812345678', 'FPS-104', 'dealer123'),
        ]

        for uname, fname, mail, ph, scode, pwd in dealer_configs:
            d = User.query.filter_by(username=uname).first()
            if not d:
                shop = FairPriceShop.query.filter_by(shop_code=scode).first()
                d_user = User(
                    username=uname,
                    full_name=fname,
                    email=mail,
                    phone=ph,
                    role='dealer',
                    shop_id=shop.id if shop else None
                )
                d_user.set_password(pwd)
                db.session.add(d_user)
                created.append(uname)

        # 4. Citizens for existing Ration Cards
        for rc in RationCard.query.all():
            u = User.query.filter_by(ration_card_id=rc.id, role='citizen').first()
            if not u:
                citizen_user = User(
                    username=rc.card_number,
                    full_name=rc.head_of_family,
                    email=f"card_{rc.id}@citizen.gov.in",
                    phone=rc.mobile or '9800000000',
                    role='citizen',
                    ration_card_id=rc.id
                )
                citizen_user.set_password('citizen123')
                db.session.add(citizen_user)
                created.append(rc.card_number)

        if created:
            db.session.commit()
    return created

if __name__ == '__main__':
    seed_database()
