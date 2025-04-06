#!/usr/bin/env python3
"""
Bakta API connection module.
Provides a unified interface for the Bakta genome annotation API with comprehensive colored logging.
"""
import os
import sys
import json
import time
import logging
import hashlib
import functools
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# ANSI color codes for terminal coloring
class Colors:
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Custom colored formatter for Bakta API operations
class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BLUE,
        logging.INFO: Colors.RED,  # Using RED for Bakta operations as requested
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED + Colors.BOLD,
        logging.CRITICAL: Colors.RED + Colors.BOLD + Colors.UNDERLINE
    }
    
    def format(self, record):
        # Get the original format
        log_message = super().format(record)
        
        # Add coloring
        levelname = record.levelname
        levelno = record.levelno
        
        # Add appropriate color - RED for INFO and proper colors for other levels
        color = self.LEVEL_COLORS.get(levelno, Colors.RESET)
        
        # For Bakta API logger, make sure all messages stand out with bold red and a clear text prefix
        if record.name == 'bakta-api':
            # Add both colored prefix and a text-only prefix for contexts where colors are stripped
            prefix = f"{Colors.RED}{Colors.BOLD}[BAKTA]"
            # Ensure the log is prefixed with [BAKTA] even if colors are stripped
            if not log_message.startswith("[BAKTA]"):
                log_message = f"[BAKTA] {log_message}"
            return f"{prefix} {log_message}{Colors.RESET}"
        
        return f"{color}{log_message}{Colors.RESET}"

# Configure comprehensive logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bakta-connect')

# Create a separate detailed logger for API operations (RED colored)
api_logger = logging.getLogger('bakta-api')
api_logger.setLevel(logging.DEBUG)

# Create console handler with colored formatter for visible distinction
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add the handler to the API logger
api_logger.addHandler(console_handler)
api_logger.propagate = False  # Prevent duplicate logs

# Ensure results directory exists
results_dir = os.environ.get('BAKTA_RESULTS_DIR', '/app/results/bakta')
os.makedirs(results_dir, exist_ok=True)
logger.info(f"Bakta results directory: {results_dir}")

# Set environment variables if needed and log their values
if not os.environ.get('BAKTA_API_URL'):
    os.environ['BAKTA_API_URL'] = 'https://api.bakta.computational.bio/api/v1'

# Log all Bakta-related environment variables
api_logger.info("Bakta environment configuration:")
for key, value in sorted(os.environ.items()):
    if key.startswith('BAKTA_'):
        masked_value = value
        if 'KEY' in key or 'TOKEN' in key:
            # Mask sensitive data but keep first/last few chars for troubleshooting
            if len(value) > 8:
                masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
            else:
                masked_value = '****'
        api_logger.info(f"  {key}: {masked_value}")

# Important: No authentication is needed for Bakta API
api_logger.info("Bakta API uses direct access without authentication")

# Track availability status
BAKTA_AVAILABLE = False
bakta_adapter = None

