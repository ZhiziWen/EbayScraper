"""
LEGO Price Comparison Tool

This script compares personal LEGO inventory prices with current eBay market values.
Features:
- Reads personal inventory from Excel file
- Fetches current market prices using scraper.py
- Calculates average and median prices
- Filters for new items from Germany
- Compares prices and calculates difference percentages
- Saves results to CSV file with timestamp
- Supports two modes: analyze all sets or specific set numbers
"""

import pandas as pd
import os
from datetime import datetime
from scraper import EbayScraper
import sys

class PriceComparisonTool:
    def __init__(self):
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_file = os.path.join(self.data_dir, 'Reselling Profit Calculator2.xlsx')
        
        # Initialize scraper
        self.scraper = EbayScraper()
        print("Price Comparison Tool initialized")

    def read_inventory(self, set_numbers=None):
        """Read the inventory from Excel file.
        Args:
            set_numbers (list): Optional list of set numbers to filter for
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
            inventory_data['Set Name'] = valid_data['Set Name']  # Add Set Name column
            inventory_data['Average Price'] = valid_data['Average price']
            
            # Remove any remaining invalid data
            inventory_data = inventory_data.dropna()
            inventory_data = inventory_data[inventory_data['Average Price'] > 0]
            
            # Filter for specific set numbers if provided
            if set_numbers:
                set_numbers = [str(num) for num in set_numbers]
                inventory_data = inventory_data[inventory_data['Set'].isin(set_numbers)]
                if inventory_data.empty:
                    print(f"No matching sets found in inventory for: {set_numbers}")
                    return None
            
            print(f"\nFound {len(inventory_data)} sets in inventory")
            return inventory_data
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def calculate_market_stats(self, ebay_data):
        """Calculate market statistics including averages and medians."""
        if ebay_data is None or ebay_data.empty:
            return {
                'avg_price': 0,
                'median_price': 0,
                'avg_shipping': 0,
                'median_shipping': 0,
                'items_found': 0
            }

        # Filter for Deutschland location and Brandneu condition
        filtered_data = ebay_data[
            (ebay_data['Location'].str.contains('Deutschland', case=False, na=False)) &
            (ebay_data['Condition'] == 'Brandneu')
        ]
        
        if filtered_data.empty:
            return {
                'avg_price': 0,
                'median_price': 0,
                'avg_shipping': 0,
                'median_shipping': 0,
                'items_found': 0
            }

        # Calculate shipping statistics (excluding 0 shipping)
        shipping_data = filtered_data[filtered_data['Shipping Fee'] > 0]['Shipping Fee']
        avg_shipping = shipping_data.mean() if not shipping_data.empty else 0
        median_shipping = shipping_data.median() if not shipping_data.empty else 0

        # Calculate total price statistics
        avg_total = filtered_data['Total Price'].mean()
        median_total = filtered_data['Total Price'].median()

        return {
            'avg_price': avg_total - avg_shipping,
            'median_price': median_total - median_shipping,
            'avg_shipping': avg_shipping,
            'median_shipping': median_shipping,
            'items_found': len(filtered_data)
        }

    def calculate_price_diff(self, market_price, my_price):
        """Calculate price difference percentage."""
        if my_price == 0 or market_price == 0:
            return 0
        return ((market_price - my_price) / my_price) * 100

    def compare_prices(self, set_numbers=None):
        """Compare prices between inventory and current market data.
        Args:
            set_numbers (list): Optional list of set numbers to analyze
        """
        inventory_data = self.read_inventory(set_numbers)
        if inventory_data is None or inventory_data.empty:
            print("No inventory data found")
            return None

        # Get series mapping
        series_mapping = self.read_series_names()
        if series_mapping is None:
            print("Warning: Could not read series names")
            series_mapping = {}

        results = []
        for _, row in inventory_data.iterrows():
            try:
                set_number = row['Set']
                set_name = row['Set Name']
                series_name = series_mapping.get(set_number, 'Unknown')  # Get series name from mapping
                my_price = float(row['Average Price'])
                print(f"\nProcessing set {set_number} ({set_name}) - Series: {series_name}")
                
                # Get current market data
                ebay_data = self.scraper.fetch_ebay_sold_items(set_number)
                if ebay_data is None or ebay_data.empty:
                    print(f"No market data found for set {set_number}")
                    continue
                
                # Calculate market statistics
                stats = self.calculate_market_stats(ebay_data)
                
                # Calculate price differences and potential profits
                avg_diff = self.calculate_price_diff(stats['avg_price'], my_price)
                median_diff = self.calculate_price_diff(stats['median_price'], my_price)
                
                result = {
                    'LEGO Set Number': set_number,
                    'Set Name': set_name,
                    'Series': series_name,  # Add series name to results
                    'My Avg Buy Price': my_price,
                    'Market Avg Price': stats['avg_price'],
                    'Market Median Price': stats['median_price'],
                    'Avg Price Diff %': avg_diff,
                    'Median Price Diff %': median_diff,
                    'Potential Profit (Avg)': stats['avg_price'] - my_price,
                    'Potential Profit (Median)': stats['median_price'] - my_price,
                    'Avg Shipping': stats['avg_shipping'],
                    'Median Shipping': stats['median_shipping']
                }
                
                results.append(result)
            except Exception as e:
                print(f"Error processing set {row['Set']}: {e}")
                continue
        
        if not results:
            print("No results found for any set!")
            return None
            
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'price_comparison_results_{timestamp}.csv'
        
        # Save results
        results_df.to_csv(os.path.join(self.data_dir, filename), index=False)
        print(f"\nResults saved to {filename}")
        
        return results_df

    def read_series_names(self):
        """Debug function to read and extract series names from the Excel file."""
        try:
            print(f"\nReading series names from {self.inventory_file}")
            
            # Read the 'Overview Total' sheet
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            
            # Clean up the data
            df = df.dropna(how='all')  # Remove completely empty rows
            df = df.dropna(how='all', axis=1)  # Remove completely empty columns
            
            # Get the 'Set' column
            set_column = df['Set'].fillna('')
            
            # Initialize variables
            current_series = None
            series_mapping = {}
            
            # Process each row
            for value in set_column:
                value = str(value).strip()
                # Skip empty rows
                if not value:
                    continue
                    
                # If the value is not numeric, it's a series name
                if not value.replace('.', '').isdigit():
                    current_series = value
                    print(f"\nFound series: {current_series}")
                else:
                    # If we have a current series and this is a set number
                    if current_series:
                        # Clean up the set number (remove decimal points)
                        set_number = str(int(float(value)))
                        series_mapping[set_number] = current_series
                        print(f"Set {set_number} belongs to series {current_series}")
            
            print("\nComplete series mapping:")
            for set_num, series in series_mapping.items():
                print(f"Set {set_num}: {series}")
                
            return series_mapping
            
        except Exception as e:
            print(f"Error reading series names: {e}")
            return None

def main():
    """Main function to run the price comparison tool."""
    print("\nStarting LEGO Price Comparison Tool...")
    tool = PriceComparisonTool()
    
    # Debug: Read series names first
    print("\nDebug: Reading series names...")
    series_mapping = tool.read_series_names()
    if series_mapping:
        print(f"\nFound {len(series_mapping)} sets with series names")
    
    # Continue with normal operation...
    if len(sys.argv) > 1:
        set_numbers = sys.argv[1:]
        print(f"\nAnalyzing specific sets: {set_numbers}")
        results = tool.compare_prices(set_numbers)
    else:
        print("\nAnalyzing all sets in inventory")
        results = tool.compare_prices()
    
    if results is not None:
        print("\nComparison Results:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(results)
        print(f"\nTotal sets processed: {len(results)}")

if __name__ == "__main__":
    main()
