#!/usr/bin/env python3
"""
Fix the syntax error in the API file.

This script fixes the unmatched parenthesis in the API file.
"""
import sys
import re
import shutil
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-syntax"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_syntax_error():
    """Fix the unmatched parenthesis syntax error"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the file content
    with open(API_PATH, 'r') as f:
        content = f.readlines()
    
    # Find and fix the syntax error
    fixed_content = []
    for line in content:
        if 'logger.info("Closed AMR job repository"))' in line:
            # Remove the extra parenthesis
            fixed_line = line.replace('logger.info("Closed AMR job repository"))', 'logger.info("Closed AMR job repository")')
            fixed_content.append(fixed_line)
            print(f"Fixed syntax error: {line.strip()} -> {fixed_line.strip()}")
        else:
            fixed_content.append(line)
    
    # Write the fixed content back to the file
    with open(API_PATH, 'w') as f:
        f.writelines(fixed_content)
    
    print(f"Successfully fixed syntax error in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_syntax_error():
        print("\nSyntax error fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix syntax error. See error messages above.")
        sys.exit(1)
