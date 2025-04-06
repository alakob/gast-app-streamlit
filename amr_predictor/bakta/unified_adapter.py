#!/usr/bin/env python3
"""
Unified Bakta API Adapter

This module provides a consistent interface for Bakta API interactions by
adapting between the standalone script approach and the module approach.
It ensures compatibility in both Docker and non-Docker environments.
"""

import os
import sys
import json
import time
import logging
import requests
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger("bakta-unified-adapter")

class BaktaUnifiedAdapter:
    """
    Unified adapter for Bakta API interactions.
    
    This adapter provides a consistent interface for working with the Bakta API,
    regardless of whether we're using the standalone script approach or the module approach.
    It handles environment-specific issues like Docker path mapping and authentication.
    """
    
    def __init__(self, api_key: Optional[str] = None, environment: str = "prod"):
        """
        Initialize the adapter.
        
        Args:
            api_key: Optional API key for authentication (defaults to env var)
            environment: Environment to use (dev, staging, prod)
        """
        self.api_key = api_key or os.environ.get("BAKTA_API_KEY", "")
        self.environment = environment
        
        # Default base URL based on environment
        env_urls = {
            "dev": os.environ.get("BAKTA_API_URL_DEV", "https://dev-api.bakta.computational.bio/api/v1"),
            "staging": os.environ.get("BAKTA_API_URL_TEST", "https://staging-api.bakta.computational.bio/api/v1"),
            "prod": os.environ.get("BAKTA_API_URL_PROD", "https://bakta.computational.bio/api/v1"),
        }
        
        # Use environment-specific URL or fallback to general URL
        self.base_url = os.environ.get("BAKTA_API_URL", env_urls.get(environment, env_urls["prod"]))
        
        # Check if we're in a Docker environment
        self.is_docker = self._check_if_docker()
        logger.info(f"Initialized BaktaUnifiedAdapter (Docker: {self.is_docker}, Environment: {environment})")
        
        # Create a session with standard headers
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BaktaUnifiedAdapter/1.0"
        })
        
        # Set API key if available
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})
            logger.info("API key is configured")
        else:
            logger.warning("No API key configured, authentication may fail")
    
    def _check_if_docker(self) -> bool:
        """Check if we're running in a Docker container."""
        # Various ways to detect Docker
        if os.path.exists('/.dockerenv'):
            return True
        
        try:
            with open('/proc/1/cgroup', 'r') as f:
                return 'docker' in f.read()
        except:
            pass
            
        # Check for typical Docker environment variables
        if os.environ.get('DOCKER_CONTAINER', ''):
            return True
            
        # Default to safe assumption based on path structure
        if os.path.exists('/app/streamlit') and os.path.exists('/app/amr_predictor'):
            return True
            
        return False
    
    def _map_docker_path(self, path: str) -> str:
        """Map paths between Docker containers if needed."""
        if not self.is_docker:
            return path
            
        # Apply the same path mapping logic as in the memory
        if '/app/results/' in path:
            # Already in Docker path format, use as-is
            return path
            
        # If it's a host path that needs to be mapped to Docker container path
        # (This might need customization based on your setup)
        if path.startswith('/Users/') and '/results/' in path:
            # Extract the relevant part and map to Docker container path
            parts = path.split('/results/')
            if len(parts) > 1:
                return f"/app/results/{parts[1]}"
                
        return path
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None,
                params: Optional[Dict[str, Any]] = None, retries: int = 3) -> Dict[str, Any]:
        """
        Make a request to the API with automatic retries and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint (without base URL)
            data: Request data
            params: Query parameters
            retries: Maximum number of retries
            
        Returns:
            Response data as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        
        for attempt in range(retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=30
                )
                
                # Check for successful response
                response.raise_for_status()
                
                # Try to parse as JSON
                try:
                    return response.json()
                except ValueError:
                    # Return text response as a dict
                    return {"text": response.text}
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{retries}): {str(e)}")
                
                # Only retry certain error types
                if isinstance(e, (requests.exceptions.ConnectionError, 
                                 requests.exceptions.Timeout)) or \
                   (isinstance(e, requests.exceptions.HTTPError) and 
                    e.response.status_code >= 500):
                    # Exponential backoff
                    if attempt < retries - 1:
                        sleep_time = 2 ** attempt
                        logger.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                        continue
                
                # If we get here, we've exhausted retries or hit a non-retryable error
                logger.error(f"Request failed after {attempt+1} attempts: {str(e)}")
                
                # Improve error reporting with response details if available
                error_detail = {}
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = {
                        "status_code": e.response.status_code,
                        "reason": e.response.reason,
                        "text": e.response.text[:500]  # Truncate for readability
                    }
                
                raise Exception(f"API request failed: {str(e)}\nDetails: {json.dumps(error_detail, indent=2)}")
        
        # This should never happen due to the exception above
        raise Exception("Request failed with unknown error")
    
    async def initialize_job(self, name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize a new Bakta annotation job.
        
        Args:
            name: Job name
            config: Optional job configuration
            
        Returns:
            Dictionary with job details
        """
        config = config or {}
        payload = {
            "name": name,
            "repliconTableType": config.get("repliconTableType", "CSV")
        }
        
        logger.info(f"Initializing job: {name}")
        result = self._request("POST", "/job/init", data=payload)
        logger.info(f"Job initialized with ID: {result.get('job', {}).get('jobID')}")
        return result
    
    async def upload_fasta(self, upload_link: str, sequence_data: Union[str, bytes]) -> bool:
        """
        Upload FASTA sequence data to the provided upload link.
        
        Args:
            upload_link: Upload URL provided by initialize_job
            sequence_data: FASTA sequence data as string or bytes
            
        Returns:
            True if successful
        """
        logger.info("Uploading FASTA sequence data")
        
        # Convert string to bytes if needed
        if isinstance(sequence_data, str):
            sequence_data = sequence_data.encode('utf-8')
        
        # Use a separate session for this request to avoid content-type issues
        response = requests.put(upload_link, data=sequence_data)
        
        if response.status_code != 200:
            logger.error(f"Error uploading FASTA: {response.status_code}")
            logger.error(response.text)
            raise Exception(f"FASTA upload failed with status code {response.status_code}")
            
        logger.info("FASTA upload successful")
        return True
    
    async def start_job(self, job_id: str, secret: str, config: Dict[str, Any]) -> bool:
        """
        Start a Bakta annotation job.
        
        Args:
            job_id: Job ID
            secret: Job secret
            config: Job configuration parameters
            
        Returns:
            True if successful
        """
        logger.info(f"Starting job {job_id}")
        
        payload = {
            "config": {
                "completeGenome": config.get("completeGenome", False),
                "compliant": config.get("compliant", True),
                "dermType": config.get("dermType", None),
                "genus": config.get("genus", "Unspecified"),
                "hasReplicons": config.get("hasReplicons", False),
                "keepContigHeaders": config.get("keepContigHeaders", True),
                "locus": config.get("locus", ""),
                "locusTag": config.get("locusTag", ""),
                "minContigLength": config.get("minContigLength", 0),
                "plasmid": config.get("plasmid", ""),
                "prodigalTrainingFile": config.get("prodigalTrainingFile", None),
                "species": config.get("species", "Unspecified"),
                "strain": config.get("strain", ""),
                "translationTable": config.get("translationTable", 11)
            },
            "job": {
                "jobID": job_id,
                "secret": secret
            }
        }
        
        self._request("POST", "/job/start", data=payload)
        logger.info(f"Job {job_id} started successfully")
        return True
    
    async def check_job_status(self, job_id: str, secret: str) -> Dict[str, Any]:
        """
        Check the status of a job.
        
        Args:
            job_id: Job ID
            secret: Job secret
            
        Returns:
            Job status data
        """
        logger.info(f"Checking status of job {job_id}")
        
        payload = {
            "jobs": [
                {
                    "jobID": job_id,
                    "secret": secret
                }
            ]
        }
        
        result = self._request("POST", "/job/list", data=payload)
        
        # Extract status from the response
        if "jobs" in result and len(result["jobs"]) > 0:
            status = result["jobs"][0].get("jobStatus", "UNKNOWN")
            logger.info(f"Job {job_id} status: {status}")
        else:
            logger.warning(f"No status information found for job {job_id}")
        
        return result
    
    async def get_job_results(self, job_id: str, secret: str) -> Dict[str, Any]:
        """
        Get the results for a completed job.
        
        Args:
            job_id: Job ID
            secret: Job secret
            
        Returns:
            Job results data
        """
        logger.info(f"Getting results for job {job_id}")
        
        payload = {
            "jobID": job_id,
            "secret": secret
        }
        
        result = self._request("POST", "/job/result", data=payload)
        logger.info(f"Retrieved results for job {job_id}")
        return result
    
    async def download_result_file(self, url: str, output_path: Union[str, Path]) -> str:
        """
        Download a result file from the given URL.
        
        Args:
            url: File download URL
            output_path: Path to save the file
            
        Returns:
            Path to the downloaded file
        """
        logger.info(f"Downloading result file to {output_path}")
        output_path = Path(output_path)
        
        # Make sure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded file to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    async def download_all_results(self, results: Dict[str, Any], output_dir: Union[str, Path] = None) -> Dict[str, str]:
        """
        Download all result files from the results response.
        
        Args:
            results: Results data from get_job_results
            output_dir: Directory to save files (defaults to BAKTA_RESULTS_DIR env var)
            
        Returns:
            Dictionary mapping file types to downloaded file paths
        """
        # Determine output directory
        if output_dir is None:
            output_dir = os.environ.get("BAKTA_RESULTS_DIR", "bakta_results")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading all results to {output_dir}")
        
        # Get result files
        result_files = results.get("ResultFiles", {})
        if not result_files:
            logger.warning("No result files found in response")
            return {}
        
        downloaded_files = {}
        for file_type, url in result_files.items():
            try:
                # Determine file extension based on file type
                extension = ""
                if file_type == "GFF3":
                    extension = ".gff3"
                elif file_type == "GENBANK":
                    extension = ".gbff"
                elif file_type == "FASTA":
                    extension = ".fasta"
                elif file_type == "JSON":
                    extension = ".json"
                elif file_type == "TSV":
                    extension = ".tsv"
                else:
                    extension = f".{file_type.lower()}"
                
                # Create output file path
                job_id = results.get("job", {}).get("jobID", "unknown")
                file_name = f"{job_id}_{file_type.lower()}{extension}"
                output_path = output_dir / file_name
                
                # Download the file
                downloaded_path = await self.download_result_file(url, output_path)
                downloaded_files[file_type] = downloaded_path
                logger.info(f"Downloaded {file_type} file to {downloaded_path}")
                
            except Exception as e:
                logger.error(f"Error downloading {file_type} file: {str(e)}")
        
        logger.info(f"Downloaded {len(downloaded_files)} of {len(result_files)} files")
        return downloaded_files
    
    async def poll_job_status(self, job_id: str, secret: str, 
                            max_retries: int = 12, sleep_time: int = 10) -> Dict[str, Any]:
        """
        Poll the job status until it's completed or failed.
        
        Args:
            job_id: Job ID
            secret: Job secret
            max_retries: Maximum number of polling attempts
            sleep_time: Time to sleep between attempts (seconds)
            
        Returns:
            Final job status data
        """
        logger.info(f"Polling status for job {job_id} (max {max_retries} attempts, {sleep_time}s interval)")
        
        for i in range(max_retries):
            status_response = await self.check_job_status(job_id, secret)
            
            if "jobs" not in status_response or not status_response["jobs"]:
                logger.warning(f"Invalid status response for job {job_id}")
                continue
                
            job_status = status_response["jobs"][0].get("jobStatus")
            logger.info(f"Current status: {job_status} (Check {i+1}/{max_retries})")
            
            if job_status == "SUCCESSFUL":
                logger.info(f"Job {job_id} completed successfully")
                return status_response
                
            elif job_status == "ERROR":
                logger.error(f"Job {job_id} failed with ERROR status")
                return status_response
                
            # For all other statuses, keep polling
            if i < max_retries - 1:
                logger.info(f"Waiting {sleep_time} seconds before checking again...")
                await asyncio.sleep(sleep_time)
        
        logger.warning(f"Max retries ({max_retries}) reached for job {job_id}")
        return await self.check_job_status(job_id, secret)
    
    async def submit_job(self, sequence_data: Union[str, bytes], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a new annotation job to Bakta (end-to-end workflow).
        
        This is a high-level method that combines initialize_job, upload_fasta, and start_job
        to provide a complete job submission workflow similar to the standalone script.
        
        Args:
            sequence_data: FASTA sequence data as string or bytes
            config: Job configuration parameters
            
        Returns:
            Dictionary with job details
        """
        # Make sure we have a job name
        job_name = config.get("name", f"bakta_job_{int(time.time())}")
        logger.info(f"Submitting job: {job_name}")
        
        # Initialize the job
        init_response = await self.initialize_job(job_name, config)
        
        # Extract job details
        job_id = init_response.get("job", {}).get("jobID")
        secret = init_response.get("job", {}).get("secret")
        upload_link = init_response.get("uploadLinkFasta")
        
        if not job_id or not secret or not upload_link:
            logger.error("Missing required job information in initialization response")
            raise Exception("Invalid job initialization response")
            
        logger.info(f"Job initialized with ID: {job_id}")
        
        # Upload the sequence data
        await self.upload_fasta(upload_link, sequence_data)
        
        # Start the job
        await self.start_job(job_id, secret, config)
        
        # Return job details
        return {
            "id": job_id,
            "secret": secret,
            "name": job_name,
            "status": "STARTED",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

# Create a convenience function for instantiating the adapter
def get_adapter(api_key: Optional[str] = None, environment: str = "prod") -> BaktaUnifiedAdapter:
    """
    Get a BaktaUnifiedAdapter instance.
    
    Args:
        api_key: Optional API key for authentication
        environment: Environment to use (dev, staging, prod)
        
    Returns:
        BaktaUnifiedAdapter instance
    """
    return BaktaUnifiedAdapter(api_key, environment)

# Helper function to run async functions
def run_async(func, *args, **kwargs):
    """Run an async function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func(*args, **kwargs))
    finally:
        loop.close()
