#!/usr/bin/env python3
"""
Fix the database connection issue in the /jobs endpoint.

This script patches the list_jobs endpoint or get_jobs method to use a direct
database connection to fix the "Cannot operate on a closed database" error.
"""
import sys
import re
import shutil
import time
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
REPOSITORY_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def patch_list_jobs_endpoint():
    """Patch the list_jobs endpoint or get_jobs method"""
    # First, let's modify the repository's get_jobs method
    if not REPOSITORY_PATH.exists():
        print(f"Error: Repository file not found at {REPOSITORY_PATH}")
        return False
    
    # Make a backup
    backup_file(REPOSITORY_PATH)
    
    # Read the original file
    with open(REPOSITORY_PATH, 'r') as f:
        repo_content = f.read()
    
    # Find the get_jobs method
    get_jobs_pattern = re.compile(
        r'def get_jobs\(self, status: Optional\[str\] = None, limit: int = 100,.*?return self\.db_manager\.get_jobs\(status=status, limit=limit, offset=offset\)',
        re.DOTALL
    )
    
    match = get_jobs_pattern.search(repo_content)
    if not match:
        print("Error: Could not find get_jobs method in repository file")
        return False
    
    old_get_jobs = match.group(0)
    
    # Create the updated get_jobs method with a direct database connection
    new_get_jobs = '''def get_jobs(self, status: Optional[str] = None, limit: int = 100,
                offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of jobs.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of job data dictionaries
        """
        try:
            return self.db_manager.get_jobs(status=status, limit=limit, offset=offset)
        except sqlite3.ProgrammingError as e:
            if "Cannot operate on a closed database" in str(e):
                # If the database connection is closed, create a direct connection
                logger.info("Creating direct connection for get_jobs due to closed database")
                
                # Get database path from manager
                db_path = self.db_manager.db_path
                
                # Create a direct connection
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                try:
                    # Build query based on filter
                    if status:
                        query = """
                        SELECT * FROM amr_jobs 
                        WHERE status = ? 
                        ORDER BY created_at DESC 
                        LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, (status, limit, offset))
                    else:
                        query = """
                        SELECT * FROM amr_jobs 
                        ORDER BY created_at DESC 
                        LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, (limit, offset))
                    
                    job_rows = cursor.fetchall()
                    
                    jobs = []
                    for job_row in job_rows:
                        job_data = dict(job_row)
                        
                        # Map 'id' to 'job_id' for API compatibility
                        if 'id' in job_data:
                            job_data['job_id'] = job_data['id']
                        
                        # Get parameters for this job
                        params_cursor = conn.cursor()
                        params_cursor.execute(
                            """
                            SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                            """,
                            (job_data["id"],)
                        )
                        
                        # Add parameters to job data
                        for row in params_cursor.fetchall():
                            job_data[row["param_name"]] = row["param_value"]
                        
                        jobs.append(job_data)
                    
                    return jobs
                    
                finally:
                    # Ensure connection is closed
                    conn.close()
            else:
                # Re-raise if it's a different error
                raise'''
    
    # Replace the old get_jobs with the new one
    updated_repo_content = repo_content.replace(old_get_jobs, new_get_jobs)
    
    # Add sqlite3 import if needed
    if "import sqlite3" not in updated_repo_content:
        updated_repo_content = updated_repo_content.replace(
            "from typing import",
            "import sqlite3\nfrom typing import"
        )
    
    # Write the updated content back to the file
    with open(REPOSITORY_PATH, 'w') as f:
        f.write(updated_repo_content)
    
    print(f"Successfully patched get_jobs method in {REPOSITORY_PATH}")
    return True

if __name__ == "__main__":
    if patch_list_jobs_endpoint():
        print("\nJobs endpoint patched successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to patch jobs endpoint. See error messages above.")
        sys.exit(1)
