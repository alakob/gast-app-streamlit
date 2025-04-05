#!/usr/bin/env python3
"""
Fix the database connection management to handle closed connections consistently.

This script improves the database_manager.py file to add more robust connection handling.
"""
import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_database_manager():
    """Improve the database manager with more robust connection handling"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: Database manager file not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    backup_file(DB_MANAGER_PATH)
    
    # Read the file content
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Add a get_fresh_connection method if it doesn't exist
    if "def get_fresh_connection" not in content:
        get_connection_pattern = re.compile(
            r'def get_connection\(self\).*?return self\.conn', 
            re.DOTALL
        )
        match = get_connection_pattern.search(content)
        
        if match:
            old_method = match.group(0)
            
            # Create a new version with get_fresh_connection method
            new_methods = f'''{old_method}
    
    def get_fresh_connection(self):
        """
        Get a fresh SQLite connection.
        
        This method always creates a new connection, bypassing the cached connection.
        Use this when you need to ensure a working connection, especially in background tasks
        or when the cached connection might be closed.
        
        Returns:
            A new SQLite connection object
        """
        import sqlite3
        import logging
        
        # Create a new connection
        try:
            # Ensure the database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create a new connection with row factory
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            return conn
        except Exception as e:
            logging.error(f"Error creating fresh database connection: {str(e)}")
            raise'''
            
            # Replace the old method with the new method plus get_fresh_connection
            updated_content = content.replace(old_method, new_methods)
            
            # Update the get_job method to use get_fresh_connection as a fallback
            get_job_pattern = re.compile(
                r'def get_job\(self, job_id: str\).*?return job_data', 
                re.DOTALL
            )
            job_match = get_job_pattern.search(updated_content)
            
            if job_match:
                old_get_job = job_match.group(0)
                
                # Create a new version that uses get_fresh_connection as a fallback
                new_get_job = '''def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        """
        try:
            # First try with the cached connection
            with self.get_connection() as conn:
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
                
                return job_data
        except sqlite3.ProgrammingError as e:
            # Handle case where connection is closed
            if "Cannot operate on a closed database" in str(e):
                import logging
                logging.warning(f"Using fresh connection for job {job_id} due to closed database")
                
                # Try with a fresh connection
                try:
                    conn = self.get_fresh_connection()
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
                        conn.close()
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
                    
                    # Close the fresh connection
                    conn.close()
                    
                    return job_data
                except Exception as inner_e:
                    logging.error(f"Error with fresh connection: {str(inner_e)}")
                    raise e  # Re-raise original error
            else:
                # Re-raise if it's a different error
                raise'''
                
                # Replace the old get_job with the new one
                updated_content = updated_content.replace(old_get_job, new_get_job)
                
                # Write the updated content back to the file
                with open(DB_MANAGER_PATH, 'w') as f:
                    f.write(updated_content)
                
                print(f"Successfully updated database manager in {DB_MANAGER_PATH}")
                return True
            else:
                print("Error: Could not find get_job method in database manager")
                return False
        else:
            print("Error: Could not find get_connection method in database manager")
            return False
    else:
        print("get_fresh_connection method already exists, no changes needed to database manager")
        return True

if __name__ == "__main__":
    print("Improving database connection management...\n")
    
    if fix_database_manager():
        print("\nDatabase connection management improved successfully!")
        print("You can now restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to improve database connection management. See error messages above.")
        sys.exit(1)
