import os
import secrets
from dotenv import load_dotenv

load_dotenv()

def get_data_dir():
    data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'BarkodPOS', 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(get_data_dir(), "barkodpos.db").replace(os.sep, "/")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 30},
        'pool_pre_ping': True,
    }
    WTF_CSRF_ENABLED = False
