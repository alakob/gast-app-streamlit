#!/usr/bin/env python3
"""
Fix field name mismatches between the API model and database response.

This script modifies the get_job and get_jobs methods in the database_manager.py
to ensure field names match the API response model requirements.
"""
import os
import sys
import re
import shutil
import time
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_field_names():
    """Fix the field name mismatch in the get_job and get_jobs methods"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: File not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    create_backup(DB_MANAGER_PATH)
    
    # Read the entire file
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Replace the get_job method to map 'id' to 'job_id'
    old_get_job = """
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        \"\"\"
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        \"\"\"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get job data
            cursor.execute(
                \"\"\"
                SELECT * FROM amr_jobs WHERE id = ?
                \"\"\",
                (job_id,)
            )
            
            job_row = cursor.fetchone()
            if not job_row:
                return None
                
            job_data = dict(job_row)
            
            # Get job parameters
            cursor.execute(
                \"\"\"
                SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                \"\"\",
                (job_id,)
            )
            
            # Add parameters to job data
            for row in cursor.fetchall():
                job_data[row["param_name"]] = row["param_value"]
            
            return job_data"""
    
    new_get_job = """
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        \"\"\"
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        \"\"\"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get job data
            cursor.execute(
                \"\"\"
                SELECT * FROM amr_jobs WHERE id = ?
                \"\"\",
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
                \"\"\"
                SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                \"\"\",
                (job_id,)
            )
            
            # Add parameters to job data
            for row in cursor.fetchall():
                job_data[row["param_name"]] = row["param_value"]
            
            return job_data"""
    
    # Replace the get_jobs method to map 'id' to 'job_id' for each job
    old_get_jobs = """
    def get_jobs(self, status: Optional[str] = None, limit: int = 100, 
                offset: int = 0) -> List[Dict[str, Any]]:
        \"\"\"
        Get a list of jobs, optionally filtered by status.
        
        Args:
            status: Filter by job status
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of job data dictionaries
        \"\"\"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query based on filter
            if status:
                query = \"\"\"
                SELECT * FROM amr_jobs 
                WHERE status = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                \"\"\"
                cursor.execute(query, (status, limit, offset))
            else:
                query = \"\"\"
                SELECT * FROM amr_jobs 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                \"\"\"
                cursor.execute(query, (limit, offset))
            
            job_rows = cursor.fetchall()
            
            jobs = []
            for job_row in job_rows:
                job_data = dict(job_row)
                
                # Get parameters for this job
                params_cursor = conn.cursor()
                params_cursor.execute(
                    \"\"\"
                    SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                    \"\"\",
                    (job_data["id"],)
                )
                
                # Add parameters to job data
                for row in params_cursor.fetchall():
                    job_data[row["param_name"]] = row["param_value"]
                
                jobs.append(job_data)
            
            return jobs"""
    
    new_get_jobs = """
    def get_jobs(self, status: Optional[str] = None, limit: int = 100, 
                offset: int = 0) -> List[Dict[str, Any]]:
        \"\"\"
        Get a list of jobs, optionally filtered by status.
        
        Args:
            status: Filter by job status
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of job data dictionaries
        \"\"\"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query based on filter
            if status:
                query = \"\"\"
                SELECT * FROM amr_jobs 
                WHERE status = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                \"\"\"
                cursor.execute(query, (status, limit, offset))
            else:
                query = \"\"\"
                SELECT * FROM amr_jobs 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                \"\"\"
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
                    \"\"\"
                    SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                    \"\"\",
                    (job_data["id"],)
                )
                
                # Add parameters to job data
                for row in params_cursor.fetchall():
                    job_data[row["param_name"]] = row["param_value"]
                
                jobs.append(job_data)
            
            return jobs"""
    
    # Replace in content
    new_content = content.replace(old_get_job, new_get_job)
    new_content = new_content.replace(old_get_jobs, new_get_jobs)
    
    # Write the corrected content back to the file
    with open(DB_MANAGER_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully fixed field name mismatch in {DB_MANAGER_PATH}")
    return True

if __name__ == "__main__":
    if fix_field_names():
        print("\nField names fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix field names. See error messages above.")
        sys.exit(1)
