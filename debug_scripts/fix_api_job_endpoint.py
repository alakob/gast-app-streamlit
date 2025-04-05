#!/usr/bin/env python3
"""
Targeted fix for the job status endpoint in the API file.

This script specifically fixes the get_job_status function at lines 652-667
to properly handle closed database connections.
"""
import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_job_status_endpoint():
    """Fix the job status endpoint with robust error handling"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    backup_file(API_PATH)
    
    # Read the file content
    with open(API_PATH, 'r') as f:
        lines = f.readlines()
    
    # Find the specific get_job_status function lines
    # Based on the file outline, it's around lines 652-667
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(lines):
        # Look for the function definition
        if "async def get_job_status" in line:
            # Go back to find the decorator
            j = i
            while j >= 0 and "@app.get" not in lines[j]:
                j -= 1
            
            if j >= 0 and "@app.get" in lines[j]:
                start_line = j
                
                # Find the end of the function
                k = i + 1
                indentation = len(line) - len(line.lstrip())
                function_indent = ' ' * indentation
                
                while k < len(lines):
                    # Check if we've exited the function block 
                    # Either by hitting another function/decorator or a line with less indentation
                    next_line = lines[k]
                    if next_line.strip() and not next_line.startswith(function_indent):
                        end_line = k
                        break
                    k += 1
                
                if end_line == -1:  # If we reached end of file
                    end_line = len(lines)
                
                break
    
    if start_line == -1 or end_line == -1:
        print("Error: Could not locate get_job_status function in API file")
        return False
    
    print(f"Found get_job_status function from line {start_line+1} to {end_line}")
    
    # Create the fixed function with proper error handling
    fixed_function = '''@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str = Path(..., description="Job ID to check")):
    """
    Get the status of a job.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        Job response with current status
    """
    try:
        job = job_repository.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return job
    except sqlite3.ProgrammingError as e:
        # Handle "Cannot operate on a closed database" error
        logger.error(f"Database error when retrieving job {job_id}: {str(e)}")
        
        # Try with a fresh database connection
        try:
            # Create a fresh connection for this request
            from ..core.database_manager import AMRDatabaseManager
            fresh_db_manager = AMRDatabaseManager()
            job = fresh_db_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            return job
        except Exception as inner_e:
            logger.error(f"Error with fresh connection: {str(inner_e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")

'''
    
    # Replace the function in the file
    new_lines = lines[:start_line] + [fixed_function] + lines[end_line:]
    
    # Add sqlite3 import if not present
    has_sqlite3_import = False
    for line in new_lines:
        if "import sqlite3" in line:
            has_sqlite3_import = True
            break
    
    if not has_sqlite3_import:
        for i, line in enumerate(new_lines):
            if "import os" in line:
                new_lines.insert(i+1, "import sqlite3\n")
                print("Added sqlite3 import")
                break
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Successfully updated job status endpoint in {API_PATH}")
    return True

if __name__ == "__main__":
    print("Fixing job status endpoint in API file...\n")
    
    if fix_job_status_endpoint():
        print("\nJob status endpoint fixed successfully!")
        print("\nPlease restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix job status endpoint. See errors above.")
        sys.exit(1)
