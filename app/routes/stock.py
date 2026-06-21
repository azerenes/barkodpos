from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Category, StockMovement, Supplier, PriceHistory, ProductPrice, RecipeItem
from app import db
from sqlalchemy import or_
from datetime import datetime

stock_bp = Blueprint('stock', __name__, url_prefix='/stock')

@stock_bp.route('/')
@login_required
def stock_list():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    query = Product.query.filter_by(is_active=True)
    search = request.args.get('q', '').strip()
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            Product.barcode.ilike(like),
            Product.name.ilike(like)
        ))
    products = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('stock.html', products=products, categories=categories, suppliers=suppliers, search=search)

@stock_bp.route('/add', methods=['POST'])
@login_required
def add_product():
    barcode = request.form.get('barcode', '').strip()
    name = request.form.get('name', '').strip()

    if not barcode or not name:
        flash('Barkod ve ürün adı zorunludur', 'error')
        return redirect(url_for('stock.stock_list'))

    try:
        purchase_price = float(request.form.get('purchase_price', 0) or 0)
        sale_price = float(request.form.get('sale_price', 0) or 0)
        stock_qty = float(request.form.get('stock_qty', 0) or 0)
        min_stock_qty = float(request.form.get('min_stock_qty', 0) or 0)
        tax_rate = float(request.form.get('tax_rate', 0) or 0)
    except ValueError:
        flash('Geçersiz sayısal değer', 'error')
        return redirect(url_for('stock.stock_list'))

    if sale_price <= 0:
        flash('Satış fiyatı sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('stock.stock_list'))

    existing = Product.query.filter_by(barcode=barcode).first()
    if existing:
        flash('Bu barkod zaten kayıtlı', 'error')
        return redirect(url_for('stock.stock_list'))

    try:
        product = Product(
            barcode=barcode, name=name,
            category_id=request.form.get('category_id') or None,
            purchase_price=purchase_price, sale_price=sale_price,
            tax_rate=tax_rate, stock_qty=stock_qty, min_stock_qty=min_stock_qty,
            supplier_id=request.form.get('supplier_id') or None,
            unit=request.form.get('unit', 'Adet'),
            is_stockless=bool(request.form.get('is_stockless'))
        )
        db.session.add(product)
        db.session.flush()

        if stock_qty > 0:
            db.session.add(StockMovement(
                product_id=product.id, user_id=get_user_id(),
                branch_id=get_branch_id(), type='entry',
                quantity=stock_qty, description='İlk stok girişi'
            ))

        db.session.commit()
        flash(f'Ürün eklendi: {name}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Eklenirken hata: {str(e)}', 'error')

    return redirect(url_for('stock.stock_list'))

@stock_bp.route('/update/<int:id>', methods=['POST'])
@login_required
def update_product(id):
    product = Product.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Ürün adı zorunludur', 'error')
        return redirect(url_for('stock.stock_list'))

    try:
        sale_price = float(request.form.get('sale_price', 0) or 0)
        purchase_price = float(request.form.get('purchase_price', 0) or 0)
        if sale_price <= 0:
            flash('Satış fiyatı sıfırdan büyük olmalıdır', 'error')
            return redirect(url_for('stock.stock_list'))
        if purchase_price < 0:
            flash('Alış fiyatı negatif olamaz', 'error')
            return redirect(url_for('stock.stock_list'))
        old_sale = float(product.sale_price)
        old_purchase = float(product.purchase_price)
        product.name = name
        product.sale_price = sale_price
        product.purchase_price = purchase_price
        product.min_stock_qty = float(request.form.get('min_stock_qty', 0) or 0)
        product.tax_rate = float(request.form.get('tax_rate', 0) or 0)
        product.unit = request.form.get('unit', 'Adet')
        product.category_id = request.form.get('category_id') or None
        product.supplier_id = request.form.get('supplier_id') or None
        product.is_stockless = bool(request.form.get('is_stockless'))
        wholesale_price = float(request.form.get('wholesale_price', 0) or 0)
        wholesale_min = float(request.form.get('wholesale_min_qty', 0) or 0)
        if wholesale_price > 0:
            product.wholesale_price = wholesale_price
            product.wholesale_min_qty = wholesale_min
        from app.routes.purchase import log_price_history
        log_price_history(product.id, 'sale', old_sale, sale_price, 'Stok güncelleme')
        log_price_history(product.id, 'purchase', old_purchase, purchase_price, 'Stok güncelleme')
        db.session.commit()
        flash('Ürün güncellendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Güncelleme hatası: {str(e)}', 'error')

    return redirect(url_for('stock.stock_list'))

@stock_bp.route('/stock-entry/<int:id>', methods=['POST'])
@login_required
def stock_entry(id):
    product = Product.query.get_or_404(id)
    try:
        qty = float(request.form.get('quantity', 0) or 0)
    except ValueError:
        flash('Geçersiz miktar', 'error')
        return redirect(url_for('stock.stock_list'))

    if qty <= 0:
        flash('Miktar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('stock.stock_list'))

    try:
        product.stock_qty = float(product.stock_qty) + qty
        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=get_branch_id(), type='entry',
            quantity=qty, description=request.form.get('description', 'Stok girişi')
        ))
        db.session.commit()
        flash(f'{qty} adet stok girişi yapıldı', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('stock.stock_list'))

