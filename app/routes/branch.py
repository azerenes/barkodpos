from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Branch
from app import db

branch_bp = Blueprint('branch', __name__, url_prefix='/branch')

@branch_bp.route('/')
@login_required
def branch_list():
    if not is_admin():
        flash('Bu sayfaya erişim yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    branches = Branch.query.all()
    return render_template('branches.html', branches=branches)

@branch_bp.route('/add', methods=['POST'])
@login_required
def add_branch():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))

    name = request.form.get('name', '').strip()
    if not name:
        flash('Şube adı zorunludur', 'error')
        return redirect(url_for('branch.branch_list'))

    try:
        branch = Branch(
            name=name,
            address=request.form.get('address', '').strip(),
            phone=request.form.get('phone', '').strip()
        )
        db.session.add(branch)
        db.session.commit()
        flash('Şube eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')

    return redirect(url_for('branch.branch_list'))
