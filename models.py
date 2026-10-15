from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='citizen') # 'admin', 'dealer', 'citizen'
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=True)
    ration_card_id = db.Column(db.Integer, db.ForeignKey('ration_cards.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    shop = db.relationship('FairPriceShop', backref='dealers', foreign_keys=[shop_id])
    ration_card = db.relationship('RationCard', backref='citizen_user', foreign_keys=[ration_card_id])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role in ['admin', 'inspector']

    def is_dealer(self):
        return self.role == 'dealer'

    def is_citizen(self):
        return self.role == 'citizen'
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class FairPriceShop(db.Model):
    __tablename__ = 'ration_shops'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_code = db.Column(db.String(32), unique=True, nullable=False, index=True) # e.g. FPS-101
    shop_name = db.Column(db.String(150), nullable=False)
    dealer_name = db.Column(db.String(120), nullable=False)
    license_no = db.Column(db.String(64), unique=True, nullable=False)
    contact_no = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    ward = db.Column(db.String(64), nullable=False)
    district = db.Column(db.String(64), nullable=False, default='Central District')
    status = db.Column(db.String(20), default='Active') # 'Active', 'Inactive', 'Suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stocks = db.relationship('ShopStock', backref='shop', cascade='all, delete-orphan', lazy=True)
    ration_cards = db.relationship('RationCard', backref='assigned_shop', lazy=True)
    allocations = db.relationship('GrainAllocation', backref='shop', cascade='all, delete-orphan', lazy=True)
    transactions = db.relationship('DistributionTransaction', backref='shop', lazy=True)
    
    def __repr__(self):
        return f"<RationShop {self.shop_code} - {self.shop_name}>"

# Alias for compatibility
RationShop = FairPriceShop


class RationCard(db.Model):
    __tablename__ = 'ration_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(64), unique=True, nullable=False, index=True) # e.g. RC-AAY-1001
    card_type = db.Column(db.String(20), nullable=False) # 'AAY', 'PHH', 'NPHH', 'AY'
    head_of_family = db.Column(db.String(120), nullable=False)
    family_members_count = db.Column(db.Integer, nullable=False, default=1)
    aadhaar_last4 = db.Column(db.String(4), nullable=False) # e.g. '8821'
    mobile = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=False)
    assigned_shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=False)
    status = db.Column(db.String(20), default='Active') # 'Active', 'Suspended', 'Cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    family_members = db.relationship('FamilyMember', backref='ration_card', cascade='all, delete-orphan', lazy=True)
    transactions = db.relationship('DistributionTransaction', backref='ration_card', lazy=True)
    
    def get_card_type_badge(self):
        badges = {
            'AAY': ('AAY - Antyodaya Anna Yojana (Yellow)', 'bg-warning text-dark'),
            'PHH': ('PHH - Priority Household (Pink)', 'bg-danger text-white'),
            'NPHH': ('NPHH - Non-Priority Household (White/Blue)', 'bg-primary text-white'),
            'NPHH-S': ('NPHH-S - Non-Priority Household - Sugar (White)', 'bg-info text-dark'),
            'AY': ('AY - Annapurna Yojana (Green)', 'bg-success text-white')
        }
        return badges.get(self.card_type, (f"{self.card_type} Card", 'bg-secondary text-white'))

    def __repr__(self):
        return f"<RationCard {self.card_number} ({self.card_type}) - {self.head_of_family}>"


class AllocationRule(db.Model):
    __tablename__ = 'allocation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    card_type = db.Column(db.String(20), nullable=False) # 'PHH', 'AAY', 'NPHH', 'NPHH-S', 'AY'
    commodity_id = db.Column(db.Integer, db.ForeignKey('commodities.id'), nullable=False)
    allocation_basis = db.Column(db.String(20), nullable=False, default='PER_PERSON') # 'PER_PERSON', 'PER_CARD'
    quantity_per_unit = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False, default='kg')
    effective_month = db.Column(db.Integer, nullable=True)
    effective_year = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    commodity = db.relationship('Commodity', lazy=True)
    
    def __repr__(self):
        return f"<AllocationRule {self.card_type} + {self.commodity_id} ({self.allocation_basis}: {self.quantity_per_unit} {self.unit})>"


class FamilyMember(db.Model):
    __tablename__ = 'family_members'
    
    id = db.Column(db.Integer, primary_key=True)
    ration_card_id = db.Column(db.Integer, db.ForeignKey('ration_cards.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(64), nullable=False) # 'Self (Head)', 'Spouse', 'Son', 'Daughter', 'Mother', 'Father'
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False) # 'Male', 'Female', 'Other'
    aadhaar_last4 = db.Column(db.String(4), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<FamilyMember {self.full_name} ({self.relationship}) - Card:{self.ration_card_id}>"


class Commodity(db.Model):
    __tablename__ = 'commodities'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False) # 'RICE', 'WHEAT', 'SUGAR', 'KEROSENE', 'DAL'
    name = db.Column(db.String(64), nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='kg') # 'kg', 'liter'
    price_per_unit = db.Column(db.Float, nullable=False, default=0.0) # Subsidized price in INR
    is_active = db.Column(db.Boolean, default=True)
    
    stocks = db.relationship('ShopStock', backref='commodity', lazy=True)
    allocation_items = db.relationship('GrainAllocation', backref='commodity', lazy=True)
    
    def __repr__(self):
        return f"<Commodity {self.name} ({self.unit}) @ ₹{self.price_per_unit}>"


class GrainAllocation(db.Model):
    __tablename__ = 'grain_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    allocation_code = db.Column(db.String(64), unique=True, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=False)
    commodity_id = db.Column(db.Integer, db.ForeignKey('commodities.id'), nullable=False)
    allocated_qty = db.Column(db.Float, nullable=False)
    allocation_month = db.Column(db.String(7), nullable=False) # 'YYYY-MM'
    dispatch_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='Received')
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<GrainAllocation {self.allocation_code}: {self.allocated_qty} to Shop {self.shop_id}>"


