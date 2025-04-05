#!/usr/bin/env python3
"""
Fix indentation error in the API file.

This script corrects the indentation of the import statements in the download endpoint.
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
    backup_path = f"{file_path}.backup-indentation"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_indentation():
    """Fix indentation error in the API file"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the file line by line
    with open(API_PATH, 'r') as f:
        lines = f.readlines()
    
    # Find the problematic section and fix indentation
    fixed_lines = []
    in_download_result = False
    import_section_fixed = False
    
    for line in lines:
        # Check if we're in the download_result function
        if '@app.get("/jobs/{job_id}/download")' in line:
            in_download_result = True
            fixed_lines.append(line)
        # Check for the import statements and fix their indentation
        elif in_download_result and "import" in line and line.startswith("    import") and not import_section_fixed:
            # Remove the indentation for import statements
            fixed_line = line.lstrip()
            fixed_lines.append(fixed_line)
            import_section_fixed = True
        elif in_download_result and "import" in line and line.startswith("    import") and import_section_fixed:
            # Remove the indentation for any subsequent import statements
            fixed_line = line.lstrip()
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    # Write the fixed content back to the file
    with open(API_PATH, 'w') as f:
        f.writelines(fixed_lines)
    
    print(f"Successfully fixed indentation in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_indentation():
        print("\nIndentation fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix indentation. See error messages above.")
        sys.exit(1)
