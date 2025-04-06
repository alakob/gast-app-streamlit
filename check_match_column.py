import pandas as pd
import numpy as np

# Path to the Excel file
excel_file = "/Users/alakob/projects/gast-app-streamlit/datasets/SA_DSM_metadata_v§1.xlsx"

try:
    # Read the Excel file into a DataFrame
    antibiotic = pd.read_excel(excel_file)
    
    # Check the 'Match' column
    match_column = antibiotic['Match']
    
    # Count non-zero values
    non_zero_count = (match_column != 0).sum()
    
    # Count NaN values
    nan_count = match_column.isna().sum()
    
    # Get unique values
    unique_values = match_column.unique()
    
    print(f"Match column statistics:")
    print(f"Total rows: {len(match_column)}")
    print(f"Non-zero values: {non_zero_count}")
    print(f"NaN values: {nan_count}")
    print(f"Unique values: {unique_values}")
    
    # Show rows with non-zero Match values if any exist
    if non_zero_count > 0:
        print("\nRows with non-zero Match values:")
        non_zero_rows = antibiotic[match_column != 0]
        print(non_zero_rows)
    
except Exception as e:
    print(f"Error: {e}")
