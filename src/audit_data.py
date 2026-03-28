"""Data quality audit: scan all latest scraped CSVs for suspicious entries."""
import os, glob, re
import pandas as pd
from collections import Counter
from datetime import datetime

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Get latest CSV per set (using digits-only set number)
latest = {}
for f in glob.glob(os.path.join(data_dir, 'Ebay_Lego_*.csv')):
    m = re.match(r'Ebay_Lego_(\d+)_', os.path.basename(f))  # digits only
    if m:
        s = m.group(1)
        if s not in latest or os.path.getctime(f) > os.path.getctime(latest[s]):
            latest[s] = f

NEW_CONDITIONS = {'Brandneu', 'Brand New', 'New', 'Neu', 'Neu (Sonstige)'}
issues = []

for set_num, fpath in sorted(latest.items()):
    try:
        df = pd.read_csv(fpath)
        df_new = df[
            df['Condition'].isin(NEW_CONDITIONS) &
            df['Location'].str.contains('Deutschland', na=False)
        ]
        if df_new.empty:
            continue

        for _, row in df_new.iterrows():
            title = str(row['Title'])
            item_price = float(row['Item Price'])
            shipping = float(row['Shipping Fee'])
            flags = []

            # 1. Part/minifigure by keyword (not caught by "aus SET" filter)
            if re.search(r'\b(minifigur|minifig|einzeln|ersatzteil|bauteil)', title, re.I):
                flags.append('PART_LISTING')

            # 2. Incomplete or damaged sets
            if re.search(r'\b(unvollst|ohne\s+anleitung|ohne\s+ba\b|fehlt|fehlen|defekt|beschädigt|basteln|ohne\s+box)', title, re.I):
                flags.append('INCOMPLETE')

            # 3. Bundle: contains a DIFFERENT 5-digit set number
            other_5digit = set(re.findall(r'\b\d{5}\b', title)) - {set_num}
            if other_5digit:
                flags.append(f'BUNDLE:{other_5digit}')

            # 4. Suspiciously low item price
            if item_price < 5:
                flags.append(f'LOW_PRICE:€{item_price}')

            # 5. Unrealistic shipping for Germany
            if shipping > 30:
                flags.append(f'HIGH_SHIPPING:€{shipping}')

            if flags:
                issues.append({
                    'Set': set_num,
                    'Flags': ' | '.join(flags),
                    'Item': item_price,
                    'Ship': shipping,
                    'Title': title[:90]
                })

    except Exception as e:
        print(f'Error reading {os.path.basename(fpath)}: {e}')

print(f'Scanned {len(latest)} sets. Found {len(issues)} flagged items.\n')

all_flags = []
for i in issues:
    all_flags += [f.split(':')[0] for f in i['Flags'].split(' | ')]
for k, v in Counter(all_flags).most_common():
    print(f'  {k}: {v} items')

print()
for i in sorted(issues, key=lambda x: x['Flags']):
    print(f"Set {i['Set']}  item=€{i['Item']}  ship=€{i['Ship']}  [{i['Flags']}]")
    print(f"  {i['Title']}")
