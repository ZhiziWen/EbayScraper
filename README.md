# eBay LEGO Price Scraper

A Python scraper that fetches sold LEGO set prices from eBay Germany (ebay.de) using Selenium and BeautifulSoup.

## Features

- Searches for specific LEGO set numbers
- Filters for items sold in Germany only
- Returns prices in EUR only
- Validates set numbers in titles to avoid wrong matches
- Includes item price, shipping cost, and total price
- Includes actual sold dates
- Saves results to CSV file
- Only fetches items sold in the last 30 days

## Requirements

- Python 3.9+
- Chrome browser installed
- Conda (recommended for environment management)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/ebay-lego-scraper.git
cd ebay-lego-scraper
```

2. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate ebay-scraper
```

3. Run the setup script:
```bash
python setup.py
```

## Usage

1. Run the scraper:
```bash
python src/scraper.py
```

2. Enter LEGO set numbers when prompted (comma-separated):
```
Enter the LEGO set numbers separated by commas (e.g., 40632, 75257):
```

3. The scraper will:
   - Search for each set number
   - Filter results based on title validation
   - Extract prices and shipping costs
   - Save results to a CSV file in the `data` directory

## Output

Results are saved in the `data` directory with filename format: `ebay_sales_YYYYMMDD_HHMMSS.csv`

The CSV file contains:
- Title
- Item Price
- Shipping Fee
- Total Price
- Currency
- URL
- Set Number
- End Time (sold date)
- Location

## Notes

- The scraper is specifically designed for eBay Germany (ebay.de)
- Title validation ensures only one number with the same digit length as the target set number is allowed
- Prices are in EUR
- Shipping costs are included when available