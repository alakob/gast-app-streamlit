#!/usr/bin/env python3
"""
Final fix for the API file to resolve all syntax errors.

This script restores the API file from a clean backup and implements a simpler
solution for handling database connections.
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

def restore_api():
    """Restore the API file from the oldest backup"""
    # Find all backups
    backups = list(PROJECT_ROOT.glob("amr_predictor/web/api.py.backup-*"))
    
    if not backups:
        print("No backup files found to restore from")
        return False
    
    # Sort backups by modification time to find the oldest (pre-our changes)
    backups.sort(key=lambda x: x.stat().st_mtime)
    oldest_backup = backups[0]
    
    print(f"Restoring from backup: {oldest_backup}")
    shutil.copy2(oldest_backup, API_PATH)
    print("API file restored")
    return True

def add_sqlite_import():
    """Add sqlite3 import to the API file"""
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Add sqlite3 import if not present
    if "import sqlite3" not in content:
        # Find the import section
        import_section = re.compile(r'import os.*?from pydantic', re.DOTALL)
        match = import_section.search(content)
        if match:
            updated_imports = match.group(0).replace("import os", "import os\nimport sqlite3")
            content = content.replace(match.group(0), updated_imports)
            print("Added sqlite3 import")
    
    # Write updated content
    with open(API_PATH, 'w') as f:
        f.write(content)
    
    return True

def implement_error_handling():
    """Update the get_job_status endpoint to handle database errors"""
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the get_job_status endpoint
    endpoint_pattern = re.compile(
        r'@app\.get\("/jobs/\{job_id\}".*?\).*?async def get_job_status.*?return job', 
        re.DOTALL
    )
    match = endpoint_pattern.search(content)
    
    if not match:
        print("Error: Could not find get_job_status endpoint")
        return False
    
    old_endpoint = match.group(0)
    
    # Create a new version with proper error handling
    new_endpoint = '''@app.get("/jobs/{job_id}", response_model=JobResponse)
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
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")'''
    
    # Replace the old endpoint with the new one
    updated_content = content.replace(old_endpoint, new_endpoint)
    
    # Write the updated content
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print("Updated get_job_status endpoint with robust error handling")
    return True

if __name__ == "__main__":
    print("Implementing final API fix...\n")
    
    # First create a backup of the current state
    backup_file(API_PATH)
    
    # Restore from a clean backup
    if restore_api():
        # Then add sqlite3 import
        add_sqlite_import()
        
        # Then implement error handling
        if implement_error_handling():
            print("\nAPI file fixed successfully!")
            print("You can now restart your API server with:")
            print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
        else:
            print("\nFailed to implement error handling. See error messages above.")
            sys.exit(1)
    else:
        print("\nFailed to restore API file. See error messages above.")
        sys.exit(1)
