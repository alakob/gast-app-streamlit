#!/usr/bin/env python3
"""
Fix the parameter names in the progress tracker's update method.

This script updates the DirectProgressTracker class to accept 'increment' 
instead of 'step_increment' to match the expected interface.
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
    backup_path = f"{file_path}.backup-tracker-params"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_progress_tracker_params():
    """Fix the progress tracker parameter names"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the DirectProgressTracker.update method definition
    update_pattern = re.compile(
        r'def update\(self, step_increment=1, status=None\):.*?return self\.progress',
        re.DOTALL
    )
    
    match = update_pattern.search(content)
    if not match:
        print("Error: Could not find DirectProgressTracker.update method in API file")
        return False
    
    old_update = match.group(0)
    
    # Create the updated update method with corrected parameter names
    new_update = '''def update(self, increment=1, status=None):
                """
                Update progress tracker.
                
                Args:
                    increment: Number of steps to increment
                    status: Optional status message
                """
                self.current_step += increment
                self.progress = min(100.0, (self.current_step / self.total_steps) * 100)
                # Only update status in database if status is provided
                if status:
                    update_status("Running", progress=self.progress)
                return self.progress'''
    
    # Replace the old update method with the new one
    updated_content = content.replace(old_update, new_update)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully fixed progress tracker parameter names in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_progress_tracker_params():
        print("\nProgress tracker parameters fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix progress tracker parameters. See error messages above.")
        sys.exit(1)
