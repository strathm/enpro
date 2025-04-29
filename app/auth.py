from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from urllib.parse import urlparse
from app import db, mail
from .models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
import logging
from datetime import datetime, timedelta
import secrets
from flask_mail import Message

# Configure logging for debugging
logging.basicConfig(filename='flask.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)  # Prefix set to /admin in __init__.py

# Login Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Password Reset Request Form
class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

# Password Reset Form
class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check for testing bypass
    bypass_admin = request.args.get('bypass_admin')
    if bypass_admin == '1':
        logger.debug(f"Bypass admin login activated, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, scheme={request.scheme}, cookies={request.cookies}")
        user = User.query.filter_by(username='admin1').first()
        if user and user.role == 'admin':
            login_user(user, remember=True)
            session['bypass_admin'] = True
            session['user_id'] = user.id
            session['role'] = user.role
            session['last_activity'] = datetime.utcnow().isoformat()  # Track session activity
            session['absolute_expiry'] = (datetime.utcnow() + timedelta(days=1)).isoformat()  # 1-day absolute timeout
            logger.info(f"Bypass login: username={user.username}, user_id={user.id}, role={user.role}, is_authenticated={current_user.is_authenticated}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
            dashboard_url = url_for('admin.dashboard', _external=True, _scheme='https')
            logger.debug(f"Bypass redirecting to: {dashboard_url}")
            return redirect(dashboard_url)
        else:
            logger.debug(f"Bypass failed: admin1 user not found or not admin")
            flash('Bypass failed: Admin user not found or not admin', 'danger')

    if current_user.is_authenticated and current_user.role == 'admin':
        logger.debug(f"User already authenticated: {current_user.username}, is_authenticated={current_user.is_authenticated}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
        dashboard_url = url_for('admin.dashboard', _external=True, _scheme='https')
        logger.debug(f"Authenticated redirecting to: {dashboard_url}")
        return redirect(dashboard_url)

    form = LoginForm()
    logger.debug(f"Login route accessed: Method={request.method}, Host={request.host}, Forwarded_Host={request.headers.get('X-Forwarded-Host')}, URL={request.url}, Scheme={request.scheme}, Headers={dict(request.headers)}, Cookies={request.cookies}")
    logger.debug(f"Session before form validation: {dict(session)}")
    logger.debug(f"CSRF Token in session: {session.get('csrf_token')}")

    if form.validate_on_submit():
        logger.debug(f"Form validated: Form data={request.form}")
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data) and user.role == 'admin':
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['role'] = user.role
            session['last_activity'] = datetime.utcnow().isoformat()  # Track session activity
            session['absolute_expiry'] = (datetime.utcnow() + timedelta(days=1)).isoformat()  # 1-day absolute timeout
            logger.info(f"Successful login: username={form.username.data}, User ID={user.id}, Role={user.role}, is_authenticated={current_user.is_authenticated}, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
            next_page = request.args.get('next')
            logger.debug(f"Next page parameter: {next_page}")
            if next_page:
                parsed = urlparse(next_page)
                allowed_hosts = [request.host, 'enpro.co.ke', 'kelvinkipkemboi1.pythonanywhere.com']
                if parsed.netloc and parsed.netloc not in allowed_hosts:
                    logger.warning(f"Invalid next parameter: {next_page}")
                    next_page = None
            dashboard_url = url_for('admin.dashboard', _external=True, _scheme='https')
            response = redirect(dashboard_url if not next_page or not parsed.path.startswith('/') else next_page)
            logger.debug(f"Redirect response headers: {dict(response.headers)}, Set-Cookie={response.headers.get('Set-Cookie')}")
            return response
        else:
            flash('Invalid username or password, or not an admin.', 'danger')
            logger.warning(f"Failed login attempt: username={form.username.data}, user_exists={user is not None}, password_match={user and check_password_hash(user.password_hash, form.password.data)}, role={user.role if user else 'None'}")
    else:
        if request.method == 'POST':
            logger.debug(f"Form validation failed: Errors={form.errors}")

    seo_title = "Admin Login - Enpro"
    seo_robots = "noindex"
    return render_template('admin/login.html', form=form, seo_title=seo_title, seo_robots=seo_robots)

# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logger.info(f"User {current_user.username if current_user.is_authenticated else 'bypass_admin'} logged out, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
    session.pop('bypass_admin', None)
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('last_activity', None)
    session.pop('absolute_expiry', None)
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index', _external=True, _scheme='https'))

# Password reset request
@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated or session.get('bypass_admin'):
        logger.debug(f"Authenticated or bypass user accessed reset password, redirecting to admin.dashboard, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
        dashboard_url = url_for('admin.dashboard', _external=True, _scheme='https')
        return redirect(dashboard_url)

    form = ResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, role='admin').first()
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Send reset email
            reset_url = url_for('auth.reset_password_token', token=token, _external=True, _scheme='https')
            msg = Message('Password Reset Request', sender='noreply@enpro.co.ke', recipients=[user.email])
            msg.body = f'''To reset your password, click the following link: {reset_url}
This link will expire in 1 hour. If you did not request a password reset, please ignore this email.'''
            try:
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'info')
                logger.info(f"Password reset email sent to {user.email}, token={token}")
            except Exception as e:
                flash('Failed to send reset email. Please try again later.', 'danger')
                logger.error(f"Failed to send reset email to {user.email}: {str(e)}")
                db.session.rollback()
                return redirect(url_for('auth.reset_password_request'))
        else:
            flash('No admin account found with that email.', 'danger')
            logger.warning(f"Password reset attempt with non-existent admin email: {form.email.data}")
        return redirect(url_for('auth.reset_password_request'))

    seo_title = "Reset Password - Enpro"
    seo_robots = "noindex"
    return render_template('admin/reset_request.html', form=form, seo_title=seo_title, seo_robots=seo_robots)

# Password reset token
@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    if current_user.is_authenticated or session.get('bypass_admin'):
        logger.debug(f"Authenticated or bypass user accessed reset password token, redirecting to admin.dashboard, host={request.host}, forwarded_host={request.headers.get('X-Forwarded-Host')}, session={dict(session)}, cookies={request.cookies}")
        dashboard_url = url_for('admin.dashboard', _external=True, _scheme='https')
        return redirect(dashboard_url)

    user = User.query.filter_by(reset_token=token, role='admin').first()
    if not user or user.reset_token_expiration < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        logger.warning(f"Invalid or expired reset token: {token}")
        return redirect(url_for('auth.reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiration = None
        db.session.commit()
        flash('Your password has been reset. Please log in.', 'success')
        logger.info(f"Password reset successful for user: {user.email}")
        return redirect(url_for('auth.login'))

    seo_title = "Reset Password - Enpro"
    seo_robots = "noindex"
    return render_template('admin/reset_password.html', form=form, token=token, seo_title=seo_title, seo_robots=seo_robots)

# Debug session route
@auth_bp.route('/debug_session')
def debug_session():
    return {
        'authenticated': current_user.is_authenticated,
        'bypass_admin': session.get('bypass_admin', False),
        'user': current_user.username if current_user.is_authenticated else None,
        'role': current_user.role if current_user.is_authenticated else session.get('role', None),
        'last_activity': session.get('last_activity', None),
        'absolute_expiry': session.get('absolute_expiry', None),
        'session': dict(session),
        'host': request.host,
        'forwarded_host': request.headers.get('X-Forwarded-Host'),
        'scheme': request.scheme,
        'headers': dict(request.headers),
        'cookies': dict(request.cookies)
    }