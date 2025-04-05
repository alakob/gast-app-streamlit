#!/usr/bin/env python3
"""
Debug and fix issues with the /jobs/{job_id} endpoint.

This script:
1. Examines the database to check job entries
2. Checks for common issues with job status retrieval
3. Fixes issues in the API code for job status endpoint
"""
import os
import sys
import sqlite3
import json
import shutil
import re
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
REPO_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def check_database():
    """Check database for job entries and their structure"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    print(f"Connecting to database at {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get table schema for amr_jobs
        cursor.execute("PRAGMA table_info(amr_jobs)")
        columns = cursor.fetchall()
        print("\n=== AMR Jobs Table Schema ===")
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, Not Null: {col[3]}, Default: {col[4]}, Primary Key: {col[5]}")
        
        # Check for recent jobs
        cursor.execute("SELECT id, status, error, result_file, aggregated_result_file FROM amr_jobs ORDER BY created_at DESC LIMIT 5")
        jobs = cursor.fetchall()
        print("\n=== Recent Jobs ===")
        for job in jobs:
            job_id, status, error, result_file, aggregated_result_file = job
            print(f"Job ID: {job_id}")
            print(f"  Status: {status}")
            print(f"  Error: {error}")
            print(f"  Result File: {result_file}")
            print(f"  Aggregated Result File: {aggregated_result_file}")
            
            # Check if the referenced files exist
            if result_file:
                print(f"  Result file exists: {os.path.exists(result_file)}")
            if aggregated_result_file:
                print(f"  Aggregated result file exists: {os.path.exists(aggregated_result_file)}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

def fix_get_job_method():
    """Fix the get_job method in the repository.py file"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Backup the file
    backup_file(REPO_PATH)
    
    # Read the file content
    with open(REPO_PATH, 'r') as f:
        content = f.readlines()
    
    # Find and fix the get_job method to handle closed connections
    get_job_method_fixed = False
    in_get_job = False
    new_content = []
    
    for line in content:
        if "def get_job(self, job_id):" in line:
            in_get_job = True
            new_content.append(line)
        elif in_get_job and "return self.db_manager.get_job(job_id)" in line:
            # Replace with the improved version that handles closed connections
            new_content.append("        try:\n")
            new_content.append("            return self.db_manager.get_job(job_id)\n")
            new_content.append("        except sqlite3.ProgrammingError:\n")
            new_content.append("            # Handle case where connection is closed\n")
            new_content.append("            db_manager = AMRDatabaseManager()\n")
            new_content.append("            return db_manager.get_job(job_id)\n")
            get_job_method_fixed = True
        elif in_get_job and "def" in line and "get_job" not in line:
            # We've reached the end of the get_job method
            in_get_job = False
            new_content.append(line)
        else:
            new_content.append(line)
    
    # Write the updated content back to the file
    with open(REPO_PATH, 'w') as f:
        f.writelines(new_content)
    
    if get_job_method_fixed:
        print("Successfully fixed get_job method in repository.py")
    else:
        print("No changes made to get_job method - it may already be fixed or have a different implementation")
    
    return True

def fix_job_status_endpoint():
    """Fix the /jobs/{job_id} endpoint in api.py to handle errors properly"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Backup the file
    backup_file(API_PATH)
    
    # Read the file content
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the get_job_status function
    job_status_pattern = re.compile(
        r'@app\.get\("/jobs/{job_id}"\).*?async def get_job_status\(job_id: str\).*?return job',
        re.DOTALL
    )
    
    match = job_status_pattern.search(content)
    if not match:
        print("Error: Could not find get_job_status function in API file")
        return False
    
    old_job_status = match.group(0)
    
    # Create the improved get_job_status function with better error handling
    new_job_status = '''@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str = Path(..., description="Job ID to get status for")):
    """
    Get the status of a job.
    
    Args:
        job_id: Job ID to get status for
        
    Returns:
        Job status object
    """
    try:
        job = job_repository.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return job
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")'''
    
    # Replace the old job_status with the new one
    updated_content = content.replace(old_job_status, new_job_status)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print("Successfully updated get_job_status endpoint in api.py")
    return True

if __name__ == "__main__":
    print("Debugging AMR job status issues...\n")
    
    # First check database
    check_database()
    
    # Fix the get_job method
    fix_get_job_method()
    
    # Fix the job status endpoint
    fix_job_status_endpoint()
    
    print("\nJob status endpoint fixes completed!")
    print("Please restart your API server with:")
    print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    print("\nThen test the endpoint with:")
    print("curl http://localhost:8000/jobs/{job_id}")
