#!/usr/bin/env python3
"""
Query for all AMR jobs with error status.

This script connects to the database and lists all jobs that have failed with an error.
"""
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("error-job-query")

# Make sure we can import from the project
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Import the needed modules
    from amr_predictor.bakta.database import DatabaseManager
    from amr_predictor.dao.amr_job_dao import AMRJobDAO
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this script from the project root")
    sys.exit(1)

def get_error_jobs():
    """Query for all jobs with ERROR status"""
    try:
        # Create the database manager and DAO
        db_manager = DatabaseManager()
        job_dao = AMRJobDAO(db_manager)
        
        # Get all jobs with ERROR status (no pagination limit to see all)
        logger.info("Querying for jobs with ERROR status...")
        error_jobs = job_dao.get_all(limit=1000, status="ERROR")
        
        if not error_jobs:
            logger.info("No jobs with ERROR status found")
            return []
        
        logger.info(f"Found {len(error_jobs)} jobs with ERROR status")
        
        # Format the results for display
        formatted_jobs = []
        for job in error_jobs:
            formatted_job = {
                "id": job.id,
                "job_name": job.job_name,
                "status": job.status,
                "error": job.error,
                "created_at": str(job.created_at),
                "completed_at": str(job.completed_at) if job.completed_at else None,
                "user_id": job.user_id
            }
            formatted_jobs.append(formatted_job)
        
        return formatted_jobs
    
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return {"error": str(e)}

def main():
    """Main entry point"""
    try:
        error_jobs = get_error_jobs()
        
        # Print the results
        print("\nERROR JOBS:")
        print("===========")
        if not error_jobs:
            print("No jobs with ERROR status found.")
        else:
            print(json.dumps(error_jobs, indent=2))
            
            # Print a summary table for quick review
            print("\nSummary Table:")
            print("-" * 100)
            print(f"{'ID':<36} | {'Job Name':<20} | {'Created At':<20} | {'Error':<20}")
            print("-" * 100)
            for job in error_jobs:
                # Truncate error message for display
                error_msg = job['error'][:20] + '...' if job['error'] and len(job['error']) > 20 else job['error']
                print(f"{job['id']:<36} | {job['job_name']:<20} | {job['created_at']:<20} | {error_msg:<20}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
