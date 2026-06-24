import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash

MASTER_PASSWORD_HASH = hashlib.sha256(b'123admin123').hexdigest()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(stored_hash, password):
    if not stored_hash:
        return False
    return stored_hash == hash_password(password)

def is_master_password(password):
    return hash_password(password) == MASTER_PASSWORD_HASH

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.personel_sec'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_id():
    return session.get('user_id')

def get_branch_id():
    return session.get('branch_id')

def is_admin():
    return session.get('role') == 'admin'

def get_user_name():
    return session.get('user_name', '')

def has_permission(permission):
    if is_admin():
        return True
    perms = session.get('permissions', '')
    return permission in [p.strip() for p in perms.split(',') if p.strip()]

def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(permission):
                flash('Bu sayfaya erişim yetkiniz yok', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator