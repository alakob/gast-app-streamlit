#!/usr/bin/env python3
"""
Fix indentation errors in the database_manager.py file.

This script reads the entire file, fixes the indentation issues in the save_job method,
and writes the corrected content back to the file.
"""
import os
import sys
import re
import shutil
import time
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_save_job_indentation():
    """Fix the indentation in the save_job method"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: File not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    create_backup(DB_MANAGER_PATH)
    
    # Read the entire file
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Identify the save_job method using regex
    save_job_pattern = re.compile(
        r'def save_job\(self.*?return self\.get_job\(job_id\)',
        re.DOTALL
    )
    
    # Find the save_job method
    match = save_job_pattern.search(content)
    if not match:
        print("Error: Could not find save_job method in the file")
        return False
    
    # Extract the method
    old_method = match.group(0)
    
    # Create the corrected version with proper indentation
    corrected_method = """def save_job(self, job_id: str, status: str = "Submitted", progress: float = 0.0, 
             additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    \"\"\"
    Save a new job to the database.
    
    Args:
        job_id: Unique job ID
        status: Initial job status
        progress: Initial progress percentage
        additional_info: Additional job parameters to store
        
    Returns:
        Job data dictionary
    \"\"\"
    now = datetime.now().isoformat()
    
    with self.get_connection() as conn:
        cursor = conn.cursor()
        
        # Create the job record
        # Extract job name from additional_info if available
        job_name = "AMR Analysis Job"
        if additional_info and "input_file" in additional_info:
            job_name = f"Analysis of {additional_info['input_file']}"
            
        cursor.execute(
            \"\"\"
            INSERT INTO amr_jobs (
                id, status, progress, start_time, created_at, job_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            \"\"\",
            (job_id, status, progress, now, now, job_name)
        )
        
        # Add additional parameters if provided
        if additional_info:
            self.add_job_parameters(job_id, additional_info)
        
        conn.commit()
        
        # Return the job data
        return self.get_job(job_id)"""
    
    # Replace the old method with the corrected one
    new_content = content.replace(old_method, corrected_method)
    
    # Write the corrected content back to the file
    with open(DB_MANAGER_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully fixed indentation in {DB_MANAGER_PATH}")
    return True

if __name__ == "__main__":
    if fix_save_job_indentation():
        print("\nIndentation fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix indentation. See error messages above.")
        sys.exit(1)
