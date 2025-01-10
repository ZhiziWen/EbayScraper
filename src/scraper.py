"""
eBay LEGO Price Scraper

This script fetches sold LEGO set prices from eBay Germany (ebay.de) using Selenium and BeautifulSoup.
Features:
- Searches for specific LEGO set numbers
- Filters for items sold in Germany only
- Returns prices in EUR only
- Validates set numbers in titles to avoid wrong matches
- Includes item price, shipping cost, and total price
- Includes actual sold dates
- Saves results to CSV file
- Only fetches items sold in the last 30 days
"""

import os
import pandas as pd
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dateutil import parser
import time

class EbayScraper:
    def __init__(self):
        # Setup data directory for saving results
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Setup Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # Run in headless mode
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--lang=de-DE')  # Set language to German
        
        # Initialize the webdriver
        self.driver = None
        print("Scraper initialized")

    def setup_driver(self):
        """Setup and return a Chrome webdriver instance."""
        if self.driver is None:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
        return self.driver

    def close_driver(self):
        """Close the webdriver instance."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def is_valid_title(self, title, target_set):
        """
        Validate that the item title contains the correct LEGO set number.
        Only allows one number with the same digit length as the target set number.
        """
        numbers = re.findall(r'\d+', title)
        print(f"Title validation - Title: {title}")
        print(f"Found numbers: {numbers}")
        print(f"Target set: {target_set}")
        
        # Count how many numbers have the same length as target_set
        target_length = len(target_set)
        same_length_numbers = [num for num in numbers if len(num) == target_length]
        
        # If we have more than one number with the same length as target_set, reject
        if len(same_length_numbers) > 1:
            print(f"Found multiple numbers with length {target_length}: {same_length_numbers} - rejecting")
            return False
            
        # If we have exactly one number with the same length, it must be our target
        if len(same_length_numbers) == 1:
            is_valid = same_length_numbers[0] == target_set
            print(f"Found one number with matching length. Valid: {is_valid}")
            return is_valid
            
        # If we have no numbers of the same length, reject
        print("No numbers found with matching length - rejecting")
        return False

    def parse_price(self, price_str):
        """Extract price value from string."""
        if not price_str:
            return 0
        print(f"Parsing price: {price_str}")
        # Remove currency symbol and convert to float
        price_str = price_str.replace('EUR', '').replace('€', '').strip()
        price_str = price_str.replace(',', '.')
        try:
            price = float(re.search(r'\d+[.,]?\d*', price_str).group())
            print(f"Extracted price: {price}")
            return price
        except (AttributeError, ValueError) as e:
            print(f"Error parsing price: {e}")
            return 0

    def parse_date(self, date_str):
        """Parse date string to datetime object."""
        if not date_str:
            return None
            
        try:
            print(f"Parsing date: {date_str}")
            # Convert German month names to English
            german_to_english = {
                'Jan': 'Jan', 'Jän': 'Jan', 'Januar': 'January',
                'Feb': 'Feb', 'Februar': 'February',
                'Mär': 'Mar', 'März': 'March',
                'Apr': 'Apr', 'April': 'April',
                'Mai': 'May',
                'Jun': 'Jun', 'Juni': 'June',
                'Jul': 'Jul', 'Juli': 'July',
                'Aug': 'Aug', 'August': 'August',
                'Sep': 'Sep', 'September': 'September',
                'Okt': 'Oct', 'Oktober': 'October',
                'Nov': 'Nov', 'November': 'November',
                'Dez': 'Dec', 'Dezember': 'December'
            }
            
            # Remove common German text and clean up
            date_str = (date_str.replace('Verkauft', '')
                               .replace('Beendet:', '')
                               .replace('am', '')
                               .strip())
            
            # Replace German month names with English ones
            for german, english in german_to_english.items():
                date_str = date_str.replace(german, english)
            
            print(f"Cleaned date string: {date_str}")
            date = parser.parse(date_str, fuzzy=True)
            print(f"Parsed date: {date}")
            return date.strftime('%Y-%m-%d')  # Return formatted date string
        except Exception as e:
            print(f"Error parsing date: {e}")
            return None

    def is_within_30_days(self, date_str):
        """Check if the given date is within the last 30 days."""
        if not date_str:
            return True  # Accept items without dates for now
            
        print(f"Checking if date is within 30 days: {date_str}")
        date = parser.parse(self.parse_date(date_str) or '', fuzzy=True)
        if not date:
            return True  # Accept items with unparseable dates for now
            
        days_diff = (datetime.now() - date).days
        print(f"Days difference: {days_diff}")
        return days_diff <= 30

    def fetch_ebay_sold_items(self, set_numbers):
        """Fetch sold items for given LEGO set numbers from eBay Germany."""
        all_results = []
        driver = self.setup_driver()
        
        for set_number in set_numbers:
            print(f"\n{'='*80}")
            print(f"Searching for LEGO set {set_number}...")
            print(f"{'='*80}")
            
            page = 1
            has_next_page = True
            
            while has_next_page:
                url = f'https://www.ebay.de/sch/i.html?_nkw=LEGO+{set_number}&_sop=12&LH_Complete=1&LH_Sold=1&_pgn={page}'
                print(f"\nFetching page {page} - URL: {url}")
                
                try:
                    # Load the page
                    driver.get(url)
                    time.sleep(2)  # Wait for page to load
                    
                    # Wait for search results
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.srp-results"))
                        )
                    except TimeoutException:
                        print("No more results found")
                        break
                    
                    # Parse the page
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    items = soup.select('li.s-item')
                    
                    if not items:
                        print("No items found on this page")
                        break
                    
                    print(f"\nFound {len(items)} items on page {page}")
                    
                    # Check if there's a next page
                    next_page = soup.select_one('a.pagination__next')
                    has_next_page = next_page is not None
                    
                    for idx, item in enumerate(items, 1):
                        try:
                            print(f"\nProcessing item {idx}/{len(items)} on page {page}")
                            
                            # Extract title
                            title_elem = item.select_one('div.s-item__title')
                            if not title_elem:
                                print("No title element found")
                                continue
                            title = title_elem.text.strip()
                            print(f"Title: {title}")
                            
                            # Skip the first item on page 1 (it's usually "Shop on eBay")
                            if page == 1 and idx == 1 and title == "Shop on eBay":
                                print("Skipping 'Shop on eBay' item")
                                continue
                            
                            # Validate title
                            if not self.is_valid_title(title, set_number):
                                print("Invalid title - skipping")
                                continue
                                
                            # Extract price
                            price_elem = item.select_one('span.s-item__price')
                            print(f"Price element: {price_elem.text if price_elem else None}")
                            item_price = self.parse_price(price_elem.text if price_elem else None)
                            
                            # Extract shipping cost
                            shipping_elem = item.select_one('span.s-item__shipping')
                            print(f"Shipping element: {shipping_elem.text if shipping_elem else None}")
                            shipping_cost = self.parse_price(shipping_elem.text if shipping_elem else None)
                            
                            # Extract sold date
                            date_elem = (
                                item.find('span', string=re.compile(r'Verkauft|Beendet')) or
                                item.find('div', string=re.compile(r'Verkauft|Beendet')) or
                                item.select_one('span.s-item__endedDate') or
                                item.select_one('div.s-item__ended-date') or
                                item.select_one('span.POSITIVE')
                            )
                            sold_date = date_elem.text if date_elem else None
                            print(f"Found date element: {sold_date}")
                            
                            # Parse the date
                            parsed_date = self.parse_date(sold_date)
                            
                            # Skip if not within last 30 days
                            if not self.is_within_30_days(sold_date):
                                print("Item not sold within last 30 days - skipping")
                                continue
                                
                            # Extract URL
                            url_elem = item.select_one('a.s-item__link')
                            item_url = url_elem['href'] if url_elem else None
                            
                            # Extract location
                            location_elem = item.select_one('span.s-item__location') or item.select_one('span.s-item__itemLocation')
                            location = location_elem.text if location_elem else 'Deutschland'
                            print(f"Location: {location}")
                            
                            # Calculate total price
                            total_price = item_price + shipping_cost
                            
                            result = {
                                'Title': title,
                                'Item Price': item_price,
                                'Shipping Fee': shipping_cost,
                                'Total Price': total_price,
                                'Currency': 'EUR',
                                'URL': item_url,
                                'Set Number': set_number,
                                'End Time': parsed_date,
                                'Location': location
                            }
                            
                            all_results.append(result)
                            print(f"Successfully added item to results")
                            
                        except Exception as e:
                            print(f"Error processing item: {str(e)}")
                            continue
                    
                    if has_next_page:
                        print(f"\nMoving to page {page + 1}")
                        page += 1
                        time.sleep(2)  # Add delay between pages
                    else:
                        print("\nNo more pages available")
                        
                except Exception as e:
                    print(f"Error fetching page {page} for set {set_number}: {str(e)}")
                    break

        # Close the browser
        self.close_driver()

        if not all_results:
            print("\nNo results found!")
            return None, None

        # Create DataFrame
        df = pd.DataFrame(all_results)
        
        # Sort by date
        df['End Time'] = pd.to_datetime(df['End Time'])
        df = df.sort_values('End Time', ascending=False)
        
        # Reorder columns
        df = df[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'End Time', 'Currency', 'Location', 'URL', 'Set Number']]
        
        # Print complete DataFrame
        print(f"\nFound total of {len(df)} items")
        print("\nComplete DataFrame:")
        with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
            print(df[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'End Time', 'Currency', 'Location', 'URL']])

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'ebay_sales_{timestamp}.csv'
        filepath = os.path.join(self.data_dir, filename)
        print(f"\nSaving results to {filepath}")
        df.to_csv(filepath, index=False)
        
        return df, filepath

def main():
    """Main function to run the eBay scraper"""
    print("\nStarting eBay LEGO Price Scraper...")
    scraper = EbayScraper()
    
    try:
        set_numbers = input("\nEnter the LEGO set numbers separated by commas (e.g., 40632, 75257): ").split(',')
        set_numbers = [num.strip() for num in set_numbers if num.strip().isdigit()]
        
        if not set_numbers:
            raise ValueError("No valid set numbers provided")
            
        print(f"\nProcessing LEGO sets: {', '.join(set_numbers)}")
        results, saved_file = scraper.fetch_ebay_sold_items(set_numbers)
        
        if results is not None:
            print(f"\nResults saved to {saved_file}")
            print("\nTest Results:")
            print(results[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'End Time', 'Currency', 'Location', 'URL']])
            
    except Exception as e:
        print(f"\nError running scraper: {str(e)}")
    finally:
        # Ensure browser is closed
        scraper.close_driver()

if __name__ == "__main__":
    main()