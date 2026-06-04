from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id
from app.models import CashRegister, Sale, Expense
from app import db
from datetime import datetime, date

cashreg_bp = Blueprint('cashreg', __name__, url_prefix='/cash-register')

@cashreg_bp.route('/')
@login_required
def index():
    open_reg = CashRegister.query.filter_by(status='open', branch_id=get_branch_id()).first()
    registers = CashRegister.query.filter_by(branch_id=get_branch_id()).order_by(CashRegister.opened_at.desc()).limit(30).all()
    return render_template('cash_register.html', open_reg=open_reg, registers=registers)

@cashreg_bp.route('/open', methods=['POST'])
@login_required
def open_register():
    existing = CashRegister.query.filter_by(status='open', branch_id=get_branch_id()).first()
    if existing:
        flash('Zaten açık bir kasa var', 'error')
        return redirect(url_for('cashreg.index'))
    try:
        balance = round(float(request.form.get('opening_balance', 0)), 2)
        reg = CashRegister(
            user_id=get_user_id(), branch_id=get_branch_id(),
            opening_balance=balance, status='open',
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(reg)
        db.session.commit()
        flash('Kasa açıldı', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('cashreg.index'))

@cashreg_bp.route('/close', methods=['POST'])
@login_required
def close_register():
    reg = CashRegister.query.filter_by(status='open', branch_id=get_branch_id()).first()
    if not reg:
        flash('Açık kasa bulunamadı', 'error')
        return redirect(url_for('cashreg.index'))
    try:
        actual = round(float(request.form.get('closing_balance', 0)), 2)
        today = date.today()
        sales = Sale.query.filter(
            Sale.branch_id == get_branch_id(),
            Sale.status == 'completed',
            db.func.date(Sale.created_at) == today
        ).all()
        cash_total = sum(float(s.grand_total) for s in sales if s.payment_method == 'cash')
        card_total = sum(float(s.grand_total) for s in sales if s.payment_method == 'credit_card')

        expenses = Expense.query.filter(
            Expense.branch_id == get_branch_id(),
            db.func.date(Expense.expense_date) == today
        ).all()
        expense_total = sum(float(e.amount) for e in expenses)

        expected = round(float(reg.opening_balance) + cash_total - expense_total, 2)
        diff = round(actual - expected, 2)

        reg.closing_balance = actual
        reg.expected_balance = expected
        reg.difference = diff
        reg.status = 'closed'
        reg.closed_at = datetime.utcnow()
        reg.notes = (reg.notes or '') + f' | Nakit: {cash_total:.2f} Kart: {card_total:.2f} Gider: {expense_total:.2f}'
        db.session.commit()

        if diff != 0:
            flash(f'Kasa kapandı. Beklenen: {expected:.2f} ₺, Gerçek: {actual:.2f} ₺, Fark: {diff:.2f} ₺', 'warning')
        else:
            flash(f'Kasa kapandı. Tutar: {actual:.2f} ₺ (Tam)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('cashreg.index'))

@cashreg_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    reg = CashRegister.query.get_or_404(id)
    return render_template('cash_register_detail.html', reg=reg)
