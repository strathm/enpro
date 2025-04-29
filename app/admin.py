from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from . import db, csrf
from .models import User, Product, BlogPost, ContactSubmission, Category, Page, BlogImage
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, URL, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
import uuid
from werkzeug.utils import secure_filename
import logging
from .services import ProductService, BlogService, ContactService, PageService

# Setup logging
logging.basicConfig(filename='flask.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    def wrap(*args, **kwargs):
        logger.debug(f"Checking admin access: is_authenticated={current_user.is_authenticated}, user={current_user.username if current_user.is_authenticated else 'None'}, role={current_user.role if current_user.is_authenticated else 'None'}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
        if not current_user.is_authenticated:
            logger.warning(f"User not authenticated, redirecting to auth.login, host={request.host}")
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.login', _external=True, _scheme='https'))
        if current_user.role != 'admin':
            logger.warning(f"User {current_user.username} has role {current_user.role}, not admin, host={request.host}")
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('main.index', _external=True, _scheme='https'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return login_required(wrap)

def get_unique_filename(filename, directory):
    """Generate a unique filename by appending a counter if the file exists."""
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    return unique_filename

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    image_file = FileField('Product Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    manufacturer_url = StringField('Manufacturer URL', validators=[DataRequired(), URL(require_tld=True, message="Invalid URL"), Length(max=500)])
    source = SelectField('Source', choices=[('mascot', 'Mascot Workwear'), ('petzl', 'Petzl Safety Gear')], 
                         validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired(message="Please select a category")])
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

class ProductImportForm(FlaskForm):
    product_url = StringField('Product URL', validators=[DataRequired(), URL(require_tld=True, message="Invalid URL"), Length(max=500)])
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    image_url = StringField('Image URL', validators=[Optional(), URL(require_tld=True, message="Invalid URL"), Length(max=500)])
    manufacturer_url = StringField('Manufacturer URL', validators=[DataRequired(), URL(require_tld=True, message="Invalid URL"), Length(max=500)])
    source = SelectField('Source', choices=[('mascot', 'Mascot Workwear'), ('petzl', 'Petzl Safety Gear')], 
                         validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired(message="Please select a category")])
    submit = SubmitField('Import Product')

    def __init__(self, *args, **kwargs):
        super(ProductImportForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    image_files = FileField('Blog Images', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')], render_kw={'multiple': True})
    alt_text = StringField('Image Alt Text', validators=[Optional(), Length(max=200)])
    is_published = BooleanField('Published')
    submit = SubmitField('Save')

class PageForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    is_published = BooleanField('Published')
    submit = SubmitField('Save')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    logger.debug(f"Accessing admin dashboard, user={current_user.username}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
    product_count = Product.query.count()
    blog_count = BlogPost.query.count()
    contact_count = ContactSubmission.query.filter_by(is_resolved=False).count()
    page_count = Page.query.count()
    return render_template('admin/dashboard.html', 
                           product_count=product_count, 
                           blog_count=blog_count, 
                           contact_count=contact_count,
                           page_count=page_count)

@admin_bp.route('/products')
@admin_required
def products():
    logger.debug(f"Accessing products, user={current_user.username}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@admin_bp.route('/product/new', methods=['GET', 'POST'])
@admin_required
def product_new():
    form = ProductForm()
    if form.validate_on_submit():
        image_url = None
        if form.image_file.data:
            try:
                file = form.image_file.data
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1].lower()
                if extension not in ('.jpg', '.jpeg', '.png'):
                    flash('Invalid image format. Only JPG, JPEG, PNG allowed.', 'danger')
                    logger.error(f"Invalid image format: {extension}, user={current_user.username}, host={request.host}")
                    return render_template('admin/product_edit.html', form=form, title='New Product')
                
                # Ensure the products directory exists
                image_dir = os.path.join('app', 'static','assets', 'img', 'products')
                os.makedirs(image_dir, exist_ok=True)
                
                # Get a unique filename to avoid overwrites
                filename = get_unique_filename(filename, image_dir)
                image_path = os.path.join(image_dir, filename)
                
                # Save the file
                file.save(image_path)
                image_url = filename
                logger.info(f"Saved image: {image_path}, original filename: {file.filename}, saved as: {filename}, user={current_user.username}, host={request.host}")
            except Exception as e:
                flash(f'Failed to save image: {str(e)}', 'danger')
                logger.error(f"Image save failed: {str(e)}, user={current_user.username}, host={request.host}")
                return render_template('admin/product_edit.html', form=form, title='New Product')

        product = Product(
            name=form.name.data,
            description=form.description.data,
            image_url=image_url,
            manufacturer_url=form.manufacturer_url.data,
            source=form.source.data,
            category_id=form.category_id.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product created successfully!', 'success')
        logger.info(f"Product created: {product.name}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.products', _external=True, _scheme='https'))
    return render_template('admin/product_edit.html', form=form, title='New Product')

@admin_bp.route('/product/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def product_edit(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        image_url = product.image_url
        if request.form.get('remove_image'):
            if image_url and os.path.exists(os.path.join('app', 'static', 'assets', 'img', 'products', image_url)):
                os.remove(os.path.join('app', 'static', 'img', 'assets', 'products', image_url))
                logger.info(f"Deleted image: {image_url}, user={current_user.username}, host={request.host}")
            image_url = None
        if form.image_file.data:
            try:
                file = form.image_file.data
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1].lower()
                if extension not in ('.jpg', '.jpeg', '.png'):
                    flash('Invalid image format. Only JPG, JPEG, PNG allowed.', 'danger')
                    logger.error(f"Invalid image format: {extension}, user={current_user.username}, host={request.host}")
                    return render_template('admin/product_edit.html', form=form, title='Edit Product', product=product)
                
                # Ensure the products directory exists
                image_dir = os.path.join('app', 'static', 'assets', 'img', 'products')
                os.makedirs(image_dir, exist_ok=True)
                
                # Get a unique filename to avoid overwrites
                filename = get_unique_filename(filename, image_dir)
                image_path = os.path.join(image_dir, filename)
                
                # Save the file
                file.save(image_path)
                
                # Remove old image if it exists
                if product.image_url and os.path.exists(os.path.join('app', 'static', 'assets', 'img', 'products', product.image_url)):
                    os.remove(os.path.join('app', 'static', 'assets', 'img', 'products', product.image_url))
                    logger.info(f"Deleted old image: {product.image_url}, user={current_user.username}, host={request.host}")
                
                image_url = filename
                logger.info(f"Saved image: {image_path}, original filename: {file.filename}, saved as: {filename}, user={current_user.username}, host={request.host}")
            except Exception as e:
                flash(f'Failed to save image: {str(e)}', 'danger')
                logger.error(f"Image save failed: {str(e)}, user={current_user.username}, host={request.host}")
                return render_template('admin/product_edit.html', form=form, title='Edit Product', product=product)

        product.name = form.name.data
        product.description = form.description.data
        product.image_url = image_url
        product.manufacturer_url = form.manufacturer_url.data
        product.source = form.source.data
        product.category_id = form.category_id.data
        db.session.commit()
        flash('Product updated successfully!', 'success')
        logger.info(f"Product updated: {product.name}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.products', _external=True, _scheme='https'))
    return render_template('admin/product_edit.html', form=form, title='Edit Product', product=product)

@admin_bp.route('/product/<int:id>/delete', methods=['POST'])
@admin_required
def product_delete(id):
    product = Product.query.get_or_404(id)
    if product.image_url and os.path.exists(os.path.join('app', 'static', 'assets', 'img', 'products', product.image_url)):
        os.remove(os.path.join('app', 'static', 'assets', 'img',  'products', product.image_url))
        logger.info(f"Deleted image: {product.image_url}, user={current_user.username}, host={request.host}")
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    logger.info(f"Product deleted: {product.name}, user={current_user.username}, host={request.host}")
    return redirect(url_for('admin.products', _external=True, _scheme='https'))

@admin_bp.route('/product/import', methods=['GET', 'POST'])
@admin_required
def product_import():
    form = ProductImportForm()
    if form.validate_on_submit():
        product_url = form.product_url.data
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(product_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            domain = urlparse(product_url).netloc
            if 'mascotworkwear.com' in domain:
                source = 'mascot'
                name = soup.select_one('h1.product-title--main') or soup.find('h1')
                name = name.text.strip() if name else 'Unknown Product'
                description = soup.select_one('.product-description')
                description = description.text.strip() if description else ''
                image = soup.select_one('.product-image__main img') or soup.select_one('img[alt*="%s" i]' % name[:30])
                image_url = image['src'] if image else ''
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://www.mascotworkwear.com{image_url}"
            elif 'petzl.com' in domain:
                source = 'petzl'
                name = soup.select_one('h1.product-name') or soup.find('h1')
                name = name.text.strip() if name else 'Unknown Product'
                description = soup.select_one('.product-description') or soup.find('meta', {'name': 'description'})
                description = description.text.strip() if description and hasattr(description, 'text') else description['content'] if description else ''
                image = soup.select_one('.product-img img') or soup.select_one('img[alt*="%s" i]' % name[:30])
                image_url = image['src'] if image else image['data-src'] if image and image.get('data-src') else ''
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://www.petzl.com{image_url}"
            else:
                flash('Invalid URL. Only Mascot Workwear or Petzl URLs are supported.', 'danger')
                logger.warning(f"Invalid import URL: {product_url}, user={current_user.username}, host={request.host}")
                return render_template('admin/product_import.html', title='Import Product', form=form)

            local_image_url = ''
            if image_url:
                try:
                    img_response = requests.get(image_url, headers=headers, timeout=10)
                    img_response.raise_for_status()
                    
                    # Extract the original filename from the URL
                    parsed_url = urlparse(image_url)
                    filename = secure_filename(os.path.basename(parsed_url.path))
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        filename += '.jpg'  # Default to .jpg if no valid extension
                    
                    # Ensure the products directory exists
                    image_dir = os.path.join('app', 'static', 'assets', 'img', 'products')
                    os.makedirs(image_dir, exist_ok=True)
                    
                    # Get a unique filename to avoid overwrites
                    filename = get_unique_filename(filename, image_dir)
                    img_path = os.path.join(image_dir, filename)
                    
                    # Save the image
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                    local_image_url = filename
                    logger.info(f"Imported image: {img_path}, original URL: {image_url}, saved as: {filename}, user={current_user.username}, host={request.host}")
                except Exception as e:
                    flash(f'Failed to download image: {str(e)}', 'warning')
                    logger.error(f"Image import failed: {str(e)}, user={current_user.username}, host={request.host}")

            category_map = {
                'jacket': 1, 'trouser': 2, 'shirt': 3, 't-shirt': 4, 'polo': 5, 'sweatshirt': 6,
                'footwear': 7, 'belt': 8, 'helmet': 9, 'harness': 10, 'headlamp': 11,
                'lanyard': 12, 'carabiner': 13, 'rope': 14
            }
            suggested_category = None
            for key, cat_id in category_map.items():
                if key in name.lower() or (description and key in description.lower()):
                    suggested_category = cat_id
                    break
            suggested_category = suggested_category or 8

            form.name.data = name
            form.source.data = source
            form.description.data = description
            form.image_url.data = local_image_url
            form.manufacturer_url.data = product_url
            form.category_id.data = suggested_category

            if request.form.get('confirm'):
                product = Product(
                    name=form.name.data,
                    description=form.description.data,
                    image_url=form.image_url.data,
                    manufacturer_url=form.manufacturer_url.data,
                    source=form.source.data,
                    category_id=form.category_id.data
                )
                db.session.add(product)
                db.session.commit()
                flash('Product imported successfully!', 'success')
                logger.info(f"Product imported: {product.name}, user={current_user.username}, host={request.host}")
                return redirect(url_for('admin.products', _external=True, _scheme='https'))

        except Exception as e:
            flash(f'Failed to extract data: {str(e)}', 'danger')
            logger.error(f"Import failed: {str(e)}, user={current_user.username}, host={request.host}")

    return render_template('admin/product_import.html', title='Import Product', form=form)

@admin_bp.route('/blog')
@admin_required
def blog():
    logger.debug(f"Accessing blog, user={current_user.username}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
    posts = BlogPost.query.all()
    return render_template('admin/blog.html', posts=posts)

@admin_bp.route('/blog/new', methods=['GET', 'POST'])
@admin_required
def blog_new():
    form = BlogPostForm()
    if form.validate_on_submit():
        post = BlogPost(
            title=form.title.data,
            slug=form.slug.data,
            content=form.content.data,
            is_published=form.is_published.data,
            user_id=current_user.id
        )
        db.session.add(post)
        db.session.flush()

        if form.image_files.data:
            for file in request.files.getlist('image_files'):
                try:
                    extension = os.path.splitext(secure_filename(file.filename))[1].lower()
                    if extension not in ('.jpg', '.jpeg', '.png'):
                        flash(f'Invalid image format for {file.filename}. Only JPG, JPEG, PNG allowed.', 'danger')
                        logger.error(f"Invalid image format: {extension}, user={current_user.username}, host={request.host}")
                        continue
                    filename = f"{uuid.uuid4().hex}{extension}"
                    image_path = os.path.join('app', 'static', 'assets', 'img', 'blog', filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    file.save(image_path)
                    image = BlogImage(
                        image_url=filename,
                        alt_text=form.alt_text.data or f"Image for {form.title.data}",
                        post_id=post.id
                    )
                    db.session.add(image)
                    logger.info(f"Saved blog image: {image_path}, URL: {filename}, user={current_user.username}, host={request.host}")
                except Exception as e:
                    flash(f'Failed to save image {file.filename}: {str(e)}', 'danger')
                    logger.error(f"Blog image save failed: {str(e)}, user={current_user.username}, host={request.host}")
                    continue

        db.session.commit()
        flash('Blog post created successfully!', 'success')
        logger.info(f"Blog post created: {post.title}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.blog', _external=True, _scheme='https'))
    return render_template('admin/blog_edit.html', form=form, title='New Blog Post')

@admin_bp.route('/blog/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def blog_edit(id):
    post = BlogPost.query.get_or_404(id)
    form = BlogPostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data
        post.slug = form.slug.data
        post.content = form.content.data
        post.is_published = form.is_published.data

        delete_images = request.form.getlist('delete_images')
        for image_id in delete_images:
            image = BlogImage.query.get(int(image_id))
            if image:
                image_path = os.path.join('app', 'static', 'assets', 'img', 'blog', image.image_url)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Deleted blog image: {image_path}, user={current_user.username}, host={request.host}")
                db.session.delete(image)

        if form.image_files.data:
            for file in request.files.getlist('image_files'):
                try:
                    extension = os.path.splitext(secure_filename(file.filename))[1].lower()
                    if extension not in ('.jpg', '.jpeg', '.png'):
                        flash(f'Invalid image format for {file.filename}. Only JPG, JPEG, PNG allowed.', 'danger')
                        logger.error(f"Invalid image format: {extension}, user={current_user.username}, host={request.host}")
                        continue
                    filename = f"{uuid.uuid4().hex}{extension}"
                    image_path = os.path.join('app', 'static', 'assets', 'img', 'blog', filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    file.save(image_path)
                    image = BlogImage(
                        image_url=filename,
                        alt_text=form.alt_text.data or f"Image for {form.title.data}",
                        post_id=post.id
                    )
                    db.session.add(image)
                    logger.info(f"Saved blog image: {image_path}, URL: {filename}, user={current_user.username}, host={request.host}")
                except Exception as e:
                    flash(f'Failed to save image {file.filename}: {str(e)}', 'danger')
                    logger.error(f"Blog image save failed: {str(e)}, user={current_user.username}, host={request.host}")
                    continue

        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        logger.info(f"Blog post updated: {post.title}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.blog', _external=True, _scheme='https'))
    return render_template('admin/blog_edit.html', form=form, title='Edit Blog Post', post=post)

@admin_bp.route('/blog/<int:id>/delete', methods=['POST'])
@admin_required
def blog_delete(id):
    post = BlogPost.query.get_or_404(id)
    for image in post.images:
        image_path = os.path.join('app', 'static', 'assets', 'img', 'blog', image.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Deleted blog image: {image_path}, user={current_user.username}, host={request.host}")
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    logger.info(f"Blog post deleted: {post.title}, user={current_user.username}, host={request.host}")
    return redirect(url_for('admin.blog', _external=True, _scheme='https'))

@admin_bp.route('/contacts')
@admin_required
def contacts():
    logger.debug(f"Accessing contacts, user={current_user.username}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
    submissions = ContactSubmission.query.all()
    return render_template('admin/contacts.html', submissions=submissions)

@admin_bp.route('/contact/<int:id>/resolve', methods=['POST'])
@admin_required
def contact_resolve(id):
    submission = ContactSubmission.query.get_or_404(id)
    submission.is_resolved = True
    db.session.commit()
    flash('Contact submission marked as resolved.', 'success')
    logger.info(f"Contact submission resolved: {id}, user={current_user.username}, host={request.host}")
    return redirect(url_for('admin.contacts', _external=True, _scheme='https'))

@admin_bp.route('/pages')
@admin_required
def pages():
    logger.debug(f"Accessing pages, user={current_user.username}, host={request.host}, session={dict(session)}, cookies={request.cookies}")
    pages = Page.query.all()
    return render_template('admin/pages.html', pages=pages)

@admin_bp.route('/page/new', methods=['GET', 'POST'])
@admin_required
def page_new():
    form = PageForm()
    if form.validate_on_submit():
        page = Page(
            title=form.title.data,
            slug=form.slug.data,
            content=form.content.data,
            is_published=form.is_published.data
        )
        db.session.add(page)
        db.session.commit()
        flash('Page created successfully!', 'success')
        logger.info(f"Page created: {page.title}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.pages', _external=True, _scheme='https'))
    return render_template('admin/page_edit.html', form=form, title='New Page')

@admin_bp.route('/page/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def page_edit(id):
    page = Page.query.get_or_404(id)
    form = PageForm(obj=page)
    if form.validate_on_submit():
        page.title = form.title.data
        page.slug = form.slug.data
        page.content = form.content.data
        page.is_published = form.is_published.data
        db.session.commit()
        flash('Page updated successfully!', 'success')
        logger.info(f"Page updated: {page.title}, user={current_user.username}, host={request.host}")
        return redirect(url_for('admin.pages', _external=True, _scheme='https'))
    return render_template('admin/page_edit.html', form=form, title='Edit Page', page=page)

@admin_bp.route('/page/<int:id>/delete', methods=['POST'])
@admin_required
def page_delete(id):
    page = Page.query.get_or_404(id)
    db.session.delete(page)
    db.session.commit()
    flash('Page deleted successfully!', 'success')
    logger.info(f"Page deleted: {page.title}, user={current_user.username}, host={request.host}")
    return redirect(url_for('admin.pages', _external=True, _scheme='https'))