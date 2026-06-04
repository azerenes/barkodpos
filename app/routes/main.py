from flask import Blueprint, render_template, request, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Customer, Sale, StockMovement
from app import db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard/')
@login_required
def dashboard():
    today = datetime.utcnow().date()
    today_sales = Sale.query.filter(
        db.func.date(Sale.created_at) == today,
        Sale.status == 'completed'
    ).all()

    total_sales_today = sum(float(s.grand_total) for s in today_sales)
    total_products = Product.query.filter_by(is_active=True).count()
    total_customers = Customer.query.count()
    low_stock_list = Product.query.filter(
        Product.stock_qty <= Product.min_stock_qty,
        Product.is_active == True
    ).order_by(Product.stock_qty.asc()).limit(20).all()
    low_stock_count = len(low_stock_list)

    recent_sales = Sale.query.filter_by(status='completed')\
        .order_by(Sale.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
        total_sales_today=total_sales_today,
        total_products=total_products,
        total_customers=total_customers,
        low_stock_products=low_stock_list,
        low_stock_count=low_stock_count,
        recent_sales=recent_sales,
        sales_count_today=len(today_sales),
        today=today)

@main_bp.route('/diagnostic/info')
@login_required
def diagnostic_info():
    import platform, sys, os
    try:
        from app.update_helper import CURRENT_VERSION, GITHUB_OWNER, GITHUB_REPO
    except:
        CURRENT_VERSION = '?'
        GITHUB_OWNER = 'azerenes'
        GITHUB_REPO = 'BarkodPOS'
    info = {
        'version': CURRENT_VERSION,
        'github_owner': GITHUB_OWNER,
        'github_repo': GITHUB_REPO,
        'os': platform.platform(),
        'python': sys.version,
        'app_dir': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'user_id': get_user_id(),
        'user_name': get_user_name(),
        'branch_id': get_branch_id(),
        'is_admin': is_admin(),
        'time': datetime.utcnow().isoformat(),
    }
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance', 'barkodpos.db')
        if os.path.exists(db_path):
            info['db_size_mb'] = round(os.path.getsize(db_path) / (1024*1024), 2)
            info['db_mtime'] = datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat()
    except:
        pass
    return jsonify(info)