@stock_bp.route('/categories')
@login_required
def categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=categories)

@stock_bp.route('/add-category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Kategori adı zorunludur', 'error')
        return redirect(url_for('stock.categories'))

    try:
        if Category.query.filter_by(name=name).first():
            flash('Bu kategori zaten var', 'error')
        else:
            category = Category(name=name, description=request.form.get('description', '').strip())
            db.session.add(category)
            db.session.commit()
            flash('Kategori eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('stock.categories'))

@stock_bp.route('/labels')
@login_required
def product_labels():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    search = request.args.get('q', '').strip()
    query = Product.query.filter_by(is_active=True)
    if search:
        like = f'%{search}%'
        query = query.filter(or_(Product.barcode.ilike(like), Product.name.ilike(like)))
    products = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('labels.html', products=products, search=search)

@stock_bp.route('/csv-import', methods=['POST'])
@login_required
def csv_import():
    import csv, io
    file = request.files.get('file')
    if not file:
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('stock.stock_list'))
    try:
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        count = 0
        for row in reader:
            barcode = row.get('barcode', '').strip() or row.get('Barkod', '').strip()
            name = row.get('name', '').strip() or row.get('Ürün Adı', '').strip()
            if not barcode or not name:
                continue
            existing = Product.query.filter_by(barcode=barcode).first()
            if existing:
                existing.stock_qty = float(existing.stock_qty or 0) + float(row.get('stock_qty', 0) or row.get('Stok', 0) or 0)
                existing.sale_price = float(row.get('sale_price', 0) or row.get('Satış Fiyatı', 0) or existing.sale_price or 0)
                existing.purchase_price = float(row.get('purchase_price', 0) or row.get('Alış Fiyatı', 0) or existing.purchase_price or 0)
                existing.tax_rate = float(row.get('tax_rate', 0) or row.get('KDV', 0) or existing.tax_rate or 0)
                count += 1
            else:
                cat_name = row.get('category', '').strip() or row.get('Kategori', '').strip()
                cat = None
                if cat_name:
                    cat = Category.query.filter_by(name=cat_name).first()
                    if not cat:
                        cat = Category(name=cat_name)
                        db.session.add(cat)
                        db.session.flush()
                sup_name = row.get('supplier', '').strip() or row.get('Tedarikçi', '').strip()
                sup = None
                if sup_name:
                    sup = Supplier.query.filter_by(name=sup_name).first()
                    if not sup:
                        sup = Supplier(name=sup_name)
                        db.session.add(sup)
                        db.session.flush()
                product = Product(
                    barcode=barcode, name=name,
                    category_id=cat.id if cat else None,
                    supplier_id=sup.id if sup else None,
                    purchase_price=float(row.get('purchase_price', 0) or row.get('Alış Fiyatı', 0) or 0),
                    sale_price=float(row.get('sale_price', 0) or row.get('Satış Fiyatı', 0) or 0),
                    tax_rate=float(row.get('tax_rate', 0) or row.get('KDV', 0) or 0),
                    stock_qty=float(row.get('stock_qty', 0) or row.get('Stok', 0) or 0),
                    min_stock_qty=float(row.get('min_stock_qty', 0) or row.get('Min Stok', 0) or 0),
                    unit=row.get('unit', '') or row.get('Birim', '') or 'Adet'
                )
                db.session.add(product)
                count += 1
        db.session.commit()
        flash(f'{count} ürün içe aktarıldı', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'CSV hatası: {str(e)}', 'error')
    return redirect(url_for('stock.stock_list'))

