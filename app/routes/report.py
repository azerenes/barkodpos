from flask import Blueprint, render_template, request, jsonify, Response
from app.auth_helper import login_required, require_permission, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Sale, SaleItem, Product, Expense, StockMovement, SavedReport
from app import db
from datetime import datetime, timedelta
import json, os, shutil

report_bp = Blueprint('report', __name__, url_prefix='/report')

def get_period_range(period):
    today = datetime.now().date()
    if period == 'today':
        return today, today + timedelta(days=1)
    elif period == 'week':
        return today - timedelta(days=today.weekday()), today + timedelta(days=1)
    elif period == 'month':
        return today.replace(day=1), today + timedelta(days=1)
    elif period == 'year':
        return today.replace(month=1, day=1), today + timedelta(days=1)
    return today, today + timedelta(days=1)

def build_report_data(start_date, end_date):
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

        return {
            'sales': sales,
            'cancelled_sales': cancelled_sales,
            'total_sales': total_sales,
            'total_count': total_count,
            'avg_sale': avg_sale,
            'return_total': return_total,
            'return_count': return_count,
            'product_stats': product_stats,
            'payment_stats': payment_stats,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'total_expenses': total_expenses,
            'cash_total': cash_total,
            'card_total': card_total,
            'cash_count': cash_count,
        }
    except Exception:
        return {
            'sales': [], 'cancelled_sales': [], 'product_stats': [], 'payment_stats': [],
            'total_sales': 0, 'total_count': 0, 'avg_sale': 0,
            'return_total': 0, 'return_count': 0,
            'gross_profit': 0, 'net_profit': 0, 'total_expenses': 0,
            'cash_total': 0, 'card_total': 0, 'cash_count': 0,
        }

def build_daily_breakdown(start_date, end_date):
    days = []
    current = start_date
    while current < end_date:
        day_end = current + timedelta(days=1)
        if day_end > end_date:
            day_end = end_date
        total = db.session.query(db.func.sum(Sale.grand_total)).filter(
            Sale.created_at >= current, Sale.created_at < day_end,
            Sale.status == 'completed'
        ).scalar() or 0
        count = Sale.query.filter(
            Sale.created_at >= current, Sale.created_at < day_end,
            Sale.status == 'completed'
        ).count()
        days.append({
            'date': current.strftime('%d.%m.%Y'),
            'total': float(total),
            'count': count,
            'day_name': current.strftime('%A')
        })
        current = day_end
    return days

@report_bp.route('/')
@login_required
@require_permission('report')
def reports():
    period = request.args.get('period', 'today')
    start_date, end_date = get_period_range(period)
    data = build_report_data(start_date, end_date)
    daily_breakdown = build_daily_breakdown(start_date, end_date)
    saved_reports = SavedReport.query.order_by(SavedReport.created_at.desc()).limit(20).all()
    return render_template('reports.html',
        period=period, daily_breakdown=daily_breakdown,
        saved_reports=saved_reports,
        **data)

@report_bp.route('/save-report', methods=['POST'])
@login_required
@require_permission('report')
def save_report():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403
    period = request.args.get('period', 'today')
    start_date, end_date = get_period_range(period)
    data = build_report_data(start_date, end_date)
    report_data = {
        'period': period,
        'total_sales': data['total_sales'],
        'total_count': data['total_count'],
        'avg_sale': data['avg_sale'],
        'return_total': data['return_total'],
        'return_count': data['return_count'],
        'gross_profit': data['gross_profit'],
        'net_profit': data['net_profit'],
        'total_expenses': data['total_expenses'],
        'cash_total': data['cash_total'],
        'card_total': data['card_total'],
    }
    period_labels = {'today': 'Günlük', 'week': 'Haftalık', 'month': 'Aylık', 'year': 'Yıllık'}
    label = period_labels.get(period, period)
    name = f"{label} Rapor - {start_date.strftime('%d.%m.%Y')}"
    report = SavedReport(
        user_id=get_user_id(),
        name=name,
        period=period,
        start_date=start_date,
        end_date=end_date,
        data_json=json.dumps(report_data, ensure_ascii=False, default=str)
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'success': True, 'name': name})

