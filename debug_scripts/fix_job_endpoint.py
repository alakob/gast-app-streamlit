#!/usr/bin/env python3
"""
Fix the get_job_status endpoint in the API to properly handle database errors.

This script focuses on adding robust error handling to the job status endpoint
to prevent 500 Internal Server Errors caused by closed database connections.
"""
import os
import sys
import sqlite3
import re
import shutil
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
REPO_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_repository_get_job():
    """Fix the get_job method in AMRJobRepository to handle closed database connections"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Create a backup before modifying
    backup_file(REPO_PATH)
    
    with open(REPO_PATH, 'r') as file:
        content = file.read()
    
    # Check if the get_job method exists and update it with robust error handling
    get_job_pattern = re.compile(r'def get_job\(self, job_id\):.*?return.*?\n', re.DOTALL)
    match = get_job_pattern.search(content)
    
    if not match:
        print("Error: Could not find get_job method in repository file")
        return False
    
    old_get_job = match.group(0)
    
    # Create new version with error handling for closed connections
    new_get_job = """def get_job(self, job_id):
        """Get information about a specific job"""
        try:
            # First try with the existing connection
            return self.db_manager.get_job(job_id)
        except sqlite3.ProgrammingError as e:
            # Handle case where connection is closed
            import logging
            logging.warning(f"Database connection was closed, creating new connection to get job {job_id}")
            from ..core.database_manager import AMRDatabaseManager
            db_manager = AMRDatabaseManager()
            try:
                return db_manager.get_job(job_id)
            except Exception as inner_e:
                # Log the inner exception but raise the original one to maintain the call stack
                logging.error(f"Error getting job with new connection: {inner_e}")
                raise e
        
"""
    
    # Replace the old implementation with the new one
    updated_content = content.replace(old_get_job, new_get_job)
    
    with open(REPO_PATH, 'w') as file:
        file.write(updated_content)
    
    print(f"Successfully updated get_job method in {REPO_PATH}")
    return True

def fix_api_get_job_status():
    """Fix the get_job_status endpoint in the API to handle errors properly"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup before modifying
    backup_file(API_PATH)
    
    with open(API_PATH, 'r') as file:
        content = file.read()
    
    # Find the get_job_status endpoint
    job_status_pattern = re.compile(r'@app\.get\("/jobs/{job_id}"\).*?def get_job_status.*?return job\n', re.DOTALL)
    match = job_status_pattern.search(content)
    
    if not match:
        print("Error: Could not find get_job_status endpoint in API file")
        return False
    
    old_endpoint = match.group(0)
    
    # Create new version with robust error handling
    new_endpoint = """@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str = Path(..., description="Job ID to get status for")):
    """
    Get the status of a job.
    
    Args:
        job_id: Job ID to get status for
        
    Returns:
        Job response with current status
    """
    try:
        job = job_repository.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return job
    except sqlite3.ProgrammingError as e:
        logger.error(f"Database error when getting job {job_id}: {str(e)}")
        # Try with a fresh connection
        import sqlite3
        from ..core.database_manager import AMRDatabaseManager
        try:
            db_manager = AMRDatabaseManager()
            job = db_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            return job
        except Exception as inner_e:
            logger.error(f"Error retrieving job {job_id} with new connection: {str(inner_e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")

"""
    
    # Replace the old endpoint with the new one
    updated_content = content.replace(old_endpoint, new_endpoint)
    
    with open(API_PATH, 'w') as file:
        file.write(updated_content)
    
    print(f"Successfully updated get_job_status endpoint in {API_PATH}")
    return True

if __name__ == "__main__":
    print("Fixing AMR job status endpoint...\n")
    
    # First fix the repository's get_job method
    if fix_repository_get_job():
        print("Repository get_job method updated with robust error handling.")
    else:
        print("Failed to update repository get_job method.")
    
    # Then fix the API endpoint
    if fix_api_get_job_status():
        print("API get_job_status endpoint updated with robust error handling.")
    else:
        print("Failed to update API get_job_status endpoint.")
    
    print("\nFixes completed. Please restart your API server with:")
    print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
