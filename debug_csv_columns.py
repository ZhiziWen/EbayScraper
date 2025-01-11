import pandas as pd

# Path to the CSV file
csv_file_path = 'data/Ebay_Lego_21044_20241214_20250111_143403.csv'

# Read the CSV file into a DataFrame
try:
    df = pd.read_csv(csv_file_path)
    print("Columns in the CSV file:")
    print(df.columns.tolist())
except FileNotFoundError:
    print(f"File not found: {csv_file_path}")
except Exception as e:
    print(f"An error occurred: {e}") 