from . import db
from flask_login import UserMixin
from datetime import datetime, UTC
from sqlalchemy import CheckConstraint
from werkzeug.security import generate_password_hash, check_password_hash

# BlogPost model for blog content
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)  # SEO-friendly URL
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_published = db.Column(db.Boolean, default=False)
    images = db.relationship('BlogImage', backref='post', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<BlogPost {self.title}>'

# BlogImage model for blog post images
class BlogImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=False)
    alt_text = db.Column(db.String(200))  # Optional description for accessibility

    def __repr__(self):
        return f'<BlogImage {self.image_url}>'

# User model for authentication and CMS access
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    token = db.Column(db.String(100), nullable=True)  # Added for token-based auth
    token_expiration = db.Column(db.DateTime, nullable=True)  # Added for token-based auth

    blog_posts = db.relationship('BlogPost', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Category model for organizing products
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy=True)

    # Ensure case-insensitive uniqueness
    __table_args__ = (
        db.Index('ix_category_name_lower', db.func.lower(name), unique=True),
    )

    def __repr__(self):
        return f'<Category {self.name}>'

# Product model for Mascot Workwear and Petzl items
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)  # Optional product details
    image_url = db.Column(db.String(500))  # URL to product image
    manufacturer_url = db.Column(db.String(500), nullable=False)  # Redirect URL
    source = db.Column(db.String(50), nullable=False)  # 'mascot' or 'petzl'
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Restrict source to 'mascot' or 'petzl'
    __table_args__ = (
        CheckConstraint(source.in_(['mascot', 'petzl']), name='check_source_valid'),
    )

    def __repr__(self):
        return f'<Product {self.name} ({self.source})>'

# ContactSubmission model for contact form data
class ContactSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    is_resolved = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ContactSubmission from {self.name}>'

# Page model for static pages (e.g., About Us) - future-proofing
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_published = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Page {self.title}>'

# Setting model for site-wide configurations (future-proofing)
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'site_name', 'contact_email'
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<Setting {self.key} = {self.value}>'