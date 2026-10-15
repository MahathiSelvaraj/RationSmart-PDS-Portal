import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace admin_dashboard
old_dashboard = '''    @app.route('/admin/dashboard')
    @role_required('admin', 'inspector')
    def admin_dashboard():
        current_month = datetime.now().strftime('%Y-%m')
        today = date.today()
        
        total_shops = FairPriceShop.query.count()
        total_cards = RationCard.query.count()
        
        # Calculate today's sales
        today_sales = db.session.query(db.func.sum(TransactionItem.quantity)).join(
            DistributionTransaction
        ).filter(
            db.func.date(DistributionTransaction.transaction_date) == today
        ).scalar() or 0.0
        
        # Calculate total available stock
        total_stock = db.session.query(db.func.sum(ShopStock.current_stock)).scalar() or 0.0
        
        low_stocks = ShopStock.query.filter(ShopStock.current_stock <= ShopStock.min_threshold).all()
        
        return render_template(
            'admin/dashboard.html',
            total_shops=total_shops,
            total_cards=total_cards,
            today_sales=round(today_sales, 1),
            total_stock=round(total_stock, 1),
            low_stocks=low_stocks
        )'''

new_dashboard = '''    @app.route('/admin/dashboard')
    @role_required('admin', 'inspector')
    def admin_dashboard():
        current_month = datetime.now().strftime('%Y-%m')
        today = date.today()
        
        total_shops = FairPriceShop.query.count()
        total_dealers = User.query.filter_by(role='dealer').count()
        total_cards = RationCard.query.count()
        total_transactions = DistributionTransaction.query.count()
        
        today_transactions = DistributionTransaction.query.filter(
            db.func.date(DistributionTransaction.transaction_date) == today
        ).count()
        
        today_sales = db.session.query(db.func.sum(TransactionItem.quantity)).join(
            DistributionTransaction
        ).filter(
            db.func.date(DistributionTransaction.transaction_date) == today
        ).scalar() or 0.0
        
        total_stock = db.session.query(db.func.sum(ShopStock.current_stock)).scalar() or 0.0
        
        low_stocks = ShopStock.query.filter(ShopStock.current_stock <= ShopStock.min_threshold).all()
        low_stock_shops_count = len(set(s.shop_id for s in low_stocks))
        
        recent_transactions = DistributionTransaction.query.order_by(
            DistributionTransaction.transaction_date.desc()
        ).limit(8).all()

        commodities = Commodity.query.filter_by(is_active=True).all()
        
        return render_template(
            'admin/dashboard.html',
            total_shops=total_shops,
            total_dealers=total_dealers,
            total_cards=total_cards,
            total_transactions=total_transactions,
            today_transactions=today_transactions,
            today_sales=round(today_sales, 1),
            total_stock=round(total_stock, 1),
            low_stock_shops_count=low_stock_shops_count,
            low_stocks=low_stocks,
            recent_transactions=recent_transactions,
            commodities=commodities
        )'''

