"""
RationSmart - Business Logic, Configurable Entitlement Engine, Stock Depletion Forecasting, and Rule-Based Anomaly Detection
"""

from datetime import datetime, timedelta
from sqlalchemy import func
from models import (
    db, RationCard, Commodity, ShopStock, DistributionTransaction,
    TransactionItem, AnomalyLog, AllocationRule
)

# Baseline Fallback Entitlement Rules (used if DB rules are unconfigured)
ENTITLEMENT_RULES = {
    'AAY': { # Antyodaya Anna Yojana (Poorest of poor - PER_CARD 35kg TN PDS scheme)
        'RICE': lambda members: 35.0,
        'WHEAT': lambda members: 15.0,
        'SUGAR': lambda members: 1.0,
        'KEROSENE': lambda members: 1.0,
        'DAL': lambda members: 2.0,
    },
    'PHH': { # Priority Household (PER_PERSON 5kg/person TN PDS scheme, no ceiling)
        'RICE': lambda members: 5.0 * members,
        'WHEAT': lambda members: 2.0 * members,
        'SUGAR': lambda members: 1.0,
        'KEROSENE': lambda members: 1.0,
        'DAL': lambda members: 1.0,
    },
    'NPHH': { # Non-Priority Household
        'RICE': lambda members: 10.0,
        'WHEAT': lambda members: 5.0,
        'SUGAR': lambda members: 1.0,
        'KEROSENE': lambda members: 0.0,
        'DAL': lambda members: 1.0,
    },
    'NPHH-S': { # Non-Priority Household - Sugar
        'RICE': lambda members: 0.0,
        'WHEAT': lambda members: 0.0,
        'SUGAR': lambda members: 1.0,
        'KEROSENE': lambda members: 0.0,
        'DAL': lambda members: 0.0,
    },
    'AY': { # Annapurna Yojana (Indigent Senior Citizens)
        'RICE': lambda members: 7.0,
        'WHEAT': lambda members: 3.0,
        'SUGAR': lambda members: 0.5,
        'KEROSENE': lambda members: 0.0,
        'DAL': lambda members: 1.0,
    }
}


def get_monthly_entitlements(ration_card):
    """
    Calculate the baseline monthly quota of each commodity for a ration card using database-driven AllocationRules.
    Supports PER_PERSON and PER_CARD allocation bases.
    Returns a dict: { commodity_code: { ... entitlement details ... } }
    """
    commodities = Commodity.query.filter_by(is_active=True).all()
    card_type = ration_card.card_type.upper()
    members = ration_card.family_members_count or 1
    
    # Query database allocation rules for this card_type (ordered by latest updated)
    db_rules = AllocationRule.query.filter_by(card_type=card_type, is_active=True).order_by(AllocationRule.updated_at.desc(), AllocationRule.id.desc()).all()
    rule_map = {}
    for r in db_rules:
        if r.commodity_id not in rule_map:
            rule_map[r.commodity_id] = r
    
    fallback_rules = ENTITLEMENT_RULES.get(card_type, ENTITLEMENT_RULES['PHH'])
    
    entitlements = {}
    for comm in commodities:
        code = comm.code.upper()
        rule = rule_map.get(comm.id)
        
        if rule:
            basis = rule.allocation_basis.upper() # 'PER_PERSON' or 'PER_CARD'
            qty_per_unit = float(rule.quantity_per_unit)
            
            if basis == 'PER_PERSON':
                qty = round(qty_per_unit * members, 2)
                basis_label = 'Per Person'
            else:
                # PER_CARD: Entitlement remains quantity_per_unit (do NOT multiply by family size)
                qty = round(qty_per_unit, 2)
                basis_label = 'Per Card'
        else:
            # Fallback calculation if no DB rule configured yet
            calc_fn = fallback_rules.get(code, lambda m: 0.0)
            qty = round(calc_fn(members), 2)
            if card_type == 'PHH' and code in ['RICE', 'WHEAT']:
                basis = 'PER_PERSON'
                basis_label = 'Per Person'
                qty_per_unit = 3.0 if code == 'RICE' else 2.0
            else:
                basis = 'PER_CARD'
                basis_label = 'Per Card'
                qty_per_unit = qty

        # Free grains for AY cards or AAY rice/wheat under special schemes
        price = comm.price_per_unit
        if card_type == 'AY' and code in ['RICE', 'WHEAT']:
            price = 0.0
            
        entitlements[code] = {
            'commodity_id': comm.id,
            'code': comm.code,
            'name': comm.name,
            'unit': comm.unit,
            'unit_price': price,
            'entitled_qty': qty,
            'allocation_basis': basis,
            'basis_label': basis_label,
            'quantity_per_unit': qty_per_unit
        }
        
    return entitlements


def get_beneficiary_quota_status(ration_card, month_period=None):
    """
    Calculate entitlement, already claimed quantity in the month, and remaining quota.
    month_period: 'YYYY-MM', defaults to current month (e.g. '2026-09')
    """
    if not month_period:
        month_period = datetime.utcnow().strftime('%Y-%m')
        
    entitlements = get_monthly_entitlements(ration_card)
    
    # Query all completed transactions for this ration card in this month
    transactions = DistributionTransaction.query.filter_by(
        ration_card_id=ration_card.id,
        month_period=month_period,
        status='Completed'
    ).all()
    
    # Aggregate claimed quantities for current month
    claimed_map = {code: 0.0 for code in entitlements.keys()}
    for tx in transactions:
        for item in tx.items:
            comm_code = item.commodity.code.upper() if item.commodity else ''
            if comm_code in claimed_map:
                claimed_map[comm_code] += item.quantity
                
    # Build complete status report
    quota_status = []
    total_entitled = 0.0
    total_claimed = 0.0
    
    for code, ent in entitlements.items():
        claimed = round(claimed_map.get(code, 0.0), 2)
        entitled = ent['entitled_qty']
        remaining = max(0.0, round(entitled - claimed, 2))
        pct = round((claimed / entitled * 100) if entitled > 0 else (100 if claimed > 0 else 0), 1)
        
        total_entitled += entitled
        total_claimed += claimed
        
        quota_status.append({
            'commodity_id': ent['commodity_id'],
            'code': ent['code'],
            'name': ent['name'],
            'commodity_name': ent['name'],
            'unit': ent['unit'],
            'unit_price': ent['unit_price'],
            'card_type': ration_card.card_type,
            'family_members': ration_card.family_members_count or 1,
            'allocation_basis': ent['allocation_basis'],
            'basis_label': ent['basis_label'],
            'quantity_per_unit': ent['quantity_per_unit'],
            'entitled_qty': entitled,
            'claimed_qty': claimed,
            'received_qty': claimed, # Alias for UI clarity
            'remaining_qty': remaining,
            'percentage_claimed': min(100.0, pct),
            'is_fully_claimed': remaining <= 0.0 and entitled > 0
        })
        
    overall_pct = round((total_claimed / total_entitled * 100) if total_entitled > 0 else 0, 1)
    
    return {
        'month_period': month_period,
        'card_number': ration_card.card_number,
        'card_type': ration_card.card_type,
        'family_members': ration_card.family_members_count or 1,
        'quota_items': quota_status,
        'items': quota_status,
        'total_entitled': round(total_entitled, 2),
        'total_claimed': round(total_claimed, 2),
        'total_remaining': max(0.0, round(total_entitled - total_claimed, 2)),
        'overall_claimed_percentage': min(100.0, overall_pct),
        'transactions_count': len(transactions)
    }


