import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import random
import time

class EbayScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.seen_items = set()
        
    def extract_number_from_price(self, price_text):
        if 'EUR' not in price_text:
            return None
        try:
            number = re.search(r'(\d+,\d+|\d+)', price_text).group(1)
            return float(number.replace(',', '.'))
        except (AttributeError, ValueError):
            return None

    def extract_shipping_cost(self, shipping_text):
        if not shipping_text or 'kostenlos' in shipping_text.lower():
            return 0
        try:
            number = re.search(r'(\d+,\d+|\d+)', shipping_text).group(1)
            return float(number.replace(',', '.'))
        except (AttributeError, ValueError):
            return None
            
    def is_duplicate(self, title, price, date_sold):
        item_key = f"{title}_{price}_{date_sold}"
        if item_key in self.seen_items:
            return True
        self.seen_items.add(item_key)
        return False

    def validate_title_number(self, title, set_number):
        numbers = re.findall(r'\d{' + str(len(set_number)) + r'}', title)
        return str(set_number) in numbers and all(n == str(set_number) for n in numbers if len(n) == len(str(set_number)))
            
    def fetch_ebay_sold_items(self, set_number):
        items_list = []
        self.seen_items.clear()
        page = 1
        thirty_days_ago = datetime.now() - timedelta(days=30)
        continue_scraping = True
        
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0",
            # Add more User-Agent strings as needed
        ]
        
        # ScraperAPI proxy configuration
        proxies = {
            "https": "scraperapi.country_code=eu.device_type=desktop.max_cost=10.session_number=8:777993e70bd8149e6cc29976696cdbbe@proxy-server.scraperapi.com:8001"
        }
        
        while continue_scraping:
            print(f"Scraping page {page}...")
            url = (f"https://www.ebay.de/sch/i.html?_from=R40&_nkw=LEGO+{set_number}"
                  f"&_sacat=0&LH_TitleDesc=0&LH_Sold=1&LH_Complete=1"
                  f"&_fsrp=1&rt=nc&_pgn={page}"
                  f"&LH_ItemCondition=1000|1500|2000|2500|3000"
                  f"&_sop=13"
                  f"&LH_PrefLoc=3")
            
            headers = {
                "User-Agent": random.choice(USER_AGENTS)
            }
            
            try:
                response = requests.get(url, headers=headers, proxies=proxies, verify=False)
                if response.status_code != 200:
                    print(f"Failed to fetch page {page}, status code: {response.status_code}")
                    time.sleep(5)  # Wait for 5 seconds before retrying
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='s-item__wrapper')
                if not listings:
                    print("No more listings found")
                    break
                
                items_found_on_page = False
                
                for listing in listings:
                    try:
                        info_div = listing.find('div', class_='s-item__info')
                        if not info_div:
                            continue

                        title_elem = info_div.find('div', class_='s-item__title')
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        if title.lower() == 'shop on ebay':
                            continue
                            
                        print(f"Processing title: {title}")
                            
                        if not ('lego' in title.lower() and self.validate_title_number(title, set_number)):
                            print(f"Skipping - invalid title format: {title}")
                            continue
                            
                        url_elem = listing.find('a', class_='s-item__link')
                        if not url_elem:
                            continue
                        item_url = url_elem.get('href', '')
                            
                        price_elem = info_div.find('span', class_='s-item__price')
                        if not price_elem:
                            continue
                            
                        price_text = price_elem.text.strip()
                        if 'bis' in price_text.lower() or price_text.count('EUR') > 1:
                            print(f"Skipping - price range: {price_text}")
                            continue
                            
                        price = self.extract_number_from_price(price_text)
                        if price is None:
                            print(f"Skipping - invalid price: {price_text}")
                            continue
                            
                        print(f"Found valid price: {price}")
                            
                        sold_date = None
                        # Attempt to find the sold date in different elements
                        sold_elem = info_div.find('span', class_='POSITIVE')
                        if not sold_elem:
                            sold_elem = info_div.find('span', class_='s-item__ended-date')
                        
                        if sold_elem:
                            sold_text = sold_elem.text.strip()
                            print(f"Found sold text: {sold_text}")
                            
                            date_match = re.search(r'(\d{1,2})\.\s*([A-Za-zä]{3,})', sold_text)
                            if date_match:
                                day, month = date_match.groups()
                                german_months = {
                                    'Jan': '01', 'Januar': '01',
                                    'Feb': '02', 'Februar': '02',
                                    'Mär': '03', 'März': '03',
                                    'Apr': '04', 'April': '04',
                                    'Mai': '05',
                                    'Jun': '06', 'Juni': '06',
                                    'Jul': '07', 'Juli': '07',
                                    'Aug': '08', 'August': '08',
                                    'Sep': '09', 'September': '09',
                                    'Okt': '10', 'Oktober': '10',
                                    'Nov': '11', 'November': '11',
                                    'Dez': '12', 'Dezember': '12'
                                }
                                
                                month_key = next((k for k in german_months.keys() if k in month), None)
                                if month_key:
                                    current_date = datetime.now()
                                    sale_date = datetime.strptime(f"{current_date.year}-{german_months[month_key]}-{day.zfill(2)}", "%Y-%m-%d")
                                    
                                    if sale_date > current_date:
                                        sale_date = sale_date.replace(year=current_date.year - 1)
                                    
                                    if sale_date < thirty_days_ago:
                                        print(f"Skipping - too old: {sale_date}")
                                        continue_scraping = False
                                        break
                                        
                                    sold_date = sale_date.strftime("%Y-%m-%d")
                                    print(f"Valid date found: {sold_date}")
                        
                        if not sold_date:
                            print("Skipping - no valid date found")
                            continue

                        if self.is_duplicate(title, price, sold_date):
                            print(f"Skipping duplicate: {title}")
                            continue

                        condition_elem = info_div.find('span', class_='SECONDARY_INFO')
                        condition = condition_elem.text.strip() if condition_elem else "N/A"
                        
                        shipping_elem = info_div.find('span', class_='s-item__shipping s-item__logisticsCost')
                        shipping_text = shipping_elem.text.strip() if shipping_elem else "N/A"
                        shipping = self.extract_shipping_cost(shipping_text)
                        if shipping is None:
                            continue
                        
                        total_price = price + shipping
                        print(f"Adding item: {title} - {price} - {shipping} - {total_price} - {sold_date}")
                        
                        items_list.append({
                            'Title': title,
                            'Price': price,
                            'Shipping': shipping,
                            'Total Price': total_price,
                            'Condition': condition,
                            'Date Sold': sold_date,
                            'URL': item_url
                        })
                        items_found_on_page = True
                        
                    except AttributeError as e:
                        print(f"Error parsing item: {e}")
                        continue
                
                if not items_found_on_page or not continue_scraping:
                    break
                    
                page += 1
                time.sleep(2)  # Add a delay between requests to avoid being blocked
                        
            except requests.RequestException as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        if not items_list:
            print("No items found in the last 30 days!")
            return None, None
            
        df = pd.DataFrame(items_list)
        df = df.drop_duplicates(subset=['Title', 'Price', 'Date Sold'])
        
        df['Date Sold'] = pd.to_datetime(df['Date Sold'])
        df = df.sort_values('Date Sold', ascending=False)
        
        latest_date = df['Date Sold'].iloc[0].strftime('%Y%m%d')
        earliest_date = df['Date Sold'].iloc[-1].strftime('%Y%m%d')
        
        filename = f"ebay_LEGO_{set_number}_{earliest_date}_to_{latest_date}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        df['Date Sold'] = df['Date Sold'].dt.strftime('%Y-%m-%d')
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        return df, filepath

def main():
    scraper = EbayScraper()
    
    try:
        set_number = input("Enter the LEGO set number (e.g., 40632): ")
        print(f"\nStarting search for LEGO {set_number} on eBay.de (last 30 days)...")
        results, saved_file = scraper.fetch_ebay_sold_items(set_number)
        
        if results is not None:
            print(f"\nResults saved to {saved_file}")
            print("\nMost recent sales:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_rows', 10)
            print(results[['Title', 'Price', 'Shipping', 'Total Price', 'Condition', 'Date Sold', 'URL']].head(10))
            print(f"\nTotal items found: {len(results)}")
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()