import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace process_sale function
old_process_sale = '''    @app.route('/dealer/pos/process-sale', methods=['POST'])
    @role_required('dealer')
    def process_sale():
        # Backend Security: Force transaction under dealer's assigned shop
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('dealer_pos'))

        shop_id = current_user.shop_id
        shop = current_user.shop

        card_id = request.form.get('ration_card_id', type=int)
        payment_mode = request.form.get('payment_mode', 'Cash / Direct Subsidy')
        auth_mode = request.form.get('auth_mode', 'Biometric Aadhaar Authentication (Simulated)')
        
        ration_card = db.session.get(RationCard, card_id)
        if not ration_card or not shop:
            abort(404)

        # Security Check: Verify card belongs to dealer's shop
        if ration_card.assigned_shop_id != shop.id:
            flash(f"Security Enforcement: Ration Card '{ration_card.card_number}' belongs to another shop. Distribution denied.", "danger")
            return redirect(url_for('dealer_pos'))
        
        items_data = []
        commodities = Commodity.query.filter_by(is_active=True).all()
        total_bill_amount = 0.0
        
        for comm in commodities:
            qty_val = request.form.get(f'qty_{comm.id}', '0').strip()
            try:
                qty = float(qty_val)
            except ValueError:
                qty = 0.0
                
            if qty > 0:
                price = comm.price_per_unit
                if ration_card.card_type == 'AY' and comm.code in ['RICE', 'WHEAT']:
                    price = 0.0
                subtotal = round(qty * price, 2)
                total_bill_amount += subtotal
                items_data.append({
                    'commodity_id': comm.id,
                    'commodity': comm,
                    'quantity': qty,
                    'unit_price': price,
                    'subtotal': subtotal
                })
                
        if not items_data:
            flash('No commodity quantities selected for distribution.', 'danger')
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number, shop_id=shop.id))
        
        detected_anomalies = check_transaction_anomalies(
            ration_card=ration_card,
            shop_id=shop.id,
            items_to_purchase=[{'commodity_id': item['commodity_id'], 'quantity': item['quantity']} for item in items_data],
            transaction_time=datetime.now()
        )
        
        critical_errors = [a for a in detected_anomalies if a['severity'] == 'High']
        if critical_errors:
            for err in critical_errors:
                flash(f"Blocked by Policy: {err['description']}", 'danger')
                log = AnomalyLog(
                    ration_card_id=ration_card.id,
                    shop_id=shop.id,
                    anomaly_type=err['type'],
                    severity=err['severity'],
                    description=err['description'],
                    status='Flagged'
                )
                db.session.add(log)
            db.session.commit()
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number, shop_id=shop.id))
        
        current_period = datetime.now().strftime('%Y%m')
        bill_count = DistributionTransaction.query.filter(
            DistributionTransaction.month_period == datetime.now().strftime('%Y-%m')
        ).count() + 1
        bill_number = f"BILL-{current_period}-{bill_count:05d}"
        
        tx = DistributionTransaction(
            bill_number=bill_number,
            ration_card_id=ration_card.id,
            shop_id=shop.id,
            user_id=current_user.id,
            transaction_date=datetime.now(),
            month_period=datetime.now().strftime('%Y-%m'),
            total_amount=round(total_bill_amount, 2),
            payment_mode=payment_mode,
            auth_mode=auth_mode,
            status='Completed'
        )
        db.session.add(tx)
        db.session.flush()
        
        for item in items_data:
            t_item = TransactionItem(
                transaction_id=tx.id,
                commodity_id=item['commodity_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                subtotal=item['subtotal']
            )
            db.session.add(t_item)
            
            stock = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=item['commodity_id']).first()
            if stock:
                stock.current_stock = max(0.0, round(stock.current_stock - item['quantity'], 2))
                stock.updated_at = datetime.now()
                
        for a in detected_anomalies:
            log = AnomalyLog(
                transaction_id=tx.id,
                ration_card_id=ration_card.id,
                shop_id=shop.id,
                anomaly_type=a['type'],
                severity=a['severity'],
                description=a['description'],
                status='Flagged'
            )
            db.session.add(log)
            
        db.session.commit()
        flash(f"Distribution recorded successfully! Bill #{bill_number} generated.", 'success')
        return redirect(url_for('view_receipt', transaction_id=tx.id))'''

