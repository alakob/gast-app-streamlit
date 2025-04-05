#!/usr/bin/env python
"""
Test script to interact with the AMR API using file upload.
"""
import requests
import logging
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("amr-api-test")

# API configuration
API_URL = "http://localhost:8000"

def test_file_upload():
    """Test the predict endpoint with a file upload."""
    
    # Create a temporary FASTA file
    with tempfile.NamedTemporaryFile(suffix=".fasta", mode="w+", delete=False) as f:
        fasta_content = """>test_sequence
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
"""
        f.write(fasta_content)
        fasta_path = f.name
    
    try:
        logger.info(f"Testing file upload to {API_URL}/predict")
        
        # Prepare the file for upload
        with open(fasta_path, 'rb') as f:
            files = {'file': ('test.fasta', f, 'text/plain')}
            
            # Send the request
            response = requests.post(f"{API_URL}/predict", files=files)
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code < 400:
                result = response.json()
                logger.info(f"Response data: {result}")
                
                # Check if we got a job ID
                if "job_id" in result:
                    job_id = result["job_id"]
                    logger.info(f"Success! Job ID received: {job_id}")
                    
                    # Now try to check the job status
                    logger.info(f"Checking job status for {job_id}")
                    status_response = requests.get(f"{API_URL}/jobs/{job_id}")
                    logger.info(f"Status response: {status_response.status_code}")
                    
                    if status_response.status_code < 400:
                        status_data = status_response.json()
                        logger.info(f"Job status: {status_data}")
                    else:
                        logger.error(f"Failed to get job status: {status_response.text}")
                else:
                    logger.warning("No job_id in response")
            else:
                logger.error(f"API error: {response.status_code}")
                logger.error(f"Error details: {response.text}")
    
    finally:
        # Clean up
        if os.path.exists(fasta_path):
            os.remove(fasta_path)

if __name__ == "__main__":
    test_file_upload()
