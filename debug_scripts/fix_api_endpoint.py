#!/usr/bin/env python3
"""
Targeted fix for the job status endpoint in the API file.

This script specifically looks for the job status endpoint in the current API file structure
and adds proper error handling for closed database connections.
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
    """Add robust error handling to the job status endpoint using exact pattern"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Read the file content
    with open(API_PATH, 'r') as f:
        content = f.readlines()
    
    # Find the job status endpoint using line inspection
    endpoint_line_index = -1
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(content):
        if '@app.get("/jobs/{job_id}")' in line:
            endpoint_line_index = i
            start_line = i
            break
    
    if endpoint_line_index == -1:
        print("Error: Could not find job status endpoint in API file")
        return False
    
    # Now find the end of the function
    in_function = False
    for i in range(start_line + 1, len(content)):
        line = content[i]
        
        # Mark when we enter the function definition
        if "async def get_job_status" in line:
            in_function = True
        
        # Check for next route or end of indented block
        if in_function and (line.startswith('@app') or (not line.strip() and i < len(content)-1 and not content[i+1].startswith(' '))):
            end_line = i
            break
    
    if end_line == -1:
        # If we couldn't find the end, use the last line of the file
        end_line = len(content)
    
    print(f"Found job status endpoint from line {start_line} to {end_line}")
    
    # Create a backup
    backup_file(API_PATH)
    
    # Create the new endpoint with error handling
    new_endpoint = '''@app.get("/jobs/{job_id}")
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
    
    # Replace the old endpoint with the new one
    new_content = content[:start_line] + [new_endpoint] + content[end_line:]
    
    # Check for sqlite3 import
    has_sqlite3_import = False
    for line in new_content:
        if "import sqlite3" in line:
            has_sqlite3_import = True
            break
    
    # Add sqlite3 import if not present
    if not has_sqlite3_import:
        for i, line in enumerate(new_content):
            if "import os" in line:
                new_content.insert(i+1, "import sqlite3\n")
                print("Added sqlite3 import")
                break
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.writelines(new_content)
    
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
