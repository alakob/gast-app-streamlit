#!/usr/bin/env python3
"""
Bakta Executor Module - Adapted from scripts/submit_bakta.py

This module provides functionality to submit sequences to the Bakta API
for genome annotation without requiring authentication.
"""

import os
import requests
import json
import time
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple

# Configure simple direct logging for visibility in Docker logs
import sys

# Reset the root logger to ensure we start fresh
for handler in logging.root.handlers:
    logging.root.removeHandler(handler)

# Configure a direct handler to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    "\033[91m%(asctime)s - %(levelname)s - BAKTA - %(message)s\033[0m"  # ANSI red color
))

# Create logger with a direct console handler
logger = logging.getLogger("bakta-executor")
logger.setLevel(logging.INFO)
logger.handlers = [handler]  # Replace any existing handlers
logger.propagate = False  # Don't propagate to parent loggers

# Add timing and request ID tracking
import time
import uuid

# Request tracking for correlation in logs
request_id = str(uuid.uuid4())[:8]

# Bakta API base URL - Force the correct URL regardless of environment variable
BASE_URL = "https://api.bakta.computational.bio/api/v1"
# Log the override
logger.info(f"Forcing correct Bakta API URL: {BASE_URL} (overriding environment variable)")

# Directory to store results
DEFAULT_RESULTS_DIR = os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")


