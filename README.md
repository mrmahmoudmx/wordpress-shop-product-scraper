# WordPress Shop Product Scraper

A Python script that scrapes product information from any WordPress shop page and exports it to a CSV file. The scraper captures the following product details:

- Product Name
- Price
- Categories
- Description
- Image URL
- Product URL

## Requirements

- Python 3.8+
- Required packages (installed via requirements.txt):
  - requests
  - beautifulsoup4
  - lxml

## Installation

1. Clone this repository or download the files
2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
- On Windows:
```bash
venv\Scripts\activate
```
- On macOS/Linux:
```bash
source venv/bin/activate
```

4. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

Run the script using the following command:

```bash
python scraper.py --url "https://example.com/shop" --output "products.csv"
```

### Arguments:

- `--url`: (Required) The URL of the WordPress shop page to scrape
- `--output`: (Optional) The name of the output CSV file (default: products.csv)

## Output Format

The script creates a CSV file with the following columns:

- `name`: Product name
- `price`: Product price
- `categories`: Product categories (comma-separated)
- `description`: Product description
- `image_url`: URL of the product image
- `product_url`: URL of the product page

## Error Handling

- The script includes retry mechanisms for failed requests
- All errors and warnings are logged with timestamps
- If no products are found, a warning message is displayed

## Notes

- The script respects website robots.txt and includes appropriate delays between requests
- User-Agent headers are included to identify the scraper
- The script is designed to work with most WordPress themes, but some selectors might need adjustment based on the specific theme used

## Example

```bash
python scraper.py --url "https://example.com/shop" --output "my_products.csv"
```

This will:
1. Visit the shop page at example.com/shop
2. Extract all product information
3. Save the data to my_products.csv

## Limitations

- The script assumes a standard WordPress/WooCommerce setup
- Some custom WordPress themes might require selector adjustments
- Rate limiting might be necessary for large shops

## Troubleshooting

If you encounter issues:

1. Check if the shop page is accessible
2. Verify that the page uses standard WordPress/WooCommerce structure
3. Check the logs for specific error messages
4. Ensure you have proper internet connectivity

## License

This project is open-source and available under the MIT License.
