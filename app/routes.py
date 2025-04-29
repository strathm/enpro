# C:\Users\User\Desktop\CapitalShopWeb\app\main.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from . import  mail, db
from .models import Product, BlogPost, ContactSubmission, Page, Category, User
from .products import populate_products
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from .services import ProductService, BlogService, ContactService, PageService
from flask_mail import Message
main_bp = Blueprint('main', __name__)

# Contact Form
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')

# Home Page
@main_bp.route('/')
def index():
    form = ContactForm()  # Add form for contact section
    featured_products = ProductService.get_featured_products(limit=4)
    latest_posts = BlogService.get_latest_posts(limit=3)
    return render_template('index.html', products=featured_products, posts=latest_posts, form=form)

# About Us Page
@main_bp.route('/about')
def about():
    page = PageService.get_page_by_slug('about')
    if page and page.is_published:
        return render_template('about.html', page=page)
    return render_template('about.html')  # Fallback to static template

# Products Page
@main_bp.route('/products')
@main_bp.route('/products/<category>')
def products(category=None):
    categories = Category.query.order_by(Category.name).all()
    
    if category:
        category_obj = Category.query.filter(Category.name.ilike(category)).first()
        if category_obj:
            products = ProductService.get_products_by_category(category_obj.id)
            mascot_products = [p for p in products if p.source == 'mascot']
            petzl_products = [p for p in products if p.source == 'petzl']
        else:
            mascot_products = []
            petzl_products = []
    else:
        mascot_products = ProductService.get_products_by_source('mascot')
        petzl_products = ProductService.get_products_by_source('petzl')
    
    return render_template('products.html', 
                          mascot_products=mascot_products, 
                          petzl_products=petzl_products, 
                          categories=categories,
                          category=category)

# Product Details Page
@main_bp.route('/product/<int:product_id>')
def product_details(product_id):
    product = ProductService.get_product_by_id(product_id)
    if not product:
        abort(404)
    return render_template('pro-details.html', product=product)

# Blog Page
@main_bp.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    posts = BlogService.get_paginated_posts(page=page, per_page=10)
    return render_template('blog.html', posts=posts)

# Blog Post Details
@main_bp.route('/blog/<slug>')
def blog_details(slug):
    post = BlogService.get_post_by_slug(slug)
    if not post or not post.is_published:
        abort(404)
    return render_template('blog-details.html', post=post)

# Contact Page
@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Store the contact submission
        ContactService.create_submission(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data
        )
        
        # Fetch admin users from the database
        admin_users = User.query.filter_by(role='admin').all()
        admin_emails = [user.email for user in admin_users]
        
        if admin_emails:
            # Prepare email notification
            msg = Message(
                subject='New Contact Form Submission',
                recipients=admin_emails,
                body=f"""
                New contact form submission received:

                Name: {form.name.data}
                Email: {form.email.data}
                Message: {form.message.data}
                """
            )
            try:
                mail.send(msg)
            except Exception as e:
                flash('Message saved, but there was an issue sending the email notification.', 'warning')
        
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html', form=form)

# Category Filter
@main_bp.route('/category/<int:category_id>')
def category_products(category_id):
    category = Category.query.get_or_404(category_id)
    products = ProductService.get_products_by_category(category_id)
    mascot_products = [p for p in products if p.source == 'mascot']
    petzl_products = [p for p in products if p.source == 'petzl']
    categories = Category.query.order_by(Category.name).all()
    return render_template('products.html', 
                          mascot_products=mascot_products, 
                          petzl_products=petzl_products, 
                          categories=categories,
                          category=category.name.lower())
from flask_sqlalchemy import pagination
from sqlalchemy import or_, func
# Static Page
@main_bp.route('/page/<slug>')
def page(slug):
    page = PageService.get_page_by_slug(slug)
    if not page or not page.is_published:
        abort(404)
    return render_template('page.html', page=page)

# Search Functionality
@main_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of results per page

    if not query:
        flash('Please enter a search term.', 'info')
        return redirect(url_for('main.index'))

    # Search products (name, description, source)
    products_query = Product.query.filter(
        or_(
            func.lower(Product.name).contains(func.lower(query)),
            func.lower(Product.description).contains(func.lower(query)),
            func.lower(Product.source).contains(func.lower(query))
        )
    )
    products_paginated = products_query.paginate(page=page, per_page=per_page, error_out=False)

    # Search blog posts (title, content, only published)
    posts_query = BlogPost.query.filter(
        BlogPost.is_published == True,
        or_(
            func.lower(BlogPost.title).contains(func.lower(query)),
            func.lower(BlogPost.content).contains(func.lower(query))
        )
    )
    posts_paginated = posts_query.paginate(page=page, per_page=per_page, error_out=False)

    # SEO metadata
    seo_title = f"Search Results for '{query}' - enpro"
    seo_description = f"Find Mascot Workwear, Petzl safety gear, and blog posts related to '{query}' at enpro. Browse our premium industrial equipment and insights."

    return render_template(
        'search.html',
        query=query,
        products=products_paginated.items,
        products_pagination=products_paginated,
        posts=posts_paginated.items,
        posts_pagination=posts_paginated,
        seo_title=seo_title,
        seo_description=seo_description
    )

# Sitemap (for SEO)
@main_bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = [
        {'loc': url_for('main.index', _external=True), 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': url_for('main.about', _external=True), 'changefreq': 'monthly', 'priority': '0.8'},
        {'loc': url_for('main.products', _external=True), 'changefreq': 'weekly', 'priority': '0.9'},
        {'loc': url_for('main.blog', _external=True), 'changefreq': 'weekly', 'priority': '0.8'},
        {'loc': url_for('main.contact', _external=True), 'changefreq': 'monthly', 'priority': '0.7'}
    ]
    
    for product in ProductService.get_all_products():
        pages.append({'loc': url_for('main.product_details', product_id=product.id, _external=True), 
                      'changefreq': 'monthly', 'priority': '0.6'})
    for post in BlogService.get_all_posts(published_only=True):
        pages.append({'loc': url_for('main.blog_details', slug=post.slug, _external=True), 
                      'changefreq': 'monthly', 'priority': '0.7'})
    for page in PageService.get_all_pages(published_only=True):
        pages.append({'loc': url_for('main.page', slug=page.slug, _external=True), 
                      'changefreq': 'monthly', 'priority': '0.7'})
    
    return render_template('sitemap.xml', pages=pages), {'Content-Type': 'application/xml'}

# Populate Products (optional, restricted to admins in production)
@main_bp.route('/populate-products', methods=['POST'])
def populate():
    populate_products()
    flash('Products populated successfully!', 'success')
    return redirect(url_for('main.products'))

# Error Handlers
@main_bp.app_errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500