#!/usr/bin/env python3
"""
Direct fix for the job_name constraint issue in AMR Predictor.

This script makes a precise modification to the database_manager.py file
to include job_name in the INSERT statement.
"""
import os
import sys
import logging
from pathlib import Path
import shutil
import time
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("job-name-fix")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

def fix_save_job_method():
    """Make a precise modification to the save_job method"""
    db_manager_path = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"
    
    if not db_manager_path.exists():
        logger.error(f"Database manager file not found at {db_manager_path}")
        return False
    
    # Create a backup first
    backup_path = f"{db_manager_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        shutil.copy2(db_manager_path, backup_path)
        logger.info(f"Created database manager backup at {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create database manager backup: {e}")
        logger.warning("Proceeding without backup - this is risky")
    
    try:
        # Read the current file content
        with open(db_manager_path, 'r') as f:
            content = f.read()
        
        # Define the precise pattern to match
        pattern = re.compile(
            r'(\s+# Create the job record\n\s+cursor\.execute\(\n\s+"""'
            r'\n\s+INSERT INTO amr_jobs \(\n\s+id, status, progress, start_time, created_at'
            r'\n\s+\) VALUES \(\?, \?, \?, \?, \?\)'
            r'\n\s+""",\n\s+\(job_id, status, progress, now, now\)\n\s+\))'
        )
        
        # Define the replacement with job_name added
        replacement = '''        # Create the job record
        # Extract job name from additional_info if available
        job_name = "AMR Analysis Job"
        if additional_info and "input_file" in additional_info:
            job_name = f"Analysis of {additional_info['input_file']}"
            
        cursor.execute(
            """
            INSERT INTO amr_jobs (
                id, status, progress, start_time, created_at, job_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, status, progress, now, now, job_name)
        )'''
        
        # Perform the replacement
        new_content = re.sub(pattern, replacement, content)
        
        # Check if replacement was made
        if new_content != content:
            # Write back the modified content
            with open(db_manager_path, 'w') as f:
                f.write(new_content)
            
            logger.info("Successfully patched save_job method to include job_name")
            return True
        else:
            logger.warning("Could not find the exact pattern to replace")
            
            # Fallback approach - just append defaults to the function signature
            def_pattern = r'def save_job\(self, job_id: str, status: str = "Submitted", progress: float = 0\.0,'
            def_replacement = r'def save_job(self, job_id: str, status: str = "Submitted", progress: float = 0.0, job_name: str = "AMR Analysis Job",'
            
            # Try to modify the function signature as a fallback
            new_content = re.sub(def_pattern, def_replacement, content)
            
            if new_content != content:
                logger.info("Using fallback approach to add job_name parameter")
                
                # Now add job_name to the INSERT statement
                insert_pattern = r'\(job_id, status, progress, now, now\)'
                insert_replacement = r'(job_id, status, progress, now, now, job_name)'
                
                columns_pattern = r'id, status, progress, start_time, created_at'
                columns_replacement = r'id, status, progress, start_time, created_at, job_name'
                
                values_pattern = r'\?, \?, \?, \?, \?'
                values_replacement = r'?, ?, ?, ?, ?, ?'
                
                # Apply all the required changes
                new_content = re.sub(insert_pattern, insert_replacement, new_content)
                new_content = re.sub(columns_pattern, columns_replacement, new_content)
                new_content = re.sub(values_pattern, values_replacement, new_content)
                
                # Write back the modified content
                with open(db_manager_path, 'w') as f:
                    f.write(new_content)
                
                logger.info("Applied fallback fixes to include job_name")
                return True
            else:
                logger.error("Could not apply either fix method")
                return False
            
    except Exception as e:
        logger.error(f"Failed to patch database manager: {e}")
        return False

if __name__ == "__main__":
    if fix_save_job_method():
        print("\nSuccessfully fixed the job_name constraint issue!")
        print("The database operation will now include job_name in the INSERT statement.")
        print("\nPlease restart your API server for the changes to take effect:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix the job_name constraint issue. See log for details.")
        sys.exit(1)
