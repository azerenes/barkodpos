from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Supplier
from app import db

supplier_bp = Blueprint('supplier', __name__, url_prefix='/supplier')

@supplier_bp.route('/')
@login_required
def supplier_list():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    search = request.args.get('q', '').strip()
    query = Supplier.query
    if search:
        like = f'%{search}%'
        query = query.filter(Supplier.name.ilike(like))
    suppliers = query.order_by(Supplier.name).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('suppliers.html', suppliers=suppliers, search=search)

@supplier_bp.route('/add', methods=['POST'])
@login_required
def add_supplier():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Tedarikçi adı zorunludur', 'error')
        return redirect(url_for('supplier.supplier_list'))
    supplier = Supplier(
        name=name,
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        address=request.form.get('address', '').strip(),
        tax_office=request.form.get('tax_office', '').strip(),
        tax_number=request.form.get('tax_number', '').strip(),
        contact_person=request.form.get('contact_person', '').strip(),
        notes=request.form.get('notes', '').strip()
    )
    try:
        db.session.add(supplier)
        db.session.commit()
        flash('Tedarikçi eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Eklenirken hata: {str(e)}', 'error')
    return redirect(url_for('supplier.supplier_list'))

@supplier_bp.route('/update/<int:id>', methods=['POST'])
@login_required
def update_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Tedarikçi adı zorunludur', 'error')
        return redirect(url_for('supplier.supplier_list'))
    try:
        supplier.name = name
        supplier.phone = request.form.get('phone', '').strip()
        supplier.email = request.form.get('email', '').strip()
        supplier.address = request.form.get('address', '').strip()
        supplier.tax_office = request.form.get('tax_office', '').strip()
        supplier.tax_number = request.form.get('tax_number', '').strip()
        supplier.contact_person = request.form.get('contact_person', '').strip()
        supplier.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Tedarikçi güncellendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('supplier.supplier_list'))

@supplier_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    try:
        db.session.delete(supplier)
        db.session.commit()
        flash('Tedarikçi silindi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('supplier.supplier_list'))
