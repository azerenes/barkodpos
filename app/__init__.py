import json, logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text as sa_text
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.pos import pos_bp
    from app.routes.stock import stock_bp
    from app.routes.customer import customer_bp
    from app.routes.report import report_bp
    from app.routes.employee import employee_bp
    from app.routes.branch import branch_bp
    from app.routes.purchase import purchase_bp
    from app.routes.cash import cash_bp
    from app.routes.settings import settings_bp
    from app.routes.receipt import receipt_bp
    from app.routes.transfer import transfer_bp
    from app.routes.supplier import supplier_bp
    from app.routes.expense import expense_bp
    from app.routes.stock_count import stock_count_bp
    from app.routes.cash_register import cashreg_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(branch_bp)
    app.register_blueprint(purchase_bp)
    app.register_blueprint(cash_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(receipt_bp)
    app.register_blueprint(transfer_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(stock_count_bp)
    app.register_blueprint(cashreg_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_user():
        from flask import session
        return dict(
            current_user_id=session.get('user_id'),
            current_user_name=session.get('user_name', ''),
            current_user_role=session.get('role'),
            current_user_branch_id=session.get('branch_id'),
            current_user_is_admin=session.get('role') == 'admin',
            current_user_is_authenticated='user_id' in session
        )

    @app.template_filter('from_json')
    def from_json_filter(s):
        try:
            return json.loads(s)
        except Exception:
            return {}

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('error.html', code=404, message='Sayfa bulunamadı'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('error.html', code=500, message='Sunucu hatası'), 500

    with app.app_context():
        from app import models
        db.create_all()
        with db.engine.connect() as conn:
            conn.execute(sa_text('PRAGMA journal_mode=WAL'))
            conn.execute(sa_text('PRAGMA busy_timeout=5000'))

        from app.models import User, Category

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                full_name='Admin',
                role='admin'
            )
            db.session.add(admin)

        if not Category.query.first():
            default_cats = [
                'Bardak', 'Tabak', 'Çatal-Kaşık-Bıçak', 'Saklama Kabı',
                'Mutfak Aleti', 'Porselen & Seramik', 'Cam Ürünleri',
                'Dekorasyon & Ev Aksesuar', 'Bahçe & Balkon', 'Temizlik',
                'Hediye & Parti', 'Elektrikli Ev Aleti', 'Çocuk & Oyuncak',
                'Ofis & Kırtasiye', 'Gıda & Şarküteri'
            ]
            for name in default_cats:
                db.session.add(Category(name=name))

        db.session.commit()

        import os, shutil
        # Migrate existing DB from any old location to APPDATA/BarkodPOS/data/
        from config import get_data_dir
        new_db = os.path.join(get_data_dir(), 'barkodpos.db')

        if not os.path.exists(new_db):
            candidates = [
                os.path.join(app.instance_path, 'barkodpos.db'),
                os.path.join(os.path.dirname(app.instance_path.rstrip(os.sep)), 'instance', 'barkodpos.db'),
                os.path.join(os.getcwd(), 'instance', 'barkodpos.db'),
            ]
            import sys as _sys
            if getattr(_sys, 'frozen', False):
                exe_dir = os.path.dirname(_sys.executable)
                candidates.append(os.path.join(exe_dir, 'instance', 'barkodpos.db'))
            for old_db in candidates:
                if os.path.exists(old_db):
                    os.makedirs(os.path.dirname(new_db), exist_ok=True)
                    shutil.copy2(old_db, new_db)
                    break

        # migrate existing DB — add columns if missing
        with db.engine.connect() as conn:
            for stmt in [
                'ALTER TABLE products ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)',
                'ALTER TABLE products ADD COLUMN tax_rate NUMERIC(5,2) DEFAULT 0',
                'ALTER TABLE sale_items ADD COLUMN tax_rate NUMERIC(5,2) DEFAULT 0',
                'ALTER TABLE sale_items ADD COLUMN tax_amount NUMERIC(10,2) DEFAULT 0',
                'ALTER TABLE products ADD COLUMN wholesale_price NUMERIC(10,2) DEFAULT 0',
                'ALTER TABLE products ADD COLUMN wholesale_min_qty NUMERIC(10,2) DEFAULT 0',
                'ALTER TABLE products ADD COLUMN is_set BOOLEAN DEFAULT 0',
                'ALTER TABLE products ADD COLUMN is_quick_product BOOLEAN DEFAULT 0',
                'ALTER TABLE products ADD COLUMN is_stockless BOOLEAN DEFAULT 0',
            ]:
                try:
                    conn.execute(sa_text(stmt))
                except Exception:
                    pass
        from datetime import date, timedelta
        try:
            backup_dir = os.path.join(get_data_dir(), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            db_path = os.path.join(get_data_dir(), 'barkodpos.db')
            if os.path.exists(db_path):
                today = date.today().isoformat()
                backup_file = os.path.join(backup_dir, f'barkodpos_{today}.db')
                if not os.path.exists(backup_file):
                    shutil.copy2(db_path, backup_file)
                    from app.models import Product
                    products = Product.query.filter_by(is_active=True).all()
                    snapshot = [{
                        'barcode': p.barcode, 'name': p.name,
                        'purchase_price': float(p.purchase_price or 0),
                        'sale_price': float(p.sale_price or 0),
                        'stock_qty': float(p.stock_qty or 0),
                        'min_stock_qty': float(p.min_stock_qty or 0),
                        'unit': p.unit, 'is_stockless': p.is_stockless
                    } for p in products]
                    with open(os.path.join(backup_dir, f'stok_fiyat_{today}.json'), 'w', encoding='utf-8') as f:
                        json.dump(snapshot, f, ensure_ascii=False, indent=2)
                cutoff = date.today() - timedelta(days=30)
                for fname in os.listdir(backup_dir):
                    if not (fname.startswith('barkodpos_') or fname.startswith('stok_fiyat_')):
                        continue
                    fdate_str = fname.split('_')[1].split('.')[0]
                    try:
                        fdate = date.fromisoformat(fdate_str)
                        if fdate < cutoff:
                            os.remove(os.path.join(backup_dir, fname))
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass

    return app
