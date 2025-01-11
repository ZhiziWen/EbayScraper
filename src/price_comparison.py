"""
LEGO Price Comparison Tool

This script compares personal LEGO inventory prices with current eBay market values.
Features:
- Reads personal inventory from Excel file
- Fetches current market prices using scraper.py
- Calculates adjusted average prices by seller type
- Compares prices and calculates difference percentages
- Saves results to CSV file
"""

import pandas as pd
import os
from datetime import datetime
from scraper import EbayScraper

class PriceComparisonTool:
    def __init__(self):
        # Setup directories
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_file = os.path.join(self.data_dir, 'Reselling Profit Calculator2.xlsx')
        
        # Initialize scraper
        self.scraper = EbayScraper()
        print("Price Comparison Tool initialized")

    def read_inventory(self):
        """Read the inventory from Excel file."""
        try:
            print(f"\nReading inventory from {self.inventory_file}")
            # Read all sheets to find the correct one
            xl = pd.ExcelFile(self.inventory_file)
            print("Available sheets:", xl.sheet_names)
            
            # Read the 'Overview Total' sheet
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')
            print("Columns in inventory file:", df.columns.tolist())
            
            # Clean up the data
            df = df.dropna(how='all')  # Remove empty rows
            df = df.dropna(how='all', axis=1)  # Remove empty columns
            
            # Rename unnamed columns if needed
            df.columns = [str(col) if not str(col).startswith('Unnamed:') else f'Column_{i}' 
                         for i, col in enumerate(df.columns)]
            
            print("Cleaned columns:", df.columns.tolist())
            print(f"Found {len(df)} sets in inventory")
            
            # Display first few rows to verify data
            print("\nFirst few rows of inventory:")
            print(df.head())
            
            return df
        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def calculate_averages(self, ebay_data):
        """Calculate average prices by seller type."""
        if ebay_data is None or ebay_data.empty:
            return {
                'avg_price': 0,
                'avg_shipping': 0,
                'adjusted_price': 0
            }

        # Filter for Deutschland location
        ebay_data = ebay_data[ebay_data['Location'].str.contains('Deutschland', case=False, na=False)]
        
        # Calculate average shipping (excluding 0 shipping costs)
        shipping_data = ebay_data[ebay_data['Shipping Fee'] > 0]['Shipping Fee']
        avg_shipping = shipping_data.mean() if not shipping_data.empty else 0
        
        # Calculate average total price
        avg_total = ebay_data['Total Price'].mean() if not ebay_data.empty else 0
        
        # Calculate adjusted price
        adjusted_price = avg_total - avg_shipping if avg_total > 0 else 0

        return {
            'avg_price': adjusted_price,
            'avg_shipping': avg_shipping,
            'adjusted_price': adjusted_price
        }

    def process_set_data(self, ebay_data):
        """Process the eBay data for a single set."""
        if not ebay_data:
            print("No data found for this set")
            return None

        # Convert dictionary to DataFrame with a single row index
        ebay_data = pd.DataFrame([ebay_data])  # Wrap the dict in a list to create a single row

        # Calculate average prices by seller type
        avg_prices = ebay_data.groupby('Seller Type')['Total Price'].agg(['mean', 'count']).round(2)
        avg_prices.columns = ['Average Price', 'Count']
        
        # Calculate overall statistics
        stats = {
            'Overall Average': ebay_data['Total Price'].mean().round(2),
            'Minimum Price': ebay_data['Total Price'].min().round(2),
            'Maximum Price': ebay_data['Total Price'].max().round(2),
            'Number of Items': len(ebay_data)
        }
        
        return {
            'data': ebay_data,
            'averages': avg_prices,
            'stats': stats
        }

    def calculate_price_diff(self, market_price, my_price):
        """Calculate price difference percentage."""
        if my_price == 0 or market_price == 0:
            return 0
        return ((market_price - my_price) / my_price) * 100

    def compare_prices(self):
        """Compare prices between inventory and current market data."""
        inventory_data = self.read_inventory()
        if inventory_data is None or inventory_data.empty:
            print("No inventory data found")
            return None

        # Get the first 5 sets
        first_5_sets = inventory_data.head(5)
        results = []

        for _, row in first_5_sets.iterrows():
            try:
                # Convert set number to string and remove any decimal points and trailing zeros
                set_number = str(int(float(row['Set'])))
                print(f"\nProcessing set {set_number}")
                
                # Get current market data
                ebay_data = self.scraper.fetch_ebay_sold_items(set_number)
                if ebay_data is None or ebay_data.empty:
                    print(f"No market data found for set {set_number}")
                    continue
                
                # Calculate statistics
                stats = {
                    'Overall Average': ebay_data['Total Price'].mean().round(2),
                    'Minimum Price': ebay_data['Total Price'].min().round(2),
                    'Maximum Price': ebay_data['Total Price'].max().round(2),
                    'Number of Items': len(ebay_data)
                }
                
                # Calculate averages by seller type
                avg_prices = ebay_data.groupby('Seller Type')['Total Price'].agg(['mean', 'count']).round(2)
                avg_prices.columns = ['Average Price', 'Count']
                
                result = {
                    'Set Number': set_number,
                    'Inventory Price': row['Average price'],
                    'Market Average': stats['Overall Average'],
                    'Market Min': stats['Minimum Price'],
                    'Market Max': stats['Maximum Price'],
                    'Items Found': stats['Number of Items']
                }
                
                # Add seller type averages if available
                if 'Privat' in avg_prices.index:
                    result['Privat Avg Price'] = avg_prices.loc['Privat', 'Average Price']
                    result['Privat Count'] = avg_prices.loc['Privat', 'Count']
                else:
                    result['Privat Avg Price'] = 0
                    result['Privat Count'] = 0
                    
                if 'Gewerblich' in avg_prices.index:
                    result['Gewerblich Avg Price'] = avg_prices.loc['Gewerblich', 'Average Price']
                    result['Gewerblich Count'] = avg_prices.loc['Gewerblich', 'Count']
                else:
                    result['Gewerblich Avg Price'] = 0
                    result['Gewerblich Count'] = 0
                
                results.append(result)
            except Exception as e:
                print(f"Error processing set {row['Set']}: {e}")
                continue
        
        if not results:
            print("No results found for any set!")
            return None
            
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        
        # Calculate potential profit
        results_df['Potential Profit'] = results_df['Market Average'] - results_df['Inventory Price']
        
        # Sort by potential profit
        results_df = results_df.sort_values('Potential Profit', ascending=False)
        
        # Save results
        results_df.to_csv(os.path.join(self.data_dir, 'price_comparison_results.csv'), index=False)
        print("\nResults saved to price_comparison_results.csv")
        
        return results_df

def main():
    """Main function to run the price comparison tool."""
    print("\nStarting LEGO Price Comparison Tool...")
    tool = PriceComparisonTool()
    results = tool.compare_prices()
    
    if results is not None:
        print("\nComparison Results:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(results)
        print(f"\nTotal sets processed: {len(results)}")

if __name__ == "__main__":
    main()
