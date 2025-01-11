from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from src.scraper import EbayScraper

app = Flask(__name__)

# Configure upload folder for CSV files
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        set_numbers = request.form.get('set_numbers', '')
        set_numbers = [num.strip() for num in set_numbers.split(',') if num.strip().isdigit()]
        
        if not set_numbers:
            return render_template('index.html', error='No valid set numbers provided')
        
        try:
            scraper = EbayScraper()
            results, saved_files = scraper.fetch_ebay_sold_items(set_numbers)
            
            if results is not None:
                # Convert results dictionary to a format suitable for the template
                formatted_results = {}
                for set_num, df in results.items():
                    formatted_results[set_num] = {
                        'data': df.to_dict(orient='records'),
                        'file_name': os.path.basename(next(f for f in saved_files if f'_{set_num}_' in f)),
                        'count': len(df),
                        'avg_price': df['Total Price'].mean(),
                        'min_price': df['Total Price'].min(),
                        'max_price': df['Total Price'].max(),
                        'date_range': f"{df['End Time'].min():%Y-%m-%d} to {df['End Time'].max():%Y-%m-%d}"
                    }
                return render_template('results.html', results=formatted_results, set_numbers=set_numbers)
            else:
                return render_template('index.html', error='No results found')
                
        except Exception as e:
            return render_template('index.html', error=f'Error: {str(e)}')
            
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    """Download a CSV file."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Run without debug mode
    app.run(host='127.0.0.1', port=5000)
