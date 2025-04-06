import pandas as pd
import pickle

# Path to the Excel file
excel_file = "/Users/alakob/projects/gast-app-streamlit/datasets/SA_DSM_metadata_v§1.xlsx"

try:
    # Read the Excel file into a DataFrame
    print(f"Reading Excel file: {excel_file}")
    antibiotic_df = pd.read_excel(excel_file)
    
    # Show original DataFrame shape
    print(f"Original DataFrame shape: {antibiotic_df.shape}")
    print(f"Original columns: {antibiotic_df.columns.tolist()}")
    
    # Drop the 'Match' column
    antibiotic_df = antibiotic_df.drop('Match', axis=1)
    
    # Show the modified DataFrame shape
    print(f"Modified DataFrame shape: {antibiotic_df.shape}")
    print(f"Remaining columns: {antibiotic_df.columns.tolist()}")
    
    # Show the first few rows of the modified DataFrame
    print("\nFirst 5 rows of the modified DataFrame:")
    print(antibiotic_df.head())
    
    # Save the DataFrame to a pickle file for later use
    pickle_file = "/Users/alakob/projects/gast-app-streamlit/datasets/antibiotic_df.pkl"
    with open(pickle_file, 'wb') as f:
        pickle.dump(antibiotic_df, f)
    print(f"\nDataFrame saved to: {pickle_file}")
    
    # Also save as CSV for easy viewing
    csv_file = "/Users/alakob/projects/gast-app-streamlit/datasets/antibiotic_df.csv"
    antibiotic_df.to_csv(csv_file, index=False)
    print(f"DataFrame also saved as CSV: {csv_file}")
    
except Exception as e:
    print(f"Error: {e}")