def check_monthly_duplicate_purchases(ration_card, month_period=None, commodity_ids=None):
    """
    Checks if this ration card already has recorded successful (Completed) purchases
    for any commodity in the specified calendar month period ('YYYY-MM').
    Returns a dictionary of duplicate alerts keyed by commodity_id.
    Failed and cancelled transactions are excluded.
    """
    if not month_period:
        month_period = datetime.now().strftime('%Y-%m')
        
    quota_status = get_beneficiary_quota_status(ration_card, month_period=month_period)
    quota_map = {item['commodity_id']: item for item in quota_status['quota_items']}
    
    completed_txs = DistributionTransaction.query.filter_by(
        ration_card_id=ration_card.id,
        month_period=month_period,
        status='Completed'
    ).order_by(DistributionTransaction.transaction_date.desc()).all()
    
    alerts = {}
    for tx in completed_txs:
        for item in tx.items:
            comm = item.commodity
            if not comm:
                continue
            if commodity_ids is not None and comm.id not in commodity_ids:
                continue
                
            q_info = quota_map.get(comm.id, {})
            if comm.id not in alerts:
                alerts[comm.id] = {
                    'commodity_id': comm.id,
                    'commodity_name': comm.name,
                    'commodity_code': comm.code,
                    'unit': comm.unit,
                    'previous_purchases': [],
                    'total_previous_qty': 0.0,
                    'entitled_qty': q_info.get('entitled_qty', 0.0),
                    'claimed_qty': q_info.get('claimed_qty', 0.0),
                    'remaining_qty': q_info.get('remaining_qty', 0.0),
                    'unit_price': q_info.get('unit_price', comm.price_per_unit)
                }
            
            purchaser_name = tx.purchaser_display if hasattr(tx, 'purchaser_display') else tx.ration_card.head_of_family
            alerts[comm.id]['previous_purchases'].append({
                'transaction_id': tx.id,
                'bill_number': tx.bill_number,
                'date': tx.transaction_date.strftime('%d %b %Y, %I:%M %p'),
                'quantity': item.quantity,
                'unit': comm.unit,
                'purchasing_member': purchaser_name,
                'shop_name': tx.shop.shop_name if tx.shop else 'Fair Price Shop',
                'status': tx.status
            })
            alerts[comm.id]['total_previous_qty'] = round(alerts[comm.id]['total_previous_qty'] + item.quantity, 2)
            
    return alerts


def estimate_stock_depletion(shop_id):
    """
    Calculates current stock balance and forecasts depletion & threshold days based on historical usage.
    Iterates over all active commodities to ensure complete inventory reporting per shop.
    """
    commodities = Commodity.query.filter_by(is_active=True).all()
    shop_stocks = ShopStock.query.filter_by(shop_id=shop_id).all()
    stock_map = {s.commodity_id: s for s in shop_stocks}
    
    depletion_reports = []
    for comm in commodities:
        stock = stock_map.get(comm.id)
        if stock:
            has_stock_record = True
            curr_stock = round(stock.current_stock, 2)
            threshold = round(stock.min_threshold, 2)
        else:
            has_stock_record = False
            curr_stock = 0.0
            threshold = 150.0
        
        # Calculate historical outflow from completed transactions for this shop & commodity
        items = db.session.query(
            TransactionItem.quantity,
            DistributionTransaction.transaction_date
        ).join(
            DistributionTransaction, TransactionItem.transaction_id == DistributionTransaction.id
        ).filter(
            DistributionTransaction.shop_id == shop_id,
            TransactionItem.commodity_id == comm.id,
            DistributionTransaction.status == 'Completed'
        ).all()
        
        if items:
            total_outflow = sum(item[0] for item in items)
            distinct_dates = set(item[1].date() for item in items if item[1])
            days_count = max(1, len(distinct_dates))
            avg_daily_outflow = round(total_outflow / float(days_count), 2)
        else:
            total_outflow = 0.0
            avg_daily_outflow = 0.0
            
        if avg_daily_outflow > 0:
            days_to_depletion_num = round(curr_stock / avg_daily_outflow, 1)
            depletion_str = f"~{days_to_depletion_num} days"
            
            if curr_stock > threshold:
                days_to_threshold_num = round((curr_stock - threshold) / avg_daily_outflow, 1)
                threshold_str = f"~{days_to_threshold_num} days"
                status = 'Adequate'
                badge_class = 'bg-success'
            else:
                days_to_threshold_num = 0
                threshold_str = "Threshold Reached"
                status = 'Low Stock / Threshold Reached'
                badge_class = 'bg-danger'
        else:
            days_to_threshold_num = None
            days_to_depletion_num = None
            depletion_str = "Insufficient historical data for reliable estimate"
            if not has_stock_record:
                status = 'No Stock Record'
                badge_class = 'bg-secondary'
                threshold_str = 'Insufficient usage data'
            elif curr_stock <= threshold:
                threshold_str = "Threshold Reached"
                status = 'Low Stock / Threshold Reached'
                badge_class = 'bg-danger'
            else:
                threshold_str = "Insufficient usage data"
                status = 'Insufficient Data'
                badge_class = 'bg-secondary'
            
        depletion_reports.append({
            'commodity_id': comm.id,
            'commodity_code': comm.code,
            'commodity_name': comm.name,
            'unit': comm.unit,
            'has_stock_record': has_stock_record,
            'current_stock': curr_stock if has_stock_record else 'No stock record',
            'stock_qty': curr_stock,
            'min_threshold': threshold,
            'avg_daily_outflow': avg_daily_outflow,
            'daily_consumption_rate': avg_daily_outflow, # Alias
            'days_to_threshold_num': days_to_threshold_num,
            'days_to_depletion_num': days_to_depletion_num,
            'threshold_display': threshold_str,
            'depletion_display': depletion_str,
            'estimated_days_to_threshold': threshold_str if (has_stock_record and curr_stock <= threshold) else (days_to_threshold_num if days_to_threshold_num is not None else threshold_str),
            'estimated_days_to_depletion': days_to_depletion_num if days_to_depletion_num is not None else depletion_str,
            'estimated_days_remaining': f"{days_to_depletion_num}" if days_to_depletion_num is not None else 'No recent outflow',
            'status': status,
            'badge_class': badge_class,
            'is_low_stock': has_stock_record and (curr_stock <= threshold)
        })
        
    return depletion_reports


