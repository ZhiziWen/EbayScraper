import os
import subprocess
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def create_directory_structure():
    # Create project directories
    directories = ['src', 'data']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        
def create_environment_file():
    environment_content = """name: ebay-scraper
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.9
  - requests
  - beautifulsoup4
  - pandas
  - pip"""
    
    with open('environment.yml', 'w') as f:
        f.write(environment_content)

def create_scraper_file():
    scraper_content = """import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

class EbayScraper:
    def __init__(self):
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
    def fetch_ebay_sold_items(self, keyword, max_pages=1):
        items_list = []
        
        for page in range(1, max_pages + 1):
            # Format the URL for sold items
            url = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={keyword}&_sacat=0&LH_TitleDesc=0&_fsrp=1&rt=nc&LH_Sold=1&LH_Complete=1&_pgn={page}"
            
            # Send request with headers to avoid being blocked
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all item listings
            listings = soup.find_all('div', class_='s-item__info')
            
            for listing in listings:
                try:
                    # Extract title
                    title = listing.find('div', class_='s-item__title').text.strip()
                    
                    # Extract price
                    price_elem = listing.find('span', class_='s-item__price')
                    price = price_elem.text.strip() if price_elem else "N/A"
                    
                    # Extract date sold
                    date_elem = listing.find('span', class_='s-item__ended-date')
                    date_sold = date_elem.text.strip() if date_elem else "N/A"
                    
                    # Add to items list
                    items_list.append({
                        'Title': title,
                        'Price': price,
                        'Date Sold': date_sold
                    })
                    
                except AttributeError as e:
                    continue
        
        # Convert to DataFrame
        df = pd.DataFrame(items_list)
        
        # Save to CSV
        filename = f"ebay_sold_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False)
        
        return df, filepath

if __name__ == "__main__":
    scraper = EbayScraper()
    keyword = input("Enter the item you want to search for: ")
    number_of_pages = int(input("Enter the number of pages to scrape (1-100): "))
    
    results, saved_file = scraper.fetch_ebay_sold_items(keyword, number_of_pages)
    
    print(f"\nResults saved to {saved_file}")
    print("\nFirst few results:")
    print(results.head())
"""
    
    with open('src/scraper.py', 'w') as f:
        f.write(scraper_content)

def create_readme():
    readme_content = ""

    