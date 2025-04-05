#!/usr/bin/env python3
"""
Fix indentation error in the repository.py file.

This script fixes the indentation issue in the get_job method that's causing a syntax error.
"""
import sys
import re
import shutil
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
REPO_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-indentation"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_indentation():
    """Fix indentation error in the repository.py file"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Make a backup
    backup_file(REPO_PATH)
    
    # Read the file lines
    with open(REPO_PATH, 'r') as f:
        lines = f.readlines()
    
    # Identify and fix the indentation issue
    in_get_job = False
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if we've encountered the get_job method
        if "def get_job(self, job_id: str)" in line:
            in_get_job = True
            fixed_lines.append(line)
            continue
        
        # If we're in the get_job method, check for indentation issues
        if in_get_job:
            # If line contains a triple-quoted docstring start
            if '"""' in line and not line.strip().startswith('"""'):
                fixed_lines.append(line)
            elif line.strip().startswith('"""'):
                # This is where the issue is - the docstring needs proper indentation
                indentation = "    "  # Standard 4-space indentation
                fixed_lines.append(f"{indentation}{line}")
            else:
                fixed_lines.append(line)
                
                # If we see 'return', we're likely at the end of the method
                if "return" in line:
                    in_get_job = False
        else:
            fixed_lines.append(line)
    
    # Write the fixed content back to the file
    with open(REPO_PATH, 'w') as f:
        f.writelines(fixed_lines)
    
    print(f"Successfully fixed indentation in {REPO_PATH}")
    return True

if __name__ == "__main__":
    if fix_indentation():
        print("\nIndentation fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix indentation. See error messages above.")
        sys.exit(1)
