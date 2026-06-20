from flask import Blueprint, render_template, request, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Sale, SaleItem, Product, Expense
from app import db
from datetime import datetime, timedelta

report_bp = Blueprint('report', __name__, url_prefix='/report')

@report_bp.route('/')
@login_required
def reports():
    period = request.args.get('period', 'today')
    today = datetime.utcnow().date()

    period_map = {
        'today': (today, today + timedelta(days=1)),
        'week': (today - timedelta(days=today.weekday()), today + timedelta(days=1)),
        'month': (today.replace(day=1), today + timedelta(days=1)),
        'year': (today.replace(month=1, day=1), today + timedelta(days=1)),
    }
    start_date, end_date = period_map.get(period, (today, today + timedelta(days=1)))

    try:
        all_sales = Sale.query.filter(
            Sale.created_at >= start_date, Sale.created_at < end_date
        ).order_by(Sale.created_at.desc()).all()

        sales = [s for s in all_sales if s.status == 'completed']
        cancelled_sales = [s for s in all_sales if s.status == 'cancelled']

        total_sales = sum(float(s.grand_total) for s in sales)
        total_count = len(sales)
        return_total = sum(float(s.grand_total) for s in cancelled_sales)
        return_count = len(cancelled_sales)
        avg_sale = total_sales / total_count if total_count > 0 else 0

        product_stats = db.session.query(
            SaleItem.product_id, Product.name,
            db.func.sum(SaleItem.quantity).label('total_qty'),
            db.func.sum(SaleItem.total_price).label('total_amount')
        ).join(Product, SaleItem.product_id == Product.id)\
         .join(Sale, SaleItem.sale_id == Sale.id)\
         .filter(Sale.created_at >= start_date, Sale.created_at < end_date, Sale.status == 'completed')\
         .group_by(SaleItem.product_id, Product.name)\
         .order_by(db.desc('total_amount')).limit(20).all()

        payment_stats = db.session.query(
            Sale.payment_method,
            db.func.count(Sale.id).label('count'),
            db.func.sum(Sale.grand_total).label('total')
        ).filter(Sale.created_at >= start_date, Sale.created_at < end_date, Sale.status == 'completed')\
         .group_by(Sale.payment_method).all()

        # profit calculation
        total_purchase_cost = 0
        for s in sales:
            for item in SaleItem.query.filter_by(sale_id=s.id).all():
                prod = Product.query.get(item.product_id)
                if prod:
                    total_purchase_cost += float(item.quantity) * float(prod.purchase_price)
        gross_profit = total_sales - total_purchase_cost
        total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.expense_date >= start_date, Expense.expense_date < end_date
        ).scalar() or 0
        net_profit = gross_profit - float(total_expenses)

        # daily cash summary
        cash_total = db.session.query(db.func.sum(Sale.grand_total)).filter(
            Sale.created_at >= start_date, Sale.created_at < end_date,
            Sale.status == 'completed', Sale.payment_method == 'cash'
        ).scalar() or 0
        card_total = db.session.query(db.func.sum(Sale.grand_total)).filter(
            Sale.created_at >= start_date, Sale.created_at < end_date,
            Sale.status == 'completed', Sale.payment_method == 'credit_card'
        ).scalar() or 0
        cash_count = Sale.query.filter(
            Sale.created_at >= start_date, Sale.created_at < end_date,
            Sale.status == 'completed', Sale.payment_method == 'cash'
        ).count()

    except Exception:
        sales, cancelled_sales, product_stats, payment_stats = [], [], [], []
        total_sales = total_count = avg_sale = 0
        return_total = return_count = 0
        gross_profit = net_profit = total_expenses = 0
        cash_total = card_total = 0
        cash_count = 0

    return render_template('reports.html',
        period=period, sales=sales, cancelled_sales=cancelled_sales,
        total_sales=total_sales, total_count=total_count, avg_sale=avg_sale,
        return_total=return_total, return_count=return_count,
        product_stats=product_stats, payment_stats=payment_stats,
        gross_profit=gross_profit, net_profit=net_profit,
        total_expenses=total_expenses,
        cash_total=cash_total, card_total=card_total,
        cash_count=cash_count)

@report_bp.route('/weekly-data')
@login_required
def weekly_data():
    today = datetime.utcnow().date()
    days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    labels = []
    totals = []
    for i in range(7):
        d = today - timedelta(days=today.weekday() - i)
        day_start = d
        day_end = d + timedelta(days=1)
        total = db.session.query(db.func.sum(Sale.grand_total)).filter(
            Sale.created_at >= day_start, Sale.created_at < day_end,
            Sale.status == 'completed'
        ).scalar() or 0
        labels.append(days[i])
        totals.append(float(total))
    return jsonify({'labels': labels, 'totals': totals})

@report_bp.route('/payment-data')
@login_required
def payment_data():
    today = datetime.utcnow().date()
    cash = db.session.query(db.func.sum(Sale.grand_total)).filter(
        db.func.date(Sale.created_at) == today, Sale.payment_method == 'cash', Sale.status == 'completed'
    ).scalar() or 0
    card = db.session.query(db.func.sum(Sale.grand_total)).filter(
        db.func.date(Sale.created_at) == today, Sale.payment_method == 'credit_card', Sale.status == 'completed'
    ).scalar() or 0
    return jsonify({'cash': float(cash), 'card': float(card)})
