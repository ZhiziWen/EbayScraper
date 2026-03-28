"""
LEGO Market Data Collector

This script focuses on fetching and saving raw data for each LEGO set.
Features:
- Reads inventory from Excel file
- Fetches current market data using scraper.py
- Filters for items from Deutschland and in "Brandneu" condition
- Saves individual CSV files for each set
- Creates a manifest file listing all generated CSVs
- Parallel scraping with multiple Chrome instances (configurable workers)
- Rate limiting to avoid eBay IP bans
"""

import os
import sys
import time
import random
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper import EbayScraper

# Maximum parallel Chrome instances. Keep this conservative to avoid eBay rate-limiting.
MAX_WORKERS = 3
# Random delay range (seconds) between starting each worker's next set.
# This staggers requests so eBay doesn't see simultaneous bursts from one IP.
DELAY_BETWEEN_SETS = (2, 5)


class MarketDataCollector:
    def __init__(self):
        """Initialize the Market Data Collector."""
        self.base_dir = os.getcwd()
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.inventory_dir = os.path.join(self.base_dir, 'Inventory')
        self.inventory_file = os.path.join(self.inventory_dir, 'Reselling Profit Calculator2.xlsx')

        # Create directories if they don't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.inventory_dir, exist_ok=True)

        print("Market Data Collector initialized\n")

    def read_inventory(self):
        """Read inventory from Excel file."""
        try:
            import pandas as pd
            if not os.path.exists(self.inventory_file):
                print(f"Inventory file not found: {self.inventory_file}")
                return None

            print(f"Reading inventory from {self.inventory_file}\n")
            df = pd.read_excel(self.inventory_file, sheet_name='Overview Total')

            # Clean data and extract set numbers
            df = df.dropna(how='all').dropna(axis=1, how='all')
            valid_data = df[df['Set'].apply(lambda x: str(x).replace('.0', '').isdigit())]

            if valid_data.empty:
                print("No valid set numbers found in inventory")
                return None

            set_numbers = valid_data['Set'].astype(str).str.replace('.0', '').tolist()
            print(f"Found {len(set_numbers)} sets in inventory\n")
            return set_numbers

        except Exception as e:
            print(f"Error reading inventory: {e}")
            return None

    def _fetch_single_set(self, scraper, set_number):
        """Fetch and save market data for a single set using the given scraper instance.
        Returns (set_number, filepath) or (set_number, None)."""
        try:
            # Random delay to stagger requests across workers
            delay = random.uniform(*DELAY_BETWEEN_SETS)
            time.sleep(delay)

            print(f"\nFetching data for set {set_number}")

            ebay_data = scraper.fetch_ebay_sold_items(set_number)
            if ebay_data is None or ebay_data.empty:
                print(f"No market data found for set {set_number}")
                return (set_number, None)

            # Filter for Deutschland location and Brandneu condition
            filtered_data = ebay_data[
                (ebay_data['Location'].str.contains('Deutschland', case=False, na=False)) &
                (ebay_data['Condition'].isin(['Brandneu', 'Brand New', 'New', 'Neu', 'Neu (Sonstige)']))
            ]

            if filtered_data.empty:
                print(f"No valid items found for set {set_number} after filtering")
                return (set_number, None)

            # Find the CSV file created by the scraper
            csv_files = [f for f in os.listdir(self.data_dir)
                         if f.startswith(f'Ebay_Lego_{set_number}_') and f.endswith('.csv')]
            if not csv_files:
                print(f"No CSV file found for set {set_number}")
                return (set_number, None)

            latest_file = max(csv_files)
            filepath = os.path.join(self.data_dir, latest_file)
            print(f"Using data file: {latest_file}")

            return (set_number, filepath)

        except Exception as e:
            print(f"Error processing set {set_number}: {e}")
            return (set_number, None)

    def _worker(self, set_numbers_chunk):
        """Worker function: one Chrome instance processes a list of sets sequentially."""
        scraper = EbayScraper()
        results = []
        try:
            for set_number in set_numbers_chunk:
                result = self._fetch_single_set(scraper, set_number)
                results.append(result)
        finally:
            scraper.close()
        return results

    def fetch_all_parallel(self, set_numbers, max_workers=MAX_WORKERS):
        """Fetch market data for all sets using parallel Chrome instances.

        Sets are divided into chunks, one chunk per worker. Each worker opens
        one Chrome instance and processes its chunk sequentially with random
        delays between sets. This limits the total number of concurrent
        connections to eBay and avoids triggering rate limits.
        """
        n = len(set_numbers)
        workers = min(max_workers, n)

        if workers <= 1:
            # Fall back to single-threaded mode
            scraper = EbayScraper()
            data_files = []
            try:
                for sn in set_numbers:
                    _, path = self._fetch_single_set(scraper, sn)
                    if path:
                        data_files.append(path)
            finally:
                scraper.close()
            return data_files

        # Split sets into roughly equal chunks for each worker
        chunks = [[] for _ in range(workers)]
        for i, sn in enumerate(set_numbers):
            chunks[i % workers].append(sn)

        print(f"Starting {workers} parallel workers for {n} sets "
              f"({', '.join(str(len(c)) for c in chunks)} sets per worker)")
        print(f"Random delay between sets: {DELAY_BETWEEN_SETS[0]}-{DELAY_BETWEEN_SETS[1]}s\n")

        data_files = []
        failed_sets = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._worker, chunk): i
                       for i, chunk in enumerate(chunks)}

            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    results = future.result()
                    for set_number, path in results:
                        if path:
                            data_files.append(path)
                        else:
                            failed_sets.append(set_number)
                except Exception as e:
                    print(f"Worker {worker_id} failed: {e}")

        if failed_sets:
            print(f"\nNo data for {len(failed_sets)} sets: {', '.join(failed_sets)}")
        print(f"Successfully collected data for {len(data_files)}/{n} sets")

        return data_files

    def create_manifest(self, data_files):
        """Create a manifest file listing all generated CSVs."""
        try:
            if not data_files:
                print("No data files to include in manifest")
                return None

            manifest = {
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'files': data_files
            }

            filename = f'market_data_manifest_{manifest["timestamp"]}.json'
            filepath = os.path.join(self.data_dir, filename)

            with open(filepath, 'w') as f:
                json.dump(manifest, f, indent=2)

            print(f"\nCreated manifest file: {filename}")
            return filepath

        except Exception as e:
            print(f"Error creating manifest: {e}")
            return None


def main():
    """Main function to run the market data collection."""
    print("Starting LEGO Market Data Collection...")
    collector = MarketDataCollector()

    # Check if specific set numbers were provided as command line arguments
    if len(sys.argv) > 1:
        set_numbers = sys.argv[1:]
        print(f"Processing specified sets: {', '.join(set_numbers)}\n")
    else:
        set_numbers = collector.read_inventory()
        if not set_numbers:
            print("No sets to process. Please check your inventory file or provide set numbers as arguments.")
            return

    # Fetch all sets (parallel when > 1 set)
    data_files = collector.fetch_all_parallel(set_numbers)

    # Create manifest file
    collector.create_manifest(data_files)

    print("\nMarket data collection completed!")


if __name__ == "__main__":
    main()
