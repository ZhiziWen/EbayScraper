from src.scraper import EbayScraper

# Example LEGO set number for testing
example_set_number = '40632'

# Initialize the scraper
scraper = EbayScraper()

# Fetch sold items for the example set number
results, saved_file = scraper.fetch_ebay_sold_items([example_set_number])

# Print the results
if results is not None:
    print("\nTest Results:")
    print(results[['Title', 'Item Price', 'Shipping Fee', 'Total Price', 'Currency', 'Location', 'End Time', 'URL']])
else:
    print("\nNo results found for the test LEGO set number.") 