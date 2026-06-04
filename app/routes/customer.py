from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Customer, Payment, Sale
from app import db

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/')
@login_required
def customer_list():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    search = request.args.get('q', '').strip()
    query = Customer.query
    if search:
        like = f'%{search}%'
        query = query.filter(Customer.name.ilike(like))
    customers = query.order_by(Customer.name).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('customers.html', customers=customers, search=search)

@customer_bp.route('/add', methods=['POST'])
@login_required
def add_customer():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Müşteri adı zorunludur', 'error')
        return redirect(url_for('customer.customer_list'))

    customer = Customer(
        name=name,
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        address=request.form.get('address', '').strip(),
        tax_office=request.form.get('tax_office', '').strip(),
        tax_number=request.form.get('tax_number', '').strip()
    )
    try:
        db.session.add(customer)
        db.session.commit()
        flash('Müşteri eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Eklenirken hata: {str(e)}', 'error')
    return redirect(url_for('customer.customer_list'))

@customer_bp.route('/detail/<int:id>')
@login_required
def customer_detail(id):
    customer = Customer.query.get_or_404(id)
    payments = Payment.query.filter_by(customer_id=customer.id).order_by(Payment.created_at.desc()).all()
    sales = Sale.query.filter_by(customer_id=customer.id, status='completed').order_by(Sale.created_at.desc()).all()
    return render_template('customer_detail.html', customer=customer, payments=payments, sales=sales)

@customer_bp.route('/payment/<int:id>', methods=['POST'])
@login_required
def add_payment(id):
    customer = Customer.query.get_or_404(id)
    try:
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash('Geçersiz tutar', 'error')
        return redirect(url_for('customer.customer_detail', id=customer.id))

    if amount <= 0:
        flash('Tutar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('customer.customer_detail', id=customer.id))

    payment_type = request.form.get('type')
    if payment_type not in ['payment', 'collection']:
        flash('Geçersiz işlem tipi', 'error')
        return redirect(url_for('customer.customer_detail', id=customer.id))

    description = request.form.get('description', '').strip()

    try:
        payment = Payment(
            customer_id=customer.id,
            user_id=get_user_id(),
            amount=amount,
            type=payment_type,
            description=description
        )
        db.session.add(payment)

        if payment_type == 'payment':
            customer.balance = float(customer.balance) - amount
        else:
            customer.balance = float(customer.balance) + amount

        db.session.commit()
        flash('İşlem kaydedildi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'İşlem hatası: {str(e)}', 'error')

    return redirect(url_for('customer.customer_detail', id=customer.id))

@customer_bp.route('/extract/<int:id>')
@login_required
def extract(id):
    customer = Customer.query.get_or_404(id)
    sales = Sale.query.filter_by(customer_id=id, status='completed').order_by(Sale.created_at.desc()).all()
    payments = Payment.query.filter_by(customer_id=id).order_by(Payment.created_at.desc()).all()
    return render_template('customer_extract.html', customer=customer, sales=sales, payments=payments)

@customer_bp.route('/extract/<int:id>/json')
@login_required
def extract_json(id):
    customer = Customer.query.get_or_404(id)
    sales = Sale.query.filter_by(customer_id=id, status='completed').order_by(Sale.created_at).all()
    payments = Payment.query.filter_by(customer_id=id).order_by(Payment.created_at).all()
    rows = []
    balance = 0
    for s in sales:
        balance += float(s.grand_total)
        rows.append({
            'date': s.created_at.strftime('%d.%m.%Y %H:%M'), 'type': 'satis',
            'desc': f'Satis #{s.receipt_no}', 'debit': float(s.grand_total),
            'credit': 0, 'balance': round(balance, 2)
        })
    for p in payments:
        amt = float(p.amount)
        if p.type == 'collection':
            balance += amt
            rows.append({
                'date': p.created_at.strftime('%d.%m.%Y %H:%M'), 'type': 'tahsilat',
                'desc': p.description or 'Tahsilat', 'debit': amt, 'credit': 0, 'balance': round(balance, 2)
            })
        else:
            balance -= amt
            rows.append({
                'date': p.created_at.strftime('%d.%m.%Y %H:%M'), 'type': 'odeme',
                'desc': p.description or 'Odeme', 'debit': 0, 'credit': amt, 'balance': round(balance, 2)
            })
    rows.sort(key=lambda x: x['date'])
    return jsonify({
        'customer': customer.name, 'balance': round(balance, 2),
        'rows': rows, 'sale_total': sum(float(s.grand_total) for s in sales),
        'payment_total': sum(float(p.amount) for p in payments)
    })
