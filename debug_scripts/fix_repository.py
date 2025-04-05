#!/usr/bin/env python3
"""
Fix the structure of the get_job method in repository.py.

This script completely rewrites the get_job method with proper structure to fix
the 'return outside function' error.
"""
import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
REPO_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def restore_repository():
    """Restore the repository.py file from a backup before our modifications"""
    backups = list(PROJECT_ROOT.glob("amr_predictor/core/repository.py.backup-*"))
    
    if not backups:
        print("No backup files found to restore from")
        return False
    
    # Sort backups by modification time to find the oldest (pre-our changes)
    backups.sort(key=lambda x: x.stat().st_mtime)
    oldest_backup = backups[0]
    
    print(f"Restoring from backup: {oldest_backup}")
    shutil.copy2(oldest_backup, REPO_PATH)
    print("Repository file restored")
    return True

def implement_robust_get_job():
    """Implement a robust get_job method in repository.py"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Read the file content
    with open(REPO_PATH, 'r') as f:
        content = f.read()
    
    # Find the get_job method
    method_pattern = re.compile(
        r'def get_job\(self, job_id: str\).*?job_data = self\.db_manager\.get_job\(job_id\).*?return job_data', 
        re.DOTALL
    )
    match = method_pattern.search(content)
    
    if not match:
        print("Error: Could not find get_job method pattern in repository.py")
        return False
    
    old_method = match.group(0)
    
    # Create a new version with proper structure and error handling
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
    
    # Write the updated content back to the file
    with open(REPO_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully updated get_job method in {REPO_PATH}")
    return True

if __name__ == "__main__":
    print("Fixing the repository get_job method...\n")
    
    # First restore from a clean backup
    backup_file(REPO_PATH)  # Backup current state before restoring
    if restore_repository():
        # Then implement a clean version of the get_job method
        if implement_robust_get_job():
            print("\nRepository get_job method fixed successfully!")
            print("You can now restart your API server with:")
            print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
        else:
            print("\nFailed to implement get_job method. See error messages above.")
            sys.exit(1)
    else:
        print("\nFailed to restore repository. See error messages above.")
        sys.exit(1)
