import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'BZ6xC4KQp7HW8duX7MCiFVBXZz0HiQ4fFjiux95TtoA'

    # Main Database (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://enpro_user:enpro_password@localhost:5432/enpro'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,      # Test connections before use to avoid aborted transactions
        'pool_recycle': 3600,       # Recycle connections every 1 hour
        'pool_size': 5,             # Number of connections to keep open
        'max_overflow': 10,         # Allow up to 10 additional connections
    }

    # CSRF (disabled for debugging, re-enable in production)
    WTF_CSRF_ENABLED = False
    WTF_CSRF_CHECK_DEFAULT = False
    # TODO: Re-enable WTF_CSRF_ENABLED = True for production security after debugging

    # Sessions (server-side with Flask-Session)
    SESSION_TYPE = 'sqlalchemy'  # Store sessions in database
    SESSION_SQLALCHEMY_TABLE = 'sessions'  # Explicitly name the sessions table
    SESSION_SQLALCHEMY = None  # Will be set in app.py to use the same db instance
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = None  # Use request host for enpro.co.ke and kelvinkipkemboi1.pythonanywhere.com
    SESSION_COOKIE_PATH = '/'  # Valid for all paths

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'capitalshop', 'assets', 'img', 'Uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'mail.enpro.co.ke'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 465)
    MAIL_USE_SSL = True  # Use SSL for port 465
    MAIL_USE_TLS = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'notification@enpro.co.ke'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'Tq48Qkq3w9'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'notification@enpro.co.ke'

    # Misc
    POSTS_PER_PAGE = 10

    # Maximum file size for the database (100 MB)
    MAX_DB_SIZE = 100 * 1024 * 1024  # 100 MB

    def switch_database(self):
        """Switch to a new database if the current one exceeds 100MB."""
        # No need for switching database in this case since PostgreSQL is being used
        pass

# Development Configuration
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries for debugging
    SESSION_COOKIE_SECURE = False  # Allow non-HTTPS for local dev
    PREFERRED_URL_SCHEME = 'http'  # Use HTTP for URL generation in development
    SESSION_COOKIE_DOMAIN = None
    WTF_CSRF_ENABLED = False
    WTF_CSRF_CHECK_DEFAULT = False

# Production Configuration
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://enpro_user:enpro_password@localhost:5432/enpro'
    SESSION_TYPE = 'sqlalchemy'
    SESSION_SQLALCHEMY_TABLE = 'sessions'  # Explicitly name the sessions table
    SESSION_COOKIE_SECURE = True  # Enforce HTTPS for session cookies
    PREFERRED_URL_SCHEME = 'https'  # Enforce HTTPS for URL generation
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    WTF_CSRF_ENABLED = False  # TODO: Re-enable for security after debugging
    WTF_CSRF_CHECK_DEFAULT = False
    SERVER_NAME = None  # Allow dynamic host handling

# Environment mapping
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}

def get_config(env=None):
    env = env or os.environ.get('FLASK_ENV', 'production')
    return config_by_name.get(env, ProductionConfig)