#!/usr/bin/env python3
import sys
import json
import requests
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("job_checker")

# API URL - Try to get from environment or use default
AMR_API_URL = os.environ.get("AMR_API_URL", "http://localhost:8000")
AMR_API_KEY = os.environ.get("AMR_API_KEY", "")

def check_job_status(job_id, api_url=AMR_API_URL, api_key=AMR_API_KEY):
    """Check status of a specific AMR job."""
    logger.info(f"Checking status for job ID: {job_id}")
    logger.info(f"Using API URL: {api_url}")
    
    # Set headers with API key if provided
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        # First try to get the job status
        status_url = f"{api_url}/jobs/{job_id}"
        logger.info(f"Making GET request to: {status_url}")
        status_response = requests.get(status_url, headers=headers, timeout=10)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            logger.info(f"Job status: {json.dumps(status_data, indent=2)}")
            
            # If job is successful, try to get results
            if status_data.get("status") == "SUCCESSFUL":
                try:
                    results_url = f"{api_url}/jobs/{job_id}/results"
                    logger.info(f"Job successful, fetching results from: {results_url}")
                    results_response = requests.get(results_url, headers=headers, timeout=10)
                    
                    if results_response.status_code == 200:
                        results_data = results_response.json()
                        logger.info(f"Results retrieved successfully")
                        return {
                            "status": status_data,
                            "results": results_data
                        }
                    else:
                        error_msg = f"Error fetching results: HTTP {results_response.status_code}"
                        logger.error(error_msg)
                        return {
                            "status": status_data,
                            "error_fetching_results": error_msg,
                            "response_text": results_response.text
                        }
                except Exception as e:
                    logger.error(f"Exception while fetching results: {str(e)}")
                    return {
                        "status": status_data,
                        "error_fetching_results": str(e)
                    }
            
            return status_data
        else:
            error_msg = f"Error getting job status: HTTP {status_response.status_code}"
            logger.error(error_msg)
            try:
                response_text = status_response.text
            except:
                response_text = "Could not retrieve response text"
            
            return {
                "error": error_msg,
                "response_text": response_text,
                "status_code": status_response.status_code
            }
    except requests.RequestException as e:
        logger.error(f"Request exception: {str(e)}")
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = "0e855cc1-ca74-4042-b5ce-17358d6cd2d8"  # Default to the job ID provided
    
    # Log current environment settings
    logger.info(f"Environment AMR_API_URL: {os.environ.get('AMR_API_URL', 'Not set')}")
    logger.info(f"Using AMR_API_URL: {AMR_API_URL}")
    
    result = check_job_status(job_id)
    print("\nRESULT:")
    print(json.dumps(result, indent=2))
