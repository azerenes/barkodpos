from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default='employee')
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Branch(db.Model):
    __tablename__ = 'branches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)
    users = db.relationship('User', backref='branch', lazy=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    purchase_price = db.Column(db.Numeric(10,2), default=0)
    sale_price = db.Column(db.Numeric(10,2), default=0)
    tax_rate = db.Column(db.Numeric(5,2), default=0)
    unit = db.Column(db.String(20), default='Adet')
    stock_qty = db.Column(db.Numeric(10,2), default=0)
    min_stock_qty = db.Column(db.Numeric(10,2), default=0)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    wholesale_price = db.Column(db.Numeric(10,2), default=0)
    wholesale_min_qty = db.Column(db.Numeric(10,2), default=0)
    is_set = db.Column(db.Boolean, default=False)
    is_quick_product = db.Column(db.Boolean, default=False)
    is_stockless = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    tax_office = db.Column(db.String(100))
    tax_number = db.Column(db.String(50))
    balance = db.Column(db.Numeric(10,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    sales = db.relationship('Sale', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    total_amount = db.Column(db.Numeric(10,2), default=0)
    discount = db.Column(db.Numeric(10,2), default=0)
    tax_amount = db.Column(db.Numeric(10,2), default=0)
    grand_total = db.Column(db.Numeric(10,2), default=0)
    payment_method = db.Column(db.String(20), default='cash')
    status = db.Column(db.Enum('completed', 'cancelled'), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.now)
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='sales')

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(200))
    barcode = db.Column(db.String(50))
    quantity = db.Column(db.Numeric(10,2), default=1)
    unit_price = db.Column(db.Numeric(10,2), default=0)
    total_price = db.Column(db.Numeric(10,2), default=0)
    tax_rate = db.Column(db.Numeric(5,2), default=0)
    tax_amount = db.Column(db.Numeric(10,2), default=0)
    product = db.relationship('Product')

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    type = db.Column(db.Enum('entry', 'exit', 'transfer_in', 'transfer_out', 'sale', 'return'), nullable=False)
    quantity = db.Column(db.Numeric(10,2), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    product = db.relationship('Product')
    user = db.relationship('User', backref='stock_movements')

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    tax_office = db.Column(db.String(100))
    tax_number = db.Column(db.String(50))
    contact_person = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    products = db.relationship('Product', backref='supplier', lazy=True)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    amount = db.Column(db.Numeric(10,2), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    payment_method = db.Column(db.Enum('cash', 'credit_card', 'bank_transfer'), default='cash')
    expense_date = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='expenses')

class PurchaseInvoice(db.Model):
    __tablename__ = 'purchase_invoices'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    invoice_no = db.Column(db.String(100))
    invoice_date = db.Column(db.DateTime, default=datetime.now)
    total_amount = db.Column(db.Numeric(10,2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    supplier = db.relationship('Supplier')
    user = db.relationship('User')

class PurchaseInvoiceItem(db.Model):
    __tablename__ = 'purchase_invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('purchase_invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,2), default=1)
    unit_price = db.Column(db.Numeric(10,2), default=0)
    total_price = db.Column(db.Numeric(10,2), default=0)
    product = db.relationship('Product')
    invoice = db.relationship('PurchaseInvoice', backref='items')

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    price_type = db.Column(db.Enum('purchase', 'sale'), nullable=False)
    old_price = db.Column(db.Numeric(10,2), default=0)
    new_price = db.Column(db.Numeric(10,2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    product = db.relationship('Product')
    user = db.relationship('User')

class CashRegister(db.Model):
    __tablename__ = 'cash_registers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    opening_balance = db.Column(db.Numeric(10,2), default=0)
    closing_balance = db.Column(db.Numeric(10,2), default=0)
    expected_balance = db.Column(db.Numeric(10,2), default=0)
    difference = db.Column(db.Numeric(10,2), default=0)
    status = db.Column(db.Enum('open', 'closed'), default='open')
    notes = db.Column(db.Text)
    opened_at = db.Column(db.DateTime, default=datetime.now)
    closed_at = db.Column(db.DateTime)
    user = db.relationship('User')

class ProductPrice(db.Model):
    __tablename__ = 'product_prices'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    price_type = db.Column(db.String(20), nullable=False)  # retail, wholesale
    price = db.Column(db.Numeric(10,2), default=0)
    min_qty = db.Column(db.Numeric(10,2), default=0)
    product = db.relationship('Product')

class RecipeItem(db.Model):
    __tablename__ = 'recipe_items'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,2), default=1)
    product = db.relationship('Product', foreign_keys=[product_id])
    component = db.relationship('Product', foreign_keys=[component_id])

class StockCount(db.Model):
    __tablename__ = 'stock_counts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    status = db.Column(db.Enum('in_progress', 'completed', 'cancelled'), default='in_progress')
    notes = db.Column(db.Text)
    total_items = db.Column(db.Integer, default=0)
    matched_items = db.Column(db.Integer, default=0)
    mismatch_items = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    user = db.relationship('User')

class StockCountItem(db.Model):
    __tablename__ = 'stock_count_items'
    id = db.Column(db.Integer, primary_key=True)
    count_id = db.Column(db.Integer, db.ForeignKey('stock_counts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    system_qty = db.Column(db.Numeric(10,2), default=0)
    counted_qty = db.Column(db.Numeric(10,2), default=0)
    difference = db.Column(db.Numeric(10,2), default=0)
    status = db.Column(db.Enum('pending', 'matched', 'mismatch'), default='pending')
    product = db.relationship('Product')
    count = db.relationship('StockCount', backref='items')

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Numeric(10,2), nullable=False)
    type = db.Column(db.Enum('payment', 'collection'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User')

class SavedReport(db.Model):
    __tablename__ = 'saved_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(200), nullable=False)
    period = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User')