class ShopStock(db.Model):
    __tablename__ = 'shop_stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=False)
    commodity_id = db.Column(db.Integer, db.ForeignKey('commodities.id'), nullable=False)
    current_stock = db.Column(db.Float, nullable=False, default=0.0)
    min_threshold = db.Column(db.Float, nullable=False, default=150.0)
    last_replenished_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('shop_id', 'commodity_id', name='uq_shop_commodity_stock'),)
    
    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_threshold

    def __repr__(self):
        return f"<ShopStock Shop:{self.shop_id} Comm:{self.commodity_id} Stock:{self.current_stock}>"


class DistributionTransaction(db.Model):
    __tablename__ = 'distribution_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(64), unique=True, nullable=False, index=True)
    ration_card_id = db.Column(db.Integer, db.ForeignKey('ration_cards.id'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id'), nullable=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    month_period = db.Column(db.String(7), nullable=False) # 'YYYY-MM'
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_mode = db.Column(db.String(32), default='Cash / Direct Subsidy')
    auth_mode = db.Column(db.String(64), default='Biometric Aadhaar Authentication (Simulated)')
    status = db.Column(db.String(20), default='Completed')
    notes = db.Column(db.String(255), nullable=True)
    
    items = db.relationship('TransactionItem', backref='transaction', cascade='all, delete-orphan', lazy=True)
    anomalies = db.relationship('AnomalyLog', backref='transaction', lazy=True)
    dealer_user = db.relationship('User', backref='recorded_sales', foreign_keys=[user_id])
    purchasing_member = db.relationship('FamilyMember', foreign_keys=[family_member_id], lazy=True)

    @property
    def purchaser_display(self):
        if self.purchasing_member:
            return f"{self.purchasing_member.full_name} ({self.purchasing_member.relationship})"
        if self.ration_card:
            return f"{self.ration_card.head_of_family} (Head of Family)"
        return "Customer / Beneficiary"
    
    def __repr__(self):
        return f"<DistributionTransaction {self.bill_number} - Card:{self.ration_card_id}>"


class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('distribution_transactions.id'), nullable=False)
    commodity_id = db.Column(db.Integer, db.ForeignKey('commodities.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    commodity = db.relationship('Commodity', lazy=True)
    
    def __repr__(self):
        return f"<TransactionItem Comm:{self.commodity_id} Qty:{self.quantity}>"


class AnomalyLog(db.Model):
    __tablename__ = 'anomaly_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('distribution_transactions.id'), nullable=True)
    ration_card_id = db.Column(db.Integer, db.ForeignKey('ration_cards.id'), nullable=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=True)
    anomaly_type = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(20), default='Medium')
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Flagged')
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    ration_card = db.relationship('RationCard', lazy=True)
    shop = db.relationship('FairPriceShop', lazy=True)
    
    def __repr__(self):
        return f"<AnomalyLog [{self.severity}] {self.anomaly_type}>"


class Grievance(db.Model):
    __tablename__ = 'grievances'
    
    id = db.Column(db.Integer, primary_key=True)
    grievance_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    ration_card_number = db.Column(db.String(64), nullable=False, index=True)
    citizen_name = db.Column(db.String(120), nullable=False)
    citizen_phone = db.Column(db.String(20), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('ration_shops.id'), nullable=True)
    category = db.Column(db.String(100), default='Other', nullable=False)
    commodity_id = db.Column(db.Integer, db.ForeignKey('commodities.id'), nullable=True)
    ration_card_id = db.Column(db.Integer, db.ForeignKey('ration_cards.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Pending') # 'Pending', 'In Progress', 'Resolved', 'Rejected'
    response_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    shop = db.relationship('FairPriceShop', lazy=True)
    commodity = db.relationship('Commodity', lazy=True)
    ration_card = db.relationship('RationCard', foreign_keys=[ration_card_id], lazy=True)
    submitter = db.relationship('User', foreign_keys=[user_id], lazy=True)
    audit_logs = db.relationship('ComplaintAuditLog', backref='complaint', lazy=True, cascade='all, delete-orphan', order_by='ComplaintAuditLog.created_at.desc()')
    
    @property
    def complaint_number(self):
        return self.grievance_code
    
    def __repr__(self):
        return f"<Grievance {self.grievance_code} - {self.subject}>"


Complaint = Grievance


class ComplaintAuditLog(db.Model):
    __tablename__ = 'complaint_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('grievances.id'), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    changed_by = db.relationship('User', foreign_keys=[changed_by_user_id], lazy=True)
    
    def __repr__(self):
        return f"<ComplaintAuditLog Complaint:{self.complaint_id} {self.old_status}->{self.new_status}>"

