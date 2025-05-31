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
        desc_div = soup.find('div', class_='woocommerce-product-details__short-description')
        if desc_div:
            description = desc_div.get_text(strip=True)
        else:
            # Try alternative description location
            desc_div = soup.find('div', class_='description')
            if desc_div:
                description = desc_div.get_text(strip=True)
        
        # Get product categories
        categories = []
        category_links = soup.select('.posted_in a')
        if category_links:
            categories = [cat.get_text(strip=True) for cat in category_links]
        
        return {
            'description': description,
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
            name_element = product.find('h2', class_='woocommerce-loop-product__title') or \
                          product.find('h2', class_='product-title')
            if name_element:
                name = name_element.get_text(strip=True)
                
            # Get product URL
            url_element = product.find('a', class_='woocommerce-LoopProduct-link') or \
                         product.find('a', class_='product-link')
            if url_element:
                product_url = urljoin(base_url, url_element.get('href', ''))
            
            # Get price
            price_element = product.find('span', class_='price') or \
                          product.find('span', class_='amount')
            if price_element:
                price = price_element.get_text(strip=True)
            
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

def save_to_csv(products, output_file):
    """
    Save product information to CSV file
    """
    fieldnames = ['name', 'price', 'categories', 'description', 'image_url', 'product_url']
    
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for product in products:
                writer.writerow(product)
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
