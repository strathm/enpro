import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_session import Session
from sqlalchemy.exc import InternalError
from sqlalchemy.sql import text  # Import text for SQL queries
import logging

# Configure logging
logging.basicConfig(filename='flask.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static/assets')
    logger.debug(f"Template folder: {os.path.abspath(app.template_folder)}")

    # Load configuration based on environment
    from config import get_config
    app.config.from_object(get_config())

    # Ensure SESSION_SQLALCHEMY is set to use the same db instance
    app.config['SESSION_SQLALCHEMY'] = db

    # Apply ProxyFix for forwarded headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # Initialize Flask-Session
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    Session(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import models after db is initialized to avoid circular import
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        logger.debug(f"Loading user with ID: {user_id}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}")
        return User.query.get(int(user_id))

    # Handle aborted transactions
    @app.before_request
    def handle_aborted_transaction():
        try:
            # Test query to check transaction state, using text() for raw SQL
            db.session.execute(text('SELECT 1'))
        except InternalError as e:
            logger.error(f"Transaction error: {str(e)}, URL={request.url}, host={request.host}")
            if 'current transaction is aborted' in str(e):
                db.session.rollback()  # Roll back the aborted transaction
                db.session.commit()   # Ensure the session is clean
            else:
                raise  # Re-raise other errors

    # Session validation middleware
    @app.before_request
    def validate_session():
        if request.blueprint == 'admin' and current_user.is_authenticated:
            last_activity = session.get('last_activity')
            absolute_expiry = session.get('absolute_expiry')
            now = datetime.utcnow()

            # Check absolute timeout (1 day)
            if absolute_expiry and datetime.fromisoformat(absolute_expiry) < now:
                logger.warning(f"Session expired (absolute timeout): user={current_user.username}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
                logout_user()
                session.clear()
                flash('Your session has expired. Please log in again.', 'danger')
                return redirect(url_for('auth.login', _external=True, _scheme=app.config['PREFERRED_URL_SCHEME']))

            # Check idle timeout (30 minutes)
            if last_activity and (now - datetime.fromisoformat(last_activity)) > timedelta(minutes=30):
                logger.warning(f"Session expired (idle timeout): user={current_user.username}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
                logout_user()
                session.clear()
                flash('Your session has timed out due to inactivity. Please log in again.', 'danger')
                return redirect(url_for('auth.login', _external=True, _scheme=app.config['PREFERRED_URL_SCHEME']))

            # Update last activity
            session['last_activity'] = now.isoformat()

    from .routes import main_bp
    from .auth import auth_bp
    from .admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/admin')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    app.jinja_env.filters['capitalize_source'] = lambda s: s.capitalize()

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%Y-%m-%d'):
        if value == 'now':
            value = datetime.utcnow()
        return value.strftime(format)

    @app.errorhandler(404)
    def not_found(error):
        logger.error(f"404 error: {str(error)}, URL={request.url}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Rollback the transaction to avoid issues with aborted transactions
        db.session.rollback()
        logger.error(f"500 error: {str(error)}, URL={request.url}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}")
        return render_template('500.html'), 500

    with app.app_context():
        db.engine.dispose()  # Reset connection pool on startup
        db.create_all()  # Creates tables if they don't exist

    return app

def create_test_app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://user:password@localhost/test_enpro'
    return app