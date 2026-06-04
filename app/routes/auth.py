from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/personel', methods=['GET', 'POST'])
def personel_sec():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user and user.is_active:
                session['user_id'] = user.id
                session['user_name'] = user.full_name or user.username
                session['role'] = user.role
                session['branch_id'] = user.branch_id
                return redirect(url_for('main.dashboard'))
        flash('Personel seçilmedi', 'error')
    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    return render_template('personel_sec.html', users=users)

@auth_bp.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('auth.personel_sec'))