new_process_sale = '''    @app.route('/dealer/pos/process-sale', methods=['POST'])
    @role_required('dealer')
    def process_sale():
        # Backend Security: Force transaction under dealer's assigned shop
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('dealer_pos'))

        shop_id = current_user.shop_id
        shop = current_user.shop

        card_id = request.form.get('ration_card_id', type=int)
        payment_mode = request.form.get('payment_mode', 'Cash / Direct Subsidy')
        auth_mode = request.form.get('auth_mode', 'Biometric Aadhaar Authentication (Simulated)')
        
        ration_card = db.session.get(RationCard, card_id)
        if not ration_card:
            flash("Distribution Rejected: Invalid or non-existent Ration Card.", "danger")
            return redirect(url_for('dealer_pos'))
            
        if ration_card.status != 'Active':
            flash(f"Distribution Rejected: Ration Card '{ration_card.card_number}' is {ration_card.status}. Only Active cards can receive ration.", "danger")
            return redirect(url_for('dealer_pos'))

        # Security Check: Verify card belongs to dealer's shop
        if ration_card.assigned_shop_id != shop.id:
            flash(f"Security Enforcement: Ration Card '{ration_card.card_number}' belongs to another shop ({ration_card.assigned_shop.shop_name}). Distribution denied.", "danger")
            return redirect(url_for('dealer_pos'))
        
        # Monthly Quota Validation
        quota_status = get_beneficiary_quota_status(ration_card)
        quota_map = {item['commodity_id']: item for item in quota_status['quota_items']}

        items_data = []
        commodities = Commodity.query.filter_by(is_active=True).all()
        total_bill_amount = 0.0
        
        for comm in commodities:
            qty_val = request.form.get(f'qty_{comm.id}', '0').strip()
            try:
                qty = float(qty_val)
            except ValueError:
                qty = 0.0
                
            if qty < 0:
                flash("Distribution Rejected: Grain quantity cannot be negative.", "danger")
                return redirect(url_for('dealer_pos', card_number=ration_card.card_number))

            if qty > 0:
                comm_quota = quota_map.get(comm.id)
                remaining_quota = comm_quota['remaining_qty'] if comm_quota else 0.0
                
                # 1. Validation: Quantity exceeds remaining entitlement
                if qty > remaining_quota:
                    flash(f"Distribution Rejected: Requested {qty} {comm.unit} of {comm.name} exceeds customer's remaining entitlement ({remaining_quota} {comm.unit}).", "danger")
                    return redirect(url_for('dealer_pos', card_number=ration_card.card_number))
                
                # 2. Validation: Quantity exceeds shop available stock
                stock = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=comm.id).first()
                available_stock = stock.current_stock if stock else 0.0
                if qty > available_stock:
                    flash(f"Distribution Rejected: Requested {qty} {comm.unit} of {comm.name} exceeds shop's available stock ({available_stock} {comm.unit}).", "danger")
                    return redirect(url_for('dealer_pos', card_number=ration_card.card_number))

                price = comm.price_per_unit
                if ration_card.card_type == 'AY' and comm.code in ['RICE', 'WHEAT']:
                    price = 0.0
                subtotal = round(qty * price, 2)
                total_bill_amount += subtotal
                items_data.append({
                    'commodity_id': comm.id,
                    'commodity': comm,
                    'quantity': qty,
                    'unit_price': price,
                    'subtotal': subtotal
                })
                
        if not items_data:
            flash('Distribution Rejected: Please enter at least one valid grain quantity greater than 0.', 'danger')
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number))
        
        detected_anomalies = check_transaction_anomalies(
            ration_card=ration_card,
            shop_id=shop.id,
            items_to_purchase=[{'commodity_id': item['commodity_id'], 'quantity': item['quantity']} for item in items_data],
            transaction_time=datetime.now()
        )
        
        critical_errors = [a for a in detected_anomalies if a['severity'] == 'High']
        if critical_errors:
            for err in critical_errors:
                flash(f"Blocked by Policy: {err['description']}", 'danger')
                log = AnomalyLog(
                    ration_card_id=ration_card.id,
                    shop_id=shop.id,
                    anomaly_type=err['type'],
                    severity=err['severity'],
                    description=err['description'],
                    status='Flagged'
                )
                db.session.add(log)
            db.session.commit()
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number))
        
        # Atomic Bill Generation & Stock Deduction
        try:
            current_period = datetime.now().strftime('%Y%m')
            bill_count = DistributionTransaction.query.filter(
                DistributionTransaction.month_period == datetime.now().strftime('%Y-%m')
            ).count() + 1
            bill_number = f"BILL-{current_period}-{bill_count:05d}"
            
            tx = DistributionTransaction(
                bill_number=bill_number,
                ration_card_id=ration_card.id,
                shop_id=shop.id,
                user_id=current_user.id,
                transaction_date=datetime.now(),
                month_period=datetime.now().strftime('%Y-%m'),
                total_amount=round(total_bill_amount, 2),
                payment_mode=payment_mode,
                auth_mode=auth_mode,
                status='Completed'
            )
            db.session.add(tx)
            db.session.flush()
            
            for item in items_data:
                t_item = TransactionItem(
                    transaction_id=tx.id,
                    commodity_id=item['commodity_id'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    subtotal=item['subtotal']
                )
                db.session.add(t_item)
                
                # Deduct stock ONLY from dealer's assigned shop
                stock = ShopStock.query.filter_by(shop_id=shop.id, commodity_id=item['commodity_id']).first()
                if stock:
                    stock.current_stock = max(0.0, round(stock.current_stock - item['quantity'], 2))
                    stock.updated_at = datetime.now()
                    
            for a in detected_anomalies:
                log = AnomalyLog(
                    transaction_id=tx.id,
                    ration_card_id=ration_card.id,
                    shop_id=shop.id,
                    anomaly_type=a['type'],
                    severity=a['severity'],
                    description=a['description'],
                    status='Flagged'
                )
                db.session.add(log)
                
            db.session.commit()
            flash(f"Distribution recorded successfully! Bill #{bill_number} generated.", 'success')
            return redirect(url_for('view_receipt', transaction_id=tx.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Transaction Error: Bill generation failed ({str(e)}). Stock was NOT reduced.", 'danger')
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number))'''

