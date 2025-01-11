"""
LEGO Price Analysis Tool

This script analyzes market data for LEGO sets, comparing inventory prices with eBay sold prices.
It can work with partial market data, analyzing only the sets for which data is available.
"""

import os
import pandas as pd
import glob
from datetime import datetime
import re

class PriceAnalyzer:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        self.inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')

    def read_inventory(self):
        """Read inventory from Excel file and return DataFrame with set numbers and buying prices."""
        if not os.path.exists(self.inventory_file):
            print(f"Inventory file not found: {self.inventory_file}")
            return None

        try:
            # Read the Excel file
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            
            # Clean up the data
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            
            # Create a new DataFrame for inventory data
            inventory_data = pd.DataFrame(columns=['Set', 'Set Name', 'Series', 'Average price'])
            
            current_series = None
            for _, row in df.iterrows():
                if pd.notna(row.iloc[0]) and not str(row.iloc[0]).replace('.', '').isdigit():
                    current_series = row.iloc[0]
                elif pd.notna(row.iloc[0]) and str(row.iloc[0]).replace('.', '').isdigit():
                    set_number = str(int(float(row.iloc[0])))
                    set_name = row.iloc[1] if pd.notna(row.iloc[1]) else 'Unknown'
                    
                    # Handle the average price
                    avg_price_str = str(row['Average price']) if pd.notna(row['Average price']) else ''
                    if avg_price_str.strip() in ['', '-', '  -   € ']:
                        avg_price = 0
                    else:
                        try:
                            # Remove currency symbol and convert to float
                            avg_price_str = avg_price_str.replace('€', '').replace(',', '.').strip()
                            avg_price = float(avg_price_str)
                        except (ValueError, TypeError):
                            avg_price = 0
                    
                    inventory_data = pd.concat([inventory_data, pd.DataFrame({
                        'Set': [set_number],
                        'Set Name': [set_name],
                        'Series': [current_series],
                        'Average price': [avg_price]
                    })], ignore_index=True)
            
            print(f"Found {len(inventory_data)} sets in inventory")
            return inventory_data
        except Exception as e:
            print(f"Error reading inventory file: {e}")
            return None

    def find_latest_market_data(self, set_number):
        """Find the latest market data file for a given set number."""
        pattern = os.path.join(self.data_dir, f'Ebay_Lego_{set_number}_*.csv')
        files = glob.glob(pattern)
        if not files:
            return None
        return max(files, key=os.path.getctime)

    def calculate_statistics(self, market_data):
        """Calculate market statistics from the data."""
        if market_data.empty:
            return None

        stats = {
            'items_found': len(market_data),
            'market_avg_price': round(market_data['Total Price'].mean(), 2),
            'market_median_price': round(market_data['Total Price'].median(), 2),
            'avg_shipping': round(market_data['Shipping Fee'].mean(), 2),
            'median_shipping': round(market_data['Shipping Fee'].median(), 2)
        }
        return stats

    def generate_comparison_report(self):
        """Generate a comparison report for all sets with available market data."""
        inventory_data = self.read_inventory()
        if inventory_data is None or inventory_data.empty:
            print("No inventory data available")
            return

        results = []
        sets_without_data = []

        for _, row in inventory_data.iterrows():
            set_number = row['Set']
            market_data_file = self.find_latest_market_data(set_number)
            
            if market_data_file is None:
                sets_without_data.append(set_number)
                continue

            try:
                market_data = pd.read_csv(market_data_file)
                stats = self.calculate_statistics(market_data)
                
                if stats is None:
                    sets_without_data.append(set_number)
                    continue

                my_price = float(row['Average price'])
                # Calculate both average and median price differences
                avg_price_diff_percent = round(((stats['market_avg_price'] - my_price) / my_price) * 100, 2) if my_price > 0 else 0
                median_price_diff_percent = round(((stats['market_median_price'] - my_price) / my_price) * 100, 2) if my_price > 0 else 0
                
                # Calculate both average and median potential profits
                potential_profit_avg = round(stats['market_avg_price'] - my_price, 2)
                potential_profit_median = round(stats['market_median_price'] - my_price, 2)

                result = {
                    'LEGO Set Number': set_number,
                    'Set Name': row['Set Name'],
                    'Series': row['Series'],
                    'Number Sold': stats['items_found'],
                    'My Avg Buy Price': round(my_price, 2),
                    'Market Avg Price': stats['market_avg_price'],
                    'Market Median Price': stats['market_median_price'],
                    'Avg Price Diff %': avg_price_diff_percent,
                    'Median Price Diff %': median_price_diff_percent,
                    'Potential Profit (Avg)': potential_profit_avg,
                    'Potential Profit (Median)': potential_profit_median,
                    'Avg Shipping': stats['avg_shipping'],
                    'Median Shipping': stats['median_shipping']
                }
                results.append(result)
                print(f"Processed set {set_number}: Found {stats['items_found']} items")

            except Exception as e:
                print(f"Error processing set {set_number}: {e}")
                sets_without_data.append(set_number)

        if not results:
            print("No market data available for any sets")
            return

        # Create DataFrame and save to CSV
        results_df = pd.DataFrame(results)
        # Ensure correct column order
        column_order = [
            'LEGO Set Number',
            'Set Name',
            'Series',
            'Number Sold',
            'My Avg Buy Price',
            'Market Avg Price',
            'Market Median Price',
            'Avg Price Diff %',
            'Median Price Diff %',
            'Potential Profit (Avg)',
            'Potential Profit (Median)',
            'Avg Shipping',
            'Median Shipping'
        ]
        results_df = results_df[column_order]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        start_date = (datetime.now() - pd.Timedelta(days=30)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        filename = f'Price_Comparison_Results_{start_date}_{end_date}_{timestamp}.csv'
        filepath = os.path.join(self.data_dir, filename)
        
        results_df.to_csv(filepath, index=False)
        print(f"\nResults saved to: {filepath}")
        print(f"Analyzed {len(results)} sets")
        if sets_without_data:
            print(f"No data found for {len(sets_without_data)} sets: {', '.join(sets_without_data)}")

if __name__ == '__main__':
    analyzer = PriceAnalyzer()
    analyzer.generate_comparison_report()
