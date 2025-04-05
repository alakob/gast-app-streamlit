#!/usr/bin/env python3
"""
Fix transaction handling in the database_manager.py file.

This script modifies the add_job_parameters method to not start a new transaction
when one is already active.
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

def fix_transaction_handling():
    """Fix the transaction handling in the add_job_parameters method"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: File not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    create_backup(DB_MANAGER_PATH)
    
    # Read the entire file
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Replace the BEGIN transaction call in add_job_parameters
    old_code = """
            # Begin transaction
            conn.execute("BEGIN")
            
            try:
                for param_name, param_value in parameters.items():
                    # Convert value to string
                    param_value_str = str(param_value)
                    
                    # Check if parameter already exists
                    cursor.execute(
                        "SELECT id FROM amr_job_parameters WHERE job_id = ? AND param_name = ?",
                        (job_id, param_name)
                    )
                    
                    if cursor.fetchone() is not None:
                        # Update existing parameter
                        cursor.execute(
                            "UPDATE amr_job_parameters SET param_value = ? WHERE job_id = ? AND param_name = ?",
                            (param_value_str, job_id, param_name)
                        )
                    else:
                        # Insert new parameter
                        cursor.execute(
                            "INSERT INTO amr_job_parameters (job_id, param_name, param_value) VALUES (?, ?, ?)",
                            (job_id, param_name, param_value_str)
                        )
                
                conn.commit()
                return True
            
            except Exception as e:
                # Rollback on error
                conn.rollback()
                logger.error(f"Error adding job parameters: {str(e)}")
                return False"""
    
    new_code = """
            try:
                for param_name, param_value in parameters.items():
                    # Convert value to string
                    param_value_str = str(param_value)
                    
                    # Check if parameter already exists
                    cursor.execute(
                        "SELECT id FROM amr_job_parameters WHERE job_id = ? AND param_name = ?",
                        (job_id, param_name)
                    )
                    
                    if cursor.fetchone() is not None:
                        # Update existing parameter
                        cursor.execute(
                            "UPDATE amr_job_parameters SET param_value = ? WHERE job_id = ? AND param_name = ?",
                            (param_value_str, job_id, param_name)
                        )
                    else:
                        # Insert new parameter
                        cursor.execute(
                            "INSERT INTO amr_job_parameters (job_id, param_name, param_value) VALUES (?, ?, ?)",
                            (job_id, param_name, param_value_str)
                        )
                
                # Commit is handled by the context manager
                return True
            
            except Exception as e:
                # Log the error but let the context manager handle the transaction
                logger.error(f"Error adding job parameters: {str(e)}")
                raise  # Re-raise to let context manager handle rollback"""
    
    # Replace in content
    new_content = content.replace(old_code, new_code)
    
    # Also fix the delete_job method transaction handling
    old_delete_code = """
            # Begin transaction
            conn.execute("BEGIN")
            
            try:
                # Delete job parameters (foreign key constraint will handle this,
                # but being explicit for clarity)
                cursor.execute("DELETE FROM amr_job_parameters WHERE job_id = ?", (job_id,))
                
                # Delete job
                cursor.execute("DELETE FROM amr_jobs WHERE id = ?", (job_id,))
                
                # Check if any rows were affected
                deleted = cursor.rowcount > 0
                
                conn.commit()
                return deleted
            
            except Exception as e:
                # Rollback on error
                conn.rollback()
                logger.error(f"Error deleting job: {str(e)}")
                return False"""
                
    new_delete_code = """
            try:
                # Delete job parameters (foreign key constraint will handle this,
                # but being explicit for clarity)
                cursor.execute("DELETE FROM amr_job_parameters WHERE job_id = ?", (job_id,))
                
                # Delete job
                cursor.execute("DELETE FROM amr_jobs WHERE id = ?", (job_id,))
                
                # Check if any rows were affected
                deleted = cursor.rowcount > 0
                
                # Commit is handled by the context manager
                return deleted
            
            except Exception as e:
                # Log the error but let the context manager handle the transaction
                logger.error(f"Error deleting job: {str(e)}")
                raise  # Re-raise to let context manager handle rollback"""
    
    # Replace in content
    new_content = new_content.replace(old_delete_code, new_delete_code)
    
    # Write the corrected content back to the file
    with open(DB_MANAGER_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully fixed transaction handling in {DB_MANAGER_PATH}")
    return True

if __name__ == "__main__":
    if fix_transaction_handling():
        print("\nTransaction handling fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix transaction handling. See error messages above.")
        sys.exit(1)
