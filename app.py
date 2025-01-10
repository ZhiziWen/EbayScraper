from flask import Flask, render_template, request, redirect, url_for
from src.scraper import EbayScraper

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        set_numbers = request.form.get('set_numbers', '')
        set_numbers = [num.strip() for num in set_numbers.split(',') if num.strip().isdigit()]
        
        if not set_numbers:
            return render_template('index.html', error='No valid set numbers provided')
        
        scraper = EbayScraper()
        results, saved_file = scraper.fetch_ebay_sold_items(set_numbers)
        
        if results is not None:
            return render_template('results.html', results=results.to_dict(orient='records'))
        else:
            return render_template('index.html', error='No results found')
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
