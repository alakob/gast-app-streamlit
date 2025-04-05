#!/usr/bin/env python3
"""
Direct database query for AMR jobs with ERROR status.
This script directly connects to the SQLite database to find failed jobs.
"""
import os
import sys
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct-error-query")

def find_db_path():
    """Find the database file path"""
    # Default location based on the code we've seen
    default_path = os.path.expanduser("~/.amr_predictor/bakta/bakta.db")
    
    if os.path.exists(default_path):
        logger.info(f"Found database at: {default_path}")
        return default_path
    
    # Look for .env file that might contain database path
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        logger.info("Reading .env file for database location...")
        with open(env_path, "r") as f:
            for line in f:
                if "DATABASE_PATH" in line or "DB_PATH" in line:
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        path = parts[1].strip().strip("'").strip('"')
                        logger.info(f"Found database path in .env: {path}")
                        return path
    
    logger.warning(f"Using default database path: {default_path}")
    return default_path

def get_error_jobs(db_path):
    """Query the database directly for jobs with ERROR status"""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Enable dictionary cursor
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query for all jobs with ERROR status
        cursor.execute("""
            SELECT * FROM amr_jobs 
            WHERE status = 'ERROR' OR status LIKE '%FAILED%'
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("No jobs with ERROR status found")
            return []
        
        logger.info(f"Found {len(rows)} jobs with ERROR status")
        
        # Format the results for display
        error_jobs = []
        for row in rows:
            job_dict = dict(row)
            
            # Attempt to get additional error details if available
            error_detail = job_dict.get('error', 'Unknown error')
            
            error_jobs.append({
                "id": job_dict.get('id'),
                "job_name": job_dict.get('job_name'),
                "status": job_dict.get('status'),
                "error": error_detail,
                "created_at": job_dict.get('created_at'),
                "completed_at": job_dict.get('completed_at'),
                "user_id": job_dict.get('user_id')
            })
        
        conn.close()
        return error_jobs
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

def main():
    """Main entry point"""
    try:
        # Find the database path
        db_path = find_db_path()
        
        # Get jobs with ERROR status
        error_jobs = get_error_jobs(db_path)
        
        # Print the results
        print("\nERROR JOBS:")
        print("===========")
        if not error_jobs:
            print("No jobs with ERROR status found.")
        else:
            print(json.dumps(error_jobs, indent=2))
            
            # Print a summary table for quick review
            print("\nSummary Table:")
            print("-" * 120)
            print(f"{'ID':<36} | {'Job Name':<20} | {'Created At':<20} | {'Error':<40}")
            print("-" * 120)
            for job in error_jobs:
                # Truncate error message for display
                error_msg = job['error']
                if error_msg and len(error_msg) > 40:
                    error_msg = error_msg[:37] + '...'
                print(f"{job['id']:<36} | {job['job_name']:<20} | {job['created_at']:<20} | {error_msg:<40}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
