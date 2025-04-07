import pandas as pd
import sys

# Path to the Excel file
excel_file = "/Users/alakob/projects/gast-app-streamlit/datasets/SA_DSM_metadata_v§1.xlsx"

try:
    # Read the Excel file into a DataFrame
    print(f"Reading Excel file: {excel_file}")
    antibiotic = pd.read_excel(excel_file)
    
    # Show the first 10 rows
    print("\nFirst 10 rows of the DataFrame:")
    print(antibiotic.head(10))
    
    # Print some basic information about the DataFrame
    print("\nDataFrame info:")
    print(f"Number of rows: {len(antibiotic)}")
    print(f"Columns: {', '.join(antibiotic.columns)}")
    
except Exception as e:
    print(f"Error reading Excel file: {e}", file=sys.stderr)
