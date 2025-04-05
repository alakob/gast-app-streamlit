#!/usr/bin/env python3
"""
Query the AMR API directly to find jobs with error status.
"""
import os
import sys
import json
import logging
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amr-api-checker")

# Get API URL from environment or use default
AMR_API_URL = os.environ.get("AMR_API_URL", "http://localhost:8000")
AMR_API_KEY = os.environ.get("AMR_API_KEY", "")

def get_all_jobs():
    """Query the API for all jobs"""
    try:
        logger.info(f"Querying AMR API at {AMR_API_URL} for jobs")
        
        # Set up headers
        headers = {}
        if AMR_API_KEY:
            headers["X-API-Key"] = AMR_API_KEY
        
        # Make API request to get jobs
        url = urljoin(AMR_API_URL, "/jobs")
        logger.info(f"Making GET request to: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            jobs = response.json()
            logger.info(f"Successfully retrieved {len(jobs)} jobs")
            return jobs
        else:
            logger.error(f"API returned status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return []
            
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

def filter_error_jobs(jobs):
    """Filter jobs to find those with error status"""
    error_jobs = []
    
    for job in jobs:
        status = job.get("status", "").upper()
        if "ERROR" in status or "FAIL" in status:
            error_jobs.append(job)
    
    return error_jobs

def main():
    """Main entry point"""
    try:
        # Get all jobs from the API
        all_jobs = get_all_jobs()
        
        if not all_jobs:
            print("\nNo jobs were found via the API. Possible reasons:")
            print("1. The API service isn't running")
            print("2. The API URL is incorrect")
            print("3. Authentication is required but not provided")
            print(f"\nAPI URL used: {AMR_API_URL}")
            return
            
        # Filter for jobs with error status
        error_jobs = filter_error_jobs(all_jobs)
        
        # Print results
        print("\nAMR API JOBS WITH ERROR STATUS:")
        print("===============================")
        
        if not error_jobs:
            print(f"No jobs with error status found among {len(all_jobs)} total jobs.")
        else:
            print(f"Found {len(error_jobs)} jobs with error status out of {len(all_jobs)} total jobs.")
            print(json.dumps(error_jobs, indent=2))
            
            # Print summary table
            print("\nSummary Table:")
            print("-" * 120)
            print(f"{'ID':<36} | {'Status':<15} | {'Created At':<20} | {'Error':<40}")
            print("-" * 120)
            
            for job in error_jobs:
                job_id = job.get('id', 'Unknown')
                status = job.get('status', 'Unknown')
                created_at = job.get('created_at', 'Unknown')
                error = job.get('error', '')
                
                # Truncate error message
                if error and len(str(error)) > 40:
                    error = str(error)[:37] + '...'
                
                print(f"{job_id:<36} | {status:<15} | {created_at:<20} | {error:<40}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
