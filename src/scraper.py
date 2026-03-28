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
        # Setup data directory for saving results, create if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Setup Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # Run in headless mode
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--lang=de-DE')  # Set language to German
        # Add user agent to avoid detection
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize the webdriver
        self.driver = None
        print("Scraper initialized")

    def setup_driver(self):
        """Setup and return a Chrome webdriver instance."""
        if self.driver is None:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            # Hide webdriver property to avoid detection
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
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
        Rejects individual part/minifigure listings (e.g. "AUS SET 21160").
        """
        # Reject part listings: set number appears after "aus" (e.g. "AUS SET 21160", "aus 21160")
        # Use (?!\d) instead of \b because eBay appends "Wird in neuem..." directly to the number
        if re.search(rf'\baus\s+(set\s+)?{re.escape(target_set)}(?!\d)', title, re.I):
            print(f"Part listing detected ('aus ... {target_set}') - rejecting")
            return False

        # Reject individual minifigures with explicit LEGO minifig part codes (e.g. sw1057, hp157)
        # Check for both "Minifigur sw1057" and "sw1057 ... Minifigur" orderings; allow space in code
        if re.search(r'\b(minifigur|minifig)\b', title, re.I) and \
           re.search(r'\b[a-z]{2,3}\s?\d{3,4}\b', title, re.I):
            print(f"Individual minifigure with part code detected - rejecting")
            return False

        # Reject multi-set bundle listings (e.g. "x4 Lego 40565", "2x", "3 Stück", "Lot")
        if re.search(r'(^x[2-9]\s|^[2-9]x\s|\b[2-9]\s*stück\b|\blot\b|\bbundle\b)', title, re.I):
            print(f"Multi-set bundle listing detected - rejecting")
            return False

        # Reject listings selling only instructions/sticker sheets (not the full set)
        if re.search(r'\b(bauanleitung|anleitung|aufkleber|sticker)\b', title, re.I) and \
           not re.search(r'\b(neu|new|ovp|versiegelt|sealed)\b', title, re.I):
            print(f"Instruction/sticker-only listing detected - rejecting")
            return False

        # Reject listings explicitly without box/OVP (sells for less, not comparable to sealed sets)
        if re.search(r'\b(ohne\s+ovp|ohne\s+box|ohne\s+karton|karton\s+fehlt)\b', title, re.I):
            print(f"Without-box listing detected - rejecting")
            return False

        numbers = re.findall(r'\d+', title)
        print(f"Title validation - Title: {title}")
        print(f"Found numbers: {numbers}")
        print(f"Target set: {target_set}")
        
        # Count how many numbers have the same length as target_set
        target_length = len(target_set)
        same_length_numbers = [num for num in numbers if len(num) == target_length]
        
        # If we have more than one number with the same length as target_set, check if all are the target
        if len(same_length_numbers) > 1:
            if all(num == target_set for num in same_length_numbers):
                print(f"All numbers match the target set number: {same_length_numbers} - accepting")
                return True
            else:
                print(f"Found multiple numbers with length {target_length} that do not match target: {same_length_numbers} - rejecting")
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

    def parse_shipping(self, shipping_str, set_number):
        """Extract shipping cost from string, handling free shipping and avoiding set numbers."""
        if not shipping_str:
            return 0
        
        print(f"Parsing shipping: {shipping_str}")
        
        # Check for free shipping keywords
        shipping_lower = shipping_str.lower()
        if any(keyword in shipping_lower for keyword in ['kostenlos', 'free', 'gratis', 'inklusive']):
            print("Free shipping detected")
            return 0
        
        # Handle new eBay format: "+EUR 6,19" or "+€ 6,19"
        # Remove the + sign and currency symbols
        shipping_str = shipping_str.replace('+', '').strip()
        shipping_str = shipping_str.replace('EUR', '').replace('€', '').strip()
        shipping_str = re.sub(r'Versand|Shipping|Porto|Post|Lieferung', '', shipping_str, flags=re.I).strip()
        
        # Replace comma with dot for decimal
        shipping_str = shipping_str.replace(',', '.')
        
        # Extract number, but make sure it's not the set number
        try:
            # Find all numbers in the string (including decimals)
            numbers = re.findall(r'\d+\.?\d*', shipping_str)
            if not numbers:
                return 0
            
            # Filter out the set number
            filtered_numbers = []
            for n in numbers:
                # Remove dots to compare with set number
                n_clean = n.replace('.', '')
                # Check if it's the set number (as integer or as part of a larger number)
                if n_clean != str(set_number) and not n_clean.startswith(str(set_number)) and not str(set_number).startswith(n_clean):
                    filtered_numbers.append(n)
            
            if not filtered_numbers:
                # If only the set number was found, it's likely not shipping info
                print(f"Only set number found in shipping text, assuming free shipping")
                return 0
            
            # Take the first valid number (usually the shipping cost)
            shipping_cost = float(filtered_numbers[0])
            
            # Sanity check: shipping shouldn't be more than 100 EUR typically
            if shipping_cost > 100:
                print(f"Shipping cost {shipping_cost} seems too high, assuming free shipping")
                return 0
            
            print(f"Extracted shipping: {shipping_cost}")
            return shipping_cost
        except (AttributeError, ValueError) as e:
            print(f"Error parsing shipping: {e}")
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
                'Mrz': 'Mar', 'Mär': 'Mar', 'März': 'March',
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

    def save_results_to_csv(self, df, set_number):
        """Save results to CSV with specific naming format."""
        if df is None or df.empty:
            return None
            
        # Get the date range from the data
        df['End Time'] = pd.to_datetime(df['End Time'])
        start_date = df['End Time'].min().strftime('%Y%m%d')
        end_date = df['End Time'].max().strftime('%Y%m%d')
        current_time = datetime.now().strftime('%H%M%S')
        
        # Create filename with the specified format
        filename = f'Ebay_Lego_{set_number}_{start_date}_{end_date}_{current_time}.csv'
        filepath = os.path.join(self.data_dir, filename)
        
        print(f"\nSaving results for set {set_number} to {filepath}")
        df.to_csv(filepath, index=False)
        return filepath

    def fetch_ebay_sold_items(self, set_number):
        """Fetch sold items for a given LEGO set number from eBay Germany."""
        driver = self.setup_driver()
        results = []  # List to store results
        
        print(f"\n{'='*80}")
        print(f"Searching for LEGO set {set_number}...")
        print(f"{'='*80}")
        
        page = 1
        has_next_page = True
        reached_old_items = False
        
        while has_next_page and not reached_old_items:
            url = f'https://www.ebay.de/sch/i.html?_nkw=LEGO+{set_number}&_sop=12&LH_Complete=1&LH_Sold=1&_pgn={page}'
            print(f"\nFetching page {page} - URL: {url}")
            
            try:
                # Load the page
                driver.get(url)

                # Smart wait: try selectors with a combined timeout instead of fixed sleep
                results_found = False
                selectors_to_try = [
                    "ul.srp-results",
                    "ul[class*='srp-results']",
                    ".srp-list",
                    "ul[class*='results']"
                ]
                for selector in selectors_to_try:
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        results_found = True
                        break
                    except TimeoutException:
                        continue

                if not results_found:
                    print("Timeout waiting for search results")
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    if soup.find(string=re.compile(r'keine.*ergebnisse|no.*results', re.I)):
                        print("No results found on eBay")
                    break

                # Short wait for remaining dynamic content (reduced from 3s)
                time.sleep(1)
                
                # Parse the page
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Check if we got blocked or captcha
                page_text = soup.get_text().lower()
                if any(keyword in page_text for keyword in ['captcha', 'verify you are human', 'access denied', 'blocked']):
                    print("WARNING: Possible CAPTCHA or blocking detected on eBay")
                    debug_file = os.path.join(self.data_dir, f'debug_blocked_page_{page}.html')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    print(f"Saved page HTML to {debug_file} for debugging")
                    break
                
                # Try multiple selectors for items
                items = soup.select('li.s-item')
                if not items:
                    items = soup.select('li[class*="s-item"]')
                if not items:
                    items = soup.select('.s-item')
                if not items:
                    items = soup.select('li[data-view]')
                if not items:
                    # Try to find any list items in the results area
                    results_container = soup.select_one('ul.srp-results, ul[class*="srp-results"], .srp-list')
                    if results_container:
                        items = results_container.select('li')
                
                if not items:
                    print("No items found on this page")
                    # Debug: save HTML to see what we got
                    debug_file = os.path.join(self.data_dir, f'debug_page_{page}.html')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    print(f"Saved page HTML to {debug_file} for debugging")
                    break
                
                print(f"\nFound {len(items)} items on page {page}")
                
                # Check if there's a next page
                next_page = soup.select_one('a.pagination__next')
                has_next_page = next_page is not None
                
                old_items_count = 0  # Counter for items older than 30 days
                valid_items_on_page = 0  # Counter for valid items on this page
                
                for idx, item in enumerate(items, 1):
                    try:
                        print(f"\nProcessing item {idx}/{len(items)} on page {page}")
                        
                        # Extract title - try multiple selectors
                        title_elem = (
                            item.select_one('div.s-item__title') or
                            item.select_one('.s-item__title') or
                            item.select_one('h3.s-item__title') or
                            item.select_one('a.s-item__link') or
                            item.select_one('[class*="title"]')
                        )
                        if not title_elem:
                            print("No title element found")
                            continue
                        title = title_elem.text.strip()
                        # Clean up title (remove extra whitespace, newlines)
                        title = ' '.join(title.split())
                        print(f"Title: {title}")
                        
                        # Skip the first item on page 1 (it's usually "Shop on eBay")
                        if page == 1 and idx == 1 and title == "Shop on eBay":
                            print("Skipping 'Shop on eBay' item")
                            continue
                        
                        # Validate title
                        if not self.is_valid_title(title, set_number):
                            print("Invalid title - skipping")
                            continue
                            
                        # Extract sold date first to check if we should continue
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
                        
                        # Check if item is within 30 days
                        if not self.is_within_30_days(sold_date):
                            print("Item not sold within last 30 days - skipping")
                            old_items_count += 1
                            # If we've found multiple old items, assume we've reached the cutoff
                            if old_items_count >= 3 and valid_items_on_page > 0:
                                print("\nFound multiple items older than 30 days - stopping pagination")
                                reached_old_items = True
                                break
                            continue
                            
                        valid_items_on_page += 1
                            
                        # Extract price - try multiple selectors
                        price_elem = (
                            item.select_one('span.s-item__price') or
                            item.select_one('.s-item__price') or
                            item.select_one('span[class*="price"]') or
                            item.select_one('.s-item__detail--primary') or
                            item.find('span', class_=re.compile(r'price', re.I)) or
                            item.find('span', string=re.compile(r'€|EUR', re.I))
                        )
                        
                        # If still not found, search for price pattern in all elements
                        if not price_elem:
                            # Try divs first (often used for price)
                            all_divs = item.find_all('div')
                            for div in all_divs:
                                text = div.get_text()
                                if text and re.search(r'€|EUR', text) and re.search(r'\d+[.,]\d+', text):
                                    # Make sure it's not shipping or other info
                                    if not re.search(r'Versand|Shipping|kostenlos', text, re.I):
                                        price_elem = div
                                        break
                            
                            # If still not found, try spans
                            if not price_elem:
                                all_spans = item.find_all('span')
                                for span in all_spans:
                                    text = span.get_text()
                                    if text and re.search(r'€|EUR', text) and re.search(r'\d+[.,]\d+', text):
                                        # Make sure it's not shipping or other info
                                        if not re.search(r'Versand|Shipping|kostenlos', text, re.I):
                                            price_elem = span
                                            break
                        
                        price_text = price_elem.text.strip() if price_elem else None
                        print(f"Price element: {price_text}")
                        item_price = self.parse_price(price_text)
                        
                        # Extract shipping cost - try comprehensive selectors
                        # eBay uses various class names for shipping
                        shipping_elem = None
                        # First, try the new eBay structure (found in debug files)
                        # Look for div.s-card__attribute-row that contains shipping info
                        rows = item.find_all('div', class_='s-card__attribute-row')
                        for row in rows:
                            row_text = row.get_text()
                            # Check if this row contains shipping info (Lieferung, Versand, or +EUR pattern)
                            if re.search(r'Lieferung|Versand|Shipping|\+EUR|\+€', row_text, re.I):
                                # Try to find the span with the shipping price (starts with +)
                                spans = row.find_all('span')
                                for span in spans:
                                    text = span.get_text().strip()
                                    # Check if it starts with + and has a number (shipping format: +EUR 6,19)
                                    if re.search(r'^\+.*EUR.*[\d,\.]+|^\+.*€.*[\d,\.]+|^\+[\d,\.]+', text):
                                        shipping_elem = span
                                        break
                                if not shipping_elem:
                                    # If no span with + found, check for "kostenlos" or "free"
                                    if re.search(r'kostenlos|free', row_text, re.I):
                                        shipping_elem = row
                                        break
                                if shipping_elem:
                                    break
                        if shipping_elem:
                            pass  # Found it, continue below
                        else:
                            # Fallback to old eBay structure
                            shipping_selectors = [
                                'span.s-item__shipping',
                                '.s-item__shipping',
                                'span[class*="shipping"]',
                                'div[class*="shipping"]',
                                '.s-item__detail--secondary',
                                'span.s-item__freeXDays',
                                '.s-item__freeXDays',
                            ]
                            
                            for selector in shipping_selectors:
                                try:
                                    elem = item.select_one(selector)
                                    if elem:
                                        text = elem.get_text().strip()
                                        if text and (re.search(r'Versand|Shipping|kostenlos|free|€|EUR|[\d,\.]+', text, re.I)):
                                            shipping_elem = elem
                                            break
                                except Exception as e:
                                    continue
                        
                        # If still not found, search all elements with shipping-related classes
                        if not shipping_elem:
                            for tag in ['span', 'div', 'p']:
                                elems = item.find_all(tag, class_=re.compile(r'shipping|versand|free', re.I))
                                for elem in elems:
                                    text = elem.get_text().strip()
                                    if text and len(text) < 100:  # Shipping info is usually short
                                        shipping_elem = elem
                                        break
                                if shipping_elem:
                                    break
                        
                        # If still not found, search by text content
                        if not shipping_elem:
                            for tag in ['span', 'div', 'p', 'td']:
                                elems = item.find_all(tag)
                                for elem in elems:
                                    text = elem.get_text().strip()
                                    # Look for elements that contain shipping keywords and a price
                                    if text and re.search(r'Versand|Shipping|Porto', text, re.I):
                                        if re.search(r'[\d,\.]+', text) or re.search(r'kostenlos|free', text, re.I):
                                            # Make sure it's not too long (likely not shipping)
                                            if len(text) < 100:
                                                shipping_elem = elem
                                                break
                                if shipping_elem:
                                    break
                        
                        shipping_text = shipping_elem.text.strip() if shipping_elem else None
                        
                        # If shipping not found, try to find it in the entire item text
                        if not shipping_text:
                            item_text = item.get_text()
                            
                            # Look for shipping patterns in the full item text
                            shipping_patterns = [
                                r'Versand[:\s]+([€EUR\s]*[\d,\.]+)',
                                r'Shipping[:\s]+([€EUR\s]*[\d,\.]+)',
                                r'Porto[:\s]+([€EUR\s]*[\d,\.]+)',
                                r'([€EUR\s]*[\d,\.]+)\s*Versand',
                                r'([€EUR\s]*[\d,\.]+)\s*Shipping',
                                r'Versandkosten[:\s]+([€EUR\s]*[\d,\.]+)',
                                r'([€EUR\s]*[\d,\.]+)\s*€?\s*Versand',
                            ]
                            for pattern in shipping_patterns:
                                match = re.search(pattern, item_text, re.I)
                                if match:
                                    potential_shipping = match.group(1).strip()
                                    # Make sure it's not the set number or item price
                                    potential_num = re.search(r'[\d,\.]+', potential_shipping)
                                    if potential_num:
                                        num_value = potential_num.group().replace(',', '.')
                                        try:
                                            num_float = float(num_value)
                                            # Check if it's reasonable shipping (not the set number, not too high)
                                            if num_float < 100 and num_float != float(set_number):
                                                shipping_text = potential_shipping
                                                print(f"Found shipping via pattern: {shipping_text}")
                                                break
                                        except ValueError:
                                            continue
                            
                            # Also check for "kostenlos" or "free" shipping
                            if not shipping_text:
                                if re.search(r'kostenlos|free\s+shipping|versand\s+kostenlos|versand\s+inkl', item_text, re.I):
                                    shipping_text = "kostenlos"
                                    print("Found free shipping in item text")
                            
                            # Last resort: check all text nodes for shipping info
                            if not shipping_text:
                                for elem in item.find_all(['span', 'div', 'p', 'td']):
                                    text = elem.get_text()
                                    if text and len(text) < 50:  # Short text likely to be shipping
                                        if re.search(r'versand|shipping', text, re.I) and re.search(r'[\d,\.]+', text):
                                            # Extract the number
                                            num_match = re.search(r'([\d,\.]+)', text)
                                            if num_match:
                                                try:
                                                    num_val = float(num_match.group().replace(',', '.'))
                                                    if num_val < 100 and num_val != float(set_number):
                                                        shipping_text = text.strip()
                                                        print(f"Found shipping in text node: {shipping_text}")
                                                        break
                                                except ValueError:
                                                    continue
                        
                        print(f"Shipping element: {shipping_text}")
                        shipping_cost = self.parse_shipping(shipping_text, set_number)
                        
                        # Debug: Save first valid item HTML to inspect structure
                        if valid_items_on_page == 1 and page == 1:
                            debug_item_file = os.path.join(self.data_dir, f'debug_item_{set_number}.html')
                            with open(debug_item_file, 'w', encoding='utf-8') as f:
                                f.write(str(item.prettify()))
                            print(f"DEBUG: Saved item HTML to {debug_item_file} for inspection")
                            
                            # Also save all class names for debugging
                            debug_classes_file = os.path.join(self.data_dir, f'debug_classes_{set_number}.txt')
                            with open(debug_classes_file, 'w', encoding='utf-8') as f:
                                f.write("All class names in item:\n")
                                for elem in item.find_all(True):
                                    classes = elem.get('class', [])
                                    if classes:
                                        f.write(f"{elem.name}: {', '.join(classes)}\n")
                            print(f"DEBUG: Saved class names to {debug_classes_file}")
                            
                            # Save all text content for inspection
                            debug_text_file = os.path.join(self.data_dir, f'debug_text_{set_number}.txt')
                            with open(debug_text_file, 'w', encoding='utf-8') as f:
                                f.write("All text content in item:\n")
                                for elem in item.find_all(['span', 'div', 'p']):
                                    text = elem.get_text().strip()
                                    if text and len(text) < 200:
                                        classes = elem.get('class', [])
                                        class_str = ', '.join(classes) if classes else 'no-class'
                                        f.write(f"[{elem.name}.{class_str}]: {text}\n")
                            print(f"DEBUG: Saved text content to {debug_text_file}")
                        
                        # Extract URL
                        url_elem = item.select_one('a.s-item__link')
                        item_url = url_elem['href'] if url_elem else None
                        
                        # Extract location - look for "Standort in Deutschland" in attribute rows
                        location = 'Deutschland'  # Default
                        location_rows = item.find_all('div', class_='s-card__attribute-row')
                        for row in location_rows:
                            row_text = row.get_text()
                            if 'Standort' in row_text or 'Deutschland' in row_text:
                                # Extract location from "Standort in Deutschland"
                                if 'Deutschland' in row_text:
                                    location = 'Deutschland'
                                    break
                                # Try to extract other locations
                                location_match = re.search(r'Standort\s+in\s+([^,]+)', row_text)
                                if location_match:
                                    location = location_match.group(1).strip()
                                    break
                        
                        # Fallback to old structure
                        if location == 'Deutschland':
                            location_elem = (
                                item.select_one('span.s-item__location') or
                                item.select_one('span.s-item__itemLocation')
                            )
                            if location_elem:
                                location = location_elem.text.strip()
                                if location.startswith('aus '):
                                    location = location[4:]  # Remove 'aus ' prefix
                        
                        print(f"Location: {location}")
                        
                        # Extract item condition and seller type from subtitle
                        # New eBay structure: div.s-card__subtitle contains "Gebraucht | Privat"
                        subtitle_elem = (
                            item.select_one('div.s-card__subtitle') or
                            item.select_one('div.s-card__subtitle-row') or
                            item.select_one('span.SECONDARY_INFO')  # Fallback to old structure
                        )
                        
                        condition = 'Unknown'
                        seller_type = 'Unknown'
                        
                        if subtitle_elem:
                            subtitle_text = subtitle_elem.get_text().strip()
                            print(f"Subtitle text: {subtitle_text}")
                            
                            # Split by | to get condition and seller type
                            if '|' in subtitle_text:
                                parts = [p.strip() for p in subtitle_text.split('|')]
                                if len(parts) >= 1:
                                    condition = parts[0]
                                if len(parts) >= 2:
                                    seller_type = parts[1]
                            else:
                                # If no |, check if it's just condition or seller type
                                if 'Gewerblich' in subtitle_text or 'Privat' in subtitle_text:
                                    seller_type = 'Gewerblich' if 'Gewerblich' in subtitle_text else 'Privat'
                                    # Try to find condition elsewhere
                                    condition = subtitle_text.replace('Gewerblich', '').replace('Privat', '').strip()
                                    if not condition:
                                        condition = 'Unknown'
                                else:
                                    condition = subtitle_text
                        
                        # Map German condition names - keep "Brandneu" as is for filtering
                        condition_map = {
                            'Gebraucht': 'Used',
                            'Neu': 'New',
                            'Brandneu': 'Brandneu',  # Keep original for filtering
                            'OVP': 'Sealed',
                            'Ungeöffnet': 'Unopened'
                        }
                        if condition in condition_map:
                            condition = condition_map[condition]
                        
                        print(f"Condition: {condition}")
                        print(f"Seller Type: {seller_type}")
                        
                        # Calculate total price
                        total_price = round(item_price + shipping_cost, 2)

                        # Skip items where price parsing failed (item_price = 0 means no price found)
                        if item_price == 0:
                            print(f"Skipping item with zero item price (price parsing failed): {title[:60]}")
                            continue

                        result = {
                            'Title': title,
                            'Item Price': item_price,
                            'Shipping Fee': shipping_cost,
                            'Total Price': total_price,
                            'End Time': parsed_date,
                            'Currency': 'EUR',
                            'Location': location,
                            'URL': item_url,
                            'Set Number': set_number,
                            'Condition': condition,
                            'Seller Type': seller_type
                        }
                        
                        results.append(result)
                        print(f"Successfully added item to results")
                        
                    except Exception as e:
                        print(f"Error processing item: {str(e)}")
                        continue
                
                if reached_old_items:
                    print(f"\nStopping pagination as we've reached items older than 30 days")
                    break
                    
                if has_next_page and not reached_old_items:
                    print(f"\nMoving to page {page + 1}")
                    page += 1
                    time.sleep(1)  # Brief courtesy delay between pages
                else:
                    print("\nNo more pages available")
                    
            except Exception as e:
                print(f"Error fetching page {page} for set {set_number}: {str(e)}")
                break

        # Process results for current set number
        if results:
            # Create DataFrame for current set
            df = pd.DataFrame(results)
            
            # Sort by date
            df['End Time'] = pd.to_datetime(df['End Time'])
            df = df.sort_values('End Time', ascending=False)
            
            # Reorder columns
            df = df[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'End Time', 'Condition', 'Seller Type', 'Currency', 'Location', 'URL', 'Set Number']]
            
            # Ensure 'Seller Type' column is present
            if 'Seller Type' not in df.columns:
                df['Seller Type'] = 'Unknown'
            
            # Save to CSV
            filepath = self.save_results_to_csv(df, set_number)

            # Print results for current set
            print(f"\nFound {len(df)} items for set {set_number}")
            print(f"\nResults for set {set_number}:")
            with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
                print(df[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'End Time', 'Condition', 'Seller Type', 'Currency', 'Location', 'URL']])

            # NOTE: Driver is kept alive for reuse across sets. Call close() when fully done.
            return df
        else:
            print(f"\nNo results found for set {set_number}")
            return None

    def close(self):
        """Close the WebDriver when done."""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                print("WebDriver closed successfully")
        except Exception as e:
            print(f"Error closing WebDriver: {e}")

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
        saved_files = []
        for set_number in set_numbers:
            result = scraper.fetch_ebay_sold_items(set_number)
            if result is not None:
                # Find the saved file for this set
                csv_files = [f for f in os.listdir(scraper.data_dir) 
                            if f.startswith(f'Ebay_Lego_{set_number}_') and f.endswith('.csv')]
                if csv_files:
                    # Get the latest file
                    latest_file = max(csv_files)
                    saved_files.append(os.path.join(scraper.data_dir, latest_file))
        
        if saved_files:
            print("\nScraping completed successfully!")
            print("\nFiles saved:")
            for filepath in saved_files:
                print(filepath)
            
    except Exception as e:
        print(f"\nError running scraper: {str(e)}")
    finally:
        # Ensure browser is closed
        scraper.close_driver()

if __name__ == "__main__":
    main()