def initialize_job(job_name: str = "GAST_analysis"):
    """Initialize a new Bakta annotation job
    
    Args:
        job_name: Name for the job
        
    Returns:
        dict: Job initialization data including job ID and upload URL
    """
    init_url = f"{BASE_URL}/job/init"
    
    payload = {
        "name": job_name,
        "repliconTableType": "CSV"
    }
    
    logger.info(f"[REQ-{request_id}] Initializing Bakta job with name: {job_name}")
    logger.info(f"[REQ-{request_id}] Using Bakta API URL: {BASE_URL}")
    logger.info(f"[REQ-{request_id}] Sending POST request to: {init_url}")
    logger.info(f"[REQ-{request_id}] Request payload: {json.dumps(payload)}")
    
    start_time = time.time()
    try:
        response = requests.post(init_url, json=payload)
        duration = time.time() - start_time
        
        logger.info(f"[REQ-{request_id}] Received response in {duration:.2f}s with status code: {response.status_code}")
        
        # Log response headers for debugging
        logger.debug(f"[REQ-{request_id}] Response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        job_data = response.json()
        job_id = job_data.get('job', {}).get('jobID')
        secret = job_data.get('job', {}).get('secret')
        
        logger.info(f"[REQ-{request_id}] Job initialized with ID: {job_id}, secret: {secret}")
        logger.info(f"[REQ-{request_id}] Response content: {json.dumps(job_data)}")
        
        return job_data
    except requests.exceptions.HTTPError as e:
        duration = time.time() - start_time
        logger.error(f"[REQ-{request_id}] HTTP error initializing job after {duration:.2f}s: {str(e)}")
        logger.error(f"[REQ-{request_id}] Response content: {e.response.text}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[REQ-{request_id}] Error initializing job after {duration:.2f}s: {str(e)}")
        raise


def upload_fasta(upload_link: str, fasta_data: str):
    """Upload the FASTA sequence data
    
    Args:
        upload_link: URL for uploading FASTA data
        fasta_data: FASTA sequence data as string
        
    Returns:
        bool: True if upload was successful
    """
    logger.info(f"[REQ-{request_id}] Uploading FASTA data to: {upload_link}")
    
    # Log the FASTA content (truncated if too long)
    if len(fasta_data) > 500:
        logger.info(f"[REQ-{request_id}] FASTA content (truncated): {fasta_data[:250]}...{fasta_data[-250:]}")
    else:
        logger.info(f"[REQ-{request_id}] FASTA content: {fasta_data}")
    
    start_time = time.time()
    try:
        response = requests.put(upload_link, data=fasta_data)
        duration = time.time() - start_time
        
        logger.info(f"[REQ-{request_id}] Received upload response in {duration:.2f}s with status code: {response.status_code}")
        response.raise_for_status()
        
        logger.info(f"[REQ-{request_id}] FASTA data uploaded successfully in {duration:.2f}s")
        return True
    except requests.exceptions.HTTPError as e:
        duration = time.time() - start_time
        logger.error(f"[REQ-{request_id}] HTTP error uploading FASTA after {duration:.2f}s: {str(e)}")
        logger.error(f"[REQ-{request_id}] Response content: {e.response.text}")
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[REQ-{request_id}] Error uploading FASTA after {duration:.2f}s: {str(e)}")
        raise


def start_job(job_id: str, secret: str):
    """Start the annotation job
    
    Args:
        job_id: Job ID
        secret: Job secret
        
    Returns:
        bool: True if job started successfully
    """
    start_url = f"{BASE_URL}/job/start"
    
    # Important: prodigalTrainingFile is set to null (None in Python)
    # This should prevent the API from trying to use a prodigal training file
    payload = {
        "config": {
            "completeGenome": False,
            "compliant": True,
            "dermType": None,
            "genus": "Unspecified",
            "hasReplicons": False,
            "keepContigHeaders": True,
            "locus": "GAST",
            "locusTag": "GAST",
            "minContigLength": 0,
            "plasmid": "",
            "prodigalTrainingFile": None,  # Explicitly set to None/null
            "species": "Unspecified",
            "strain": "GAST-Analysis",
            "translationTable": 11
        },
        "job": {
            "jobID": job_id,
            "secret": secret
        }
    }
    
    logger.info(f"Starting job {job_id}")
    
    try:
        response = requests.post(start_url, json=payload)
        response.raise_for_status()
        
        logger.info(f"Job {job_id} started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting job: {str(e)}")
        raise


def check_job_status(job_id: str, secret: str) -> dict:
    """Check the status of the job
    
    Args:
        job_id: Job ID
        secret: Job secret
        
    Returns:
        dict: Job status information
    """
    list_url = f"{BASE_URL}/job/list"
    
    payload = {
        "jobs": [
            {
                "jobID": job_id,
                "secret": secret
            }
        ]
    }
    
    try:
        response = requests.post(list_url, json=payload)
        response.raise_for_status()
        
        status_data = response.json()
        job_status = status_data.get("jobs", [{}])[0].get("jobStatus", "UNKNOWN")
        logger.info(f"Job {job_id} status: {job_status}")
        
        return status_data
    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        raise


def get_job_logs(job_id: str, secret: str) -> str:
    """Get the logs of a job
    
    Args:
        job_id: Job ID
        secret: Job secret
        
    Returns:
        str: Job logs
    """
    logs_url = f"{BASE_URL}/job/logs?jobID={job_id}&secret={secret}"
    
    try:
        response = requests.get(logs_url)
        response.raise_for_status()
        
        logs = response.text
        logger.info(f"Retrieved logs for job {job_id}")
        
        return logs
    except Exception as e:
        logger.error(f"Error getting job logs: {str(e)}")
        raise


def get_job_results(job_id: str, secret: str) -> dict:
    """Get the results of a completed job
    
    Args:
        job_id: Job ID
        secret: Job secret
        
    Returns:
        dict: Job results including file URLs
    """
    result_url = f"{BASE_URL}/job/result"
    
    payload = {
        "jobID": job_id,
        "secret": secret
    }
    
    try:
        response = requests.post(result_url, json=payload)
        response.raise_for_status()
        
        results = response.json()
        logger.info(f"Retrieved results for job {job_id}")
        
        return results
    except Exception as e:
        logger.error(f"Error getting job results: {str(e)}")
        raise


def download_result_file(url: str, output_path: Union[str, Path]) -> Path:
    """Download a result file from the given URL
    
    Args:
        url: URL to download from
        output_path: Path to save the file
        
    Returns:
        Path: Path to the downloaded file
    """
    output_path = Path(output_path)
    
    try:
        logger.info(f"Downloading file to {output_path}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Make sure the output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
        logger.info(f"Download complete: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise


def download_all_results(results: dict, output_dir: Union[str, Path] = None) -> int:
    """Download all result files from the results response
    
    Args:
        results: Results data from get_job_results
        output_dir: Directory to save the files
        
    Returns:
        int: Number of files successfully downloaded
    """
    if output_dir is None:
        output_dir = Path(DEFAULT_RESULTS_DIR)
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter out the 'sequence' entry which isn't a file
    result_files = results.get("ResultFiles", {})
    if "sequence" in result_files:
        del result_files["sequence"]
    
    total_files = len(result_files)
    successful_downloads = 0
    
    logger.info(f"Downloading {total_files} result files to {output_dir}")
    
    for file_type, url in result_files.items():
        try:
            # Determine file extension based on file type
            if file_type == "faa":
                extension = ".faa"
                file_desc = "Proteins (FASTA)"
            elif file_type == "ffn":
                extension = ".ffn"
                file_desc = "Genes (FASTA)"
            elif file_type == "fna":
                extension = ".fna"
                file_desc = "Contigs (FASTA)"
            elif file_type == "gbff":
                extension = ".gbff"
                file_desc = "GenBank"
            elif file_type == "gff3":
                extension = ".gff3"
                file_desc = "GFF3"
            elif file_type == "hypotheticalProteinFaa":
                extension = ".hypothetical.faa"
                file_desc = "Hypothetical Proteins (FASTA)"
            elif file_type == "json":
                extension = ".json"
                file_desc = "JSON"
            elif file_type == "tsv":
                extension = ".tsv"
                file_desc = "TSV"
            elif file_type == "txt":
                extension = ".txt"
                file_desc = "TXT"
            else:
                extension = f".{file_type}"
                file_desc = file_type
                
            # Use job ID from URL as base filename to ensure uniqueness
            job_id = results.get("jobID", "unknown_job")
            output_file = output_dir / f"{job_id}.{file_type}{extension}"
            
            # Download the file
            download_result_file(url, output_file)
            successful_downloads += 1
            logger.info(f"✓ Downloaded {file_desc} file: {output_file}")
        except Exception as e:
            logger.error(f"✗ Failed to download {file_type}: {str(e)}")
    
    logger.info(f"Downloaded {successful_downloads}/{total_files} files to '{output_dir}' directory")
    return successful_downloads


def poll_job_status(job_id: str, secret: str, max_retries: int = 12, sleep_time: int = 10) -> dict:
    """Poll the job status until it's completed or failed
    
    Args:
        job_id: Job ID
        secret: Job secret
        max_retries: Maximum number of status checks
        sleep_time: Time to sleep between checks in seconds
        
    Returns:
        dict: Final job status
    """
    for i in range(max_retries):
        status_response = check_job_status(job_id, secret)
        job_status = status_response.get("jobs", [{}])[0].get("jobStatus")
        
        logger.info(f"Current status: {job_status} (Check {i+1}/{max_retries})")
        
        if job_status == "SUCCESSFUL":
            logger.info("Job completed successfully!")
            try:
                results = get_job_results(job_id, secret)
                logger.info("Results URLs:")
                for file_type, url in results.get("ResultFiles", {}).items():
                    logger.info(f"{file_type}: {url}")
                
                # Download all result files
                download_all_results(results)
            except Exception as e:
                logger.error(f"Error getting results: {str(e)}")
            return status_response
            
        elif job_status == "ERROR":
            logger.error("Job failed. Fetching logs for more information...")
            try:
                logs = get_job_logs(job_id, secret)
                logger.info("Job Logs:")
                logger.info("="*80)
                logger.info(logs)
                logger.info("="*80)
            except Exception as e:
                logger.error(f"Error getting logs: {str(e)}")
            return status_response
        
        logger.info(f"Waiting {sleep_time} seconds before checking again...")
        time.sleep(sleep_time)
    
    logger.warning(f"Max retries ({max_retries}) reached. The job is still running.")
    return check_job_status(job_id, secret)


def submit_bakta_analysis(fasta_content: str, job_name: str = None, output_dir: Union[str, Path] = None) -> Tuple[str, str, dict]:
    """Submit a FASTA sequence for Bakta analysis
    
    Args:
        fasta_content: FASTA sequence as string
        job_name: Name for the job (optional)
        output_dir: Directory to save results (default: /app/results/bakta)
        
    Returns:
        tuple: (job_id, secret, status_data)
    """
    # Generate a unique request ID for tracking this operation through logs
    global request_id
    request_id = str(uuid.uuid4())[:8]
    
    if job_name is None:
        job_name = f"GAST_analysis_{int(time.time())}"
        
    if output_dir is None:
        output_dir = DEFAULT_RESULTS_DIR
    
    total_start_time = time.time()
    logger.info(f"[REQ-{request_id}] === STARTING BAKTA ANALYSIS OPERATION ====")
    logger.info(f"[REQ-{request_id}] Job name: {job_name}")
    logger.info(f"[REQ-{request_id}] Output directory: {output_dir}")
    logger.info(f"[REQ-{request_id}] Environment variables:")
    # Log all Bakta-related environment variables with masking
    for key, value in sorted(os.environ.items()):
        if key.startswith('BAKTA_'):
            masked_value = value
            if 'KEY' in key or 'TOKEN' in key or 'SECRET' in key:
                # Mask sensitive data but keep first/last few chars for debugging
                if len(value) > 8:
                    masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
                else:
                    masked_value = '****'
            logger.info(f"[REQ-{request_id}]   {key}: {masked_value}")
    
    # Make sure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"[REQ-{request_id}] Created output directory: {output_dir}")
        
    try:
        # Step 1: Initialize the job
        logger.info(f"[REQ-{request_id}] --- STEP 1: Initializing Bakta job ---")
        init_response = initialize_job(job_name)
        
        job_id = init_response.get("job", {}).get("jobID")
        secret = init_response.get("job", {}).get("secret")
        upload_link = init_response.get("uploadLinkFasta")
        
        if not all([job_id, secret, upload_link]):
            logger.error(f"[REQ-{request_id}] Missing required data from job initialization")
            logger.error(f"[REQ-{request_id}] Response content: {json.dumps(init_response)}")
            raise ValueError("Missing required data from job initialization")
            
        logger.info(f"[REQ-{request_id}] Job ID: {job_id}")
        # Mask the secret partially
        masked_secret = secret[:4] + '*' * (len(secret) - 8) + secret[-4:] if len(secret) > 8 else '****'
        logger.info(f"[REQ-{request_id}] Secret: {masked_secret}")
        
        # Step 2: Upload the FASTA sequence
        logger.info(f"[REQ-{request_id}] --- STEP 2: Uploading sequence ---")
        upload_fasta(upload_link, fasta_content)
        
        # Step 3: Start the job
        logger.info(f"[REQ-{request_id}] --- STEP 3: Starting annotation job ---")
        start_job(job_id, secret)
        
        logger.info(f"[REQ-{request_id}] Job successfully started!")
        
        # Step 4: Poll for job completion and download results
        logger.info(f"[REQ-{request_id}] --- STEP 4: Tracking job status ---")
        final_status = poll_job_status(job_id, secret)
        job_status = final_status.get("jobs", [{}])[0].get("jobStatus")
        
        # Save job info to a file for easy reference
        info_path = Path(output_dir) / f"{job_id}_info.txt"
        with open(info_path, "w") as f:
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Secret: {secret}\n")
            f.write(f"URL: https://bakta.computational.bio/annotation/{job_id}?secret={secret}\n")
            f.write(f"Final Status: {job_status}\n")
            
        total_duration = time.time() - total_start_time
        logger.info(f"[REQ-{request_id}] Job info saved to: {info_path}")
        logger.info(f"[REQ-{request_id}] To view your job results, visit:")
        logger.info(f"[REQ-{request_id}] https://bakta.computational.bio/annotation/{job_id}?secret={secret}")
        logger.info(f"[REQ-{request_id}] === COMPLETED BAKTA ANALYSIS OPERATION IN {total_duration:.2f}s ====")
        
        return job_id, secret, final_status
        
    except Exception as e:
        total_duration = time.time() - total_start_time
        logger.error(f"[REQ-{request_id}] Error in Bakta analysis after {total_duration:.2f}s: {str(e)}")
        logger.error(f"[REQ-{request_id}] === BAKTA ANALYSIS OPERATION FAILED ====")
        raise


if __name__ == "__main__":
    # Example usage when run as a script
    if len(sys.argv) < 2:
        print("Usage: python bakta_executor.py [fasta_file_path]")
        sys.exit(1)
        
    fasta_path = sys.argv[1]
    with open(fasta_path, "r") as f:
        fasta_content = f.read()
        
    submit_bakta_analysis(fasta_content)
