import re
import os
from flask import current_app
from flask_mail import Message
from . import mail  # Assuming Flask-Mail is added in __init__.py

def generate_slug(title):
    """Generate a URL-friendly slug from a title."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower()).strip()
    slug = re.sub(r'\s+', '-', slug)
    return slug[:200]  # Truncate to match model field length

def send_email(subject, recipients, body, html=None):
    """Send an email using Flask-Mail (future-proofing)."""
    if not hasattr(current_app, 'extensions') or 'mail' not in current_app.extensions:
        raise RuntimeError("Flask-Mail is not initialized.")
    msg = Message(subject, recipients=recipients, sender=current_app.config['MAIL_DEFAULT_SENDER'])
    msg.body = body
    if html:
        msg.html = html
    mail.send(msg)

def sanitize_filename(filename):
    """Sanitize a filename for safe storage (future-proofing for uploads)."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

def get_upload_path(filename):
    """Generate a path for uploaded files."""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], sanitize_filename(filename))

def paginate_query(query, page, per_page):
    """Paginate a SQLAlchemy query."""
    return query.paginate(page=page, per_page=per_page, error_out=False)

def validate_url(url):
    """Basic URL validation."""
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None