@stock_bp.route('/price-history')
@login_required
def price_history():
    product_id = request.args.get('product_id', type=int)
    query = PriceHistory.query.order_by(PriceHistory.created_at.desc())
    if product_id:
        query = query.filter_by(product_id=product_id)
    history = query.limit(100).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('price_history.html', history=history, products=products, selected_id=product_id)

@stock_bp.route('/price-history/<int:product_id>')
@login_required
def price_history_json(product_id):
    history = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.created_at.desc()).all()
    return jsonify([{
        'id': h.id, 'price_type': h.price_type, 'old_price': round(float(h.old_price), 2),
        'new_price': round(float(h.new_price), 2), 'notes': h.notes or '',
        'created_at': h.created_at.strftime('%d.%m.%Y %H:%M'),
        'user_name': h.user.full_name if h.user else ''
    } for h in history])

@stock_bp.route('/prices/<int:product_id>', methods=['GET', 'POST'])
@login_required
def manage_prices(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        sale_price = round(float(request.form.get('sale_price', 0)), 2)
        purchase_price = round(float(request.form.get('purchase_price', 0)), 2)
        wholesale_price = round(float(request.form.get('wholesale_price', 0)), 2)
        wholesale_min = round(float(request.form.get('wholesale_min_qty', 0)), 2)

        old_sale = float(product.sale_price)
        old_purchase = float(product.purchase_price)

        if sale_price > 0 and sale_price != old_sale:
            product.sale_price = sale_price
        if purchase_price > 0 and purchase_price != old_purchase:
            product.purchase_price = purchase_price

        product.wholesale_price = wholesale_price
        product.wholesale_min_qty = wholesale_min
        db.session.commit()
        flash('Fiyatlar güncellendi', 'success')
        return redirect(url_for('stock.price_history', product_id=product_id))

    history = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.created_at.desc()).limit(20).all()
    return render_template('manage_prices.html', product=product, history=history)

@stock_bp.route('/set-products')
@login_required
def set_products():
    sets = Product.query.filter_by(is_set=True, is_active=True).order_by(Product.name).all()
    return render_template('set_products.html', sets=sets)

