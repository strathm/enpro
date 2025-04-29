import requests
from bs4 import BeautifulSoup
from . import db
from .models import Product
from datetime import datetime

# Headers to mimic a browser (helps avoid scraping blocks)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Base URLs for scraping
MASCOT_URL = 'https://www.mascotworkwear.com/en/jackets'
PETZL_URL = 'https://www.petzl.com/US/en'

def fetch_mascot_products():
    """Fetch product data from Mascot Workwear (mocked for now)."""
    try:
        response = requests.get(MASCOT_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Placeholder: Replace with actual scraping logic based on site structure
        # Example: Find product items (adjust selectors based on real HTML)
        products = []
        # Assuming products are in a div with class 'product-item'
        for item in soup.select('.product-item'):  # Hypothetical selector
            name = item.select_one('.product-name').text.strip() if item.select_one('.product-name') else 'Unknown'
            image = item.select_one('img')['src'] if item.select_one('img') else ''
            url = item.select_one('a')['href'] if item.select_one('a') else MASCOT_URL
            products.append({
                'name': name,
                'image_url': image,
                'manufacturer_url': url,
                'source': 'mascot'
            })
        
        # Mock data for now (replace with real scraping above)
        if not products:
            products = [
                {'name': 'Mascot Jacket 1', 'image_url': 'https://www.mascotworkwear.com/img1.jpg', 
                 'manufacturer_url': 'https://www.mascotworkwear.com/en/jackets/product1', 'source': 'mascot'},
                {'name': 'Mascot Jacket 2', 'image_url': 'https://www.mascotworkwear.com/img2.jpg', 
                 'manufacturer_url': 'https://www.mascotworkwear.com/en/jackets/product2', 'source': 'mascot'}
            ]
        return products
    except requests.RequestException as e:
        print(f"Error fetching Mascot products: {e}")
        return []

def fetch_petzl_products():
    """Fetch product data from Petzl (mocked for now)."""
    try:
        response = requests.get(PETZL_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Placeholder: Replace with actual scraping logic
        products = []
        # Assuming products are in a div with class 'product'
        for item in soup.select('.product'):  # Hypothetical selector
            name = item.select_one('.title').text.strip() if item.select_one('.title') else 'Unknown'
            image = item.select_one('img')['src'] if item.select_one('img') else ''
            url = item.select_one('a')['href'] if item.select_one('a') else PETZL_URL
            products.append({
                'name': name,
                'image_url': image,
                'manufacturer_url': url,
                'source': 'petzl'
            })
        
        # Mock data for now (replace with real scraping above)
        if not products:
            products = [
                {'name': 'Petzl Helmet 1', 'image_url': 'https://www.petzl.com/img1.jpg', 
                 'manufacturer_url': 'https://www.petzl.com/US/en/product1', 'source': 'petzl'},
                {'name': 'Petzl Harness 2', 'image_url': 'https://www.petzl.com/img2.jpg', 
                 'manufacturer_url': 'https://www.petzl.com/US/en/product2', 'source': 'petzl'}
            ]
        return products
    except requests.RequestException as e:
        print(f"Error fetching Petzl products: {e}")
        return []

def populate_products():
    """Populate the Product table with data from Mascot and Petzl."""
    mascot_products = fetch_mascot_products()
    petzl_products = fetch_petzl_products()
    all_products = mascot_products + petzl_products

    for product_data in all_products:
        # Check if product already exists to avoid duplicates
        existing_product = Product.query.filter_by(name=product_data['name'], 
                                                 source=product_data['source']).first()
        if not existing_product:
            product = Product(
                name=product_data['name'],
                image_url=product_data['image_url'],
                manufacturer_url=product_data['manufacturer_url'],
                source=product_data['source'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(product)
        elif existing_product.manufacturer_url != product_data['manufacturer_url']:
            # Update URL if it changes
            existing_product.manufacturer_url = product_data['manufacturer_url']
            existing_product.updated_at = datetime.utcnow()

    db.session.commit()
    print(f"Populated {len(all_products)} products into the database.")

def update_products():
    """Update existing products or add new ones (future-proofing)."""
    # Similar to populate_products but could include deletion of outdated products
    populate_products()  # For now, just re-run population

# Future-proofing: Manual product addition (if scraping isn’t viable)
def add_product(name, image_url, manufacturer_url, source, description=None, category_id=None):
    """Manually add a product to the database."""
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

# Future-proofing: Clear products (e.g., for testing or reset)
def clear_products():
    """Remove all products from the database."""
    Product.query.delete()
    db.session.commit()
    print("All products cleared from the database.")