def calculate_demand_forecast(shop_id=None, commodity_id=None):
    """
    Intelligent Demand Forecasting & Reorder Recommendation System.
    Uses historical completed transactions to calculate average monthly & daily demand and suggested reorders.
    """
    from models import FairPriceShop
    
    query_shops = FairPriceShop.query.order_by(FairPriceShop.shop_code)
    if shop_id:
        query_shops = query_shops.filter_by(id=shop_id)
    shops = query_shops.all()
    
    query_comms = Commodity.query.filter_by(is_active=True)
    if commodity_id:
        query_comms = query_comms.filter_by(id=commodity_id)
    commodities = query_comms.all()
    
    forecast_results = []
    
    for shop in shops:
        for comm in commodities:
            items = db.session.query(
                TransactionItem.quantity,
                DistributionTransaction.month_period
            ).join(
                DistributionTransaction, TransactionItem.transaction_id == DistributionTransaction.id
            ).filter(
                DistributionTransaction.shop_id == shop.id,
                TransactionItem.commodity_id == comm.id,
                DistributionTransaction.status == 'Completed'
            ).all()
            
            stock_obj = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm.id).first()
            current_stock = round(stock_obj.current_stock, 1) if stock_obj else 0.0
            
            if not items:
                forecast_results.append({
                    'shop': shop,
                    'commodity': comm,
                    'current_stock': current_stock,
                    'has_sufficient_data': False,
                    'total_outflow': 0.0,
                    'months_analyzed': 0,
                    'avg_monthly_demand': 0.0,
                    'avg_daily_demand': 0.0,
                    'estimated_coverage_days': 'N/A',
                    'status': 'Insufficient Data',
                    'badge_class': 'bg-secondary',
                    'recommended_reorder_qty': 0.0,
                    'message': 'Insufficient historical data for reliable demand estimation.'
                })
            else:
                total_outflow = sum(item[0] for item in items)
                distinct_months = set(item[1] for item in items if item[1])
                months_analyzed = max(1, len(distinct_months))
                
                avg_monthly_demand = round(total_outflow / float(months_analyzed), 1)
                avg_daily_demand = round(avg_monthly_demand / 30.0, 2)
                
                if avg_daily_demand > 0:
                    coverage_days = int(round(current_stock / avg_daily_demand))
                    coverage_str = f"~{coverage_days} days"
                else:
                    coverage_days = 999
                    coverage_str = "N/A"
                    
                if current_stock < avg_monthly_demand:
                    status = 'Replenishment Recommended'
                    badge_class = 'bg-warning text-dark'
                    reorder_qty = round(max(0.0, avg_monthly_demand - current_stock), 1)
                else:
                    status = 'Adequate Stock'
                    badge_class = 'bg-success'
                    reorder_qty = 0.0
                    
                forecast_results.append({
                    'shop': shop,
                    'commodity': comm,
                    'current_stock': current_stock,
                    'has_sufficient_data': True,
                    'total_outflow': round(total_outflow, 1),
                    'months_analyzed': months_analyzed,
                    'avg_monthly_demand': avg_monthly_demand,
                    'avg_daily_demand': avg_daily_demand,
                    'estimated_coverage_days': coverage_str,
                    'coverage_days_num': coverage_days,
                    'status': status,
                    'badge_class': badge_class,
                    'recommended_reorder_qty': reorder_qty,
                    'message': f"Calculated from {months_analyzed} month(s) transaction history."
                })
                
    return forecast_results


