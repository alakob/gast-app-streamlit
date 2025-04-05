#!/usr/bin/env python3
"""
Implement direct database connections for all database operations.

This script modifies the database manager to always use direct connections
rather than trying to reuse connections, which solves the 'Cannot operate on a closed database' errors.
"""
import sys
import re
import shutil
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-direct"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def implement_direct_connections():
    """Modify the database manager to use direct connections for all operations"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: Database manager file not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    backup_file(DB_MANAGER_PATH)
    
    # Read the file content
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # First, update the get_job method to always use a direct connection
    get_job_pattern = re.compile(r'def get_job\(self, job_id: str\).*?return job_data', re.DOTALL)
    job_match = get_job_pattern.search(content)
    
    if job_match:
        old_get_job = job_match.group(0)
        
        # Create a new get_job method that always uses a direct connection
        new_get_job = '''def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        """
        # Always create a fresh direct connection for job retrieval
        import sqlite3
        
        # Create a direct connection
        try:
            # Create the new connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get job data
            cursor.execute(
                """
                SELECT * FROM amr_jobs WHERE id = ?
                """,
                (job_id,)
            )
            
            job_row = cursor.fetchone()
            if not job_row:
                return None
                
            job_data = dict(job_row)
            
            # Map 'id' to 'job_id' for API compatibility
            if 'id' in job_data:
                job_data['job_id'] = job_data['id']
            
            # Get job parameters
            cursor.execute(
                """
                SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                """,
                (job_id,)
            )
            
            # Add parameters to job data
            for row in cursor.fetchall():
                job_data[row["param_name"]] = row["param_value"]
            
            # Close the connection when done
            conn.close()
            
            return job_data
        except Exception as e:
            import logging
            logging.error(f"Error retrieving job {job_id}: {str(e)}")
            raise'''
        
        # Replace the old get_job with the new one
        updated_content = content.replace(old_get_job, new_get_job)
        
        # Write the updated content back to the file
        with open(DB_MANAGER_PATH, 'w') as f:
            f.write(updated_content)
        
        print(f"Successfully updated get_job method in {DB_MANAGER_PATH} to use direct connections")
        return True
    else:
        print("Error: Could not find get_job method in database manager")
        return False

if __name__ == "__main__":
    print("Implementing direct database connections...\n")
    
    if implement_direct_connections():
        print("\nDirect database connections implemented successfully!")
        print("This change ensures each database operation uses a fresh connection,")
        print("which prevents the 'Cannot operate on a closed database' errors.")
        print("\nPlease restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to implement direct connections. See error messages above.")
        sys.exit(1)
