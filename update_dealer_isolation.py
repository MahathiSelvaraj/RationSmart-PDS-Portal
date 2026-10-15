import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace dealer_pos implementation
old_pos = '''    @app.route('/dealer/pos', methods=['GET', 'POST'])
    @role_required('dealer')
    def dealer_pos():
        shop_id = current_user.shop_id or request.args.get('shop_id', type=int) or 1
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        
        card_search = request.args.get('card_number', '').strip()
        selected_card = None
        quota_status = None
        stock_status = estimate_stock_depletion(shop.id)
        commodities = Commodity.query.filter_by(is_active=True).all()
        
        if card_search:
            selected_card = RationCard.query.filter(
                (RationCard.card_number == card_search) |
                (RationCard.mobile == card_search) |
                (RationCard.aadhaar_last4 == card_search)
            ).first()
            
            if selected_card:
                quota_status = get_beneficiary_quota_status(selected_card)
            else:
                flash(f"No active Ration Card found with query: '{card_search}'", 'warning')

        return render_template(
            'dealer/pos.html',
            shop=shop,
            selected_card=selected_card,
            quota_status=quota_status,
            stock_status=stock_status,
            commodities=commodities,
            card_search=card_search
        )'''

new_pos = '''    @app.route('/dealer/pos', methods=['GET', 'POST'])
    @role_required('dealer')
    def dealer_pos():
        # Backend Security: Strictly enforce assigned shop for Dealer
        if not current_user.shop_id:
            flash("Account Error: Your dealer account is not assigned to any Fair Price Shop. Contact District Administrator.", "danger")
            return redirect(url_for('login'))
            
        shop = current_user.shop
        if not shop:
            abort(404)
        
        card_search = request.args.get('card_number', '').strip()
        selected_card = None
        quota_status = None
        stock_status = estimate_stock_depletion(shop.id)
        commodities = Commodity.query.filter_by(is_active=True).all()
        
        if card_search:
            selected_card = RationCard.query.filter(
                (RationCard.card_number == card_search) |
                (RationCard.mobile == card_search) |
                (RationCard.aadhaar_last4 == card_search)
            ).first()
            
            if selected_card:
                # Security Check: Ensure card belongs to Dealer's assigned shop
                if selected_card.assigned_shop_id != shop.id:
                    flash(f"Access Restriction: Ration Card '{card_search}' belongs to '{selected_card.assigned_shop.shop_name}'. You can only disburse ration for your assigned shop ({shop.shop_name}).", "warning")
                    selected_card = None
                else:
                    quota_status = get_beneficiary_quota_status(selected_card)
            else:
                flash(f"No active Ration Card found with query: '{card_search}'", 'warning')

        return render_template(
            'dealer/pos.html',
            shop=shop,
            selected_card=selected_card,
            quota_status=quota_status,
            stock_status=stock_status,
            commodities=commodities,
            card_search=card_search
        )'''

# Replace process_sale implementation
old_sale = '''    @app.route('/dealer/pos/process-sale', methods=['POST'])
    @role_required('dealer')
    def process_sale():
        card_id = request.form.get('ration_card_id', type=int)
        shop_id = request.form.get('shop_id', type=int) or current_user.shop_id or 1
        payment_mode = request.form.get('payment_mode', 'Cash / Direct Subsidy')
        auth_mode = request.form.get('auth_mode', 'Biometric Aadhaar Authentication (Simulated)')
        
        ration_card = db.session.get(RationCard, card_id)
        shop = db.session.get(FairPriceShop, shop_id)
        if not ration_card or not shop:
            abort(404)'''

new_sale = '''    @app.route('/dealer/pos/process-sale', methods=['POST'])
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
            return redirect(url_for('dealer_pos'))'''

# Replace dealer_stock implementation
old_dealer_stock = '''    @app.route('/dealer/stock')
    @role_required('dealer')
    def dealer_stock():
        shop_id = current_user.shop_id or request.args.get('shop_id', type=int) or 1
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)'''

new_dealer_stock = '''    @app.route('/dealer/stock')
    @role_required('dealer')
    def dealer_stock():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)'''

# Replace dealer_sales_history implementation
old_sales_hist = '''    @app.route('/dealer/sales-history')
    @role_required('dealer')
    def dealer_sales_history():
        shop_id = current_user.shop_id or request.args.get('shop_id', type=int) or 1
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)'''

new_sales_hist = '''    @app.route('/dealer/sales-history')
    @role_required('dealer')
    def dealer_sales_history():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)'''

code = code.replace(old_pos, new_pos)
code = code.replace(old_sale, new_sale)
code = code.replace(old_dealer_stock, new_dealer_stock)
code = code.replace(old_sales_hist, new_sales_hist)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Shop isolation logic updated in app.py!")
