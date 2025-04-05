#!/usr/bin/env python3
"""
Fix the custom progress tracker implementation in the predict_task function.

This script updates the DirectProgressTracker class to match the expected interface.
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
    backup_path = f"{file_path}.backup-tracker"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_progress_tracker():
    """Fix the progress tracker implementation"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the DirectProgressTracker class definition
    tracker_pattern = re.compile(
        r'class DirectProgressTracker:.*?def update\(self, step_increment=1\):.*?return self\.progress',
        re.DOTALL
    )
    
    match = tracker_pattern.search(content)
    if not match:
        print("Error: Could not find DirectProgressTracker class in API file")
        return False
    
    old_tracker = match.group(0)
    
    # Create the updated tracker class that matches the expected interface
    new_tracker = '''class DirectProgressTracker:
            def __init__(self, job_id, total_steps=100):
                self.job_id = job_id
                self.total_steps = total_steps
                self.current_step = 0
                self.progress = 0.0
            
            def update(self, step_increment=1, status=None):
                """
                Update progress tracker.
                
                Args:
                    step_increment: Number of steps to increment
                    status: Optional status message
                """
                self.current_step += step_increment
                self.progress = min(100.0, (self.current_step / self.total_steps) * 100)
                # Only update status in database if status is provided
                if status:
                    update_status("Running", progress=self.progress)
                return self.progress
            
            def set_error(self, error_message):
                """
                Set error in progress tracker.
                
                Args:
                    error_message: Error message
                """
                update_status("Error", error=error_message)
                return self.progress'''
    
    # Replace the old tracker with the new one
    updated_content = content.replace(old_tracker, new_tracker)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully fixed progress tracker implementation in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_progress_tracker():
        print("\nProgress tracker fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix progress tracker. See error messages above.")
        sys.exit(1)