# Import our integration point
try:
    # Make sure we can find the modules
    sys.path.append('/app')
    logger.info("Added /app to module search path")
    
    # Try to import from standalone script first
    try:
        import submit_bakta
        logger.info(f"Successfully imported standalone Bakta script from {submit_bakta.__file__}")
        
        # Create an adapter class with comprehensive logging
        class BaktaInterface:
            def __init__(self):
                self.base_url = submit_bakta.BASE_URL
                logger.info(f"Initialized BaktaInterface with API URL: {self.base_url}")
                
                # Set up job tracking for diagnostics
                self.job_history = {}
            
            def _generate_job_id(self, fasta_content, job_name):
                """Generate a unique tracking ID for internal use"""
                content_hash = hashlib.md5(fasta_content.encode('utf-8') if isinstance(fasta_content, str) else fasta_content).hexdigest()[:8]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"job_{timestamp}_{content_hash}_{job_name if job_name else 'unnamed'}"
            
            def submit_job(self, fasta_data=None, job_name=None, config_params=None, fasta_content=None):
                """Submit a job to the Bakta API with detailed logging."""
                # Start timing
                start_time = time.time()
                tracking_id = None
                
                try:
                    # Log incoming parameters
                    api_logger.info(f"Submitting Bakta job: name='{job_name}', config={config_params}")
                    
                    # Handle different parameter formats
                    if fasta_content is None and fasta_data is not None:
                        if isinstance(fasta_data, str) and os.path.exists(fasta_data):
                            api_logger.info(f"Reading FASTA content from file: {fasta_data}")
                            with open(fasta_data, 'r') as f:
                                fasta_content = f.read()
                            # Calculate size for logging
                            file_size = os.path.getsize(fasta_data)
                            api_logger.info(f"FASTA file size: {file_size} bytes, content length: {len(fasta_content)} chars")
                        else:
                            fasta_content = str(fasta_data)
                            api_logger.info(f"Using provided data as FASTA content, length: {len(fasta_content)} chars")
                    elif fasta_content is not None:
                        api_logger.info(f"Using provided FASTA content directly, length: {len(fasta_content)} chars")
                    else:
                        api_logger.error("No FASTA data provided")
                        raise ValueError("No FASTA data provided (fasta_data or fasta_content required)")
                    
                    # Generate tracking ID
                    tracking_id = self._generate_job_id(fasta_content, job_name)
                    api_logger.info(f"Internal tracking ID: {tracking_id}")
                    
                    # Merge config parameters
                    config = {}
                    if job_name:
                        config['name'] = job_name
                    if config_params:
                        config.update(config_params)
                    api_logger.info(f"Final job configuration: {json.dumps(config)}")
                    
                    # Initialize job - API CALL #1
                    api_logger.info(f"Initializing Bakta job at {self.base_url}")
                    init_response = submit_bakta.initialize_job()
                    
                    # Log detailed response
                    job_id = init_response['job']['jobID']
                    secret = init_response['job']['secret']
                    upload_link = init_response['uploadLinkFasta']
                    api_logger.info(f"Job initialized: ID={job_id}, secret={'*'*(len(secret)-8) + secret[-4:] if len(secret) > 8 else '****'}")
                    api_logger.debug(f"Upload link: {upload_link}")
                    
                    # Upload FASTA - API CALL #2
                    api_logger.info(f"Uploading FASTA content ({len(fasta_content)} chars) for job {job_id}")
                    upload_start = time.time()
                    submit_bakta.upload_fasta(upload_link, fasta_content)
                    upload_duration = time.time() - upload_start
                    api_logger.info(f"FASTA upload completed in {upload_duration:.2f} seconds")
                    
                    # Start job - API CALL #3
                    api_logger.info(f"Starting Bakta job {job_id}")
                    start_job_start = time.time()
                    submit_bakta.start_job(job_id, secret)
                    start_job_duration = time.time() - start_job_start
                    api_logger.info(f"Job start request completed in {start_job_duration:.2f} seconds")
                    
                    # Store job details for tracking
                    total_duration = time.time() - start_time
                    self.job_history[job_id] = {
                        'tracking_id': tracking_id,
                        'job_id': job_id,
                        'secret': secret,
                        'submitted_at': datetime.now().isoformat(),
                        'name': config.get('name', 'unnamed'),
                        'upload_duration': upload_duration,
                        'start_duration': start_job_duration,
                        'total_submit_duration': total_duration
                    }
                    
                    logger.info(f"Successfully submitted Bakta job {job_id} in {total_duration:.2f} seconds")
                    
                    # Return job ID
                    return job_id
                    
                except Exception as e:
                    error_msg = f"Error submitting Bakta job: {str(e)}"
                    if tracking_id:
                        error_msg += f" (tracking ID: {tracking_id})"
                    logger.error(error_msg)
                    api_logger.exception("Detailed exception info for job submission error:")
                    raise
                
            def check_job_status(self, job_id, secret):
                """Check the status of a job with detailed logging."""
                try:
                    api_logger.info(f"Checking status of Bakta job {job_id}")
                    start_time = time.time()
                    response = submit_bakta.check_job_status(job_id, secret)
                    duration = time.time() - start_time
                    
                    # Log the response details
                    status = response.get('job', {}).get('status', 'UNKNOWN')
                    api_logger.info(f"Job {job_id} status: {status} (query took {duration:.2f}s)")
                    
                    # Update job history with status
                    if job_id in self.job_history:
                        self.job_history[job_id]['last_checked'] = datetime.now().isoformat()
                        self.job_history[job_id]['last_status'] = status
                    
                    return response
                except Exception as e:
                    logger.error(f"Error checking status of Bakta job {job_id}: {str(e)}")
                    api_logger.exception(f"Detailed exception info for status check error:")
                    raise
                
            def get_job_results(self, job_id, secret):
                """Get the results of a job with detailed logging."""
                try:
                    api_logger.info(f"Retrieving results for Bakta job {job_id}")
                    start_time = time.time()
                    response = submit_bakta.get_job_results(job_id, secret)
                    duration = time.time() - start_time
                    
                    # Log the results summary
                    num_files = len(response.get('data', {}).get('files', []))
                    api_logger.info(f"Retrieved {num_files} result files for job {job_id} in {duration:.2f}s")
                    
                    # Log detailed file list
                    if api_logger.isEnabledFor(logging.DEBUG):
                        files = response.get('data', {}).get('files', [])
                        for idx, file_info in enumerate(files):
                            api_logger.debug(f"Result file {idx+1}/{num_files}: {file_info.get('name')} ({file_info.get('size', 0)} bytes)")
                    
                    # Update job history
                    if job_id in self.job_history:
                        self.job_history[job_id]['results_retrieved_at'] = datetime.now().isoformat()
                        self.job_history[job_id]['result_file_count'] = num_files
                    
                    return response
                except Exception as e:
                    logger.error(f"Error retrieving results for Bakta job {job_id}: {str(e)}")
                    api_logger.exception(f"Detailed exception info for results retrieval error:")
                    raise
                
            def download_result_file(self, file_url, output_path):
                """Download a result file with detailed logging."""
                try:
                    api_logger.info(f"Downloading result file from {file_url} to {output_path}")
                    start_time = time.time()
                    result = submit_bakta.download_result_file(file_url, output_path)
                    duration = time.time() - start_time
                    
                    # Log success with file size
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        api_logger.info(f"Downloaded {file_size} bytes to {output_path} in {duration:.2f}s")
                    else:
                        api_logger.warning(f"Download completed but file not found at {output_path}")
                    
                    return result
                except Exception as e:
                    logger.error(f"Error downloading result file from {file_url}: {str(e)}")
                    api_logger.exception(f"Detailed exception info for file download error:")
                    raise
                
            def download_all_results(self, results, output_dir=None):
                """Download all result files with detailed logging."""
                try:
                    # Use default results directory if not specified
                    if output_dir is None:
                        output_dir = results_dir
                    
                    # Ensure directory exists
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                        api_logger.info(f"Created results directory: {output_dir}")
                    
                    # Get job ID from results if available
                    job_id = results.get('job', {}).get('jobID', 'unknown')
                    api_logger.info(f"Downloading all results for job {job_id} to {output_dir}")
                    
                    # Start timing
                    start_time = time.time()
                    
                    # Download all files
                    result = submit_bakta.download_all_results(results, output_dir)
                    duration = time.time() - start_time
                    
                    # Count files and get total size
                    file_count = 0
                    total_size = 0
                    if os.path.exists(output_dir):
                        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir)]
                        file_count = len(files)
                        total_size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
                    
                    api_logger.info(f"Downloaded {file_count} files ({total_size} bytes) in {duration:.2f}s")
                    api_logger.info(f"Results location: {output_dir}")
                    
                    # List files with types for debugging
                    if api_logger.isEnabledFor(logging.DEBUG):
                        api_logger.debug(f"Files downloaded to {output_dir}:")
                        for filename in os.listdir(output_dir):
                            file_path = os.path.join(output_dir, filename)
                            if os.path.isfile(file_path):
                                file_size = os.path.getsize(file_path)
                                api_logger.debug(f"  - {filename} ({file_size} bytes)")
                    
                    # Update job history if we have the job ID
                    job_id = results.get('job', {}).get('jobID')
                    if job_id and job_id in self.job_history:
                        self.job_history[job_id]['results_downloaded_at'] = datetime.now().isoformat()
                        self.job_history[job_id]['download_location'] = output_dir
                        self.job_history[job_id]['downloaded_file_count'] = file_count
                        self.job_history[job_id]['downloaded_total_size'] = total_size
                    
                    return result
                except Exception as e:
                    logger.error(f"Error downloading all results: {str(e)}")
                    api_logger.exception(f"Detailed exception info for bulk download error:")
                    raise
        
        # Create global adapter
        bakta_adapter = BaktaInterface()
        
        # Set flag
        BAKTA_AVAILABLE = True
        logger.info(f'Successfully initialized Bakta standalone adapter with URL: {submit_bakta.BASE_URL}')
    except ImportError as e:
        logger.warning(f'Failed to import standalone script: {e}')
        BAKTA_AVAILABLE = False
except Exception as e:
    logger.error(f'Error in Bakta connection setup: {e}')
    BAKTA_AVAILABLE = False

def create_bakta_interface():
    """Create a compatible interface for the existing app code."""
    if BAKTA_AVAILABLE:
        logger.info("Creating Bakta interface for application")
        return bakta_adapter
    else:
        logger.warning("Bakta integration not available, returning None")
        return None

# Export informational method to check logger configuration
def get_log_status():
    """Return status information about the logging configuration."""
    return {
        'main_logger': {
            'name': logger.name,
            'level': logging.getLevelName(logger.level),
            'handlers': [h.__class__.__name__ for h in logger.handlers] if logger.handlers else ['inherited']
        },
        'api_logger': {
            'name': api_logger.name,
            'level': logging.getLevelName(api_logger.level),
            'handlers': [h.__class__.__name__ for h in api_logger.handlers] if api_logger.handlers else ['inherited']
        },
        'bakta_available': BAKTA_AVAILABLE,
        'results_dir': results_dir
    }

# Exports
__all__ = ['BAKTA_AVAILABLE', 'bakta_adapter', 'create_bakta_interface', 'get_log_status']
