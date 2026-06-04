from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Category, StockMovement
from app import db

purchase_bp = Blueprint('purchase', __name__, url_prefix='/purchase')

@purchase_bp.route('/')
@login_required
def purchase():
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    categories = Category.query.order_by(Category.name).all()
    movements = StockMovement.query.filter(
        StockMovement.type.in_(['entry', 'exit'])
    ).order_by(StockMovement.created_at.desc()).limit(50).all()
    return render_template('purchase.html', products=products, categories=categories, movements=movements)

@purchase_bp.route('/add-stock', methods=['POST'])
@login_required
def add_stock():
    product_id = request.form.get('product_id')
    if not product_id:
        flash('Ürün seçilmedi', 'error')
        return redirect(url_for('purchase.purchase'))

    try:
        quantity = float(request.form.get('quantity', 0) or 0)
    except ValueError:
        flash('Geçersiz miktar', 'error')
        return redirect(url_for('purchase.purchase'))

    if quantity <= 0:
        flash('Miktar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('purchase.purchase'))

    product = Product.query.get(product_id)
    if not product:
        flash('Ürün bulunamadı', 'error')
        return redirect(url_for('purchase.purchase'))

    try:
        purchase_price = request.form.get('purchase_price', type=float)
        if purchase_price and purchase_price > 0:
            product.purchase_price = purchase_price

        product.stock_qty = float(product.stock_qty) + quantity

        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=get_branch_id(), type='entry',
            quantity=quantity,
            description=request.form.get('description', '').strip() or 'Alış fişi ile stok girişi'
        ))
        db.session.commit()
        flash(f'{quantity} adet {product.name} stok eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('purchase.purchase'))

@purchase_bp.route('/remove-stock', methods=['POST'])
@login_required
def remove_stock():
    product_id = request.form.get('product_id')
    if not product_id:
        flash('Ürün seçilmedi', 'error')
        return redirect(url_for('purchase.purchase'))

    try:
        quantity = float(request.form.get('quantity', 0) or 0)
    except ValueError:
        flash('Geçersiz miktar', 'error')
        return redirect(url_for('purchase.purchase'))

    if quantity <= 0:
        flash('Miktar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('purchase.purchase'))

    product = Product.query.get(product_id)
    if not product:
        flash('Ürün bulunamadı', 'error')
        return redirect(url_for('purchase.purchase'))

    if float(product.stock_qty) < quantity:
        flash(f'Yetersiz stok! Mevcut: {product.stock_qty}', 'error')
        return redirect(url_for('purchase.purchase'))

    try:
        product.stock_qty = float(product.stock_qty) - quantity
        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=get_branch_id(), type='exit',
            quantity=quantity,
            description=request.form.get('description', '').strip() or 'Stok çıkışı'
        ))
        db.session.commit()
        flash(f'{quantity} adet {product.name} stok çıkışı yapıldı', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('purchase.purchase'))

@purchase_bp.route('/history')
@login_required
def history():
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(100).all()
    return render_template('purchase_history.html', movements=movements)
