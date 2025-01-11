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

import pandas as pd
import os
from datetime import datetime
from scraper import EbayScraper
import json

class MarketDataCollector:
    def __init__(self):
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        self.inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')
        
        # Create directories if they don't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.inventory_dir, exist_ok=True)
        
        # Initialize scraper
        self.scraper = EbayScraper()
        print("Market Data Collector initialized")
        
        # Verify inventory file exists
        if not os.path.exists(self.inventory_file):
            print(f"Warning: Inventory file not found at {self.inventory_file}")
            print("Please ensure the Excel file is in the Inventory folder")

    def read_inventory(self):
        """Read the inventory from Excel file.
        Returns:
            DataFrame with set numbers and buying prices
        """
        try:
            print(f"\nReading inventory from {self.inventory_file}")
            
            # Read the 'Overview Total' sheet
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            
            # Clean up the data
            df = df.dropna(how='all')  # Remove completely empty rows
            df = df.dropna(how='all', axis=1)  # Remove completely empty columns
            
            # Filter rows that have valid set numbers and are not summary rows
            valid_data = df[
                df['Set'].notna() &  # Set number exists
                df['Set'].astype(str).str.match(r'^\d+$').fillna(False) &  # Set is numeric
                df['Average price'].notna()  # Price exists
            ]
            
            # Create inventory data with correct columns
            inventory_data = pd.DataFrame()
            inventory_data['Set'] = valid_data['Set'].astype(str).apply(lambda x: str(int(float(x))))
            inventory_data['Set Name'] = valid_data['Set Name']
            inventory_data['Average Price'] = valid_data['Average price']
            
            # Remove any remaining invalid data
            inventory_data = inventory_data.dropna()
            inventory_data = inventory_data[inventory_data['Average Price'] > 0]
            
            print(f"\nFound {len(inventory_data)} sets in inventory")
            return inventory_data
            
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def fetch_and_save_set_data(self, set_number):
        """Fetch and save market data for a specific set.
        Args:
            set_number (str): LEGO set number
        Returns:
            str: Path to saved CSV file
        """
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
        """Create a manifest file listing all generated CSVs.
        Args:
            data_files (dict): Dictionary mapping set numbers to CSV file paths
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        manifest_file = os.path.join(self.data_dir, f'market_data_manifest_{timestamp}.json')
        
        with open(manifest_file, 'w') as f:
            json.dump(data_files, f, indent=4)
        
        print(f"\nManifest file created: {manifest_file}")
        return manifest_file

def main():
    """Main function to collect market data for all sets."""
    print("\nStarting LEGO Market Data Collection...")
    collector = MarketDataCollector()
    
    # Read inventory
    inventory_data = collector.read_inventory()
    if inventory_data is None or inventory_data.empty:
        print("No inventory data found")
        return
    
    # Process each set
    data_files = {}
    for _, row in inventory_data.iterrows():
        set_number = row['Set']
        csv_path = collector.fetch_and_save_set_data(set_number)
        if csv_path:
            data_files[set_number] = {
                'csv_path': csv_path,
                'set_name': row['Set Name'],
                'my_price': float(row['Average Price'])
            }
    
    # Create manifest file
    if data_files:
        manifest_file = collector.create_manifest(data_files)
        print(f"\nData collection complete. Manifest saved to: {manifest_file}")
        print(f"Total sets processed: {len(data_files)}")
    else:
        print("\nNo data collected for any sets")

if __name__ == "__main__":
    main() 