def check_transaction_anomalies(ration_card, shop_id, items_to_purchase, transaction_time=None):
    """
    Rule-Based Anomaly Detection Engine:
    Checks for Over-quota, Repeated short-period, Unusually large quantity, Same-day multiple distribution, and Stock deficit.
    """
    if transaction_time is None:
        transaction_time = datetime.utcnow()
        
    anomalies = []
    month_period = transaction_time.strftime('%Y-%m')
    quota_status = get_beneficiary_quota_status(ration_card, month_period)
    remaining_map = {item['commodity_id']: item['remaining_qty'] for item in quota_status['items']}
    entitled_map = {item['commodity_id']: item['entitled_qty'] for item in quota_status['items']}
    name_map = {item['commodity_id']: item['name'] for item in quota_status['items']}
    unit_map = {item['commodity_id']: item['unit'] for item in quota_status['items']}
    
    # 1. Quantity checks
    for item in items_to_purchase:
        cid = int(item.get('commodity_id', 0))
        qty = float(item.get('quantity', 0.0))
        rem = remaining_map.get(cid, 0.0)
        cname = name_map.get(cid, 'Commodity')
        unit = unit_map.get(cid, 'kg')
        
        # Hard policy check (High severity - blocks transaction)
        if qty > rem + 0.001:
            anomalies.append({
                'type': 'Over-Quota Attempt',
                'severity': 'High',
                'description': f"Attempted to disburse {qty} {unit} of {cname} when remaining monthly quota is {rem} {unit}."
            })
            
        # Rule 2: Unusually Large Quantity (Medium severity - non-blocking flag)
        ent = entitled_map.get(cid, 0.0)
        if ent > 0 and qty > (ent * 1.5):
            anomalies.append({
                'type': 'Unusually Large Quantity',
                'severity': 'Medium',
                'description': f"Flagged for Review: Quantity of {cname} ({qty} {unit}) is unusually high compared with normal distribution pattern ({ent} {unit})."
            })
            
        # Stock Deficit Check (High severity - blocks transaction)
        stock = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=cid).first()
        if not stock or stock.current_stock < qty:
            curr_stk = stock.current_stock if stock else 0.0
            anomalies.append({
                'type': 'Stock Inconsistency / Deficit Sale',
                'severity': 'High',
                'description': f"Transaction requested {qty} {unit} of {cname} but Shop only has {curr_stk} {unit} in recorded inventory."
            })
            
    # 2. Previous transaction checks
    recent_txs = DistributionTransaction.query.filter_by(
        ration_card_id=ration_card.id,
        status='Completed'
    ).order_by(DistributionTransaction.transaction_date.desc()).all()
    
    if recent_txs:
        # Multiple Transactions for Same Customer on Same Day
        same_day_txs = [tx for tx in recent_txs if tx.transaction_date.date() == transaction_time.date()]
        if same_day_txs:
            anomalies.append({
                'type': 'Same-Day Multiple Distribution',
                'severity': 'Medium',
                'description': f"Flagged for Review: Multiple transactions recorded on the same calendar date for customer {ration_card.card_number} (Previous Bill: {same_day_txs[0].bill_number})."
            })
            
        # Repeated Transactions in a Short Period
        recent_tx = recent_txs[0]
        time_diff = abs(transaction_time - recent_tx.transaction_date)
        if time_diff < timedelta(hours=24):
            hours_ago = round(time_diff.total_seconds() / 3600.0, 1)
            anomalies.append({
                'type': 'Repeated Short-Period Distribution',
                'severity': 'Medium',
                'description': f"Flagged for Review: Multiple transactions recorded within a short time period ({hours_ago} hours ago, Bill: {recent_tx.bill_number})."
            })
            
    # Off-Hours Distribution (Low severity)
    current_hour = transaction_time.hour
    if current_hour < 7 or current_hour >= 20:
        anomalies.append({
            'type': 'Off-Hours Distribution',
            'severity': 'Low',
            'description': f"Transaction recorded at {transaction_time.strftime('%I:%M %p')}, outside standard PDS hours (07:00 AM - 08:00 PM)."
        })
        
    return anomalies
