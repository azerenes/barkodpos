from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import User, Branch
from app import db

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/')
@login_required
def employee_list():
    if not is_admin():
        flash('Bu sayfaya erişim yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    employees = User.query.filter(User.role == 'employee').all()
    branches = Branch.query.all()
    return render_template('employees.html', employees=employees, branches=branches)

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

    try:
        user = User(
            username=username,
            full_name=full_name, role='employee',
            branch_id=request.form.get('branch_id') or None
        )
        db.session.add(user)
        db.session.commit()
        flash('Personel eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('employee.employee_list'))
