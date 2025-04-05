#!/usr/bin/env python3
"""
Make the progress tracker more flexible by accepting **kwargs.

This script updates the DirectProgressTracker class to accept any keyword
arguments, making it more robust against interface changes.
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
    backup_path = f"{file_path}.backup-kwargs"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_progress_tracker_kwargs():
    """Update the progress tracker to accept **kwargs"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the DirectProgressTracker class
    tracker_class_pattern = re.compile(
        r'class DirectProgressTracker:.*?def set_error\(self, error_message\):.*?return self\.progress',
        re.DOTALL
    )
    
    match = tracker_class_pattern.search(content)
    if not match:
        print("Error: Could not find complete DirectProgressTracker class in API file")
        return False
    
    old_tracker_class = match.group(0)
    
    # Create an updated version of the tracker class with **kwargs support
    new_tracker_class = '''class DirectProgressTracker:
            def __init__(self, job_id, total_steps=100):
                self.job_id = job_id
                self.total_steps = total_steps
                self.current_step = 0
                self.progress = 0.0
            
            def update(self, increment=1, status=None, **kwargs):
                """
                Update progress tracker.
                
                Args:
                    increment: Number of steps to increment
                    status: Optional status message
                    **kwargs: Additional keyword arguments (ignored)
                """
                self.current_step += increment
                self.progress = min(100.0, (self.current_step / self.total_steps) * 100)
                # Only update status in database if status is provided
                if status:
                    update_status("Running", progress=self.progress)
                return self.progress
            
            def set_error(self, error_message, **kwargs):
                """
                Set error in progress tracker.
                
                Args:
                    error_message: Error message
                    **kwargs: Additional keyword arguments (ignored)
                """
                update_status("Error", error=error_message)
                return self.progress'''
    
    # Replace the old tracker class with the new one
    updated_content = content.replace(old_tracker_class, new_tracker_class)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully updated progress tracker to accept **kwargs in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_progress_tracker_kwargs():
        print("\nProgress tracker updated successfully to accept any parameters!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to update progress tracker. See error messages above.")
        sys.exit(1)
