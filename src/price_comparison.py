"""
LEGO Price Analysis Tool

This script handles the analysis of collected market data.
Features:
- Reads market data from individual CSV files
- Calculates statistics and metrics
- Generates comprehensive comparison report
- Saves results to CSV with timestamp
- Can work with or without manifest file
"""

import pandas as pd
import os
from datetime import datetime
import json
import re

class PriceAnalyzer:
    def __init__(self):
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        
        print("Price Analyzer initialized")

    def read_inventory(self):
        """Read the inventory from Excel file."""
        try:
            inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')
            if not os.path.exists(inventory_file):
                print(f"Inventory file not found: {inventory_file}")
                return None
            
            print(f"\nReading inventory from {inventory_file}")
            
            # Read the 'Overview Total' sheet
            df = pd.read_excel(inventory_file, sheet_name='Overview Total')
            
            # Clean up the data
            df = df.dropna(how='all')
            df = df.dropna(how='all', axis=1)
            
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
            
            print(f"Found {len(inventory_data)} sets in inventory")
            return inventory_data
            
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def read_market_data(self, csv_path):
        """Read market data from CSV file."""
        try:
            if not os.path.exists(csv_path):
                print(f"Market data file not found: {csv_path}")
                return None
            
            data = pd.read_csv(csv_path)
            return data
            
        except Exception as e:
            print(f"Error reading market data: {e}")
            return None

    def calculate_statistics(self, market_data, my_price):
        """Calculate statistics from market data."""
        if market_data is None or market_data.empty:
            return {
                'avg_price': 0.00,
                'median_price': 0.00,
                'avg_shipping': 0.00,
                'median_shipping': 0.00,
                'items_found': 0,
                'price_diff_pct': 0.00,
                'potential_profit': 0.00
            }

        # Calculate shipping statistics (excluding 0 shipping)
        shipping_data = market_data[market_data['Shipping Fee'] > 0]['Shipping Fee']
        avg_shipping = round(shipping_data.mean(), 2) if not shipping_data.empty else 0.00
        median_shipping = round(shipping_data.median(), 2) if not shipping_data.empty else 0.00

        # Calculate total price statistics
        avg_total = round(market_data['Total Price'].mean(), 2)
        median_total = round(market_data['Total Price'].median(), 2)
        
        # Calculate average and median prices (excluding shipping)
        avg_price = round(avg_total - avg_shipping, 2)
        median_price = round(median_total - median_shipping, 2)
        
        # Calculate price difference percentage
        price_diff_pct = round(((avg_price - my_price) / my_price) * 100, 2) if my_price > 0 else 0
        
        # Calculate potential profit
        potential_profit = round(avg_price - my_price, 2)

        return {
            'avg_price': avg_price,
            'median_price': median_price,
            'avg_shipping': avg_shipping,
            'median_shipping': median_shipping,
            'items_found': len(market_data),
            'price_diff_pct': price_diff_pct,
            'potential_profit': potential_profit
        }

    def read_series_names(self):
        """Read series names from inventory file."""
        try:
            inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')
            if not os.path.exists(inventory_file):
                print(f"Inventory file not found: {inventory_file}")
                return {}
            
            # Read the 'Overview Total' sheet
            df = pd.read_excel(inventory_file, sheet_name='Overview Total')
            
            # Clean up the data
            df = df.dropna(how='all')
            df = df.dropna(how='all', axis=1)
            
            # Get the 'Set' column
            set_column = df['Set'].fillna('')
            
            # Initialize variables
            current_series = None
            series_mapping = {}
            
            # Process each row
            for value in set_column:
                value = str(value).strip()
                if not value:
                    continue
                    
                if not value.replace('.', '').isdigit():
                    current_series = value
                else:
                    if current_series:
                        set_number = str(int(float(value)))
                        series_mapping[set_number] = current_series
            
            return series_mapping
            
        except Exception as e:
            print(f"Error reading series names: {e}")
            return {}

    def find_latest_data_files(self):
        """Find the latest market data files for each set in the data directory."""
        try:
            # Get all Ebay Lego CSV files
            csv_files = [f for f in os.listdir(self.data_dir) 
                        if f.startswith('Ebay_Lego_') and f.endswith('.csv')]
            if not csv_files:
                print("No market data files found in data directory")
                return None
            
            # Group files by set number and get the latest for each
            set_files = {}
            for file in csv_files:
                # Extract set number using regex (Ebay_Lego_21028_...)
                match = re.search(r'Ebay_Lego_(\d+)_', file)
                if match:
                    set_number = match.group(1)
                    if set_number not in set_files or file > set_files[set_number]:
                        set_files[set_number] = file
            
            return set_files
            
        except Exception as e:
            print(f"Error finding data files: {e}")
            return None

    def generate_comparison_report(self, manifest_path=None):
        """Generate comparison report from market data."""
        try:
            # Get inventory data
            inventory_data = self.read_inventory()
            if inventory_data is None:
                return None
            
            # Create inventory lookup
            inventory_lookup = inventory_data.set_index('Set').to_dict('index')
            
            # Get data files (either from manifest or by finding latest files)
            if manifest_path and os.path.exists(manifest_path):
                print(f"Reading manifest file: {manifest_path}")
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                data_files = {set_num: info['csv_path'] for set_num, info in manifest.items()}
            else:
                print("No manifest file provided or found, searching for latest data files...")
                data_files = self.find_latest_data_files()
                if not data_files:
                    return None
                data_files = {set_num: os.path.join(self.data_dir, filename) 
                            for set_num, filename in data_files.items()}
            
            # Get series mapping
            series_mapping = self.read_series_names()
            
            # Process each set's data
            results = []
            for set_number, csv_path in data_files.items():
                try:
                    # Get inventory info
                    inv_info = inventory_lookup.get(set_number)
                    if not inv_info:
                        print(f"No inventory data found for set {set_number}")
                        continue
                    
                    # Read market data
                    market_data = self.read_market_data(csv_path)
                    if market_data is None:
                        continue
                    
                    # Calculate statistics
                    stats = self.calculate_statistics(market_data, inv_info['Average Price'])
                    
                    # Create result entry
                    result = {
                        'LEGO Set Number': set_number,
                        'Set Name': inv_info['Set Name'],
                        'Series': series_mapping.get(set_number, 'Unknown'),
                        'Number Sold': stats['items_found'],
                        'My Avg Buy Price': round(inv_info['Average Price'], 2),
                        'Market Avg Price': stats['avg_price'],
                        'Market Median Price': stats['median_price'],
                        'Avg Price Diff %': stats['price_diff_pct'],
                        'Potential Profit': stats['potential_profit'],
                        'Avg Shipping': stats['avg_shipping'],
                        'Median Shipping': stats['median_shipping']
                    }
                    
                    results.append(result)
                    print(f"Processed set {set_number}")
                    
                except Exception as e:
                    print(f"Error processing set {set_number}: {e}")
                    continue
            
            if not results:
                print("No results generated")
                return None
            
            # Create results DataFrame
            results_df = pd.DataFrame(results)
            
            # Generate timestamp and date range for filename
            current_time = datetime.now()
            timestamp = current_time.strftime('%H%M%S')
            start_date = (current_time.replace(day=1) - pd.DateOffset(days=30)).strftime('%Y%m%d')
            end_date = current_time.strftime('%Y%m%d')
            
            # Create filename with date range
            filename = f'Price_Comparison_Results_{start_date}_{end_date}_{timestamp}.csv'
            
            # Save results
            output_path = os.path.join(self.data_dir, filename)
            results_df.to_csv(output_path, index=False, float_format='%.2f')
            print(f"\nResults saved to {filename}")
            
            return results_df
            
        except Exception as e:
            print(f"Error generating comparison report: {e}")
            return None

def main():
    """Main function to analyze market data and generate report."""
    print("\nStarting LEGO Price Analysis...")
    analyzer = PriceAnalyzer()
    
    # Try to find latest manifest file
    manifest_files = [f for f in os.listdir(analyzer.data_dir) if f.startswith('market_data_manifest_')]
    manifest_path = None
    if manifest_files:
        latest_manifest = max(manifest_files)
        manifest_path = os.path.join(analyzer.data_dir, latest_manifest)
        print(f"Found manifest file: {latest_manifest}")
    else:
        print("No manifest file found, will search for latest data files")
    
    # Generate comparison report
    results = analyzer.generate_comparison_report(manifest_path)
    
    if results is not None:
        print("\nAnalysis Results:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(results)
        print(f"\nTotal sets analyzed: {len(results)}")

if __name__ == "__main__":
    main()
