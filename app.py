import os
import io
import uuid
from datetime import datetime, date, timedelta
from functools import wraps
import qrcode
from PIL import Image
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort, send_file
)
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from config import Config
from models import (
    db, User, FairPriceShop, RationShop, Commodity, RationCard, FamilyMember,
    GrainAllocation, ShopStock, DistributionTransaction, TransactionItem,
    AnomalyLog, Grievance, Complaint, ComplaintAuditLog, AllocationRule
)
from rules import (
    get_monthly_entitlements, get_beneficiary_quota_status,
    estimate_stock_depletion, check_transaction_anomalies,
    calculate_demand_forecast, check_monthly_duplicate_purchases
)

def init_mysql_db_if_needed(app):
    """Auto-creates the MySQL database if not exists so users don't need MySQL Workbench."""
    if app.config.get('DB_TYPE') == 'mysql':
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                user=app.config.get('DB_USER', 'root'),
                password=app.config.get('DB_PASSWORD', ''),
                host=app.config.get('DB_HOST', 'localhost'),
                port=int(app.config.get('DB_PORT', 3306))
            )
            cursor = conn.cursor()
            db_name = app.config.get('DB_NAME', 'digital_ration_db')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            conn.close()
        except Exception as e:
            # Fallback gracefully
            pass

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Auto create MySQL database if configured
    init_mysql_db_if_needed(app)
    
    # Initialize DB & Flask-Login
    db.init_app(app)
    
    # Ensure complaints upload folder exists
    complaints_upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'complaints')
    os.makedirs(complaints_upload_dir, exist_ok=True)
    app.config['COMPLAINTS_UPLOAD_FOLDER'] = complaints_upload_dir

    with app.app_context():
        try:
            from sqlalchemy import text
            db.session.execute(text("ALTER TABLE distribution_transactions ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Safe migrations for grievances columns
        for col_sql in [
            "ALTER TABLE grievances ADD COLUMN category VARCHAR(100) DEFAULT 'Other';",
            "ALTER TABLE grievances ADD COLUMN commodity_id INTEGER REFERENCES commodities(id);",
            "ALTER TABLE grievances ADD COLUMN ration_card_id INTEGER REFERENCES ration_cards(id);",
            "ALTER TABLE grievances ADD COLUMN user_id INTEGER REFERENCES users(id);",
            "ALTER TABLE grievances ADD COLUMN attachment_path VARCHAR(255);",
            "ALTER TABLE grievances ADD COLUMN updated_at DATETIME;"
        ]:
            try:
                from sqlalchemy import text
                db.session.execute(text(col_sql))
                db.session.commit()
            except Exception:
                db.session.rollback()

        try:
            db.create_all()
        except Exception:
            pass
    
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this portal section.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Role protection decorator
    def role_required(*allowed_roles):
        def decorator(f):
            @wraps(f)
            @login_required
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated or current_user.role not in allowed_roles:
                    if current_user.role == 'citizen':
                        flash('Access Denied: Customer accounts can only view their own ration portal and entitlement status.', 'danger')
                        return redirect(url_for('citizen_dashboard'))
                    elif current_user.role == 'dealer':
                        flash('Access Denied: Dealers can only access their assigned Shop Billing and operations.', 'danger')
                        return redirect(url_for('dealer_pos'))
                    elif current_user.role in ['admin', 'inspector']:
                        flash('Access Denied: Billing operations are restricted to Shop Dealers only. Admins can view and monitor transactions.', 'danger')
                        return redirect(url_for('admin_dashboard'))
                    else:
                        flash('Access Denied: You do not have permission to access this page.', 'danger')
                        return redirect(url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # Global template context variables
    @app.context_processor
    def inject_global_vars():
        unread_anomalies = 0
        pending_grievances = 0
        if current_user.is_authenticated and current_user.role in ['admin', 'inspector']:
            unread_anomalies = AnomalyLog.query.filter_by(status='Flagged').count()
            pending_grievances = Grievance.query.filter_by(status='Pending').count()
        return {
            'current_year': datetime.now().year,
            'current_month_str': datetime.now().strftime('%B %Y'),
            'current_period': datetime.now().strftime('%Y-%m'),
            'unread_anomalies_count': unread_anomalies,
            'pending_grievances_count': pending_grievances
        }

    # =========================================================================
    # PUBLIC ROUTES
    # =========================================================================

    @app.route('/')
    def index():
        total_shops = FairPriceShop.query.filter_by(status='Active').count()
        total_cards = RationCard.query.filter_by(status='Active').count()
        current_month = datetime.now().strftime('%Y-%m')
        
        total_grains = db.session.query(db.func.sum(TransactionItem.quantity)).join(
            DistributionTransaction
        ).filter(DistributionTransaction.month_period == current_month).scalar() or 0.0
        
        shops = FairPriceShop.query.filter_by(status='Active').limit(6).all()
        commodities = Commodity.query.filter_by(is_active=True).all()
        
        return render_template('index.html',
            total_shops=total_shops,
            total_cards=total_cards,
            total_grains=round(total_grains, 1),
            shops=shops,
            commodities=commodities
        )

    # =========================================================================
    # AUTHENTICATION (LOGIN, LOGOUT, ROLE REDIRECTION)
    # =========================================================================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.role in ['admin', 'inspector']:
                return redirect(url_for('admin_dashboard'))
            elif current_user.role == 'dealer':
                return redirect(url_for('dealer_pos'))
            elif current_user.role == 'citizen':
                return redirect(url_for('citizen_dashboard'))
            
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            selected_role = request.form.get('role', '').strip().lower()
            
            # Lookup user by username or by Ration Card Number (for citizens)
            user = User.query.filter_by(username=username).first()
            if not user:
                rc = RationCard.query.filter_by(card_number=username).first()
                if rc:
                    user = User.query.filter_by(ration_card_id=rc.id, role='citizen').first()

            if user and user.check_password(password):
                if not user.is_active:
                    flash('Account is inactive. Please contact District Administrator.', 'danger')
                    return render_template('auth/login.html')
                
                # If a specific role was chosen in the UI, verify role compatibility
                if selected_role == 'admin' and user.role not in ['admin', 'inspector']:
                    flash('Access Denied: The provided account does not have Administrator privileges.', 'danger')
                    return render_template('auth/login.html')
                elif selected_role == 'dealer' and user.role != 'dealer':
                    flash('Access Denied: The provided account is not a licensed Dealer account.', 'danger')
                    return render_template('auth/login.html')
                elif selected_role == 'customer' and user.role != 'citizen':
                    flash('Access Denied: The provided account is not a Customer / Cardholder account.', 'danger')
                    return render_template('auth/login.html')

                login_user(user, remember=True)
                flash(f'Welcome back, {user.full_name}! Logged in as {user.role.upper()}.', 'success')
                
                # Check for next query parameter safely
                next_page = request.args.get('next') or request.form.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                
                # Role-based dashboard redirection
                if user.role in ['admin', 'inspector']:
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'dealer':
                    return redirect(url_for('dealer_pos'))
                elif user.role == 'citizen':
                    return redirect(url_for('citizen_dashboard'))
                
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password. Please verify credentials.', 'danger')
                
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been securely logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/citizen/dashboard')
    @role_required('citizen', 'admin', 'inspector')
    def citizen_dashboard():
        card = None
        if current_user.role == 'citizen':
            if not current_user.ration_card_id:
                flash("Account Error: Your citizen account is not linked to a Ration Card.", "danger")
                return redirect(url_for('login'))
            card = current_user.ration_card
        else:
            # Admin/Inspector viewing customer portal
            card_id = request.args.get('card_id', type=int)
            if card_id:
                card = db.session.get(RationCard, card_id)
            else:
                card = RationCard.query.first()

        if not card:
            flash("No Ration Card record available to display.", "warning")
            return redirect(url_for('admin_dashboard') if current_user.role in ['admin', 'inspector'] else url_for('login'))

        family_members = FamilyMember.query.filter_by(ration_card_id=card.id, is_active=True).all()
        quota_status = get_beneficiary_quota_status(card)
        transactions = DistributionTransaction.query.filter_by(ration_card_id=card.id).order_by(
            DistributionTransaction.transaction_date.desc()
        ).all()
        complaints = Grievance.query.filter(
            db.or_(Grievance.ration_card_id == card.id, Grievance.ration_card_number == card.card_number)
        ).order_by(Grievance.created_at.desc()).all()

        return render_template(
            'citizen/dashboard.html',
            card=card,
            family_members=family_members,
            quota_status=quota_status,
            transactions=transactions,
            complaints=complaints
        )

    @app.route('/receipt/<int:transaction_id>')
    def view_receipt(transaction_id):
        tx = db.session.get(DistributionTransaction, transaction_id)
        if not tx:
            abort(404)
            
        # Security checks for logged-in role
        if current_user.is_authenticated:
            if current_user.role == 'citizen':
                if tx.ration_card_id != current_user.ration_card_id:
                    flash("Access Denied: You are only authorized to view your own e-Receipts.", "danger")
                    return redirect(url_for('citizen_dashboard'))
            elif current_user.role == 'dealer':
                if tx.shop_id != current_user.shop_id:
                    flash("Access Denied: Dealers can only view receipts from their assigned shop.", "danger")
                    return redirect(url_for('dealer_pos'))

        return render_template('reports/receipt.html', transaction=tx)


    # =========================================================================
    # DEALER POS & OPERATIONS
    # =========================================================================

    @app.route('/dealer/pos', methods=['GET', 'POST'])
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
        family_members = []
        this_month_purchases = []
        family_purchase_history = []
        duplicate_alerts = {}
        current_period = datetime.now().strftime('%Y-%m')
        
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
                    quota_status = get_beneficiary_quota_status(selected_card, month_period=current_period)
                    family_members = FamilyMember.query.filter_by(ration_card_id=selected_card.id, is_active=True).all()
                    this_month_purchases = DistributionTransaction.query.filter_by(
                        ration_card_id=selected_card.id,
                        month_period=current_period
                    ).order_by(DistributionTransaction.transaction_date.desc()).all()
                    family_purchase_history = DistributionTransaction.query.filter_by(
                        ration_card_id=selected_card.id
                    ).order_by(DistributionTransaction.transaction_date.desc()).all()
                    duplicate_alerts = check_monthly_duplicate_purchases(selected_card, month_period=current_period)
            else:
                flash(f"No active Ration Card found with query: '{card_search}'", 'warning')

        return render_template(
            'dealer/pos.html',
            shop=shop,
            selected_card=selected_card,
            quota_status=quota_status,
            stock_status=stock_status,
            commodities=commodities,
            card_search=card_search,
            family_members=family_members,
            this_month_purchases=this_month_purchases,
            family_purchase_history=family_purchase_history,
            duplicate_alerts=duplicate_alerts,
            current_period=current_period
        )

    @app.route('/dealer/pos/process-sale', methods=['POST'])
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
            return redirect(url_for('dealer_pos', card_number=ration_card.card_number))

    @app.route('/dealer/stock')
    @role_required('dealer')
    def dealer_stock():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)
        stock_reports = estimate_stock_depletion(shop.id)
        
        allocations = GrainAllocation.query.filter_by(shop_id=shop.id).order_by(
            GrainAllocation.created_at.desc()
        ).limit(10).all()
        
        return render_template(
            'dealer/stock.html',
            shop=shop,
            stock_reports=stock_reports,
            allocations=allocations
        )

    @app.route('/dealer/sales-history')
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
        )

    @app.route('/dealer/demand-forecast')
    @role_required('dealer')
    def dealer_demand_forecast():
        if not current_user.shop_id:
            flash("Account Error: Dealer not assigned to a shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)
            
        commodity_id = request.args.get('commodity_id', type=int)
        forecasts = calculate_demand_forecast(shop_id=shop.id, commodity_id=commodity_id)
        
        return render_template(
            'dealer/demand_forecast.html',
            shop=shop,
            forecasts=forecasts
        )

    # =========================================================================
    # ADMIN PORTAL
    # =========================================================================

    @app.route('/admin/dashboard')
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
        )

    @app.route('/admin/shops', methods=['GET', 'POST'])
    @role_required('admin', 'inspector')
    def admin_shops():
        if request.method == 'POST':
            shop_code = request.form.get('shop_code', '').strip().upper()
            shop_name = request.form.get('shop_name', '').strip()
            dealer_name = request.form.get('dealer_name', '').strip()
            license_no = request.form.get('license_no', '').strip()
            contact_no = request.form.get('contact_no', '').strip()
            address = request.form.get('address', '').strip()
            ward = request.form.get('ward', '').strip()
            district = request.form.get('district', 'Central District').strip()

            dealer_username = request.form.get('dealer_username', '').strip()
            dealer_password = request.form.get('dealer_password', '').strip()

            if FairPriceShop.query.filter_by(shop_code=shop_code).first():
                flash(f"Shop Code {shop_code} already exists.", 'danger')
            elif FairPriceShop.query.filter_by(license_no=license_no).first():
                flash(f"License Number {license_no} already registered.", 'danger')
            elif dealer_username and User.query.filter_by(username=dealer_username).first():
                flash(f"Username '{dealer_username}' is already taken by another account.", 'danger')
            else:
                new_shop = FairPriceShop(
                    shop_code=shop_code,
                    shop_name=shop_name,
                    dealer_name=dealer_name,
                    license_no=license_no,
                    contact_no=contact_no,
                    address=address,
                    ward=ward,
                    district=district
                )
                db.session.add(new_shop)
                db.session.flush()

                commodities = Commodity.query.filter_by(is_active=True).all()
                for comm in commodities:
                    stk = ShopStock(shop_id=new_shop.id, commodity_id=comm.id, current_stock=0.0, min_threshold=150.0)
                    db.session.add(stk)

                if dealer_username:
                    d_user = User(
                        username=dealer_username,
                        full_name=dealer_name,
                        email=f"{dealer_username}@rationsmart.gov.in",
                        phone=contact_no,
                        role='dealer',
                        shop_id=new_shop.id
                    )
                    d_user.set_password(dealer_password or 'dealer123')
                    db.session.add(d_user)

                db.session.commit()
                flash(f"Fair Price Shop '{shop_name}' ({shop_code}) registered successfully!", 'success')
                return redirect(url_for('admin_shops'))

        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()
        return render_template('admin/shops.html', shops=shops)

    @app.route('/admin/shops/<int:shop_id>/edit', methods=['POST'])
    @role_required('admin', 'inspector')
    def edit_shop(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        shop.shop_name = request.form.get('shop_name', shop.shop_name)
        shop.dealer_name = request.form.get('dealer_name', shop.dealer_name)
        shop.contact_no = request.form.get('contact_no', shop.contact_no)
        shop.address = request.form.get('address', shop.address)
        shop.ward = request.form.get('ward', shop.ward)
        shop.status = request.form.get('status', shop.status)
        
        db.session.commit()
        flash(f"Updated details for Fair Price Shop {shop.shop_code}.", 'success')
        return redirect(url_for('admin_shops'))

    @app.route('/admin/beneficiaries', methods=['GET', 'POST'])
    @role_required('admin', 'inspector')
    def admin_beneficiaries():
        if request.method == 'POST':
            card_number = request.form.get('card_number', '').strip().upper()
            card_type = request.form.get('card_type', 'PHH')
            head_of_family = request.form.get('head_of_family', '').strip()
            family_members = int(request.form.get('family_members_count', 1))
            aadhaar_last4 = request.form.get('aadhaar_last4', '').strip()
            mobile = request.form.get('mobile', '').strip()
            address = request.form.get('address', '').strip()
            assigned_shop_id = int(request.form.get('assigned_shop_id', 1))

            if RationCard.query.filter_by(card_number=card_number).first():
                flash(f"Ration Card Number {card_number} is already registered.", 'danger')
            else:
                new_card = RationCard(
                    card_number=card_number,
                    card_type=card_type,
                    head_of_family=head_of_family,
                    family_members_count=family_members,
                    aadhaar_last4=aadhaar_last4,
                    mobile=mobile,
                    address=address,
                    assigned_shop_id=assigned_shop_id,
                    status='Active'
                )
                db.session.add(new_card)
                db.session.flush()

                # Add head of family as primary family member
                head_member = FamilyMember(
                    ration_card_id=new_card.id,
                    full_name=head_of_family,
                    relationship='Self (Head)',
                    age=40,
                    gender='Male',
                    aadhaar_last4=aadhaar_last4
                )
                db.session.add(head_member)
                db.session.commit()
                flash(f"Ration Card {card_number} ({card_type}) registered successfully!", 'success')
                return redirect(url_for('admin_beneficiaries'))

        card_type_filter = request.args.get('card_type', '')
        shop_filter = request.args.get('shop_id', type=int)
        search_query = request.args.get('search', '').strip()

        query = RationCard.query
        if card_type_filter:
            query = query.filter_by(card_type=card_type_filter)
        if shop_filter:
            query = query.filter_by(assigned_shop_id=shop_filter)
        if search_query:
            query = query.filter(
                (RationCard.card_number.ilike(f"%{search_query}%")) |
                (RationCard.head_of_family.ilike(f"%{search_query}%")) |
                (RationCard.mobile.ilike(f"%{search_query}%"))
            )

        beneficiaries = query.order_by(RationCard.id.desc()).all()
        shops = FairPriceShop.query.filter_by(status='Active').all()

        return render_template(
            'admin/beneficiaries.html',
            beneficiaries=beneficiaries,
            shops=shops,
            card_type_filter=card_type_filter,
            shop_filter=shop_filter,
            search_query=search_query
        )

    @app.route('/admin/beneficiaries/<int:card_id>/delete', methods=['POST'])
    @role_required('admin', 'inspector')
    def delete_beneficiary(card_id):
        card = db.session.get(RationCard, card_id)
        if card:
            # Manually delete family members if CASCADE is not working or to be safe
            FamilyMember.query.filter_by(ration_card_id=card.id).delete()
            db.session.delete(card)
            db.session.commit()
            flash('Beneficiary deleted successfully.', 'success')
        return redirect(url_for('admin_beneficiaries'))

    @app.route('/admin/beneficiaries/<int:card_id>/edit', methods=['POST'])
    @role_required('admin', 'inspector')
    def edit_beneficiary(card_id):
        card = db.session.get(RationCard, card_id)
        if card:
            card.head_of_family = request.form.get('head_of_family', card.head_of_family)
            card.family_members_count = int(request.form.get('family_members_count', card.family_members_count))
            card.mobile = request.form.get('mobile', card.mobile)
            db.session.commit()
            flash('Beneficiary details updated.', 'success')
        return redirect(url_for('admin_beneficiaries'))

    @app.route('/admin/allocations', methods=['GET', 'POST'])
    @role_required('admin', 'inspector')
    def admin_allocations():
        if request.method == 'POST':
            shop_id = request.form.get('shop_id', type=int)
            commodity_id = request.form.get('commodity_id', type=int)
            allocated_qty = float(request.form.get('allocated_qty', 0.0))
            allocation_month = request.form.get('allocation_month', datetime.now().strftime('%Y-%m'))
            status = request.form.get('status', 'Received')
            notes = request.form.get('notes', '').strip()

            alloc_code = f"ALC-{allocation_month}-{int(datetime.now().timestamp()) % 10000:04d}"
            
            allocation = GrainAllocation(
                allocation_code=alloc_code,
                shop_id=shop_id,
                commodity_id=commodity_id,
                allocated_qty=allocated_qty,
                allocation_month=allocation_month,
                dispatch_date=date.today(),
                status=status,
                notes=notes
            )
            db.session.add(allocation)
            
            if status == 'Received':
                stock = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=commodity_id).first()
                if stock:
                    stock.current_stock += allocated_qty
                    stock.last_replenished_at = datetime.now()
                else:
                    new_stock = ShopStock(
                        shop_id=shop_id,
                        commodity_id=commodity_id,
                        current_stock=allocated_qty,
                        last_replenished_at=datetime.now()
                    )
                    db.session.add(new_stock)

            db.session.commit()
            flash(f"PDS Grain Allocation #{alloc_code} dispatched successfully!", 'success')
            return redirect(url_for('admin_allocations'))

        allocations = GrainAllocation.query.order_by(GrainAllocation.created_at.desc()).all()
        shops = FairPriceShop.query.filter_by(status='Active').all()
        commodities = Commodity.query.filter_by(is_active=True).all()
        allocation_rules = AllocationRule.query.order_by(AllocationRule.card_type, AllocationRule.commodity_id).all()

        return render_template(
            'admin/allocations.html',
            allocations=allocations,
            shops=shops,
            commodities=commodities,
            allocation_rules=allocation_rules
        )

    @app.route('/admin/allocation-rules', methods=['POST'])
    @role_required('admin', 'inspector')
    def admin_allocation_rules():
        card_type = request.form.get('card_type', '').strip().upper()
        commodity_id = request.form.get('commodity_id', type=int)
        allocation_basis = request.form.get('allocation_basis', 'PER_PERSON').strip().upper()
        quantity_per_unit = float(request.form.get('quantity_per_unit', 0.0))
        unit = request.form.get('unit', 'kg').strip()
        is_active = request.form.get('is_active') == '1'

        if not card_type or not commodity_id:
            flash("Allocation Rule Error: Card Type and Commodity are required.", "danger")
            return redirect(url_for('admin_allocations'))

        rule = AllocationRule.query.filter_by(card_type=card_type, commodity_id=commodity_id).first()
        if rule:
            rule.allocation_basis = allocation_basis
            rule.quantity_per_unit = quantity_per_unit
            rule.unit = unit
            rule.is_active = is_active
            rule.updated_at = datetime.now()
            action_name = "updated"
        else:
            rule = AllocationRule(
                card_type=card_type,
                commodity_id=commodity_id,
                allocation_basis=allocation_basis,
                quantity_per_unit=quantity_per_unit,
                unit=unit,
                is_active=is_active
            )
            db.session.add(rule)
            action_name = "created"

        db.session.commit()
        flash(f"Entitlement Allocation Rule for {card_type} {action_name} successfully!", "success")
        return redirect(url_for('admin_allocations'))

    @app.route('/admin/stock')
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
        )

    @app.route('/admin/stock/adjust', methods=['POST'])
    @role_required('admin', 'inspector')
    def adjust_stock():
        shop_id = request.form.get('shop_id', type=int)
        commodity_id = request.form.get('commodity_id', type=int)
        new_stock_qty = float(request.form.get('new_stock_qty', 0.0))
        min_threshold = float(request.form.get('min_threshold', 150.0))
        
        stock = ShopStock.query.filter_by(shop_id=shop_id, commodity_id=commodity_id).first()
        if stock:
            stock.current_stock = max(0.0, new_stock_qty)
            stock.min_threshold = max(10.0, min_threshold)
            stock.updated_at = datetime.now()
        else:
            stock = ShopStock(
                shop_id=shop_id,
                commodity_id=commodity_id,
                current_stock=max(0.0, new_stock_qty),
                min_threshold=min_threshold
            )
            db.session.add(stock)
            
        db.session.commit()
        flash('Shop inventory & alert threshold updated successfully.', 'success')
        return redirect(url_for('admin_stock'))

    @app.route('/admin/demand-forecast')
    @role_required('admin', 'inspector')
    def admin_demand_forecast():
        shop_id = request.args.get('shop_id', type=int)
        commodity_id = request.args.get('commodity_id', type=int)
        
        forecasts = calculate_demand_forecast(shop_id=shop_id, commodity_id=commodity_id)
        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()
        commodities = Commodity.query.filter_by(is_active=True).all()
        
        return render_template(
            'admin/demand_forecast.html',
            forecasts=forecasts,
            shops=shops,
            commodities=commodities,
            selected_shop_id=shop_id,
            selected_commodity_id=commodity_id
        )

    @app.route('/admin/transaction-alerts')
    @role_required('admin', 'inspector')
    def admin_transaction_alerts():
        return admin_anomalies()

    @app.route('/admin/anomalies')
    @role_required('admin', 'inspector')
    def admin_anomalies():
        severity_filter = request.args.get('severity', '')
        status_filter = request.args.get('status', '')
        
        query = AnomalyLog.query
        if severity_filter:
            query = query.filter_by(severity=severity_filter)
        if status_filter:
            query = query.filter_by(status=status_filter)
            
        anomalies = query.order_by(AnomalyLog.detected_at.desc()).all()
        return render_template(
            'admin/anomalies.html',
            anomalies=anomalies,
            severity_filter=severity_filter,
            status_filter=status_filter
        )

    @app.route('/admin/anomalies/<int:anomaly_id>/resolve', methods=['POST'])
    @role_required('admin', 'inspector')
    def resolve_anomaly(anomaly_id):
        anomaly = db.session.get(AnomalyLog, anomaly_id)
        if not anomaly:
            abort(404)
        action_status = request.form.get('status', 'Resolved')
        notes = request.form.get('resolution_notes', '').strip()
        
        anomaly.status = action_status
        anomaly.resolution_notes = notes
        db.session.commit()
        
        flash(f"Anomaly status updated to '{action_status}'.", 'success')
        return redirect(url_for('admin_anomalies'))

    # =========================================================================
    # QR CODE-BASED COMPLAINT MANAGEMENT SYSTEM
    # =========================================================================

    VALID_COMPLAINT_CATEGORIES = [
        'Grain/product quality',
        'Shortage of quantity',
        'Incorrect billing or overcharging',
        'Dealer behaviour',
        'Shop opening hours',
        'Stock unavailability',
        'Other'
    ]

    def generate_complaint_code():
        import random, string
        prefix = datetime.utcnow().strftime('CMP-%Y%m-')
        for _ in range(100):
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = prefix + suffix
            if not Grievance.query.filter_by(grievance_code=code).first():
                return code
        return prefix + uuid.uuid4().hex[:5].upper()

    @app.route('/qr/shop/<int:shop_id>')
    def shop_qr_code(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        # Build URL using request context/host dynamically (no hardcoded localhost)
        target_url = url_for('raise_complaint', shop_code=shop.shop_code, _external=True)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#244A36", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        as_download = request.args.get('download') is not None
        filename = f"Shop_{shop.shop_code}_Complaint_QR.png"
        return send_file(img_io, mimetype='image/png', as_attachment=as_download, download_name=filename)

    @app.route('/admin/shop/<int:shop_id>/qr/print')
    @role_required('admin', 'inspector')
    def admin_shop_qr_print(shop_id):
        shop = db.session.get(FairPriceShop, shop_id)
        if not shop:
            abort(404)
        target_url = url_for('raise_complaint', shop_code=shop.shop_code, _external=True)
        return render_template('admin/shop_qr_print.html', shop=shop, target_url=target_url)

    @app.route('/complaints/raise', methods=['GET', 'POST'])
    def raise_complaint():
        # Require citizen authentication before accessing private complaint history or submitting named complaint
        if not current_user.is_authenticated:
            flash("Citizen authentication is required to register an official complaint. Please sign in with your Ration Card.", "warning")
            return redirect(url_for('login', next=request.full_path))

        shop_code = request.args.get('shop_code', '').strip().upper() or request.form.get('shop_code', '').strip().upper()
        shop_id_arg = request.args.get('shop_id', type=int) or request.form.get('shop_id', type=int)

        selected_shop = None
        if shop_code:
            selected_shop = FairPriceShop.query.filter_by(shop_code=shop_code).first()
        elif shop_id_arg:
            selected_shop = db.session.get(FairPriceShop, shop_id_arg)

        all_shops = FairPriceShop.query.filter_by(status='Active').all() or FairPriceShop.query.all()
        all_commodities = Commodity.query.filter_by(is_active=True).all() or Commodity.query.all()

        card = current_user.ration_card if current_user.role == 'citizen' else None
        if current_user.role == 'citizen' and not card:
            flash("Account Error: Your citizen account is not linked to an active Ration Card.", "danger")
            return redirect(url_for('login'))

        if not selected_shop:
            if card and card.assigned_shop:
                selected_shop = card.assigned_shop
            elif all_shops:
                selected_shop = all_shops[0]

        if request.method == 'POST':
            category = request.form.get('category', '').strip()
            subject = request.form.get('subject', '').strip()
            description = request.form.get('description', '').strip()
            commodity_id = request.form.get('commodity_id', type=int)
            submitted_shop_id = request.form.get('shop_id', type=int)

            errors = []
            if category not in VALID_COMPLAINT_CATEGORIES:
                errors.append(f"Invalid complaint category selected. Please choose from: {', '.join(VALID_COMPLAINT_CATEGORIES)}")

            target_shop = db.session.get(FairPriceShop, submitted_shop_id) if submitted_shop_id else None
            if not target_shop:
                errors.append("Please select a valid Fair Price Shop.")

            if not subject or len(subject) < 5 or len(subject) > 150:
                errors.append("Complaint subject must be between 5 and 150 characters.")

            if not description or len(description) < 10 or len(description) > 2000:
                errors.append("Detailed description must be between 10 and 2000 characters.")

            if commodity_id:
                comm = db.session.get(Commodity, commodity_id)
                if not comm:
                    errors.append("Selected commodity does not exist.")

            card_num = card.card_number if card else current_user.username
            card_id_val = card.id if card else None
            citizen_name_val = card.head_of_family if card else current_user.full_name
            citizen_phone_val = (card.mobile if card else current_user.phone) or "Not Provided"

            # Anti-duplicate submission check within 60 seconds
            dup_check = Grievance.query.filter(
                Grievance.ration_card_number == card_num,
                Grievance.shop_id == (target_shop.id if target_shop else None),
                Grievance.subject == subject,
                Grievance.description == description,
                Grievance.created_at >= datetime.utcnow() - timedelta(seconds=60)
            ).first()
            if dup_check:
                flash(f"Duplicate submission detected. You have already registered complaint #{dup_check.grievance_code}.", "warning")
                return redirect(url_for('complaint_confirmation', code=dup_check.grievance_code))

            # Attachment handling & validation
            attachment_path = None
            file = request.files.get('attachment')
            if file and file.filename:
                allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in allowed_extensions:
                    errors.append("Attachment must be an image file (.png, .jpg, .jpeg, or .webp).")
                else:
                    file.stream.seek(0, os.SEEK_END)
                    size = file.stream.tell()
                    file.stream.seek(0)
                    if size > 3 * 1024 * 1024:
                        errors.append("Attachment file size must not exceed 3 MB.")
                    else:
                        try:
                            img = Image.open(file.stream)
                            img.verify()
                            file.stream.seek(0)

                            safe_base = secure_filename(file.filename) or f"upload{ext}"
                            unique_filename = f"{uuid.uuid4().hex[:12]}_{safe_base}"
                            save_path = os.path.join(app.config['COMPLAINTS_UPLOAD_FOLDER'], unique_filename)
                            file.save(save_path)
                            attachment_path = unique_filename
                        except Exception:
                            errors.append("Uploaded file is not a valid image.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    'complaints/raise.html',
                    shops=all_shops,
                    commodities=all_commodities,
                    selected_shop=target_shop or selected_shop,
                    categories=VALID_COMPLAINT_CATEGORIES,
                    card=card,
                    form_data=request.form
                )

            code = generate_complaint_code()
            complaint = Grievance(
                grievance_code=code,
                ration_card_number=card_num,
                citizen_name=citizen_name_val,
                citizen_phone=citizen_phone_val,
                shop_id=target_shop.id,
                category=category,
                commodity_id=commodity_id if commodity_id else None,
                ration_card_id=card_id_val,
                user_id=current_user.id,
                subject=subject,
                description=description,
                attachment_path=attachment_path,
                status='Pending',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(complaint)
            db.session.flush()

            audit = ComplaintAuditLog(
                complaint_id=complaint.id,
                changed_by_user_id=current_user.id,
                old_status=None,
                new_status='Pending',
                remarks='Complaint registered by citizen.',
                created_at=datetime.utcnow()
            )
            db.session.add(audit)
            db.session.commit()

            flash(f"Complaint registered successfully. Your Reference Number is #{code}.", "success")
            return redirect(url_for('complaint_confirmation', code=code))

        return render_template(
            'complaints/raise.html',
            shops=all_shops,
            commodities=all_commodities,
            selected_shop=selected_shop,
            categories=VALID_COMPLAINT_CATEGORIES,
            card=card,
            form_data={}
        )

    @app.route('/complaints/confirmation/<string:code>')
    @login_required
    def complaint_confirmation(code):
        complaint = Grievance.query.filter_by(grievance_code=code).first_or_404()

        if current_user.role == 'citizen':
            is_owner = False
            if current_user.ration_card_id and complaint.ration_card_id == current_user.ration_card_id:
                is_owner = True
            elif current_user.ration_card and complaint.ration_card_number == current_user.ration_card.card_number:
                is_owner = True
            elif complaint.user_id == current_user.id:
                is_owner = True
            if not is_owner:
                abort(403)
        elif current_user.role == 'dealer':
            if complaint.shop_id != current_user.shop_id:
                abort(403)

        return render_template('complaints/confirmation.html', complaint=complaint)

    @app.route('/complaints/attachment/<int:complaint_id>')
    @login_required
    def get_complaint_attachment(complaint_id):
        complaint = db.session.get(Grievance, complaint_id)
        if not complaint or not complaint.attachment_path:
            abort(404)

        if current_user.role == 'citizen':
            is_owner = False
            if current_user.ration_card_id and complaint.ration_card_id == current_user.ration_card_id:
                is_owner = True
            elif current_user.ration_card and complaint.ration_card_number == current_user.ration_card.card_number:
                is_owner = True
            elif complaint.user_id == current_user.id:
                is_owner = True
            if not is_owner:
                abort(403)
        elif current_user.role == 'dealer':
            if complaint.shop_id != current_user.shop_id:
                abort(403)
        elif current_user.role not in ['admin', 'inspector']:
            abort(403)

        file_path = os.path.join(app.config['COMPLAINTS_UPLOAD_FOLDER'], complaint.attachment_path)
        if not os.path.isfile(file_path):
            abort(404)
        return send_file(file_path)

    @app.route('/admin/complaints')
    @app.route('/admin/grievances')
    @role_required('admin', 'inspector')
    def admin_grievances():
        search_q = request.args.get('search', '').strip()
        shop_filter = request.args.get('shop_id', type=int)
        cat_filter = request.args.get('category', '').strip()
        status_filter = request.args.get('status', '').strip()
        date_filter = request.args.get('date', '').strip()

        query = Grievance.query

        if search_q:
            query = query.filter(
                db.or_(
                    Grievance.grievance_code.ilike(f'%{search_q}%'),
                    Grievance.ration_card_number.ilike(f'%{search_q}%'),
                    Grievance.citizen_name.ilike(f'%{search_q}%'),
                    Grievance.subject.ilike(f'%{search_q}%')
                )
            )
        if shop_filter:
            query = query.filter(Grievance.shop_id == shop_filter)
        if cat_filter:
            query = query.filter(Grievance.category == cat_filter)
        if status_filter:
            query = query.filter(Grievance.status == status_filter)
        if date_filter:
            try:
                d_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Grievance.created_at) == d_obj)
            except ValueError:
                pass

        grievances = query.order_by(Grievance.created_at.desc()).all()

        total_count = Grievance.query.count()
        pending_count = Grievance.query.filter_by(status='Pending').count()
        in_progress_count = Grievance.query.filter_by(status='In Progress').count()
        resolved_count = Grievance.query.filter_by(status='Resolved').count()
        rejected_count = Grievance.query.filter_by(status='Rejected').count()

        shops = FairPriceShop.query.order_by(FairPriceShop.shop_code).all()
        shop_summaries = []
        for s in shops:
            s_total = Grievance.query.filter_by(shop_id=s.id).count()
            s_pending = Grievance.query.filter_by(shop_id=s.id, status='Pending').count()
            s_resolved = Grievance.query.filter_by(shop_id=s.id, status='Resolved').count()
            if s_total > 0:
                shop_summaries.append({
                    'shop': s,
                    'total': s_total,
                    'pending': s_pending,
                    'resolved': s_resolved
                })

        return render_template(
            'admin/grievances.html',
            grievances=grievances,
            shops=shops,
            categories=VALID_COMPLAINT_CATEGORIES,
            total_count=total_count,
            pending_count=pending_count,
            in_progress_count=in_progress_count,
            resolved_count=resolved_count,
            rejected_count=rejected_count,
            shop_summaries=shop_summaries,
            search_q=search_q,
            shop_filter=shop_filter,
            cat_filter=cat_filter,
            status_filter=status_filter,
            date_filter=date_filter
        )

    @app.route('/admin/complaints/<int:grv_id>/update', methods=['POST'])
    @app.route('/admin/grievances/<int:grv_id>/update', methods=['POST'])
    @role_required('admin', 'inspector')
    def update_grievance(grv_id):
        grv = db.session.get(Grievance, grv_id)
        if not grv:
            abort(404)

        old_status = grv.status
        new_status = request.form.get('status', '').strip()
        remarks = request.form.get('response_text', '').strip()

        if new_status not in ['Pending', 'In Progress', 'Resolved', 'Rejected']:
            flash("Invalid complaint status specified.", "danger")
            return redirect(url_for('admin_grievances'))

        if new_status in ['Resolved', 'Rejected'] and not remarks:
            flash("Resolution remarks are required when marking a complaint as Resolved or Rejected.", "danger")
            return redirect(url_for('admin_grievances'))

        grv.status = new_status
        if remarks:
            grv.response_text = remarks
        grv.updated_at = datetime.utcnow()
        if new_status == 'Resolved':
            grv.resolved_at = datetime.utcnow()

        audit = ComplaintAuditLog(
            complaint_id=grv.id,
            changed_by_user_id=current_user.id,
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
            created_at=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Complaint #{grv.grievance_code} status updated to '{new_status}' with audit trail recorded.", 'success')
        return redirect(url_for('admin_grievances'))

    @app.route('/dealer/complaints')
    @role_required('dealer')
    def dealer_complaints():
        if not current_user.shop_id:
            flash("Account Error: Dealer is not assigned to a Fair Price Shop.", "danger")
            return redirect(url_for('login'))
        shop = current_user.shop
        if not shop:
            abort(404)

        search_q = request.args.get('search', '').strip()
        cat_filter = request.args.get('category', '').strip()
        status_filter = request.args.get('status', '').strip()

        query = Grievance.query.filter_by(shop_id=shop.id)
        if search_q:
            query = query.filter(
                db.or_(
                    Grievance.grievance_code.ilike(f'%{search_q}%'),
                    Grievance.ration_card_number.ilike(f'%{search_q}%'),
                    Grievance.subject.ilike(f'%{search_q}%')
                )
            )
        if cat_filter:
            query = query.filter_by(category=cat_filter)
        if status_filter:
            query = query.filter_by(status=status_filter)

        complaints = query.order_by(Grievance.created_at.desc()).all()

        shop_total = Grievance.query.filter_by(shop_id=shop.id).count()
        shop_pending = Grievance.query.filter_by(shop_id=shop.id, status='Pending').count()
        shop_in_progress = Grievance.query.filter_by(shop_id=shop.id, status='In Progress').count()
        shop_resolved = Grievance.query.filter_by(shop_id=shop.id, status='Resolved').count()

        return render_template(
            'dealer/complaints.html',
            shop=shop,
            complaints=complaints,
            categories=VALID_COMPLAINT_CATEGORIES,
            shop_total=shop_total,
            shop_pending=shop_pending,
            shop_in_progress=shop_in_progress,
            shop_resolved=shop_resolved,
            search_q=search_q,
            cat_filter=cat_filter,
            status_filter=status_filter
        )

    @app.route('/dealer/complaints/<int:complaint_id>/update', methods=['POST'])
    @role_required('dealer')
    def dealer_update_complaint(complaint_id):
        complaint = db.session.get(Grievance, complaint_id)
        if not complaint:
            abort(404)

        # Strict backend authorization: Dealer CANNOT view or modify another shop's complaint
        if complaint.shop_id != current_user.shop_id:
            abort(403)

        if complaint.status in ['Resolved', 'Rejected']:
            flash("This complaint has already been concluded and cannot be edited by the shop dealer.", "danger")
            return redirect(url_for('dealer_complaints'))

        new_status = request.form.get('status', '').strip()
        remarks = request.form.get('response_text', '').strip()

        if new_status not in ['In Progress', 'Resolved']:
            flash("Invalid status change: Dealers may set status to 'In Progress' or 'Resolved' only.", "danger")
            return redirect(url_for('dealer_complaints'))

        if new_status == 'Resolved' and not remarks:
            flash("Resolution remarks are required when marking a complaint as Resolved.", "danger")
            return redirect(url_for('dealer_complaints'))

        old_status = complaint.status
        complaint.status = new_status
        if remarks:
            complaint.response_text = remarks
        complaint.updated_at = datetime.utcnow()
        if new_status == 'Resolved':
            complaint.resolved_at = datetime.utcnow()

        audit = ComplaintAuditLog(
            complaint_id=complaint.id,
            changed_by_user_id=current_user.id,
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
            created_at=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Complaint #{complaint.grievance_code} updated successfully.", "success")
        return redirect(url_for('dealer_complaints'))

    @app.route('/citizen/complaints/<int:complaint_id>')
    @login_required
    def citizen_complaint_detail(complaint_id):
        complaint = db.session.get(Grievance, complaint_id)
        if not complaint:
            abort(404)
        if current_user.role == 'citizen':
            is_owner = False
            if current_user.ration_card_id and complaint.ration_card_id == current_user.ration_card_id:
                is_owner = True
            elif current_user.ration_card and complaint.ration_card_number == current_user.ration_card.card_number:
                is_owner = True
            elif complaint.user_id == current_user.id:
                is_owner = True
            if not is_owner:
                abort(403)
        elif current_user.role == 'dealer':
            if complaint.shop_id != current_user.shop_id:
                abort(403)

        return jsonify({
            'id': complaint.id,
            'code': complaint.grievance_code,
            'category': complaint.category,
            'subject': complaint.subject,
            'description': complaint.description,
            'status': complaint.status,
            'shop': complaint.shop.shop_name if complaint.shop else 'N/A',
            'shop_code': complaint.shop.shop_code if complaint.shop else '',
            'created_at': complaint.created_at.strftime('%d-%b-%Y %I:%M %p') if complaint.created_at else '',
            'response_text': complaint.response_text,
            'attachment_url': url_for('get_complaint_attachment', complaint_id=complaint.id) if complaint.attachment_path else None
        })


    @app.route('/admin/reports')
    @role_required('admin', 'inspector')
    def admin_reports():
        current_month = datetime.now().strftime('%Y-%m')
        
        comm_stats = db.session.query(
            Commodity.name,
            Commodity.unit,
            db.func.sum(TransactionItem.quantity).label('total_distributed'),
            db.func.sum(TransactionItem.subtotal).label('total_revenue')
        ).join(TransactionItem, Commodity.id == TransactionItem.commodity_id
        ).join(DistributionTransaction, DistributionTransaction.id == TransactionItem.transaction_id
        ).filter(DistributionTransaction.month_period == current_month
        ).group_by(Commodity.id).all()
        
        shop_stats = db.session.query(
            FairPriceShop.shop_code,
            FairPriceShop.shop_name,
            FairPriceShop.dealer_name,
            db.func.count(DistributionTransaction.id).label('tx_count'),
            db.func.sum(DistributionTransaction.total_amount).label('revenue')
        ).outerjoin(DistributionTransaction, FairPriceShop.id == DistributionTransaction.shop_id
        ).group_by(FairPriceShop.id).all()
        
        return render_template(
            'admin/reports.html',
            comm_stats=comm_stats,
            shop_stats=shop_stats,
            current_month=current_month
        )

    @app.route('/admin/transactions')
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
        )


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

    # =========================================================================
    # JSON API ENDPOINTS
    # =========================================================================

    @app.route('/api/beneficiary/<card_number>')
    def api_beneficiary_quota(card_number):
        card = RationCard.query.filter_by(card_number=card_number).first()
        if not card:
            return jsonify({'success': False, 'message': 'Ration card not found'}), 404
        
        quota = get_beneficiary_quota_status(card)
        members = FamilyMember.query.filter_by(ration_card_id=card.id, is_active=True).all()
        return jsonify({
            'success': True,
            'card_number': card.card_number,
            'head_of_family': card.head_of_family,
            'card_type': card.card_type,
            'family_members': card.family_members_count,
            'members_list': [{'name': m.full_name, 'relation': m.relationship, 'age': m.age, 'gender': m.gender} for m in members],
            'assigned_shop': card.assigned_shop.shop_name if card.assigned_shop else 'N/A',
            'quota': quota
        })

    @app.route('/api/analytics/monthly-distribution')
    def api_monthly_distribution():
        commodities = Commodity.query.filter_by(is_active=True).all()
        labels = [c.name for c in commodities]
        current_month = datetime.now().strftime('%Y-%m')
        
        data = []
        for c in commodities:
            qty = db.session.query(db.func.sum(TransactionItem.quantity)).join(
                DistributionTransaction
            ).filter(
                TransactionItem.commodity_id == c.id,
                DistributionTransaction.month_period == current_month
            ).scalar() or 0.0
            data.append(round(qty, 1))
            
        return jsonify({
            'labels': labels,
            'data': data
        })

    @app.route('/api/analytics/card-categories')
    def api_card_categories():
        results = db.session.query(
            RationCard.card_type, db.func.count(RationCard.id)
        ).group_by(RationCard.card_type).all()
        
        labels = [r[0] for r in results]
        counts = [r[1] for r in results]
        
        return jsonify({
            'labels': labels,
            'counts': counts
        })

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        if not User.query.first():
            from seed_data import seed_database
            seed_database(app)
            
    print("=================================================================")
    print(" [RationSmart] Web Application is Running on http://127.0.0.1:5000")
    print(" Admin:   admin    / admin123")
    print(" Dealer:  dealer1  / dealer123")
    
    print("=================================================================")
    app.run(debug=True, host='0.0.0.0', port=5000)
