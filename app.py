from flask import Flask, render_template, request, jsonify
from src.scraper import EbayScraper
import threading
import queue
import re
import pandas as pd

app = Flask(__name__)
scraper = EbayScraper()

# Queue to store results
results_queue = queue.Queue()

def validate_set_number(number):
    """Validate if the input is a valid LEGO set number"""
    return bool(re.match(r'^\d{4,6}$', number.strip()))

def scrape_set(set_number):
    """Scrape a single set and put results in queue"""
    try:
        print(f"Starting scrape for set {set_number}...")  # Debug print
        results, filepath = scraper.fetch_ebay_sold_items(set_number)
        
        if results is not None and not results.empty:
            print(f"Found {len(results)} results for set {set_number}")  # Debug print
            # Convert DataFrame to dict and handle date format
            results_dict = []
            for _, row in results.iterrows():
                item_dict = row.to_dict()
                # Ensure date format is consistent
                if pd.notnull(item_dict.get('Date Sold')):
                    item_dict['Date Sold'] = item_dict['Date Sold'].strftime('%Y-%m-%d') if hasattr(item_dict['Date Sold'], 'strftime') else str(item_dict['Date Sold'])
                results_dict.append(item_dict)
            
            results_queue.put({
                'set_number': set_number,
                'status': 'success',
                'data': results_dict,
                'filepath': filepath,
                'total_items': len(results)
            })
            print(f"Successfully queued results for set {set_number}")  # Debug print
        else:
            print(f"No results found for set {set_number}")  # Debug print
            results_queue.put({
                'set_number': set_number,
                'status': 'no_results',
                'data': None,
                'filepath': None,
                'total_items': 0
            })
    except Exception as e:
        print(f"Error scraping set {set_number}: {str(e)}")  # Debug print
        results_queue.put({
            'set_number': set_number,
            'status': 'error',
            'error_message': str(e),
            'data': None,
            'filepath': None,
            'total_items': 0
        })

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    set_numbers = request.form.get('set_numbers', '').split()
    print(f"Received request to scrape sets: {set_numbers}")  # Debug print
    
    # Validate input
    valid_numbers = []
    invalid_numbers = []
    for number in set_numbers:
        if validate_set_number(number):
            valid_numbers.append(number)
        else:
            invalid_numbers.append(number)
    
    if not valid_numbers:
        return jsonify({
            'status': 'error',
            'message': f'No valid set numbers provided. Invalid numbers: {", ".join(invalid_numbers)}'
        })

    # Clear the queue
    while not results_queue.empty():
        results_queue.get()

    # Start scraping threads
    threads = []
    for number in valid_numbers:
        thread = threading.Thread(target=scrape_set, args=(number,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    print(f"Returning results: {results}")  # Debug print

    return jsonify({
        'status': 'success',
        'results': results,
        'invalid_numbers': invalid_numbers
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
