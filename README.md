# LEGO Price Analysis Tool

A Python-based tool for analyzing LEGO set prices by comparing your inventory prices with current market data from eBay Germany.

## Features

- Reads inventory data from Excel file (`Reselling Profit Calculator2.xlsx`)
- Fetches sold LEGO set prices from eBay Germany (ebay.de)
- Filters for items sold in the last 30 days
- Validates LEGO set numbers in titles to avoid wrong matches
- Extracts comprehensive price data including:
  - Item price
  - Shipping cost
  - Total price
  - Actual sold dates
  - Item condition
  - Seller type (Private or Commercial)
- Generates detailed price analysis including:
  - Market average and median prices
  - Price difference percentages
  - Potential profits
  - Average and median shipping costs
  - Number of items sold

## Project Structure

```
.
├── src/
│   ├── scraper.py          # eBay data scraping functionality
│   ├── get_market_data.py  # Market data collection script
│   └── price_comparison.py # Price analysis and reporting
├── Inventory/              # Contains inventory Excel file
└── data/                   # Stores scraped data and analysis results
```

## Requirements

- Python 3.9
- Required packages (specified in environment.yml):
  - selenium
  - beautifulsoup4
  - pandas
  - python-dateutil
  - flask
  - webdriver-manager

## Setup

1. Create conda environment:
```bash
conda env create -f environment.yml
```

2. Activate environment:
```bash
conda activate ebayfetchsold
```

## Usage

1. Place your inventory file (`Reselling Profit Calculator2.xlsx`) in the `Inventory` folder.

2. Collect market data:
   - For all sets in your inventory:
     ```bash
     python src/get_market_data.py
     ```
   - For specific set numbers:
     ```bash
     python src/get_market_data.py 21044 76895 21054
     ```

3. Generate price analysis:
```bash
python src/price_comparison.py
```
Note: The price analysis will compare market data with your inventory prices, so the sets must be present in your inventory file.

## Output

The tool generates a CSV file with the following columns:
- LEGO Set Number
- Set Name
- Series
- Number Sold
- My Avg Buy Price
- Market Avg Price
- Market Median Price
- Avg Price Diff %
- Median Price Diff %
- Potential Profit (Avg)
- Potential Profit (Median)
- Avg Shipping
- Median Shipping

Results are saved in the `data` folder with filename format:
`Price_Comparison_Results_STARTDATE_ENDDATE_TIMESTAMP.csv`