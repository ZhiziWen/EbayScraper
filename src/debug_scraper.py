import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    """Setup and return a Chrome webdriver instance."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--lang=de-DE')  # Set language to German
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def fetch_ebay_items(set_number):
    """Fetch and print source data for 5 items from eBay."""
    driver = setup_driver()
    url = f'https://www.ebay.de/sch/i.html?_nkw=LEGO+{set_number}&_sop=12&LH_Complete=1&LH_Sold=1&_pgn=1'
    print(f"Fetching URL: {url}")
    
    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Wait for search results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.srp-results"))
        )
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.select('li.s-item')
        
        if not items:
            print("No items found on this page")
            return
        
        print(f"Found {len(items)} items on the page")
        
        # Print source data for the first 5 items
        for idx, item in enumerate(items[:5], 1):
            print(f"\nItem {idx}:")
            print(item.prettify())
            print("\n---")
        
    except TimeoutException:
        print("Timeout while waiting for page to load")
    except Exception as e:
        print(f"Error fetching items: {str(e)}")
    finally:
        driver.quit()


def main():
    """Main function to run the eBay item fetcher for debugging."""
    set_number = input("Enter the LEGO set number for debugging (e.g., 40632): ").strip()
    if not set_number.isdigit():
        print("Invalid set number")
        return
    
    fetch_ebay_items(set_number)


if __name__ == "__main__":
    main() 