# Replace admin_stock to handle shop, grain, and low-stock filters
old_admin_stock = '''    @app.route('/admin/stock')
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

new_admin_stock = '''    @app.route('/admin/stock')
    @role_required('admin', 'inspector')
    def admin_stock():
        selected_shop_id = request.args.get('shop_id', type=int)
        selected_commodity_id = request.args.get('commodity_id', type=int)
        low_stock_only = request.args.get('low_stock_only', '') == '1'
        
        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()
        
        if selected_shop_id:
            target_shops = FairPriceShop.query.filter_by(id=selected_shop_id).all()
        else:
            target_shops = shops
            
        stock_matrix = []
        for shop in target_shops:
            depletion_data = estimate_stock_depletion(shop.id)
            
            # Apply commodity & low-stock filtering
            filtered_data = []
            for item in depletion_data:
                if selected_commodity_id and item['commodity_id'] != selected_commodity_id:
                    continue
                if low_stock_only and not item['is_low_stock']:
                    continue
                filtered_data.append(item)
                
            if filtered_data or not (selected_commodity_id or low_stock_only):
                stock_matrix.append({
                    'shop': shop,
                    'stocks': filtered_data
                })
            
        commodities = Commodity.query.filter_by(is_active=True).all()
        return render_template(
            'admin/stock.html',
            stock_matrix=stock_matrix,
            shops=shops,
            selected_shop_id=selected_shop_id,
            selected_commodity_id=selected_commodity_id,
            low_stock_only=low_stock_only,
            commodities=commodities
        )'''

# Replace admin_transactions to handle shop, dealer, date, grain, and search filters
old_admin_tx = '''    @app.route('/admin/transactions')
    @role_required('admin', 'inspector')
    def admin_transactions():
        shop_id = request.args.get('shop_id', type=int)
        search_query = request.args.get('search', '').strip()

        query = DistributionTransaction.query
        if shop_id:
            query = query.filter_by(shop_id=shop_id)
        if search_query:
            query = query.join(RationCard).filter(
                (DistributionTransaction.bill_number.ilike(f"%{search_query}%")) |
                (RationCard.card_number.ilike(f"%{search_query}%")) |
                (RationCard.head_of_family.ilike(f"%{search_query}%"))
            )

        transactions = query.order_by(DistributionTransaction.transaction_date.desc()).all()
        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()

        return render_template(
            'admin/transactions.html',
            transactions=transactions,
            shops=shops,
            selected_shop_id=shop_id,
            search_query=search_query
        )'''

new_admin_tx = '''    @app.route('/admin/transactions')
    @role_required('admin', 'inspector')
    def admin_transactions():
        shop_id = request.args.get('shop_id', type=int)
        dealer_user_id = request.args.get('user_id', type=int)
        filter_date = request.args.get('date', '').strip()
        commodity_id = request.args.get('commodity_id', type=int)
        search_query = request.args.get('search', '').strip()

        query = DistributionTransaction.query
        if shop_id:
            query = query.filter_by(shop_id=shop_id)
        if dealer_user_id:
            query = query.filter_by(user_id=dealer_user_id)
        if filter_date:
            try:
                d_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
                query = query.filter(db.func.date(DistributionTransaction.transaction_date) == d_obj)
            except ValueError:
                pass
        if commodity_id:
            query = query.join(TransactionItem).filter(TransactionItem.commodity_id == commodity_id)
        if search_query:
            query = query.join(RationCard).filter(
                (DistributionTransaction.bill_number.ilike(f"%{search_query}%")) |
                (RationCard.card_number.ilike(f"%{search_query}%")) |
                (RationCard.head_of_family.ilike(f"%{search_query}%"))
            )

        transactions = query.order_by(DistributionTransaction.transaction_date.desc()).all()
        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()
        dealers = User.query.filter_by(role='dealer').all()
        commodities = Commodity.query.filter_by(is_active=True).all()

        return render_template(
            'admin/transactions.html',
            transactions=transactions,
            shops=shops,
            dealers=dealers,
            commodities=commodities,
            selected_shop_id=shop_id,
            selected_user_id=dealer_user_id,
            filter_date=filter_date,
            selected_commodity_id=commodity_id,
            search_query=search_query
        )'''

code = code.replace(old_dashboard, new_dashboard)
code = code.replace(old_admin_stock, new_admin_stock)
code = code.replace(old_admin_tx, new_admin_tx)

# Add Shop details page and assign dealer route if not present
shop_details_code = '''
    @app.route('/admin/shops/<int:shop_id>')
    @role_required('admin', 'inspector')
    def admin_shop_details(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        current_month = datetime.now().strftime('%Y-%m')
        
        assigned_dealer = User.query.filter_by(shop_id=shop.id, role='dealer').first()
        dealers = User.query.filter_by(role='dealer').all()
        stocks = estimate_stock_depletion(shop.id)
        transactions = DistributionTransaction.query.filter_by(shop_id=shop.id).order_by(
            DistributionTransaction.transaction_date.desc()
        ).limit(10).all()
        total_transactions = DistributionTransaction.query.filter_by(shop_id=shop.id).count()
        
        monthly_distributed = db.session.query(db.func.sum(TransactionItem.quantity)).join(
            DistributionTransaction
        ).filter(
            DistributionTransaction.shop_id == shop.id,
            DistributionTransaction.month_period == current_month
        ).scalar() or 0.0

        return render_template(
            'admin/shop_detail.html',
            shop=shop,
            assigned_dealer=assigned_dealer,
            dealers=dealers,
            stocks=stocks,
            transactions=transactions,
            total_transactions=total_transactions,
            monthly_distributed=round(monthly_distributed, 1)
        )

    @app.route('/admin/shops/<int:shop_id>/assign-dealer', methods=['POST'])
    @role_required('admin', 'inspector')
    def assign_dealer_to_shop(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        dealer_user_id = request.form.get('dealer_user_id', type=int)
        dealer_user = db.session.get(User, dealer_user_id)
        if dealer_user:
            dealer_user.shop_id = shop.id
            dealer_user.role = 'dealer'
            shop.dealer_name = dealer_user.full_name
            db.session.commit()
            flash(f"Dealer '{dealer_user.full_name}' successfully assigned to Shop '{shop.shop_name}' ({shop.shop_code}).", 'success')
        return redirect(url_for('admin_shop_details', shop_id=shop.id))

    @app.route('/admin/shops/<int:shop_id>/toggle-status', methods=['POST'])
    @role_required('admin', 'inspector')
    def toggle_shop_status(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        shop.status = 'Inactive' if shop.status == 'Active' else 'Active'
        db.session.commit()
        flash(f"Shop '{shop.shop_code}' status updated to {shop.status}.", 'info')
        return redirect(url_for('admin_shop_details', shop_id=shop.id))
'''

if 'def admin_shop_details' not in code:
    # Append right before api endpoints
    code = code.replace("    # =========================================================================\n    # JSON API ENDPOINTS", shop_details_code + "\n    # =========================================================================\n    # JSON API ENDPOINTS")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Admin Dashboard, Stock, Transactions, and Shop Details endpoints updated in app.py!")
