#!/usr/bin/env python3
"""
Script to create and populate the amr_antibiotic table from Excel data.
"""
import pandas as pd
import os
from pathlib import Path

def create_amr_antibiotic_sql():
    """Read Excel file and generate SQL statements for table creation and data insertion."""
    # Read the Excel file
    excel_path = Path(__file__).parent.parent / 'datasets' / 'dsm.xlsx'
    df = pd.read_excel(excel_path)
    
    # Drop the last column
    df = df.iloc[:, :-1]
    
    # Generate CREATE TABLE statement
    columns = []
    for col in df.columns:
        # Determine column type based on data
        if df[col].dtype == 'float64' or df[col].dtype == 'int64':
            col_type = 'NUMERIC'
        else:
            col_type = 'TEXT'
        columns.append(f'    "{col}" {col_type}')
    
    create_table = f"""CREATE TABLE IF NOT EXISTS amr_antibiotic (
    id SERIAL PRIMARY KEY,
{','.join(columns)}
);"""
    
    # Generate INSERT statements
    insert_rows = []
    for _, row in df.iterrows():
        values = []
        for val in row:
            if pd.isna(val):
                values.append('NULL')
            elif isinstance(val, (int, float)):
                values.append(str(val))
            else:
                values.append(f"'{str(val)}'")
        insert_rows.append(f"({', '.join(values)})")
    
    insert_stmt = f"""INSERT INTO amr_antibiotic ({', '.join(f'"{col}"' for col in df.columns)})
VALUES
{','.join(insert_rows)};"""
    
    # Write SQL to file in the correct location
    sql_path = Path(__file__).parent.parent / 'docker' / 'postgres' / 'init' / 'init-amr-antibiotic.sql'
    sql_path.parent.mkdir(exist_ok=True)
    
    with open(sql_path, 'w') as f:
        f.write(create_table)
        f.write('\n\n-- Delete existing data\n')
        f.write('DELETE FROM amr_antibiotic;\n\n')
        f.write('-- Insert new data\n')
        f.write(insert_stmt)
    
    print(f"SQL file generated at: {sql_path}")

if __name__ == '__main__':
    create_amr_antibiotic_sql() 