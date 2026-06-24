from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, require_permission, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Expense
from app import db
from datetime import datetime

expense_bp = Blueprint('expense', __name__, url_prefix='/expense')

EXPENSE_CATEGORIES = ['Kira', 'Fatura', 'Maaş', 'Nakliye', 'Vergi', 'Tamir-Bakım', 'Kırtasiye', 'Reklam', 'Yazılım', 'Diğer']

@expense_bp.route('/')
@login_required
@require_permission('expense')
def expense_list():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    cat = request.args.get('category', '')
    query = Expense.query
    if cat:
        query = query.filter(Expense.category == cat)
    expenses = query.order_by(Expense.expense_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('expenses.html', expenses=expenses, categories=EXPENSE_CATEGORIES, selected_cat=cat)

@expense_bp.route('/add', methods=['POST'])
@login_required
@require_permission('expense')
def add_expense():
    try:
        amount = float(request.form.get('amount', 0) or 0)
    except ValueError:
        flash('Geçersiz tutar', 'error')
        return redirect(url_for('expense.expense_list'))
    if amount <= 0:
        flash('Tutar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('expense.expense_list'))
    category = request.form.get('category', '').strip()
    if category not in EXPENSE_CATEGORIES:
        flash('Geçersiz gider kategorisi', 'error')
        return redirect(url_for('expense.expense_list'))
    try:
        expense = Expense(
            user_id=get_user_id(),
            branch_id=get_branch_id(),
            amount=amount,
            category=category,
            description=request.form.get('description', '').strip(),
            payment_method=request.form.get('payment_method', 'cash'),
            expense_date=datetime.now()
        )
        db.session.add(expense)
        db.session.commit()
        flash('Gider kaydedildi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('expense.expense_list'))

@expense_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('expense')
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Gider silindi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('expense.expense_list'))
