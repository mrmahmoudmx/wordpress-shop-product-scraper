import requests
from bs4 import BeautifulSoup
import csv
import logging
import argparse
from urllib.parse import urljoin
import time
import re

def setup_logging():
    """Configure logging settings"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def fetch_page(url, retry_count=3):
    """
    Fetch the HTML content of a page with retry mechanism
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if attempt == retry_count - 1:
                logging.error(f"Failed to fetch {url} after {retry_count} attempts: {e}")
                raise
            logging.warning(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(2 ** attempt)  # Exponential backoff

def get_product_details(product_url):
    """
    Fetch detailed product information from the product page
    """
    try:
        html = fetch_page(product_url)
        soup = BeautifulSoup(html, 'lxml')
        
        # Get product description
        description = ""
        desc_div = soup.find('div', class_='rh-post-wrapper') or \
                  soup.find('div', class_='woocommerce-product-details__short-description') or \
                  soup.find('div', class_='post-inner')
        
        if desc_div:
            # Remove any script tags
            for script in desc_div.find_all('script'):
                script.decompose()
            description = ' '.join(desc_div.stripped_strings)
        
        # Get product categories
        categories = []
        
        # Try to find categories in various locations
        category_containers = [
            soup.find('div', class_='rh-breadcrumbs'),  # Breadcrumbs
            soup.find('div', class_='woocommerce-breadcrumb'),  # WooCommerce breadcrumb
            soup.find('nav', class_='woocommerce-breadcrumb'),  # Alternative breadcrumb
            soup.find('div', class_='product-categories'),  # Product categories
            soup.find('div', class_='posted_in')  # Posted in categories
        ]
        
        for container in category_containers:
            if container:
                # Try different selectors for category links
                category_links = container.select('a[href*="product-category"], a[href*="category"], span[property="name"]')
                if category_links:
                    for link in category_links:
                        category_text = link.get_text(strip=True)
                        # Skip common non-category texts
                        if category_text.lower() not in ['home', 'shop', 'products']:
                            categories.append(category_text)
                    if categories:  # If we found categories, break the loop
                        break
        
        return {
            'description': description[:500] if description else 'N/A',  # Limit description length
            'categories': ', '.join(categories) if categories else 'N/A'
        }
    except Exception as e:
        logging.error(f"Error fetching product details from {product_url}: {e}")
        return {'description': 'N/A', 'categories': 'N/A'}

def parse_products(html, base_url):
    """
    Parse product information from the shop page HTML
    """
    products = []
    soup = BeautifulSoup(html, 'lxml')
    
    # Find all product elements (adjust selectors based on WordPress theme)
    product_elements = soup.select('li.product, div.product')
    
    if not product_elements:
        logging.warning("No products found on the page!")
        return products
    
    for product in product_elements:
        try:
            # Basic product info
            name = 'N/A'
            price = 'N/A'
            image_url = 'N/A'
            product_url = 'N/A'
            
            # Get product name and URL
            product_link = None
            
            # Try to find the product link in various locations
            for link in product.find_all('a'):
                href = link.get('href', '')
                if href and 'add-to-cart' not in href and '?add-to-cart=' not in href:
                    product_link = link
                    product_url = urljoin(base_url, href)
                    break
            
            if product_link:
                # Try to get name from link text or img alt
                name = product_link.get_text(strip=True)
                if not name or name == 'Add to cart':
                    img = product_link.find('img')
                    if img:
                        name = img.get('alt', '').strip()
            
            # Clean up the name
            if not name or name == 'Add to cart':
                name = 'N/A'
            # Get price - specifically looking for the current price
            price_element = product.find('span', class_='rh_regular_price') or \
                          product.find('span', class_='price') or \
                          product.find('span', class_='amount')
            if price_element:
                # Clean up the price text to only show the current price
                price_text = price_element.get_text(strip=True)
                if 'Current price is:' in price_text:
                    price = price_text.split('Current price is:')[1].strip()
                else:
                    price = price_text
            
            # Get image URL
            img_element = product.find('img')
            if img_element:
                image_url = img_element.get('src') or img_element.get('data-src', 'N/A')
                image_url = urljoin(base_url, image_url)
            
            # Get additional details from product page
            if product_url != 'N/A':
                details = get_product_details(product_url)
            else:
                details = {'description': 'N/A', 'categories': 'N/A'}
            
            products.append({
                'name': name,
                'price': price,
                'image_url': image_url,
                'categories': details['categories'],
                'description': details['description'],
                'product_url': product_url
            })
            
        except Exception as e:
            logging.error(f"Error parsing product: {e}")
            continue
    
    return products

def clean_price(price_text):
    """Clean up price text by removing extra information and formatting"""
    if not price_text or price_text == 'N/A':
        return 'N/A'
    
    # Extract the current price if it exists
    if 'Current price is:' in price_text:
        price = price_text.split('Current price is:')[1].strip()
    else:
        price = price_text.strip()
    
    # Remove any "Original price was" text
    if 'Original price was:' in price:
        price = price.split('Original price was:')[0].strip()
    
    # Clean up any remaining periods or extra whitespace
    price = price.rstrip('.')
    return price

def save_to_csv(products, output_file):
    """
    Save product information to CSV file using pandas for proper formatting
    """
    try:
        import pandas as pd
        
        # Convert products list to DataFrame
        df = pd.DataFrame(products)
        
        # Rename columns for better readability
        df = df.rename(columns={
            'name': 'Product Name',
            'price': 'Product Price',
            'categories': 'Product Categories',
            'description': 'Product Description',
            'image_url': 'Product Image URL',
            'product_url': 'Product Page URL'
        })
        
        # Clean up price data
        df['Product Price'] = df['Product Price'].apply(clean_price)
        
        # Save to CSV with proper encoding and formatting
        df.to_csv(output_file, index=False, encoding='utf-8')
        logging.info(f"Successfully saved {len(products)} products to {output_file}")
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Scrape products from a WordPress shop page and export to CSV"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="URL of the WordPress shop page to scrape"
    )
    parser.add_argument(
        "--output",
        default="products.csv",
        help="Output CSV filename (default: products.csv)"
    )
    
    args = parser.parse_args()
    setup_logging()
    
    try:
        logging.info(f"Starting scrape of {args.url}")
        html = fetch_page(args.url)
        products = parse_products(html, args.url)
        
        if products:
            save_to_csv(products, args.output)
            logging.info("Scraping completed successfully!")
        else:
            logging.warning("No products were found to export")
            
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
