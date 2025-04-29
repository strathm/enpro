# C:\Users\User\Desktop\CapitalShopWeb\app\services.py
from . import db
from .models import Product, BlogPost, ContactSubmission, Page, Category, User
from .products import fetch_mascot_products, fetch_petzl_products
from datetime import datetime

class ProductService:
    @staticmethod
    def get_all_products(category_id=None):
        """Retrieve all products, optionally filtered by category."""
        query = Product.query
        if category_id is not None:
            query = query.filter_by(category_id=category_id)
        return query.order_by(Product.name).all()

    @staticmethod
    def get_products_by_source(source, category_id=None):
        """Retrieve products by source (e.g., 'mascot' or 'petzl'), optionally filtered by category."""
        query = Product.query.filter_by(source=source)
        if category_id is not None:
            query = query.filter_by(category_id=category_id)
        return query.order_by(Product.name).all()

    @staticmethod
    def get_product_by_id(product_id):
        """Retrieve a product by ID."""
        return Product.query.get(product_id)  # Returns None if not found, handled in routes

    @staticmethod
    def get_featured_products(limit=4):
        """Retrieve a limited number of featured products (e.g., newest)."""
        return Product.query.order_by(Product.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_products_by_category(category_id):
        """Retrieve products by category ID."""
        return Product.query.filter_by(category_id=category_id).order_by(Product.name).all()

    @staticmethod
    def search_products(query):
        """Search products by name (case-insensitive)."""
        return Product.query.filter(Product.name.ilike(f'%{query}%')).order_by(Product.name).all()

    @staticmethod
    def create_product(name, image_url, manufacturer_url, source, description=None, category_id=None):
        """Create a new product."""
        product = Product(
            name=name,
            image_url=image_url,
            manufacturer_url=manufacturer_url,
            source=source,
            description=description,
            category_id=category_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(product)
        db.session.commit()
        return product

    @staticmethod
    def update_product(product_id, **kwargs):
        """Update an existing product."""
        product = Product.query.get_or_404(product_id)
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.updated_at = datetime.utcnow()
        db.session.commit()
        return product

    @staticmethod
    def delete_product(product_id):
        """Delete a product."""
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()

    @staticmethod
    def populate_products():
        """Populate products from Mascot and Petzl."""
        mascot_products = fetch_mascot_products()
        petzl_products = fetch_petzl_products()
        for product_data in mascot_products + petzl_products:
            existing = Product.query.filter_by(name=product_data['name'], source=product_data['source']).first()
            if not existing:
                ProductService.create_product(**product_data)
            elif existing.manufacturer_url != product_data['manufacturer_url']:
                ProductService.update_product(existing.id, manufacturer_url=product_data['manufacturer_url'])

class BlogService:
    @staticmethod
    def get_all_posts(published_only=True):
        """Retrieve all blog posts, optionally filtered by published status."""
        query = BlogPost.query
        if published_only:
            query = query.filter_by(is_published=True)
        return query.order_by(BlogPost.created_at.desc()).all()

    @staticmethod
    def get_latest_posts(limit=3):
        """Retrieve the latest published blog posts."""
        return BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_paginated_posts(page, per_page):
        """Retrieve paginated published blog posts."""
        return BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=per_page)

    @staticmethod
    def get_post_by_slug(slug):
        """Retrieve a blog post by slug."""
        return BlogPost.query.filter_by(slug=slug).first()  # Returns None if not found, handled in routes

    @staticmethod
    def search_posts(query):
        """Search published blog posts by title (case-insensitive)."""
        return BlogPost.query.filter(BlogPost.title.ilike(f'%{query}%'), BlogPost.is_published==True).all()

    @staticmethod
    def create_post(title, slug, content, user_id, image_url=None, is_published=False):
        """Create a new blog post."""
        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            user_id=user_id,
            image_url=image_url,
            is_published=is_published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        return post

    @staticmethod
    def update_post(post_id, **kwargs):
        """Update an existing blog post."""
        post = BlogPost.query.get_or_404(post_id)
        for key, value in kwargs.items():
            if hasattr(post, key):
                setattr(post, key, value)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return post

    @staticmethod
    def delete_post(post_id):
        """Delete a blog post."""
        post = BlogPost.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()

class ContactService:
    @staticmethod
    def create_submission(name, email, message):
        """Create a new contact submission."""
        submission = ContactSubmission(
            name=name,
            email=email,
            message=message,
            submitted_at=datetime.utcnow()
        )
        db.session.add(submission)
        db.session.commit()
        return submission

    @staticmethod
    def get_all_submissions(resolved=False):
        """Retrieve all contact submissions, filtered by resolved status."""
        return ContactSubmission.query.filter_by(is_resolved=resolved).order_by(ContactSubmission.submitted_at.desc()).all()

    @staticmethod
    def resolve_submission(submission_id):
        """Mark a submission as resolved."""
        submission = ContactSubmission.query.get_or_404(submission_id)
        submission.is_resolved = True
        submission.resolved_at = datetime.utcnow()  # Added for tracking
        db.session.commit()
        return submission

class PageService:
    @staticmethod
    def get_all_pages(published_only=True):
        """Retrieve all pages, optionally filtered by published status."""
        query = Page.query
        if published_only:
            query = query.filter_by(is_published=True)
        return query.order_by(Page.created_at.desc()).all()

    @staticmethod
    def get_page_by_slug(slug):
        """Retrieve a page by slug."""
        return Page.query.filter_by(slug=slug).first()  # Returns None if not found, handled in routes

    @staticmethod
    def create_page(title, slug, content, is_published=True):
        """Create a new static page."""
        page = Page(
            title=title,
            slug=slug,
            content=content,
            is_published=is_published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(page)
        db.session.commit()
        return page

    @staticmethod
    def update_page(page_id, **kwargs):
        """Update an existing page."""
        page = Page.query.get_or_404(page_id)
        for key, value in kwargs.items():
            if hasattr(page, key):
                setattr(page, key, value)
        page.updated_at = datetime.utcnow()
        db.session.commit()
        return page

    @staticmethod
    def delete_page(page_id):
        """Delete a page."""
        page = Page.query.get_or_404(page_id)
        db.session.delete(page)
        db.session.commit()