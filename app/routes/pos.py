import threading, random, re
from urllib.parse import unquote
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Sale, SaleItem, Customer, StockMovement, Category
from app import db
from datetime import datetime

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')
_sale_lock = threading.Lock()

@pos_bp.route('/')
@login_required
def pos():
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).limit(30).all()
    categories = Category.query.order_by(Category.name).all()
    recent_sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(20).all()
    quick_products = Product.query.filter_by(is_active=True, is_quick_product=True).order_by(Product.name).all()
    if not quick_products:
        quick_products = products
    return render_template('pos.html', customers=customers, products=quick_products, categories=categories, recent_sales=recent_sales)

@pos_bp.route('/search-product')
@login_required
def search_product():
    q = request.args.get('q', '').strip()
    query = Product.query.filter_by(is_active=True)
    if q:
        escaped = q.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(
            (Product.barcode.like(f'%{escaped}%', escape='\\')) | (Product.name.ilike(f'%{escaped}%', escape='\\'))
        )
    products = query.order_by(Product.name).limit(15).all()
    return jsonify([{
        'id': p.id, 'barcode': p.barcode, 'name': p.name,
        'price': round(float(p.sale_price), 2), 'stock': round(float(p.stock_qty), 2), 'unit': p.unit
    } for p in products])

@pos_bp.route('/quick-sale', methods=['POST'])
@login_required
def quick_sale():
    from datetime import datetime
    from app import db
    try:
        data = request.get_json()
        name = (data.get('name', '') or '').strip()
        price = round(float(data.get('price', 0)), 2)
        if not name:
            return jsonify({'error': 'Ürün adı gerekli'}), 400
        if price <= 0:
            return jsonify({'error': 'Geçersiz fiyat'}), 400

        from app.models import Product, Category

        tax_setting = 0
        from app.routes.settings import get_setting
        try:
            tax_setting = float(get_setting('tax_rate', '0'))
        except:
            pass

        cat = Category.query.order_by(Category.id).first()
        cat_id = cat.id if cat else 1

        barcode = f"QS-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        product = Product(
            barcode=barcode,
            name=f"* {name}",
            sale_price=price,
            purchase_price=price,
            stock_qty=0,
            category_id=cat_id,
            tax_rate=tax_setting,
            is_active=True,
            unit='Adet'
        )
        db.session.add(product)
        db.session.commit()

        return jsonify({
            'id': product.id, 'barcode': product.barcode,
            'name': product.name, 'price': round(float(product.sale_price), 2),
            'stock': 0, 'unit': 'Adet'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Hata: {str(e)}'}), 500

@pos_bp.route('/recent-sales')
@login_required
def recent_sales():
    sales = Sale.query.filter_by(status='completed').order_by(Sale.created_at.desc()).limit(50).all()
    result = []
    for s in sales:
        items = SaleItem.query.filter_by(sale_id=s.id).all()
        result.append({
            'id': s.id,
            'receipt_no': s.receipt_no,
            'total': round(float(s.grand_total), 2),
            'payment_method': s.payment_method,
            'created_at': s.created_at.strftime('%d.%m.%Y %H:%M'),
            'customer_name': s.customer.name if s.customer else '',
            'items': [{'name': i.product_name, 'qty': round(float(i.quantity), 2), 'total': round(float(i.total_price), 2)} for i in items]
        })
    return jsonify(result)

@pos_bp.route('/sale-detail/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    sale = Sale.query.get(sale_id)
    if not sale:
        return jsonify({'error': 'Satış bulunamadı'}), 404
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    return jsonify({
        'id': sale.id,
        'receipt_no': sale.receipt_no,
        'total': round(float(sale.grand_total), 2),
        'discount': round(float(sale.discount), 2),
        'payment_method': sale.payment_method,
        'created_at': sale.created_at.strftime('%d.%m.%Y %H:%M'),
        'customer_name': sale.customer.name if sale.customer else '',
        'items': [{'product_id': i.product_id, 'name': i.product_name, 'barcode': i.barcode,
                   'qty': round(float(i.quantity), 2), 'price': round(float(i.unit_price), 2), 'total': round(float(i.total_price), 2)} for i in items]
    })

@pos_bp.route('/complete-sale', methods=['POST'])
@login_required
def complete_sale():
    with _sale_lock:
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Geçersiz istek'}), 400

            items = data.get('items', [])
            customer_id = data.get('customer_id')
            payment_method = data.get('payment_method', 'cash')
            discount = max(0, round(float(data.get('discount', 0)), 2))

            if not items:
                return jsonify({'error': 'Sepet boş'}), 400
            if payment_method not in ['cash', 'credit_card']:
                return jsonify({'error': 'Geçersiz ödeme yöntemi'}), 400

            receipt_no = f"BP{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{get_user_id()}{random.randint(10,99)}"

            total_amount = 0
            tax_amount = 0
            sale_items_data = []
            for item in items:
                product = Product.query.get(item['product_id'])
                if not product:
                    return jsonify({'error': 'Ürün bulunamadı'}), 404

                qty = round(float(item.get('qty', 0)), 2)
                if qty <= 0:
                    return jsonify({'error': f'Geçersiz miktar: {product.name}'}), 400

                if not product.barcode.startswith('QS-') and float(product.stock_qty) < qty:
                    return jsonify({'error': f'Yetersiz stok: {product.name} (Stok: {product.stock_qty})'}), 400

                price = round(float(product.sale_price), 2)
                line_total = round(qty * price, 2)
                tax_rate = float(product.tax_rate or 0)
                line_tax = round(line_total * tax_rate / 100, 2)
                total_amount = round(total_amount + line_total, 2)
                tax_amount = round(tax_amount + line_tax, 2)

                sale_items_data.append({
                    'product': product, 'qty': qty,
                    'price': price, 'total': line_total,
                    'tax_rate': tax_rate, 'tax': line_tax
                })

            grand_total = round(max(0, total_amount + tax_amount - discount), 2)

            sale = Sale(
                receipt_no=receipt_no,
                user_id=get_user_id(),
                customer_id=customer_id if customer_id else None,
                branch_id=get_branch_id(),
                total_amount=total_amount,
                discount=discount,
                tax_amount=tax_amount,
                grand_total=grand_total,
                payment_method=payment_method
            )
            db.session.add(sale)
            db.session.flush()

            for sd in sale_items_data:
                product = sd['product']
                qty = sd['qty']
                price = sd['price']
                line_total = sd['total']

                db.session.add(SaleItem(
                    sale_id=sale.id, product_id=product.id,
                    product_name=product.name, barcode=product.barcode,
                    quantity=qty, unit_price=price, total_price=line_total,
                    tax_rate=sd['tax_rate'], tax_amount=sd['tax']
                ))

                product.stock_qty = round(float(product.stock_qty) - qty, 2)

                db.session.add(StockMovement(
                    product_id=product.id, user_id=get_user_id(),
                    branch_id=get_branch_id(), type='sale',
                    quantity=qty, description=f'Satış #{receipt_no}'
                ))



            db.session.commit()

            pos_result = None
            if payment_method == 'credit_card':
                try:
                    from app.routes.settings import get_setting
                    ptype = get_setting('pos_type', 'none')
                    paddr = get_setting('pos_address', '')
                    ptimeout = int(float(get_setting('pos_timeout', '30')))
                    if ptype != 'none' and paddr:
                        from app.pos_helper import send_sale
                        pos_result = send_sale(grand_total, ptype, paddr, ptimeout)
                except Exception:
                    pos_result = {'success': False, 'error': 'POS iletişim hatası'}

            resp = {'success': True, 'receipt_no': receipt_no, 'grand_total': grand_total, 'sale_id': sale.id}
            if pos_result:
                resp['pos'] = pos_result
            return jsonify(resp)

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Sistem hatası: {str(e)}'}), 500

@pos_bp.route('/send-pos', methods=['POST'])
@login_required
def send_pos():
    data = request.get_json() or {}
    amount = round(float(data.get('amount', 0)), 2)
    if amount <= 0:
        return jsonify({'error': 'Geçersiz tutar'}), 400
    from app.routes.settings import get_setting
    from app.pos_helper import send_sale
    ptype = get_setting('pos_type', 'none')
    paddr = get_setting('pos_address', '')
    ptimeout = int(float(get_setting('pos_timeout', '30')))
    if ptype == 'none' or not paddr:
        return jsonify({'success': False, 'error': 'POS yapılandırılmamış', 'pos_unavailable': True})
    result = send_sale(amount, ptype, paddr, ptimeout)
    return jsonify(result)

@pos_bp.route('/return', methods=['POST'])
@login_required
def return_sale():
    with _sale_lock:
        try:
            data = request.get_json()
            sale_id = data.get('sale_id')

            sale = Sale.query.get(sale_id)
            if not sale:
                return jsonify({'error': 'Satış bulunamadı'}), 404
            if sale.status == 'cancelled':
                return jsonify({'error': 'Bu satış daha önce iade edilmiş'}), 400

            sale_items = SaleItem.query.filter_by(sale_id=sale.id).all()
            if not sale_items:
                return jsonify({'error': 'Satışa ait ürün bulunamadı'}), 404

            receipt_no = f"RI{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{get_user_id()}{random.randint(10,99)}"
            return_total = 0

            for si in sale_items:
                product = Product.query.get(si.product_id)
                if not product:
                    continue
                qty = round(float(si.quantity), 2)
                product.stock_qty = round(float(product.stock_qty) + qty, 2)
                return_total = round(return_total + float(si.total_price), 2)

                db.session.add(StockMovement(
                    product_id=product.id, user_id=get_user_id(),
                    branch_id=get_branch_id(), type='return',
                    quantity=qty, description=f'Satış iadesi #{sale.receipt_no}'
                ))

            sale.status = 'cancelled'

            db.session.commit()
            return jsonify({'success': True, 'receipt_no': receipt_no, 'refund': return_total})

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Sistem hatası: {str(e)}'}), 500
