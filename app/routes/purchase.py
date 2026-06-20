from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Product, Category, StockMovement
from app import db
from datetime import datetime

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

def log_price_history(product_id, price_type, old_price, new_price, notes=''):
    from app.models import PriceHistory
    old = round(float(old_price), 2) if old_price else 0
    new = round(float(new_price), 2) if new_price else 0
    if old == new:
        return
    db.session.add(PriceHistory(
        product_id=product_id, user_id=get_user_id(),
        price_type=price_type, old_price=old, new_price=new, notes=notes
    ))

@purchase_bp.route('/history')
@login_required
def history():
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(100).all()
    return render_template('purchase_history.html', movements=movements)

@purchase_bp.route('/invoices')
@login_required
def invoice_list():
    from app.models import PurchaseInvoice
    invoices = PurchaseInvoice.query.order_by(PurchaseInvoice.created_at.desc()).all()
    return render_template('purchase_invoices.html', invoices=invoices)

@purchase_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def invoice_new():
    from app.models import PurchaseInvoice, PurchaseInvoiceItem, Supplier
    if request.method == 'POST':
        try:
            supplier_id = request.form.get('supplier_id')
            invoice_no = request.form.get('invoice_no', '').strip()
            invoice_date_str = request.form.get('invoice_date', '')
            notes = request.form.get('notes', '').strip()
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('qty[]')
            prices = request.form.getlist('price[]')

            inv_date = datetime.strptime(invoice_date_str, '%Y-%m-%d') if invoice_date_str else datetime.utcnow()

            total = 0
            invoice = PurchaseInvoice(
                supplier_id=int(supplier_id) if supplier_id else None,
                user_id=get_user_id(), branch_id=get_branch_id(),
                invoice_no=invoice_no, invoice_date=inv_date, notes=notes
            )
            db.session.add(invoice)
            db.session.flush()

            for i in range(len(product_ids)):
                pid = product_ids[i]
                if not pid:
                    continue
                qty = round(float(quantities[i] if i < len(quantities) else 0), 2)
                price = round(float(prices[i] if i < len(prices) else 0), 2)
                if qty <= 0 or price <= 0:
                    continue
                line_total = round(qty * price, 2)
                total += line_total
                db.session.add(PurchaseInvoiceItem(
                    invoice_id=invoice.id, product_id=int(pid),
                    quantity=qty, unit_price=price, total_price=line_total
                ))
                product = Product.query.get(int(pid))
                if product:
                    old_purchase = float(product.purchase_price)
                    product.purchase_price = price
                    product.stock_qty = round(float(product.stock_qty) + qty, 2)
                    log_price_history(product.id, 'purchase', old_purchase, price, f'Fatura #{invoice_no}')
                    db.session.add(StockMovement(
                        product_id=product.id, user_id=get_user_id(),
                        branch_id=get_branch_id(), type='entry',
                        quantity=qty, description=f'Alış faturası: {invoice_no} - {product.name}'
                    ))

            invoice.total_amount = round(total, 2)
            db.session.commit()
            flash(f'Fatura kaydedildi. Toplam: {total:.2f} ₺', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('purchase.invoice_list'))

    suppliers = Supplier.query.order_by(Supplier.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('purchase_invoice_new.html', suppliers=suppliers, products=products)

@purchase_bp.route('/invoices/<int:id>')
@login_required
def invoice_detail(id):
    from app.models import PurchaseInvoice
    invoice = PurchaseInvoice.query.get_or_404(id)
    return render_template('purchase_invoice_detail.html', invoice=invoice)

@purchase_bp.route('/invoices/<int:id>/delete', methods=['POST'])
@login_required
def invoice_delete(id):
    from app.models import PurchaseInvoice, PurchaseInvoiceItem
    invoice = PurchaseInvoice.query.get_or_404(id)
    items = PurchaseInvoiceItem.query.filter_by(invoice_id=id).all()
    for item in items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock_qty = round(float(product.stock_qty) - float(item.quantity), 2)
    db.session.delete(invoice)
    db.session.commit()
    flash('Fatura silindi ve stoklar geri alindi', 'success')
    return redirect(url_for('purchase.invoice_list'))
