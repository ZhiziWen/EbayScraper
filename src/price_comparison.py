"""
LEGO Price Analysis Tool

This script analyzes market data for LEGO sets, comparing inventory prices with eBay sold prices.
It can work with partial market data, analyzing only the sets for which data is available.
"""

import os
import json
import pandas as pd
from datetime import datetime

class PriceAnalyzer:
    def __init__(self):
        """Initialize the Price Analyzer."""
        self.base_dir = os.getcwd()
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        self.inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')
        
        print("Price Analyzer initialized")

    def read_inventory(self):
        """Read inventory from Excel file."""
        try:
            if not os.path.exists(self.inventory_file):
                print(f"Inventory file not found: {self.inventory_file}")
                return None
            
            print(f"\nReading inventory from {self.inventory_file}")
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            
            # Clean data
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Extract valid rows with set numbers and prices
            valid_data = df[
                df['Set'].apply(lambda x: str(x).replace('.0', '').isdigit()) &
                df['Average price'].notna()
            ].copy()
            
            if valid_data.empty:
                print("No valid set data found in inventory")
                return None
            
            # Clean up set numbers and create inventory DataFrame
            valid_data['Set'] = valid_data['Set'].astype(str).str.replace('.0', '')
            
            print(f"Found {len(valid_data)} sets in inventory")
            return valid_data
            
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def find_latest_market_data(self, set_number):
        """Find the latest market data file for a given set number."""
        try:
            csv_files = [f for f in os.listdir(self.data_dir) 
                        if f.startswith(f'Ebay_Lego_{set_number}_') and f.endswith('.csv')]
            if not csv_files:
                return None
            
            latest_file = max(csv_files)
            return os.path.join(self.data_dir, latest_file)
            
        except Exception as e:
            print(f"Error finding market data for set {set_number}: {e}")
            return None

    def calculate_statistics(self, market_data):
        """Calculate market statistics for a set."""
        try:
            stats = {
                'items_found': len(market_data),
                'market_avg_price': round(market_data['Total Price'].mean(), 2),
                'market_median_price': round(market_data['Total Price'].median(), 2),
                'avg_shipping': round(market_data['Shipping Fee'].mean(), 2),
                'median_shipping': round(market_data['Shipping Fee'].median(), 2)
            }
            
            # Calculate averages by seller type
            seller_averages = market_data.groupby('Seller Type')['Total Price'].mean().round(2)
            stats.update({
                'avg_price_private': seller_averages.get('Privat', 0),
                'avg_price_commercial': seller_averages.get('Gewerblich', 0)
            })
            
            return stats
            
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return None

    def generate_comparison_report(self):
        """Generate a comprehensive price comparison report."""
        try:
            # Read inventory
            inventory_data = self.read_inventory()
            if inventory_data is None:
                return None
            
            results = []
            sets_with_data = 0
            sets_without_data = 0
            
            # Process each set in inventory
            for _, row in inventory_data.iterrows():
                set_number = row['Set']
                set_name = row.get('Set Name', 'Unknown')
                my_price = float(row['Average price'])
                
                # Find market data for this set
                market_data_file = self.find_latest_market_data(set_number)
                if market_data_file is None:
                    print(f"No market data found for set {set_number}")
                    sets_without_data += 1
                    continue
                
                # Read and process market data
                market_data = pd.read_csv(market_data_file)
                if market_data.empty:
                    print(f"Empty market data for set {set_number}")
                    sets_without_data += 1
                    continue
                
                # Calculate statistics
                stats = self.calculate_statistics(market_data)
                if stats is None:
                    sets_without_data += 1
                    continue
                
                # Calculate price differences
                price_diff = round(stats['market_avg_price'] - my_price, 2)
                price_diff_pct = round((price_diff / my_price) * 100, 2)
                
                # Add to results
                result = {
                    'LEGO Set Number': set_number,
                    'Set Name': set_name,
                    'My Avg Buy Price': my_price,
                    'Market Avg Price': stats['market_avg_price'],
                    'Market Median Price': stats['market_median_price'],
                    'Avg Price Diff': price_diff,
                    'Avg Price Diff %': price_diff_pct,
                    'Avg Price (Private)': stats['avg_price_private'],
                    'Avg Price (Commercial)': stats['avg_price_commercial'],
                    'Avg Shipping': stats['avg_shipping'],
                    'Median Shipping': stats['median_shipping'],
                    'Items Found': stats['items_found']
                }
                
                results.append(result)
                sets_with_data += 1
                print(f"Processed set {set_number}: Found {stats['items_found']} items")
            
            if not results:
                print("No market data found for any sets")
                return None
            
            # Create results DataFrame
            results_df = pd.DataFrame(results)
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'Price_Analysis_Results_{timestamp}.csv'
            filepath = os.path.join(self.data_dir, filename)
            results_df.to_csv(filepath, index=False)
            
            print(f"\nAnalysis complete!")
            print(f"Sets analyzed: {sets_with_data}")
            print(f"Sets without data: {sets_without_data}")
            print(f"Results saved to: {filename}")
            
            return results_df
            
        except Exception as e:
            print(f"Error generating comparison report: {e}")
            return None

def main():
    """Main function to run the price analysis."""
    print("\nStarting LEGO Price Analysis...")
    analyzer = PriceAnalyzer()
    analyzer.generate_comparison_report()

if __name__ == "__main__":
    main()
