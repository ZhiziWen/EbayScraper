# LEGO Price Comparison Tool

A Python-based tool for comparing personal LEGO inventory prices with current eBay market values. The tool consists of two main components: a scraper for fetching eBay data and a price comparison tool for analysis.

## Features

- Fetches current LEGO set prices from eBay.de
- Compares your inventory prices with market prices
- Calculates average and median prices
- Filters for new items from Germany
- Provides price difference percentages and potential profits
- Includes shipping cost analysis
- Supports both bulk analysis and specific set analysis

## Project Structure

```
project_root/
├── src/
│   ├── scraper.py
│   └── price_comparison.py
├── data/
│   └── (Generated CSV files)
└── Inventory/
    └── Reselling Profit Calculator2.xlsx
```

## Setup

1. Ensure you have Python 3.9 installed
2. Install required packages:
   ```bash
   pip install selenium webdriver-manager beautifulsoup4 pandas python-dateutil openpyxl
   ```
3. Place your inventory Excel file in the `Inventory` folder
   - File name should be: `Reselling Profit Calculator2.xlsx`
   - Sheet name should be: `Overview Total`

## Usage

### Price Comparison Tool (`price_comparison.py`)

The tool can be used in two modes:

1. Analyze All Sets:
   ```bash
   python src/price_comparison.py
   ```
   - This will analyze all LEGO sets in your inventory
   - Results will be saved as `price_comparison_results_ALL_[timestamp].csv`

2. Analyze Specific Sets:
   ```bash
   python src/price_comparison.py 21044 21034 21028
   ```
   - This will analyze only the specified set numbers
   - Results will be saved as `price_comparison_results_SETS_21044_21034_21028_[timestamp].csv`

The output CSV file includes:
- LEGO Set Number
- Set Name
- Series (e.g., Architecture, Harry Potter)
- Your Average Buy Price
- Market Average Price
- Market Median Price
- Price Difference Percentages
- Potential Profits
- Shipping Costs

### Scraper (`scraper.py`)

The scraper is used internally by the price comparison tool but can also be used standalone:

```python
from scraper import EbayScraper

scraper = EbayScraper()
data = scraper.fetch_ebay_sold_items("21044")
```

Features:
- Fetches sold items from eBay.de
- Filters for items sold in the last 30 days
- Extracts:
  - Item titles
  - Sold dates
  - Prices
  - Shipping costs
  - Item conditions
  - Seller types
  - Locations

## Data Requirements

The inventory Excel file should have the following structure:
1. Sheet name: `Overview Total`
2. Required columns:
   - `Set`: LEGO set numbers and series names
   - `Set Name`: Names of the LEGO sets
   - `Average price`: Your purchase prices

## Output Format

The tool generates a CSV file with the following columns:
1. LEGO Set Number
2. Set Name
3. Series
4. My Avg Buy Price
5. Market Avg Price
6. Market Median Price
7. Avg Price Diff %
8. Median Price Diff %
9. Potential Profit (Avg)
10. Potential Profit (Median)
11. Avg Shipping
12. Median Shipping

All numeric values are rounded to 2 decimal places.

## Notes

- The scraper focuses on items from Germany and in "Brandneu" (New) condition
- Prices are in EUR
- The tool automatically creates required directories
- Results are saved in the `data` directory with timestamps
- Series names are automatically extracted from the inventory file