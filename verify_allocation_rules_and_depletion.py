import os
import unittest
from datetime import datetime, timedelta
from app import create_app
from models import (
    db, User, FairPriceShop, Commodity, RationCard, FamilyMember,
    ShopStock, DistributionTransaction, TransactionItem, AllocationRule
)
from rules import (
    get_monthly_entitlements, get_beneficiary_quota_status,
    estimate_stock_depletion
)

class TestAllocationRulesAndDepletion(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        cls.seed_test_data()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    @classmethod
    def get_or_create_commodity(cls, code, name, unit, price):
        c = Commodity.query.filter_by(code=code).first()
        if not c:
            c = Commodity(code=code, name=name, unit=unit, price_per_unit=price, is_active=True)
            db.session.add(c)
            db.session.flush()
        return c

    @classmethod
    def seed_test_data(cls):
        # 1. Commodities
        cls.rice = cls.get_or_create_commodity('RICE', 'Rice', 'kg', 2.0)
        cls.wheat = cls.get_or_create_commodity('WHEAT', 'Wheat', 'kg', 3.0)
        cls.sugar = cls.get_or_create_commodity('SUGAR', 'Sugar', 'kg', 13.50)
        cls.kerosene = cls.get_or_create_commodity('KEROSENE', 'Kerosene', 'liter', 25.0)
        cls.dal = cls.get_or_create_commodity('DAL', 'Dal', 'kg', 35.0)

        # 2. Shop
        cls.shop1 = FairPriceShop(
            shop_code='FPS-TEST-1',
            shop_name='Test Shop 1',
            dealer_name='Dealer One',
            license_no='LIC-TEST-001',
            contact_no='9999999999',
            address='Test Address',
            ward='Ward 1'
        )
        db.session.add(cls.shop1)
        db.session.flush()

        # 3. Stocks
        cls.stock_rice = ShopStock(shop_id=cls.shop1.id, commodity_id=cls.rice.id, current_stock=300.0, min_threshold=100.0)
        cls.stock_wheat = ShopStock(shop_id=cls.shop1.id, commodity_id=cls.wheat.id, current_stock=80.0, min_threshold=100.0) # Low stock
        cls.stock_kerosene = ShopStock(shop_id=cls.shop1.id, commodity_id=cls.kerosene.id, current_stock=120.0, min_threshold=40.0)
        db.session.add_all([cls.stock_rice, cls.stock_wheat, cls.stock_kerosene])
        db.session.flush()

        # 4. Ration Cards
        # PHH - 4 members
        cls.card_phh = RationCard(
            card_number='RC-PHH-TEST',
            card_type='PHH',
            head_of_family='PHH Head',
            family_members_count=4,
            aadhaar_last4='1111',
            address='Address 1',
            assigned_shop_id=cls.shop1.id
        )
        # AAY - 4 members
        cls.card_aay = RationCard(
            card_number='RC-AAY-TEST',
            card_type='AAY',
            head_of_family='AAY Head',
            family_members_count=4,
            aadhaar_last4='2222',
            address='Address 2',
            assigned_shop_id=cls.shop1.id
        )
        # NPHH-S - 3 members
        cls.card_nphh_s = RationCard(
            card_number='RC-NPHH-S-TEST',
            card_type='NPHH-S',
            head_of_family='NPHH-S Head',
            family_members_count=3,
            aadhaar_last4='3333',
            address='Address 3',
            assigned_shop_id=cls.shop1.id
        )
        # AY - 1 member
        cls.card_ay = RationCard(
            card_number='RC-AY-TEST',
            card_type='AY',
            head_of_family='AY Head',
            family_members_count=1,
            aadhaar_last4='4444',
            address='Address 4',
            assigned_shop_id=cls.shop1.id
        )
        db.session.add_all([cls.card_phh, cls.card_aay, cls.card_nphh_s, cls.card_ay])
        db.session.flush()

        # 5. Allocation Rules in DB
        rules = [
            # PHH
            AllocationRule(card_type='PHH', commodity_id=cls.rice.id, allocation_basis='PER_PERSON', quantity_per_unit=3.0, unit='kg'),
            AllocationRule(card_type='PHH', commodity_id=cls.wheat.id, allocation_basis='PER_PERSON', quantity_per_unit=2.0, unit='kg'),
            AllocationRule(card_type='PHH', commodity_id=cls.sugar.id, allocation_basis='PER_CARD', quantity_per_unit=1.0, unit='kg'),

            # AAY
            AllocationRule(card_type='AAY', commodity_id=cls.rice.id, allocation_basis='PER_CARD', quantity_per_unit=20.0, unit='kg'),
            AllocationRule(card_type='AAY', commodity_id=cls.wheat.id, allocation_basis='PER_CARD', quantity_per_unit=15.0, unit='kg'),

            # NPHH-S
            AllocationRule(card_type='NPHH-S', commodity_id=cls.rice.id, allocation_basis='PER_CARD', quantity_per_unit=0.0, unit='kg'),
            AllocationRule(card_type='NPHH-S', commodity_id=cls.wheat.id, allocation_basis='PER_CARD', quantity_per_unit=0.0, unit='kg'),
            AllocationRule(card_type='NPHH-S', commodity_id=cls.sugar.id, allocation_basis='PER_CARD', quantity_per_unit=1.0, unit='kg'),
        ]
        db.session.add_all(rules)
        db.session.commit()

    def test_01_card_types_badge_support(self):
        """Verify all 5 card types return proper badges including NPHH-S."""
        types = ['AAY', 'PHH', 'NPHH', 'NPHH-S', 'AY']
        for t in types:
            rc = RationCard(card_number=f'RC-{t}-DUMMY', card_type=t, head_of_family='Test', assigned_shop_id=self.shop1.id, aadhaar_last4='0000', address='A')
            label, badge_class = rc.get_card_type_badge()
            self.assertIn(t, label)
            self.assertTrue(badge_class.startswith('bg-'))

    def test_02_per_person_allocation_calculation(self):
        """Verify PER_PERSON entitlement = qty_per_unit * family_members."""
        ent = get_monthly_entitlements(self.card_phh)
        # Rice: 3.0 * 4 = 12.0 kg
        self.assertEqual(ent['RICE']['entitled_qty'], 12.0)
        self.assertEqual(ent['RICE']['allocation_basis'], 'PER_PERSON')
        # Wheat: 2.0 * 4 = 8.0 kg
        self.assertEqual(ent['WHEAT']['entitled_qty'], 8.0)

    def test_03_per_card_allocation_calculation(self):
        """Verify PER_CARD entitlement = flat qty_per_unit without multiplying by family members."""
        ent = get_monthly_entitlements(self.card_aay)
        # Rice: flat 20.0 kg for AAY (4 members)
        self.assertEqual(ent['RICE']['entitled_qty'], 20.0)
        self.assertEqual(ent['RICE']['allocation_basis'], 'PER_CARD')
        # Sugar for PHH: flat 1.0 kg (4 members)
        ent_phh = get_monthly_entitlements(self.card_phh)
        self.assertEqual(ent_phh['SUGAR']['entitled_qty'], 1.0)
        self.assertEqual(ent_phh['SUGAR']['allocation_basis'], 'PER_CARD')

    def test_04_nphh_s_sugar_only_entitlement(self):
        """Verify NPHH-S card gets Sugar only (Rice=0, Wheat=0, Sugar=1)."""
        ent = get_monthly_entitlements(self.card_nphh_s)
        self.assertEqual(ent['RICE']['entitled_qty'], 0.0)
        self.assertEqual(ent['WHEAT']['entitled_qty'], 0.0)
        self.assertEqual(ent['SUGAR']['entitled_qty'], 1.0)

    def test_05_beneficiary_quota_status_and_claimed_deduction(self):
        """Verify quota status calculates claimed and remaining quantities correctly."""
        month = '2026-09'
        # Record a transaction for PHH card claiming 5 kg Rice
        tx = DistributionTransaction(
            bill_number='BILL-TEST-001',
            ration_card_id=self.card_phh.id,
            shop_id=self.shop1.id,
            transaction_date=datetime(2026, 9, 10, 10, 0),
            month_period=month,
            total_amount=10.0,
            status='Completed'
        )
        db.session.add(tx)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=tx.id, commodity_id=self.rice.id, quantity=5.0, unit_price=2.0, subtotal=10.0))
        db.session.commit()

        status = get_beneficiary_quota_status(self.card_phh, month_period=month)
        rice_item = next(i for i in status['quota_items'] if i['code'] == 'RICE')
        self.assertEqual(rice_item['entitled_qty'], 12.0)
        self.assertEqual(rice_item['claimed_qty'], 5.0)
        self.assertEqual(rice_item['remaining_qty'], 7.0) # 12 - 5 = 7

    def test_06_month_aware_quota_reset(self):
        """Verify quota resets to full entitlement in a new month period."""
        # 2026-09 had 5 kg claimed (remaining 7 kg)
        sept_status = get_beneficiary_quota_status(self.card_phh, month_period='2026-09')
        rice_sept = next(i for i in sept_status['quota_items'] if i['code'] == 'RICE')
        self.assertEqual(rice_sept['remaining_qty'], 7.0)

        # 2026-10 should have 0 claimed (remaining 12 kg)
        oct_status = get_beneficiary_quota_status(self.card_phh, month_period='2026-10')
        rice_oct = next(i for i in oct_status['quota_items'] if i['code'] == 'RICE')
        self.assertEqual(rice_oct['claimed_qty'], 0.0)
        self.assertEqual(rice_oct['remaining_qty'], 12.0)

    def test_07_dynamic_admin_rule_update(self):
        """Verify changing AllocationRule in DB immediately alters entitlement calculations."""
        # Change PHH Rice from 3.0 kg/person to 5.0 kg/person
        rule = AllocationRule.query.filter_by(card_type='PHH', commodity_id=self.rice.id).first()
        self.assertIsNotNone(rule)
        rule.quantity_per_unit = 5.0
        rule.updated_at = datetime.now()
        db.session.commit()
        db.session.expire_all()

        ent = get_monthly_entitlements(self.card_phh)
        # 5.0 * 4 members = 20.0 kg
        self.assertEqual(ent['RICE']['entitled_qty'], 20.0)

        # Reset back for clean state
        rule.quantity_per_unit = 3.0
        rule.updated_at = datetime.now()
        db.session.commit()
        db.session.expire_all()

    def test_08_depletion_forecast_adequate_stock(self):
        """Verify depletion calculation for adequate stock (current_stock > threshold)."""
        # Create a clean dedicated shop for depletion forecast test
        shop_dep = FairPriceShop(
            shop_code='FPS-DEP-99', shop_name='Depletion Test Shop',
            dealer_name='Dep Dealer', license_no='LIC-DEP-99', contact_no='9999988888',
            address='Dep Address', ward='Ward 9'
        )
        db.session.add(shop_dep)
        db.session.flush()

        stock_dep = ShopStock(shop_id=shop_dep.id, commodity_id=self.rice.id, current_stock=300.0, min_threshold=100.0)
        db.session.add(stock_dep)
        db.session.flush()

        card_dep = RationCard(card_number='RC-DEP-99', card_type='PHH', head_of_family='Dep Head', family_members_count=4, aadhaar_last4='9999', address='Addr', assigned_shop_id=shop_dep.id)
        db.session.add(card_dep)
        db.session.flush()

        # Record 2 days of rice outflow in shop_dep (20 kg on Day 1, 20 kg on Day 2 -> avg outflow = (20+20)/2 = 20 kg/day)
        tx1 = DistributionTransaction(
            bill_number='BILL-DEP-001', ration_card_id=card_dep.id, shop_id=shop_dep.id,
            transaction_date=datetime(2026, 9, 1), month_period='2026-09', status='Completed'
        )
        tx2 = DistributionTransaction(
            bill_number='BILL-DEP-002', ration_card_id=card_dep.id, shop_id=shop_dep.id,
            transaction_date=datetime(2026, 9, 2), month_period='2026-09', status='Completed'
        )
        db.session.add_all([tx1, tx2])
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=tx1.id, commodity_id=self.rice.id, quantity=20.0, unit_price=2.0, subtotal=40.0))
        db.session.add(TransactionItem(transaction_id=tx2.id, commodity_id=self.rice.id, quantity=20.0, unit_price=2.0, subtotal=40.0))
        db.session.commit()

        depletion = estimate_stock_depletion(shop_dep.id)
        rice_dep = next(d for d in depletion if d['commodity_code'] == 'RICE')

        self.assertEqual(rice_dep['avg_daily_outflow'], 20.0)
        self.assertEqual(rice_dep['status'], 'Adequate')

    def test_09_depletion_forecast_low_stock_threshold_reached(self):
        """Verify depletion calculation when stock <= min_threshold."""
        # Wheat stock is 80.0, min_threshold is 100.0 (already low)
        depletion = estimate_stock_depletion(self.shop1.id)
        wheat_dep = next(d for d in depletion if d['commodity_code'] == 'WHEAT')

        self.assertTrue(wheat_dep['is_low_stock'])
        self.assertEqual(wheat_dep['estimated_days_to_threshold'], 'Threshold Reached')
        self.assertEqual(wheat_dep['status'], 'Low Stock / Threshold Reached')

    def test_10_depletion_forecast_zero_outflow_safe_handling(self):
        """Verify safe handling when outflow = 0 (no division by zero or negative days)."""
        # Kerosene has 0 outflow transactions recorded
        depletion = estimate_stock_depletion(self.shop1.id)
        kero_dep = next((d for d in depletion if d['commodity_code'] == 'KEROSENE'), None)
        if kero_dep:
            self.assertEqual(kero_dep['avg_daily_outflow'], 0.0)
            self.assertEqual(kero_dep['threshold_display'], 'Insufficient usage data')
            self.assertEqual(kero_dep['depletion_display'], 'Insufficient historical data for reliable estimate')

if __name__ == '__main__':
    unittest.main()
