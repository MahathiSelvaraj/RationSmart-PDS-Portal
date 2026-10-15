from app import create_app
from models import db, AllocationRule, Commodity

def seed_allocation_rules():
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # Get commodity mapping by code
        commodities = Commodity.query.all()
        comm_map = {c.code.upper(): c for c in commodities}
        
        if not comm_map:
            print("No commodities found in DB! Run seed_data.py first.")
            return

        # Define default rules for 5 card types (including PHH, AAY, NPHH, NPHH-S, AY)
        default_rules = [
            # PHH - Priority Household (TN PDS: Rice is 5.0 kg per person per month with no upper ceiling)
            ('PHH', 'RICE', 'PER_PERSON', 5.0, 'kg'),
            ('PHH', 'WHEAT', 'PER_PERSON', 2.0, 'kg'),
            ('PHH', 'SUGAR', 'PER_CARD', 1.0, 'kg'),
            ('PHH', 'KEROSENE', 'PER_CARD', 1.0, 'liter'),
            ('PHH', 'DAL', 'PER_CARD', 1.0, 'kg'),

            # AAY - Antyodaya Anna Yojana (TN PDS Citizen Charter: 35.0 kg per card per month)
            ('AAY', 'RICE', 'PER_CARD', 35.0, 'kg'),
            ('AAY', 'WHEAT', 'PER_CARD', 15.0, 'kg'),
            ('AAY', 'SUGAR', 'PER_CARD', 1.0, 'kg'),
            ('AAY', 'KEROSENE', 'PER_CARD', 1.0, 'liter'),
            ('AAY', 'DAL', 'PER_CARD', 2.0, 'kg'),

            # NPHH - Non-Priority Household (PER_CARD)
            ('NPHH', 'RICE', 'PER_CARD', 10.0, 'kg'),
            ('NPHH', 'WHEAT', 'PER_CARD', 5.0, 'kg'),
            ('NPHH', 'SUGAR', 'PER_CARD', 1.0, 'kg'),
            ('NPHH', 'KEROSENE', 'PER_CARD', 0.0, 'liter'),
            ('NPHH', 'DAL', 'PER_CARD', 1.0, 'kg'),

            # NPHH-S - Non-Priority Household - Sugar (Sugar only)
            ('NPHH-S', 'RICE', 'PER_CARD', 0.0, 'kg'),
            ('NPHH-S', 'WHEAT', 'PER_CARD', 0.0, 'kg'),
            ('NPHH-S', 'SUGAR', 'PER_CARD', 1.0, 'kg'),
            ('NPHH-S', 'KEROSENE', 'PER_CARD', 0.0, 'liter'),
            ('NPHH-S', 'DAL', 'PER_CARD', 0.0, 'kg'),

            # AY - Annapurna Yojana (Indigent Seniors)
            ('AY', 'RICE', 'PER_CARD', 7.0, 'kg'),
            ('AY', 'WHEAT', 'PER_CARD', 3.0, 'kg'),
            ('AY', 'SUGAR', 'PER_CARD', 0.5, 'kg'),
            ('AY', 'KEROSENE', 'PER_CARD', 0.0, 'liter'),
            ('AY', 'DAL', 'PER_CARD', 1.0, 'kg'),
        ]

        added_count = 0
        updated_count = 0
        for card_type, comm_code, basis, qty, unit in default_rules:
            comm = comm_map.get(comm_code)
            if not comm:
                continue
            rule = AllocationRule.query.filter_by(card_type=card_type, commodity_id=comm.id).first()
            if not rule:
                rule = AllocationRule(
                    card_type=card_type,
                    commodity_id=comm.id,
                    allocation_basis=basis,
                    quantity_per_unit=qty,
                    unit=unit,
                    is_active=True
                )
                db.session.add(rule)
                added_count += 1
            else:
                rule.allocation_basis = basis
                rule.quantity_per_unit = qty
                rule.unit = unit
                rule.is_active = True
                updated_count += 1
                
        db.session.commit()
        print(f"Successfully seeded AllocationRules! Added: {added_count}, Updated: {updated_count}")

if __name__ == '__main__':
    seed_allocation_rules()
