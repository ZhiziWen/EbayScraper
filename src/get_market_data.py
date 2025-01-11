"""
LEGO Market Data Collector

This script focuses on fetching and saving raw data for each LEGO set.
Features:
- Reads inventory from Excel file
- Fetches current market data using scraper.py
- Filters for items from Deutschland and in "Brandneu" condition
- Saves individual CSV files for each set
- Creates a manifest file listing all generated CSVs
"""

import os
import sys
from datetime import datetime
import json
from scraper import EbayScraper

class MarketDataCollector:
    def __init__(self):
        """Initialize the Market Data Collector."""
        self.base_dir = os.getcwd()
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        self.inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')
        
        # Create directories if they don't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.inventory_dir, exist_ok=True)
        
        # Initialize scraper
        print("Scraper initialized")
        self.scraper = EbayScraper()
        print("Market Data Collector initialized\n")

    def read_inventory(self):
        """Read inventory from Excel file."""
        try:
            import pandas as pd
            if not os.path.exists(self.inventory_file):
                print(f"Inventory file not found: {self.inventory_file}")
                return None
            
            print(f"Reading inventory from {self.inventory_file}\n")
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            
            # Clean data and extract set numbers
            df = df.dropna(how='all').dropna(axis=1, how='all')
            valid_data = df[df['Set'].apply(lambda x: str(x).replace('.0', '').isdigit())]
            
            if valid_data.empty:
                print("No valid set numbers found in inventory")
                return None
                
            set_numbers = valid_data['Set'].astype(str).str.replace('.0', '').tolist()
            print(f"Found {len(set_numbers)} sets in inventory\n")
            return set_numbers
            
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def fetch_and_save_set_data(self, set_number):
        """Fetch and save market data for a specific set."""
        try:
            print(f"\nFetching data for set {set_number}")
            
            # Get market data
            ebay_data = self.scraper.fetch_ebay_sold_items(set_number)
            if ebay_data is None or ebay_data.empty:
                print(f"No market data found for set {set_number}")
                return None
            
            # Filter for Deutschland location and Brandneu condition
            filtered_data = ebay_data[
                (ebay_data['Location'].str.contains('Deutschland', case=False, na=False)) &
                (ebay_data['Condition'] == 'Brandneu')
            ]
            
            if filtered_data.empty:
                print(f"No valid items found for set {set_number} after filtering")
                return None
            
            # Find the CSV file created by the scraper
            csv_files = [f for f in os.listdir(self.data_dir) 
                        if f.startswith(f'Ebay_Lego_{set_number}_') and f.endswith('.csv')]
            if not csv_files:
                print(f"No CSV file found for set {set_number}")
                return None
                
            # Get the latest file
            latest_file = max(csv_files)
            filepath = os.path.join(self.data_dir, latest_file)
            print(f"Using data file: {latest_file}")
            
            return filepath
            
        except Exception as e:
            print(f"Error processing set {set_number}: {e}")
            return None

    def create_manifest(self, data_files):
        """Create a manifest file listing all generated CSVs."""
        try:
            if not data_files:
                print("No data files to include in manifest")
                return None
                
            manifest = {
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'files': data_files
            }
            
            filename = f'market_data_manifest_{manifest["timestamp"]}.json'
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            print(f"\nCreated manifest file: {filename}")
            return filepath
            
        except Exception as e:
            print(f"Error creating manifest: {e}")
            return None

def main():
    """Main function to run the market data collection."""
    print("Starting LEGO Market Data Collection...")
    collector = MarketDataCollector()
    
    # Check if specific set numbers were provided as command line arguments
    if len(sys.argv) > 1:
        set_numbers = sys.argv[1:]
        print(f"Processing specified sets: {', '.join(set_numbers)}\n")
    else:
        # If no arguments provided, read all sets from inventory
        set_numbers = collector.read_inventory()
        if not set_numbers:
            print("No sets to process. Please check your inventory file or provide set numbers as arguments.")
            return
    
    # Process each set
    data_files = []
    for set_number in set_numbers:
        csv_path = collector.fetch_and_save_set_data(set_number)
        if csv_path:
            data_files.append(csv_path)
    
    # Create manifest file
    collector.create_manifest(data_files)
    
    # Close the scraper
    collector.scraper.close()
    print("\nMarket data collection completed!")

if __name__ == "__main__":
    main() 