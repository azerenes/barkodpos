from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Setting
from app import db
from config import get_data_dir
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
    from app.update_helper import CURRENT_VERSION
    import glob
    backup_dir = get_data_dir()
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.db')], reverse=True)
    return render_template('settings.html', backups=backups,
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
        printer_type=get_setting('printer_type', 'none'),
        printer_address=get_setting('printer_address', ''),
        pos_type=get_setting('pos_type', 'none'),
        pos_address=get_setting('pos_address', ''),
        pos_timeout=get_setting('pos_timeout', '30'),
        currency_usd=get_setting('currency_usd', '0'),
        currency_eur=get_setting('currency_eur', '0'),
        auto_add_on_scan=get_setting('auto_add_on_scan', '0'),
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
        set_setting('printer_type', request.form.get('printer_type', 'none'))
        set_setting('printer_address', request.form.get('printer_address', ''))
        set_setting('pos_type', request.form.get('pos_type', 'none'))
        set_setting('pos_address', request.form.get('pos_address', ''))
        set_setting('pos_timeout', request.form.get('pos_timeout', '30'))
        set_setting('currency_usd', request.form.get('currency_usd', '0'))
        set_setting('currency_eur', request.form.get('currency_eur', '0'))
        set_setting('auto_add_on_scan', request.form.get('auto_add_on_scan', '0'))
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
        db_path = os.path.join(get_data_dir(), 'barkodpos.db')
        backup_path = os.path.join(get_data_dir(), f'backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            flash(f'Yedekleme tamam: backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db', 'success')
        else:
            flash('Veritabanı dosyası bulunamadı', 'error')
    except Exception as e:
        flash(f'Yedekleme hatası: {str(e)}', 'error')
    return redirect(url_for('settings.index'))

@settings_bp.route('/restore', methods=['POST'])
@login_required
def restore():
    if not is_admin():
        flash('Yetkiniz yok', 'error')
        return redirect(url_for('main.dashboard'))
    import glob
    backup_file = request.form.get('backup_file', '').strip()
    if not backup_file or '..' in backup_file:
        flash('Geçersiz dosya', 'error')
        return redirect(url_for('settings.index'))
    backup_path = os.path.join(get_data_dir(), backup_file)
    if not os.path.exists(backup_path):
        flash('Dosya bulunamadı', 'error')
        return redirect(url_for('settings.index'))
    try:
        db_path = os.path.join(get_data_dir(), 'barkodpos.db')
        if os.path.exists(db_path):
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy2(db_path, os.path.join(get_data_dir(), f'pre_restore_{ts}.db'))
        shutil.copy2(backup_path, db_path)
        flash(f'Veritabanı geri yüklendi: {backup_file}. Uygulama yeniden başlatıldığında etkin olur.', 'success')
    except Exception as e:
        flash(f'Geri yükleme hatası: {str(e)}', 'error')
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

@settings_bp.route('/test-pos', methods=['POST'])
@login_required
def test_pos():
    if not is_admin():
        return jsonify({'error': 'Yetkiniz yok'}), 403
    from app.pos_helper import test_connection, list_ports
    ptype = request.form.get('pos_type') or request.json.get('pos_type') if request.is_json else None
    paddr = request.form.get('pos_address') or request.json.get('pos_address') if request.is_json else None
    if not ptype:
        ptype = get_setting('pos_type', 'none')
    if not paddr:
        paddr = get_setting('pos_address', '')
    result = test_connection(ptype, paddr)
    ports = list_ports() if ptype == 'serial' else []
    result['available_ports'] = ports
    return jsonify(result)
