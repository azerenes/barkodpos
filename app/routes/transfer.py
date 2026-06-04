from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Branch, StockMovement
from app import db

transfer_bp = Blueprint('transfer', __name__, url_prefix='/transfer')

@transfer_bp.route('/')
@login_required
def transfer():
    if not is_admin():
        flash('Bu sayfaya erişim yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    branches = Branch.query.all()
    movements = StockMovement.query.filter(
        StockMovement.type.in_(['transfer_in', 'transfer_out'])
    ).order_by(StockMovement.created_at.desc()).limit(50).all()
    return render_template('transfer.html', products=products, branches=branches, movements=movements)

@transfer_bp.route('/do-transfer', methods=['POST'])
@login_required
def do_transfer():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))

    product_id = request.form.get('product_id')
    from_branch_id = request.form.get('from_branch_id')
    to_branch_id = request.form.get('to_branch_id')

    if not product_id or not from_branch_id or not to_branch_id:
        flash('Tüm alanlar zorunludur', 'error')
        return redirect(url_for('transfer.transfer'))

    if from_branch_id == to_branch_id:
        flash('Gönderen ve alan şube aynı olamaz', 'error')
        return redirect(url_for('transfer.transfer'))

    try:
        quantity = float(request.form.get('quantity', 0) or 0)
    except ValueError:
        flash('Geçersiz miktar', 'error')
        return redirect(url_for('transfer.transfer'))

    if quantity <= 0:
        flash('Miktar sıfırdan büyük olmalıdır', 'error')
        return redirect(url_for('transfer.transfer'))

    product = Product.query.get(product_id)
    if not product:
        flash('Ürün bulunamadı', 'error')
        return redirect(url_for('transfer.transfer'))

    if float(product.stock_qty) < quantity:
        flash(f'Yetersiz stok! Mevcut: {product.stock_qty}', 'error')
        return redirect(url_for('transfer.transfer'))

    try:
        product.stock_qty = float(product.stock_qty) - quantity

        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=from_branch_id, type='transfer_out',
            quantity=quantity,
            description=f'Şube transferi #{from_branch_id} -> #{to_branch_id}'
        ))
        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=to_branch_id, type='transfer_in',
            quantity=quantity,
            description=f'Şube transferi #{from_branch_id} -> #{to_branch_id}'
        ))
        db.session.commit()
        flash(f'{quantity} adet ürün transfer edildi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('transfer.transfer'))