@report_bp.route('/saved-reports')
@login_required
@require_permission('report')
def list_saved_reports():
    reports = SavedReport.query.order_by(SavedReport.created_at.desc()).all()
    result = []
    for r in reports:
        result.append({
            'id': r.id,
            'name': r.name,
            'period': r.period,
            'created_at': r.created_at.strftime('%d.%m.%Y %H:%M'),
            'data': json.loads(r.data_json),
        })
    return jsonify(result)

@report_bp.route('/delete-report/<int:report_id>', methods=['POST'])
@login_required
@require_permission('report')
def delete_report(report_id):
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403
    report = SavedReport.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})

@report_bp.route('/reset-sales', methods=['POST'])
@login_required
@require_permission('report')
def reset_sales():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403

    try:
        from config import get_data_dir
        db_path = os.path.join(get_data_dir(), 'barkodpos.db')
        backup_path = os.path.join(get_data_dir(),
            f'sales_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)

        SaleItem.query.delete()
        Sale.query.delete()

        StockMovement.query.filter(
            StockMovement.type.in_(['sale', 'return'])
        ).delete(synchronize_session=False)

        products = Product.query.all()
        for p in products:
            entries = db.session.query(db.func.coalesce(db.func.sum(StockMovement.quantity), 0)).filter(
                StockMovement.product_id == p.id,
                StockMovement.type.in_(['entry', 'transfer_in'])
            ).scalar()
            exits = db.session.query(db.func.coalesce(db.func.sum(StockMovement.quantity), 0)).filter(
                StockMovement.product_id == p.id,
                StockMovement.type.in_(['exit', 'transfer_out'])
            ).scalar()
            new_stock = float(entries) - float(exits)
            p.stock_qty = max(0, round(new_stock, 2))

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Tüm satışlar silindi, stoklar yeniden hesaplandı.',
            'backup': os.path.basename(backup_path)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@report_bp.route('/weekly-data')
@login_required
@require_permission('report')
def weekly_data():
    today = datetime.now().date()
    days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    labels = []
    totals = []
    for i in range(7):
        d = today - timedelta(days=today.weekday() - i)
        total = db.session.query(db.func.sum(Sale.grand_total)).filter(
            Sale.created_at >= d, Sale.created_at < d + timedelta(days=1),
            Sale.status == 'completed'
        ).scalar() or 0
        labels.append(days[i])
        totals.append(float(total))
    return jsonify({'labels': labels, 'totals': totals})

@report_bp.route('/payment-data')
@login_required
@require_permission('report')
def payment_data():
    today = datetime.now().date()
    cash = db.session.query(db.func.sum(Sale.grand_total)).filter(
        db.func.date(Sale.created_at) == today, Sale.payment_method == 'cash', Sale.status == 'completed'
    ).scalar() or 0
    card = db.session.query(db.func.sum(Sale.grand_total)).filter(
        db.func.date(Sale.created_at) == today, Sale.payment_method == 'credit_card', Sale.status == 'completed'
    ).scalar() or 0
    return jsonify({'cash': float(cash), 'card': float(card)})

@report_bp.route('/export-csv')
@login_required
@require_permission('report')
def export_report_csv():
    period = request.args.get('period', 'today')
    start_date, end_date = get_period_range(period)
    all_sales = Sale.query.filter(
        Sale.created_at >= start_date, Sale.created_at < end_date
    ).order_by(Sale.created_at.desc()).all()

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Fis No', 'Musteri', 'Tutar', 'Indirim', 'Odeme', 'Tarih', 'Tur'])
    for s in all_sales:
        writer.writerow([
            s.receipt_no or '',
            s.customer.name if s.customer else '',
            str(s.grand_total or 0), str(s.discount or 0),
            s.payment_method or '',
            s.created_at.strftime('%d.%m.%Y %H:%M') if s.created_at else '',
            'Iade' if s.status == 'cancelled' else 'Satis'
        ])
    csv_output = output.getvalue()
    return Response(
        '\ufeff' + csv_output,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=satis_raporu_{period}.csv'}
    )
