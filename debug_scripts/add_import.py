#!/usr/bin/env python3
"""
Add missing import statement for sqlite3 to the API file.

This script adds the missing import statement for the sqlite3 module.
"""
import sys
import shutil
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-import"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def add_sqlite3_import():
    """Add sqlite3 import to the API file"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        lines = f.readlines()
    
    # Find where imports end
    import_end_index = 0
    for i, line in enumerate(lines):
        if "import" in line and not line.strip().startswith("#"):
            import_end_index = i
    
    # Check if sqlite3 is already imported
    sqlite3_imported = any("import sqlite3" in line for line in lines)
    if not sqlite3_imported:
        # Add sqlite3 import after the last import
        lines.insert(import_end_index + 1, "import sqlite3\n")
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.writelines(lines)
    
    print(f"Successfully added sqlite3 import to {API_PATH}")
    return True

if __name__ == "__main__":
    if add_sqlite3_import():
        print("\nSQLite3 import added successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to add sqlite3 import. See error messages above.")
        sys.exit(1)
