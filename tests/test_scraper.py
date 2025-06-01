import pytest
import responses
from bs4 import BeautifulSoup
import json
from scraper import (
    fetch_page,
    parse_products,
    get_product_details,
    clean_price,
    save_to_csv
)

# Sample HTML content for testing
SAMPLE_SHOP_HTML = """
<html>
    <body>
        <div class="products">
            <li class="product">
                <a href="/product/test-product">
                    <img src="/test-image.jpg" alt="Test Product">
                </a>
                <span class="price">$99.99</span>
            </li>
        </div>
    </body>
</html>
"""

SAMPLE_PRODUCT_HTML = """
<html>
    <body>
        <div class="rh-post-wrapper">
            <p>This is a test product description.</p>
        </div>
        <div class="product-categories">
            <a href="/category/test">Test Category</a>
        </div>
    </body>
</html>
"""

@pytest.fixture
def mock_responses():
    with responses.RequestsMock() as rsps:
        yield rsps

def test_fetch_page_success(mock_responses):
    """Test successful page fetch"""
    url = "https://test.com/shop"
    mock_responses.add(
        responses.GET,
        url,
        body=SAMPLE_SHOP_HTML,
        status=200
    )
    
    result = fetch_page(url)
    assert SAMPLE_SHOP_HTML in result

def test_fetch_page_retry(mock_responses):
    """Test retry mechanism on failed requests"""
    url = "https://test.com/shop"
    # First two requests fail, third succeeds
    mock_responses.add(
        responses.GET,
        url,
        status=500
    )
    mock_responses.add(
        responses.GET,
        url,
        status=500
    )
    mock_responses.add(
        responses.GET,
        url,
        body=SAMPLE_SHOP_HTML,
        status=200
    )
    
    result = fetch_page(url)
    assert SAMPLE_SHOP_HTML in result
    assert len(mock_responses.calls) == 3

def test_parse_products():
    """Test parsing products from HTML"""
    base_url = "https://test.com"
    products = parse_products(SAMPLE_SHOP_HTML, base_url)
    
    assert len(products) == 1
    product = products[0]
    assert product['name'] == 'Test Product'
    assert product['price'] == '$99.99'
    assert product['image_url'] == 'https://test.com/test-image.jpg'

def test_get_product_details(mock_responses):
    """Test fetching product details"""
    url = "https://test.com/product/test"
    mock_responses.add(
        responses.GET,
        url,
        body=SAMPLE_PRODUCT_HTML,
        status=200
    )
    
    details = get_product_details(url)
    assert "test product description" in details['description'].lower()
    assert "Test Category" in details['categories']

def test_clean_price():
    """Test price cleaning functionality"""
    assert clean_price("Current price is: $99.99") == "$99.99"
    assert clean_price("$99.99") == "$99.99"
    assert clean_price("N/A") == "N/A"
    assert clean_price("Original price was: $129.99 Current price is: $99.99") == "$99.99"

def test_save_to_csv(tmp_path):
    """Test saving products to CSV"""
    products = [{
        'name': 'Test Product',
        'price': '$99.99',
        'image_url': 'https://test.com/image.jpg',
        'categories': 'Test Category',
        'description': 'Test Description',
        'product_url': 'https://test.com/product'
    }]
    
    output_file = tmp_path / "test_products.csv"
    save_to_csv(products, str(output_file))
    
    # Verify file exists and contains correct data
    assert output_file.exists()
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'Test Product' in content
        assert '$99.99' in content
        assert 'Test Category' in content

def test_fetch_page_failure(mock_responses):
    """Test handling of failed page fetch"""
    url = "https://test.com/shop"
    # All attempts fail
    for _ in range(3):
        mock_responses.add(
            responses.GET,
            url,
            status=500
        )
    
    with pytest.raises(Exception):
        fetch_page(url)
    assert len(mock_responses.calls) == 3  # Verify all retry attempts were made

def test_parse_products_empty():
    """Test parsing HTML with no products"""
    empty_html = "<html><body></body></html>"
    products = parse_products(empty_html, "https://test.com")
    assert len(products) == 0

def test_get_product_details_error(mock_responses):
    """Test handling of errors in product details fetch"""
    url = "https://test.com/product/error"
    mock_responses.add(
        responses.GET,
        url,
        status=404
    )
    
    details = get_product_details(url)
    assert details['description'] == 'N/A'
    assert details['categories'] == 'N/A'
