import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def fetch_ebay_sold_items(keyword, max_pages=1):
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
    return df

# Example usage
if __name__ == "__main__":
    keyword = input("Enter the item you want to search for: ")
    number_of_pages = int(input("Enter the number of pages to scrape (1-100): "))
    
    results = fetch_ebay_sold_items(keyword, number_of_pages)
    
    # Save to CSV
    filename = f"ebay_sold_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results.to_csv(filename, index=False)
    
    print(f"\nResults saved to {filename}")
    print("\nFirst few results:")
    print(results.head())