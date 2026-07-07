from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user')  # admin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(300))
    tax_number = db.Column(db.String(50))
    contact_person = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    projects = db.relationship('Project', backref='client', lazy=True)
    invoices = db.relationship('Invoice', backref='client', lazy=True)


class Subcontractor(db.Model):
    __tablename__ = 'subcontractors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(300))
    tax_number = db.Column(db.String(50))
    contact_person = db.Column(db.String(100))
    specialty = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    payments = db.relationship('SubcontractorPayment', backref='subcontractor', lazy=True)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    status = db.Column(db.String(30), default='active')  # active, completed, paused, cancelled
    contract_value = db.Column(db.Numeric(15, 2), default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    currency = db.Column(db.String(3), default='HUF')

    invoices = db.relationship('Invoice', backref='project', lazy=True, cascade='all, delete-orphan')
    subcontractor_payments = db.relationship('SubcontractorPayment', backref='project', lazy=True, cascade='all, delete-orphan')
    inventory_items = db.relationship('ProjectInventory', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def contract_value_f(self):
        return float(self.contract_value or 0)

    @property
    def total_invoiced(self):
        return sum(
            float(i.amount_with_vat or i.amount or 0)
            for i in self.invoices
            if i.direction == 'outgoing' and i.status != 'cancelled'
        )

    @property
    def total_received(self):
        return sum(
            float(i.amount_with_vat or i.amount or 0)
            for i in self.invoices
            if i.direction == 'outgoing' and i.status == 'paid'
        )

    @property
    def total_subcontractor_cost(self):
        return sum(float(p.amount or 0) for p in self.subcontractor_payments)

    @property
    def total_subcontractor_paid(self):
        return sum(float(p.amount or 0) for p in self.subcontractor_payments if p.status == 'paid')

    @property
    def outstanding(self):
        return self.total_invoiced - self.total_received

    @property
    def profit(self):
        return self.total_received - self.total_subcontractor_paid


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # outgoing (kimenő), incoming (bejövő)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), default=27)
    amount_with_vat = db.Column(db.Numeric(15, 2))
    description = db.Column(db.Text)
    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    paid_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    notes = db.Column(db.Text)
    currency = db.Column(db.String(3), default='HUF')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notification_sent = db.Column(db.Boolean, default=False)
    pdf_data = db.Column(db.LargeBinary, nullable=True)
    pdf_filename = db.Column(db.String(255), nullable=True)


class SubcontractorPayment(db.Model):
    __tablename__ = 'subcontractor_payments'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    subcontractor_id = db.Column(db.Integer, db.ForeignKey('subcontractors.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    paid_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    invoice_ref = db.Column(db.String(100))
    notes = db.Column(db.Text)
    currency = db.Column(db.String(3), default='HUF')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_sent = db.Column(db.Boolean, default=False)


class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100))
    unit = db.Column(db.String(30))  # m, db, kg, stb.
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    total_stock = db.Column(db.Numeric(12, 2), default=0)
    category = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project_usage = db.relationship('ProjectInventory', backref='item', lazy=True, cascade='all, delete-orphan')

    @property
    def used_total(self):
        return sum(float(u.quantity_used) for u in self.project_usage)

    @property
    def remaining(self):
        return float(self.total_stock) - self.used_total


class ProjectInventory(db.Model):
    __tablename__ = 'project_inventory'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity_planned = db.Column(db.Numeric(12, 2), default=0)
    quantity_used = db.Column(db.Numeric(12, 2), default=0)
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def variance(self):
        return float(self.quantity_used) - float(self.quantity_planned)

    @property
    def variance_pct(self):
        if float(self.quantity_planned) == 0:
            return 0
        return ((float(self.quantity_used) - float(self.quantity_planned)) / float(self.quantity_planned)) * 100