@stock_bp.route('/set-products/new', methods=['GET', 'POST'])
@login_required
def set_product_new():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            barcode = request.form.get('barcode', '').strip() or f'SET-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}'
            sale_price = round(float(request.form.get('sale_price', 0)), 2)
            cat_id = request.form.get('category_id')
            component_ids = request.form.getlist('component_id[]')
            quantities = request.form.getlist('component_qty[]')
            if not name or sale_price <= 0:
                flash('Ad ve fiyat gerekli', 'error')
                return redirect(url_for('stock.set_product_new'))
            set_product = Product(
                barcode=barcode, name=name, sale_price=sale_price, purchase_price=0,
                stock_qty=0, category_id=int(cat_id) if cat_id else None,
                unit='Adet', is_active=True, is_set=True,
                tax_rate=float(request.form.get('tax_rate', 0) or 0)
            )
            db.session.add(set_product)
            db.session.flush()
            for i in range(len(component_ids)):
                cid = component_ids[i]
                qty = round(float(quantities[i] if i < len(quantities) else 1), 2)
                if cid and qty > 0:
                    db.session.add(RecipeItem(product_id=set_product.id, component_id=int(cid), quantity=qty))
                    comp = Product.query.get(int(cid))
                    if comp:
                        set_product.purchase_price = round(float(set_product.purchase_price) + float(comp.purchase_price) * qty, 2)
            db.session.commit()
            flash('Set ürün oluşturuldu', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('stock.set_products'))

    products = Product.query.filter_by(is_active=True, is_set=False).order_by(Product.name).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('set_product_new.html', products=products, categories=categories)

@stock_bp.route('/set-products/<int:id>')
@login_required
def set_product_detail(id):
    set_prod = Product.query.get_or_404(id)
    components = RecipeItem.query.filter_by(product_id=id).all()
    return render_template('set_product_detail.html', set_prod=set_prod, components=components)

@stock_bp.route('/set-products/<int:id>/unpack', methods=['POST'])
@login_required
def set_product_unpack(id):
    set_prod = Product.query.get_or_404(id)
    if not set_prod.is_set:
        return jsonify({'error': 'Set ürün değil'}), 400
    qty = round(float(request.form.get('qty', 1)), 2)
    if qty <= 0:
        flash('Geçersiz miktar', 'error')
        return redirect(url_for('stock.set_product_detail', id=id))
    if float(set_prod.stock_qty) < qty:
        flash(f'Yetersiz stok: {set_prod.stock_qty}', 'error')
        return redirect(url_for('stock.set_product_detail', id=id))
    components = RecipeItem.query.filter_by(product_id=id).all()
    for comp in components:
        comp_product = Product.query.get(comp.component_id)
        if comp_product:
            comp_product.stock_qty = round(float(comp_product.stock_qty) + float(comp.quantity) * qty, 2)
    set_prod.stock_qty = round(float(set_prod.stock_qty) - qty, 2)
    db.session.commit()
    flash(f'{qty} adet set ürün açıldı, bileşenler stoğa eklendi', 'success')
    return redirect(url_for('stock.set_product_detail', id=id))

@stock_bp.route('/export-csv')
@login_required
def export_stock_csv():
    query = Product.query.filter_by(is_active=True).order_by(Product.name)
    search = request.args.get('q', '').strip()
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            Product.barcode.ilike(like),
            Product.name.ilike(like)
        ))
    products = query.all()
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Barkod', 'Urun Adi', 'Kategori', 'Alis Fiyati', 'Satis Fiyati', 'Stok', 'Min Stok', 'Birim', 'Stoksuz'])
    for p in products:
        writer.writerow([
            p.barcode, p.name,
            p.category.name if p.category else '',
            str(p.purchase_price or 0), str(p.sale_price or 0),
            str(p.stock_qty or 0), str(p.min_stock_qty or 0), p.unit or '',
            'Evet' if p.is_stockless else ''
        ])
    csv_output = output.getvalue()
    return Response(
        '\ufeff' + csv_output,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=stok_listesi.csv'}
    )

@stock_bp.route('/toggle-quick/<int:id>', methods=['POST'])
@login_required
def toggle_quick(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'error': 'Ürün bulunamadı'}), 404
    product.is_quick_product = not product.is_quick_product
    db.session.commit()
    return jsonify({'success': True, 'is_quick_product': product.is_quick_product})

@stock_bp.route('/add-category-ajax', methods=['POST'])
@login_required
def add_category_ajax():
    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Kategori adı gerekli'}), 400
    try:
        if Category.query.filter_by(name=name).first():
            return jsonify({'success': False, 'error': 'Bu kategori zaten var'}), 400
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return jsonify({'success': True, 'id': category.id, 'name': category.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
