from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import User, Branch
from app import db

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

PERMISSION_LABELS = {
    'pos': 'POS (Satış)',
    'stock': 'Stok Yönetimi',
    'purchase': 'Alış / Stok Giriş',
    'customer': 'Cari Hesap',
    'cash': 'Kasa',
    'expense': 'Giderler',
    'report': 'Raporlar',
}

ALL_PERMISSIONS = ['pos', 'stock', 'purchase', 'customer', 'cash', 'expense', 'report']

@employee_bp.route('/')
@login_required
def employee_list():
    if not is_admin():
        flash('Bu sayfaya erişim yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    employees = User.query.filter(User.role == 'employee').all()
    branches = Branch.query.all()
    return render_template('employees.html', employees=employees, branches=branches,
        permission_labels=PERMISSION_LABELS, all_permissions=ALL_PERMISSIONS)

@employee_bp.route('/add', methods=['POST'])
@login_required
def add_employee():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))

    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()

    if not username:
        flash('Kullanıcı adı zorunludur', 'error')
        return redirect(url_for('employee.employee_list'))

    if User.query.filter_by(username=username).first():
        flash('Bu kullanıcı adı zaten kullanılıyor', 'error')
        return redirect(url_for('employee.employee_list'))

    permissions = ','.join(p for p in ALL_PERMISSIONS if request.form.get(f'perm_{p}'))

    try:
        user = User(
            username=username, full_name=full_name, role='employee',
            branch_id=request.form.get('branch_id') or None,
            permissions=permissions
        )
        db.session.add(user)
        db.session.commit()
        flash('Personel eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('employee.employee_list'))

@employee_bp.route('/update-permissions', methods=['POST'])
@login_required
def update_permissions():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403

    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user or user.role != 'employee':
        return jsonify({'error': 'Personel bulunamadı'}), 404

    permissions = ','.join(p for p in ALL_PERMISSIONS if request.form.get(f'perm_{p}'))
    user.permissions = permissions
    db.session.commit()
    return jsonify({'success': True, 'message': 'Yetkiler güncellendi'})

@employee_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Personel bulunamadı'}), 404

    user.password_hash = None
    db.session.commit()
    return jsonify({'success': True, 'message': f'{user.full_name or user.username} şifresi sıfırlandı. Personel giriş yapınca yeni şifre belirleyecek.'})
