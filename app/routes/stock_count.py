from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, require_permission, get_user_id, get_branch_id, is_admin
from app.models import StockCount, StockCountItem, Product, Category, StockMovement
from app import db
from datetime import datetime

stock_count_bp = Blueprint('stock_count', __name__, url_prefix='/stock-count')

@stock_count_bp.route('/')
@login_required
@require_permission('stock')
def index():
    counts = StockCount.query.order_by(StockCount.created_at.desc()).all()
    return render_template('stock_count.html', counts=counts)

@stock_count_bp.route('/new', methods=['POST'])
@login_required
@require_permission('stock')
def new_count():
    data = request.get_json()
    category_id = data.get('category_id')
    query = Product.query.filter_by(is_active=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    products = query.order_by(Product.name).all()
    if not products:
        return jsonify({'error': 'Sayılacak ürün bulunamadı'}), 400
    count = StockCount(
        user_id=get_user_id(), branch_id=get_branch_id(),
        status='in_progress', notes=data.get('notes', ''),
        total_items=len(products)
    )
    db.session.add(count)
    db.session.flush()
    for p in products:
        qty = round(float(p.stock_qty), 2)
        db.session.add(StockCountItem(
            count_id=count.id, product_id=p.id,
            system_qty=qty, counted_qty=qty, difference=0
        ))
    db.session.commit()
    return jsonify({'id': count.id, 'total': len(products)})

@stock_count_bp.route('/<int:id>')
@login_required
@require_permission('stock')
def detail(id):
    count = StockCount.query.get_or_404(id)
    categories = Category.query.order_by(Category.name).all()
    return render_template('stock_count_detail.html', count=count, categories=categories)

@stock_count_bp.route('/<int:id>/items')
@login_required
@require_permission('stock')
def items(id):
    count = StockCount.query.get_or_404(id)
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    items_query = StockCountItem.query.filter_by(count_id=id)
    if q:
        items_query = items_query.join(Product).filter(
            (Product.name.ilike(f'%{q}%')) | (Product.barcode.ilike(f'%{q}%'))
        )
    if status_filter:
        items_query = items_query.filter_by(status=status_filter)
    items = items_query.order_by(StockCountItem.id).all()
    return jsonify([{
        'id': i.id, 'product_id': i.product_id,
        'barcode': i.product.barcode if i.product else '',
        'name': i.product.name if i.product else '',
        'system_qty': round(float(i.system_qty), 2),
        'counted_qty': round(float(i.counted_qty), 2),
        'difference': round(float(i.difference), 2),
        'status': i.status,
        'unit': i.product.unit if i.product else ''
    } for i in items])

@stock_count_bp.route('/<int:id>/update', methods=['POST'])
@login_required
@require_permission('stock')
def update_item(id):
    data = request.get_json()
    item = StockCountItem.query.get(data.get('item_id'))
    if not item or item.count_id != id:
        return jsonify({'error': 'Kalem bulunamadı'}), 404
    counted = round(float(data.get('counted_qty', 0)), 2)
    diff = round(counted - float(item.system_qty), 2)
    item.counted_qty = counted
    item.difference = diff
    item.status = 'matched' if diff == 0 else 'mismatch'
    db.session.commit()
    return jsonify({
        'id': item.id, 'difference': diff,
        'status': item.status, 'counted_qty': counted
    })

@stock_count_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@require_permission('stock')
def complete_count(id):
    count = StockCount.query.get_or_404(id)
    if count.status != 'in_progress':
        return jsonify({'error': 'Sayım zaten tamamlanmış'}), 400
    items = StockCountItem.query.filter_by(count_id=id).all()
    for i in items:
        if i.status == 'pending':
            diff = round(float(i.counted_qty) - float(i.system_qty), 2)
            if diff == 0:
                i.status = 'matched'
            else:
                i.status = 'mismatch'
                i.difference = diff
    db.session.flush()
    matched = sum(1 for i in items if i.status == 'matched')
    mismatched = sum(1 for i in items if i.status == 'mismatch')
    count.matched_items = matched
    count.mismatch_items = mismatched
    count.status = 'completed'
    count.completed_at = datetime.now()
    db.session.commit()
    return jsonify({'success': True, 'matched': matched, 'mismatched': mismatched, 'total': len(items)})

@stock_count_bp.route('/<int:id>/apply', methods=['POST'])
@login_required
@require_permission('stock')
def apply_count(id):
    count = StockCount.query.get_or_404(id)
    if count.status != 'completed':
        return jsonify({'error': 'Sayım önce tamamlanmalı'}), 400
    items = StockCountItem.query.filter_by(count_id=id, status='mismatch').all()
    updated = 0
    for item in items:
        product = Product.query.get(item.product_id)
        if not product:
            continue
        diff = round(float(item.counted_qty) - float(item.system_qty), 2)
        if diff == 0:
            continue
        old_qty = round(float(product.stock_qty), 2)
        product.stock_qty = item.counted_qty
        movement_type = 'entry' if diff > 0 else 'exit'
        desc = f'Sayim duzeltmesi: {old_qty} -> {item.counted_qty} (fark: {diff})'
        db.session.add(StockMovement(
            product_id=product.id, user_id=get_user_id(),
            branch_id=get_branch_id(), type=movement_type,
            quantity=abs(diff), description=desc
        ))
        updated += 1
    db.session.commit()
    flash(f'Sayim uygulandi. {updated} urun guncellendi.', 'success')
    return jsonify({'success': True, 'updated': updated})
