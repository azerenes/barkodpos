from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Setting
from app import db
import shutil, os, sys, subprocess

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

def get_setting(key, default=''):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default

def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        db.session.add(Setting(key=key, value=value))

@settings_bp.route('/')
@login_required
def index():
    if not is_admin():
        flash('Bu sayfaya erişim yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    from app.update_helper import CURRENT_VERSION, GITHUB_OWNER, GITHUB_REPO
    return render_template('settings.html',
        company_name=get_setting('company_name', 'İşletmem'),
        tax_office=get_setting('tax_office', ''),
        tax_number=get_setting('tax_number', ''),
        address=get_setting('address', ''),
        phone=get_setting('phone', ''),
        email=get_setting('email', ''),
        tax_rate=get_setting('tax_rate', '0'),
        currency=get_setting('currency', '₺'),
        low_stock_warning=get_setting('low_stock_warning', '10'),
        smtp_host=get_setting('smtp_host', ''),
        smtp_port=get_setting('smtp_port', '587'),
        smtp_user=get_setting('smtp_user', ''),
        smtp_pass=get_setting('smtp_pass', ''),
        smtp_tls=get_setting('smtp_tls', '1'),
        from_email=get_setting('from_email', ''),
        github_repo=f'{GITHUB_OWNER}/{GITHUB_REPO}',
        current_version=CURRENT_VERSION)

@settings_bp.route('/save', methods=['POST'])
@login_required
def save():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    try:
        set_setting('company_name', request.form.get('company_name', ''))
        set_setting('tax_office', request.form.get('tax_office', ''))
        set_setting('tax_number', request.form.get('tax_number', ''))
        set_setting('address', request.form.get('address', ''))
        set_setting('phone', request.form.get('phone', ''))
        set_setting('email', request.form.get('email', ''))
        set_setting('tax_rate', request.form.get('tax_rate', '0'))
        set_setting('currency', request.form.get('currency', '₺'))
        set_setting('low_stock_warning', request.form.get('low_stock_warning', '10'))
        set_setting('smtp_host', request.form.get('smtp_host', ''))
        set_setting('smtp_port', request.form.get('smtp_port', '587'))
        set_setting('smtp_user', request.form.get('smtp_user', ''))
        set_setting('smtp_pass', request.form.get('smtp_pass', ''))
        set_setting('smtp_tls', request.form.get('smtp_tls', '1'))
        set_setting('from_email', request.form.get('from_email', ''))
        db.session.commit()
        flash('Ayarlar kaydedildi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'error')
    return redirect(url_for('settings.index'))

@settings_bp.route('/backup')
@login_required
def backup():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    try:
        import sqlite3, io, datetime
        db_path = 'instance/barkodpos.db'
        backup_path = f'instance/backup_{datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.db'
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            flash(f'Yedekleme tamam: backup_{datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.db', 'success')
        else:
            flash('Veritabanı dosyası bulunamadı', 'error')
    except Exception as e:
        flash(f'Yedekleme hatası: {str(e)}', 'error')
    return redirect(url_for('settings.index'))

@settings_bp.route('/check-update')
@login_required
def check_update():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403
    from app.update_helper import check_update
    result = check_update()
    return jsonify(result)

@settings_bp.route('/do-update', methods=['POST'])
@login_required
def do_update():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403
    from app.update_helper import check_update, download_and_apply
    info = check_update()
    if info.get('error'):
        return jsonify({'error': info['error']}), 400
    if not info.get('has_update'):
        return jsonify({'error': 'Güncelleme yok'}), 400

    result = download_and_apply(info)
    if result.get('error'):
        return jsonify(result), 400

    bat_path = result['bat_path']
    try:
        subprocess.Popen(['cmd.exe', '/c', 'start', '', bat_path], shell=True)
    except Exception:
        pass

    return jsonify({
        'success': True,
        'message': 'Güncelleme indirildi. Uygulama yeniden başlayacak.'
    })