# Replace dealer_sales_history function with filtering
old_dealer_sales_history = '''    @app.route('/dealer/sales-history')
    @role_required('dealer')
    def dealer_sales_history():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)
        
        transactions = DistributionTransaction.query.filter_by(shop_id=shop.id).order_by(
            DistributionTransaction.transaction_date.desc()
        ).all()
        
        return render_template(
            'dealer/sales_history.html',
            shop=shop,
            transactions=transactions
        )'''

new_dealer_sales_history = '''    @app.route('/dealer/sales-history')
    @role_required('dealer')
    def dealer_sales_history():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)
            
        search_query = request.args.get('search', '').strip()
        filter_date = request.args.get('date', '').strip()
        
        query = DistributionTransaction.query.filter_by(shop_id=shop.id)
        
        if filter_date:
            try:
                d_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
                query = query.filter(db.func.date(DistributionTransaction.transaction_date) == d_obj)
            except ValueError:
                pass
                
        if search_query:
            query = query.join(RationCard).filter(
                (DistributionTransaction.bill_number.ilike(f"%{search_query}%")) |
                (RationCard.card_number.ilike(f"%{search_query}%")) |
                (RationCard.head_of_family.ilike(f"%{search_query}%"))
            )
        
        transactions = query.order_by(DistributionTransaction.transaction_date.desc()).all()
        
        return render_template(
            'dealer/sales_history.html',
            shop=shop,
            transactions=transactions,
            search_query=search_query,
            filter_date=filter_date
        )'''

# Replace admin_stock function with shop filtering
old_admin_stock = '''    @app.route('/admin/stock')
    @role_required('admin', 'inspector')
    def admin_stock():
        shops = FairPriceShop.query.filter_by(status='Active').all()
        stock_matrix = []
        for shop in shops:
            depletion_data = estimate_stock_depletion(shop.id)
            stock_matrix.append({
                'shop': shop,
                'stocks': depletion_data
            })
            
        commodities = Commodity.query.filter_by(is_active=True).all()
        return render_template(
            'admin/stock.html',
            stock_matrix=stock_matrix,
            shops=shops,
            commodities=commodities
        )'''

new_admin_stock = '''    @app.route('/admin/stock')
    @role_required('admin', 'inspector')
    def admin_stock():
        selected_shop_id = request.args.get('shop_id', type=int)
        shops = FairPriceShop.query.filter_by(status='Active').all()
        
        if selected_shop_id:
            target_shops = FairPriceShop.query.filter_by(id=selected_shop_id, status='Active').all()
        else:
            target_shops = shops
            
        stock_matrix = []
        for shop in target_shops:
            depletion_data = estimate_stock_depletion(shop.id)
            stock_matrix.append({
                'shop': shop,
                'stocks': depletion_data
            })
            
        commodities = Commodity.query.filter_by(is_active=True).all()
        return render_template(
            'admin/stock.html',
            stock_matrix=stock_matrix,
            shops=shops,
            selected_shop_id=selected_shop_id,
            commodities=commodities
        )'''

code = code.replace(old_process_sale, new_process_sale)
code = code.replace(old_dealer_sales_history, new_dealer_sales_history)
code = code.replace(old_admin_stock, new_admin_stock)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Validation and stock rules updated in app.py!")
