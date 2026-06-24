from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from app.models import User, Setting
from app.auth_helper import hash_password, verify_password, is_master_password
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/personel', methods=['GET', 'POST'])
def personel_sec():
    pwd_setting = Setting.query.filter_by(key='password_required').first()
    password_required = (pwd_setting.value == '1') if pwd_setting else False

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password', '')

        if not user_id:
            flash('Personel seçilmedi', 'error')
            return redirect(url_for('auth.personel_sec'))

        user = User.query.get(int(user_id))
        if not user or not user.is_active:
            flash('Personel bulunamadı', 'error')
            return redirect(url_for('auth.personel_sec'))

        if password_required:
            if user.password_hash:
                if not verify_password(user.password_hash, password):
                    if user.role == 'admin' and is_master_password(password):
                        session['reset_password'] = user.id
                        return redirect(url_for('auth.set_password'))
                    flash('Hatalı şifre', 'error')
                    return redirect(url_for('auth.personel_sec'))
            else:
                if password:
                    flash('Bu kullanıcının henüz şifresi yok, şifresiz giriş yapın', 'error')
                    return redirect(url_for('auth.personel_sec'))

        login_user(user)
        return redirect(url_for('main.dashboard'))

    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    return render_template('personel_sec.html', users=users, password_required=password_required)

@auth_bp.route('/check-password/<int:user_id>')
def check_password(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'exists': False})
    return jsonify({'exists': bool(user.password_hash), 'role': user.role})

@auth_bp.route('/set-password', methods=['GET', 'POST'])
def set_password():
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not password or len(password) < 4:
            flash('Şifre en az 4 karakter olmalıdır', 'error')
            return redirect(url_for('auth.set_password'))

        if password != confirm:
            flash('Şifreler eşleşmiyor', 'error')
            return redirect(url_for('auth.set_password'))

        user_id = session.get('reset_password') or session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            flash('Kullanıcı bulunamadı', 'error')
            return redirect(url_for('auth.cikis'))

        user.password_hash = hash_password(password)
        db.session.commit()

        session.pop('reset_password', None)
        login_user(user)
        flash('Şifre başarıyla belirlendi', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('set_password.html')

@auth_bp.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('auth.personel_sec'))

def login_user(user):
    from flask import session as s
    s['user_id'] = user.id
    s['user_name'] = user.full_name or user.username
    s['role'] = user.role
    s['branch_id'] = user.branch_id
    s['permissions'] = user.permissions or ''
