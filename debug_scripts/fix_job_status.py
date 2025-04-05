#!/usr/bin/env python3
"""
Fix the job status endpoint to handle closed database connections.

This script adds error handling to the get_job_status endpoint
to catch and recover from the "Cannot operate on a closed database" error.
"""
import os
import sys
import re
import shutil
import sqlite3
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

def fix_job_status_endpoint():
    """Add robust error handling to the job status endpoint"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    backup_file(API_PATH)
    
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the job status endpoint using regex
    endpoint_pattern = re.compile(
        r'@app\.get\("/jobs/\{job_id\}"\).*?async def get_job_status.*?return job', 
        re.DOTALL
    )
    match = endpoint_pattern.search(content)
    
    if not match:
        print("Error: Could not find job status endpoint in API file")
        return False
    
    old_endpoint = match.group(0)
    
    # Create a new version with proper error handling
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
        from ..core.database_manager import AMRDatabaseManager
        try:
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
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")'''
    
    # Replace the old endpoint with the new one
    updated_content = content.replace(old_endpoint, new_endpoint)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully updated job status endpoint in {API_PATH}")
    return True

def update_repository():
    """Add error handling to the repository's get_job method"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Create a backup
    backup_file(REPO_PATH)
    
    with open(REPO_PATH, 'r') as f:
        content = f.read()
    
    # Find the get_job method using regex
    method_pattern = re.compile(
        r'def get_job\(self, job_id: str\).*?return job_data', 
        re.DOTALL
    )
    match = method_pattern.search(content)
    
    if not match:
        print("Error: Could not find get_job method in repository file")
        return False
    
    old_method = match.group(0)
    
    # Create a new version with proper error handling
    new_method = '''def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job data by ID.
    
    Args:
        job_id: Job ID to retrieve
        
    Returns:
        Job data or None if not found
    """
    try:
        job_data = self.db_manager.get_job(job_id)
        
        if job_data is None:
            logger.warning(f"Job not found: {job_id}")
            
        return job_data
    except sqlite3.ProgrammingError as e:
        if "Cannot operate on a closed database" in str(e):
            logger.warning(f"Reconnecting to database for job {job_id}")
            # Create a fresh connection
            from ..core.database_manager import AMRDatabaseManager
            fresh_db = AMRDatabaseManager()
            return fresh_db.get_job(job_id)
        else:
            # Re-raise if it's a different error
            raise'''
    
    # Replace the old method with the new one
    updated_content = content.replace(old_method, new_method)
    
    # Add sqlite3 import if not already present
    if "import sqlite3" not in content:
        import_section = re.compile(r'import.*?\n\n', re.DOTALL)
        match = import_section.search(content)
        if match:
            imports = match.group(0)
            updated_imports = imports.replace('\n\n', '\nimport sqlite3\n\n')
            updated_content = updated_content.replace(imports, updated_imports)
    
    # Write the updated content back to the file
    with open(REPO_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully updated repository get_job method in {REPO_PATH}")
    return True

if __name__ == "__main__":
    print("Fixing job status endpoint...\n")
    
    repository_updated = update_repository()
    endpoint_updated = fix_job_status_endpoint()
    
    if repository_updated and endpoint_updated:
        print("\nAll fixes completed successfully!")
    else:
        print("\nSome fixes were not applied. Please check the messages above.")
    
    print("\nPlease restart your API server with:")
    print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
