from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Category, StockMovement, Supplier
from app import db
from sqlalchemy import or_

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
            unit=request.form.get('unit', 'Adet')
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
        product.name = name
        product.sale_price = sale_price
        product.purchase_price = purchase_price
        product.min_stock_qty = float(request.form.get('min_stock_qty', 0) or 0)
        product.tax_rate = float(request.form.get('tax_rate', 0) or 0)
        product.unit = request.form.get('unit', 'Adet')
        product.category_id = request.form.get('category_id') or None
        product.supplier_id = request.form.get('supplier_id') or None
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

@stock_bp.route('/add-category-ajax', methods=['POST'])
@login_required
def add_category_ajax():
    from flask import jsonify
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
