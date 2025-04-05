#!/usr/bin/env python3
"""
Add missing result_file column to the amr_jobs table.

This script adds the missing result_file and aggregated_result_file columns to 
the amr_jobs table that are needed by the predict_task function.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"

def ensure_result_columns():
    """Ensure result_file and aggregated_result_file columns exist in amr_jobs table"""
    print(f"Working with database at: {DB_PATH}")
    
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check the current schema
        cursor.execute("PRAGMA table_info(amr_jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Current amr_jobs columns: {columns}")
        
        # Add result_file column if it doesn't exist
        if "result_file" not in columns:
            print("Adding missing result_file column...")
            cursor.execute("ALTER TABLE amr_jobs ADD COLUMN result_file TEXT")
            print("result_file column added successfully")
        else:
            print("result_file column already exists")
        
        # Add aggregated_result_file column if it doesn't exist
        if "aggregated_result_file" not in columns:
            print("Adding missing aggregated_result_file column...")
            cursor.execute("ALTER TABLE amr_jobs ADD COLUMN aggregated_result_file TEXT")
            print("aggregated_result_file column added successfully")
        else:
            print("aggregated_result_file column already exists")
        
        # Commit the changes
        conn.commit()
        
        # Verify the columns were added
        cursor.execute("PRAGMA table_info(amr_jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Updated amr_jobs columns: {columns}")
        
        print("\nSchema updated successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        # Close the connection
        conn.close()

if __name__ == "__main__":
    if ensure_result_columns():
        print("\nDatabase schema updated successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to update database schema. See error messages above.")
        sys.exit(1)
