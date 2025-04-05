#!/usr/bin/env python3
"""
Fix for the job_name constraint issue in the AMR Predictor.

This script addresses the NOT NULL constraint on job_name field
by patching the save_job method to always provide a default job name
when one isn't specified.
"""
import os
import sys
import logging
from pathlib import Path
import sqlite3
import time
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("job-name-fix")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

def patch_database_manager():
    """Patch the database manager to handle the job_name constraint"""
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
        
        # Find the save_job method signature
        save_job_signature = "def save_job(self, job_id: str, status: str = \"Submitted\", progress: float = 0.0, "
        save_job_params = "additional_info: Optional[Dict[str, Any]] = None)"
        
        if save_job_signature in content and save_job_params in content:
            # Generate the replacement code to handle job_name
            old_code = """        # Create the job record
        cursor.execute(
            \"\"\"
            INSERT INTO amr_jobs (
                id, status, progress, start_time, created_at
            ) VALUES (?, ?, ?, ?, ?)
            \"\"\",
            (job_id, status, progress, now, now)
        )"""
            
            new_code = """        # Extract job_name from additional_info or use a default
        job_name = "AMR Analysis Job"
        if additional_info and "input_file" in additional_info:
            job_name = f"Analysis of {additional_info['input_file']}"
        
        # Create the job record
        cursor.execute(
            \"\"\"
            INSERT INTO amr_jobs (
                id, status, progress, start_time, created_at, job_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            \"\"\",
            (job_id, status, progress, now, now, job_name)
        )"""
            
            # Replace the code
            updated_content = content.replace(old_code, new_code)
            
            if updated_content != content:
                # Write back the modified content
                with open(db_manager_path, 'w') as f:
                    f.write(updated_content)
                
                logger.info("Successfully patched database_manager.py to handle job_name requirement")
                return True
            else:
                logger.warning("Could not locate the specific code to patch")
                return False
        else:
            logger.warning("Could not locate the save_job method signature")
            return False
            
    except Exception as e:
        logger.error(f"Failed to patch database manager: {e}")
        return False

if __name__ == "__main__":
    if patch_database_manager():
        print("\nSuccessfully fixed the job_name constraint issue!")
        print("The API will now provide default job names when none are specified.")
        print("\nYou should restart your API server for the changes to take effect:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix the job_name constraint issue. See log for details.")
        sys.exit(1)
