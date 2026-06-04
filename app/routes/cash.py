from flask import Blueprint, render_template
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Sale
from app import db
from datetime import datetime

cash_bp = Blueprint('cash', __name__, url_prefix='/cash')

@cash_bp.route('/')
@login_required
def cash_register():
    today = datetime.utcnow().date()
    today_sales = Sale.query.filter(
        db.func.date(Sale.created_at) == today,
        Sale.status == 'completed'
    ).all()

    cash_total = card_total = debt_total = 0
    for s in today_sales:
        total = float(s.grand_total)
        if s.payment_method == 'cash':
            cash_total += total
        elif s.payment_method == 'credit_card':
            card_total += total
        elif s.payment_method == 'debt':
            debt_total += total

    grand_total = cash_total + card_total + debt_total

    return render_template('cash.html',
        cash_total=cash_total, card_total=card_total,
        debt_total=debt_total, grand_total=grand_total,
        sales_count=len(today_sales),
        today_sales=today_sales, today=today)
