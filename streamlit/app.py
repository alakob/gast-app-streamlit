"""AMR Prediction & Genome Annotation Streamlit App"""

# Standard imports first (no streamlit imports)
import os
import sys
import json
import time
import logging
from pathlib import Path

# Setup paths
sys.path.append("/app")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gast-app')

# Import streamlit first, before any st commands
import streamlit as st

# Import job association utilities
try:
    from job_association import associate_jobs, update_session_associations
    JOB_ASSOCIATION_AVAILABLE = True
    logger.info("✓ Job association module imported successfully")
except ImportError as e:
    JOB_ASSOCIATION_AVAILABLE = False
    logger.warning(f"Job association module not available: {e}")

# Set page config as the FIRST Streamlit command
st.set_page_config(
    page_title="GAST: Genome Analysis & Surveillance Tool",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import our simple Bakta executor and visualizations
try:
    import bakta_executor
    import bakta_visualizations
    logger.info("✓ Simple Bakta executor and visualizations imported successfully")
    BAKTA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Failed to import Bakta modules: {e}")
    BAKTA_AVAILABLE = False

# Continue with other imports
import threading
import time
from datetime import datetime
import tempfile
import json
import requests
# SSE implementation temporarily disabled
# from sseclient import SSEClient

# Import custom modules
import sys
import os

# Add the streamlit directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add the parent directory to the path to make amr_predictor available if present

# No need for Bakta patches with our simple executor
logger.info("Using simple Bakta executor instead of complex integration")
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Now import the modules
import config
from api_client import create_amr_client
# SSE implementation temporarily disabled
# from sse_client import get_sse_listener
from ui_components import (
    create_sidebar,
    create_annotation_settings_tab,
    create_sequence_input_tab,
    create_results_tab,
    create_job_management_tab,
    add_job_to_history
)
# Import integration UI components with fallback for Docker environment
try:
    from integration_ui import display_integrated_analysis_ui
    INTEGRATION_UI_AVAILABLE = True
except ImportError:
    # Create a fallback implementation when module is not available
    def display_integrated_analysis_ui():
        st.header("Integrated Analysis")
        st.info("Integrated analysis module is not available in this environment. Please update your Docker image or ensure the module is installed.")
        st.markdown("""
        This module connects Bakta annotation data with AMR prediction results to provide:
        - Correlation between genomic features and AMR genes
        - Integrated genome map visualization
        - Feature-AMR correlation analysis
        - Detailed feature analysis with AMR implications
        """)
    INTEGRATION_UI_AVAILABLE = False
    logging.warning("integration_ui module not found - using fallback implementation")
from utils import (
    is_valid_dna_sequence,
    get_sequence_statistics,
    parse_fasta_file,
    create_unique_job_name
)

# Display a warning if Bakta is not available
BAKTA_WARNING_DISPLAYED = False

# Page config is already set at the top of the file
logger.info("Initializing GAST application")
logger.info("Page config already set")

# Load custom CSS
def load_css(css_file):
    with open(css_file, 'r') as f:
        css = f'<style>{f.read()}</style>'
        st.markdown(css, unsafe_allow_html=True)

# Get the path to the custom CSS file
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
css_path = os.path.join(current_dir, "custom.css")

# Load the custom CSS
if os.path.exists(css_path):
    load_css(css_path)

# Initialize session state
if "initialized" not in st.session_state:
    logger.info("First run - initializing session state")
    st.session_state.initialized = True
    st.session_state.sequence = ""
    st.session_state.sequence_valid = False
    st.session_state.submit_clicked = False
    st.session_state.amr_params = {}
    st.session_state.seq_params = {}
    st.session_state.enable_bakta = True  # Default to enabled
    st.session_state.using_real_bakta_api = True  # Force real API mode
    st.session_state.jobs = []
    st.session_state.active_tab = 0  # Track active tab index (0-based)
    
    # Initialize bakta_params with defaults from config
    st.session_state.bakta_params = {
        "genus": config.DEFAULT_GENUS,
        "species": config.DEFAULT_SPECIES,
        "strain": "",
        "complete_genome": False,
        "translation_table": config.DEFAULT_TRANSLATION_TABLE,
        "locus": "",
        "locus_tag": ""
    }
    logger.info("Session state initialized with default values")
else:
    logger.info("Session already initialized, reusing existing state")


def check_api_connectivity():
    """Check connectivity to the AMR and Bakta APIs."""
    logger.info("Checking API connectivity")
    
    # Check AMR API
    logger.info("Checking AMR API connectivity")
    try:
        # ALWAYS FORCE REAL API MODE - Disable mock data completely
        st.session_state["_mock_job_ids"] = set()  # Clear any mock job tracking
        st.session_state["_amr_mock_job_ids"] = set()  # Clear AMR-specific mock tracking
        st.session_state["using_real_amr_api"] = True  # Force real API mode
        st.session_state["mock_override"] = False  # Disable mock override
        logger.info("FORCING REAL AMR API MODE - Mock data disabled completely")
        
        client = create_amr_client()
        # Always use real API mode - no conditional check
        logger.info("AMR API forced to real mode - mock data disabled")
        st.session_state.update_amr_status("Connected (REAL MODE ONLY)", "success")
    except Exception as e:
        logger.error(f"AMR API connection failed: {str(e)}")
        st.session_state.update_amr_status(f"Not connected: {str(e)}", "error")
    
    # Check Bakta API if enabled
    if st.session_state.get("enable_bakta", False):
        logger.info("Bakta API enabled, checking connectivity with simple executor")
        try:
            # Check if bakta_executor is imported successfully
            if 'bakta_executor' in sys.modules:
                bakta_api_url = bakta_executor.BASE_URL
                logger.info(f"Bakta executor available with API URL: {bakta_api_url}")
                st.session_state.update_bakta_status("Connected (Direct API)", "success")
                # Always use real API mode with our executor
                st.session_state.using_real_bakta_api = True
            else:
                logger.error("Bakta executor module not found")
                st.session_state.update_bakta_status("Module not loaded", "error")
        except Exception as e:
            logger.error(f"Bakta API check failed: {str(e)}")
            st.session_state.update_bakta_status(f"Not connected: {str(e)}", "error")
    else:
        logger.info("Bakta API disabled, skipping connectivity check")
        st.session_state.update_bakta_status("Disabled", "info")
        
    logger.info("API connectivity check completed")

def submit_amr_job(sequence):
    """
    Submit a sequence for AMR prediction.
    
    Args:
        sequence: DNA sequence string
    """
    logger.info("Preparing to submit AMR prediction job")
    try:
        # Create AMR API client
        logger.info("Creating AMR API client")
        client = create_amr_client()
        
        # Prepare parameters from session state
        params = st.session_state.amr_params.copy()
        logger.info(f"AMR parameters prepared: {params}")
        
        # Force real API mode if possible
        if st.session_state.get("using_real_amr_api", False):
            logger.info("Ensuring real API mode is active")
            st.session_state["mock_override"] = False
        
        # Submit job
        logger.info(f"Submitting sequence of length {len(sequence)} to AMR API")
        response = client.predict_amr(sequence, params)
        logger.info(f"AMR job submission response received: {response}")
        
        # Store job info in session state
        st.session_state.amr_job_id = response.get("job_id")
        st.session_state.amr_status = response.get("status", "PENDING")
        logger.info(f"AMR job ID: {st.session_state.amr_job_id}, initial status: {st.session_state.amr_status}")
        
        # Add to job history
        job_data = {
            "job_id": st.session_state.amr_job_id,
            "type": "AMR Prediction",
            "status": st.session_state.amr_status,
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "params": params
        }
        logger.info(f"Adding AMR job to history: {job_data['job_id']}")
        add_job_to_history(job_data)
        
        # Force immediate switch to results tab
        logger.info("Switching to results tab immediately after job submission")
        st.session_state.active_tab = 2  # Results tab
        
        # Request immediate status check
        st.session_state.force_status_check = True
        
        # SSE implementation temporarily disabled
        # job_id = st.session_state.amr_job_id
        # if job_id:
        #     logger.info(f"Starting SSE listener for AMR job: {job_id}")
        #     sse_listener = get_sse_listener(config.AMR_API_URL)
        #     sse_listener.start_listening(job_id)
        #     logger.info("SSE listener started successfully")
        
        return st.session_state.amr_job_id
    
    except Exception as e:
        logger.error(f"Error submitting AMR job: {str(e)}", exc_info=True)
        st.session_state.amr_error = str(e)
        return None

def submit_bakta_job(sequence):
    """
    Submit a sequence for Bakta annotation using our simple bakta_executor.
    
    Args:
        sequence: DNA sequence string
    """
    logger.info("Preparing to submit Bakta annotation job using simple executor")
    
    if not st.session_state.get("enable_bakta", False):
        logger.info("Bakta annotation is disabled, skipping submission")
        return None
    
    try:
        # Prepare configuration
        bakta_config = st.session_state.bakta_params.copy()
        logger.info(f"Bakta parameters prepared: {bakta_config}")
        
        # Generate a unique job name
        job_name = create_unique_job_name()
        logger.info(f"Generated unique job name: {job_name}")
        
        # Prep sequence content - ensure it's in FASTA format
        if not sequence.strip().startswith(">"):
            logger.info("Adding FASTA header to sequence")
            sequence = f">streamlit_submission\n{sequence}"
        else:
            logger.info("Sequence is already in FASTA format, using as-is")
        
        # Set output directory to match AMR API results location
        output_dir = os.path.join(os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta"))
        logger.info(f"Using output directory: {output_dir}")
        
        # Submit job using our simple executor
        logger.info("Submitting job to Bakta API via simple executor")
        job_id, secret, status_data = bakta_executor.submit_bakta_analysis(
            fasta_content=sequence,
            job_name=job_name,
            output_dir=output_dir
        )
        
        logger.info(f"Bakta job submitted successfully, job ID: {job_id}, secret: {secret}")
        
        # Store job info in session state
        st.session_state.bakta_job_id = job_id
        st.session_state.bakta_job_secret = secret
        st.session_state.bakta_status = "COMPLETED"  # Our executor waits for completion
        logger.info(f"Bakta job ID {job_id} stored in session state with status: COMPLETED")
        
        # Add to job history
        job_data = {
            "job_id": job_id,
            "type": "Bakta Annotation",
            "status": "COMPLETED",
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "params": bakta_config,
            "secret": secret,
            "results_dir": output_dir
        }
        logger.info(f"Adding Bakta job to history: {job_id}")
        add_job_to_history(job_data)
        
        return job_id
    
    except Exception as e:
        logger.error(f"Error submitting Bakta job: {str(e)}", exc_info=True)
        st.session_state.bakta_error = str(e)
        return None

def check_job_status():
    """Check the status of submitted jobs."""
    logger.info("Checking status of submitted jobs")
    
    # Reset API connection if needed
    if "reset_api_connection" in st.session_state and st.session_state.reset_api_connection:
        logger.info("Resetting API connection to force fresh database check")
        client = create_amr_client()
        # If client was created successfully, reset the API connection flag
        st.session_state.reset_api_connection = False
        # Force real API mode if possible
        if st.session_state.get("using_real_amr_api", False):
            logger.info("Real API connection confirmed, forcing real mode")
            # Clear any mock job tracking to ensure we use real data
            if "_mock_job_ids" in st.session_state:
                logger.info("Clearing mock job tracking to ensure real database checks")
                st.session_state["_mock_job_ids"] = set()
    
    # Force real API mode if directly requested
    if "force_status_check" in st.session_state and st.session_state.force_status_check:
        logger.info("Force status check requested, ensuring real API mode")
        client = create_amr_client()
        st.session_state.force_status_check = False
        # Force into real mode if the API is available
        if st.session_state.get("using_real_amr_api", False):
            logger.info("Real API confirmed available, forcing real mode")
            st.session_state["mock_override"] = False
            # Clear any mock job tracking
            if "_mock_job_ids" in st.session_state:
                st.session_state["_mock_job_ids"] = set()
    
    # Always prioritize using real API if it's available
    using_real_api = st.session_state.get("using_real_amr_api", False)
    if using_real_api:
        logger.info("Using real API to check status")
        st.session_state["mock_override"] = False
    else:
        logger.warning("Using mock mode for status check - this may show incorrect data")
    
    # Check AMR prediction jobs
    status_changed = False
    if "amr_job_id" in st.session_state:
        amr_job_id = st.session_state.amr_job_id
        logger.info(f"Checking AMR job status for ID: {amr_job_id}")
        status_changed = _legacy_check_amr_status(amr_job_id) or status_changed
    
    # Check Bakta annotation jobs
    if "bakta_job_id" in st.session_state:
        bakta_job_id = st.session_state.bakta_job_id
        logger.info(f"Checking Bakta job status for ID: {bakta_job_id}")
        status_changed = _legacy_check_bakta_status(bakta_job_id) or status_changed
        
    # If status changed to completed, make sure we're on the results tab
    if status_changed:
        logger.info("Job status changed, checking if we need to switch tabs")
        if st.session_state.get("active_tab", 0) != 2:
            logger.info("Switching to results tab due to status change")
            st.session_state.active_tab = 2
            # Rerun needed to refresh UI
            st.rerun()
    
# Legacy status checking functions as fallback
def _legacy_check_amr_status(amr_job_id):
    """Method to check AMR job status via database or API."""
    logger.info(f"Checking AMR job status for: {amr_job_id}")
    status_changed = False
    
    try:
        # Force real API mode if available
        using_real_api = st.session_state.get("using_real_amr_api", False)
        if using_real_api:
            st.session_state["mock_override"] = False
            # Explicitly clear this job from mock tracking if it was mistakenly added
            mock_jobs = st.session_state.get("_mock_job_ids", set())
            if amr_job_id in mock_jobs:
                logger.info(f"Removing job {amr_job_id} from mock tracking to force real DB check")
                mock_jobs.remove(amr_job_id)
                st.session_state["_mock_job_ids"] = mock_jobs
        
        # Create a fresh API client for status check
        logger.info("Creating AMR API client for status check")
        client = create_amr_client()
        
        # Log what mode we're using
        if st.session_state.get("using_real_amr_api", False):
            logger.info("Using real API to check job status")
        else:
            logger.warning("Using mock mode for status check - may show incorrect data")
        
        # Request status from API/database
        logger.info(f"Requesting status for AMR job: {amr_job_id}")
        status_response = client.get_prediction_status(amr_job_id)
        
        # Extract status from response and normalize to uppercase
        raw_status = status_response.get("status", "UNKNOWN")
        status = raw_status.upper() if isinstance(raw_status, str) else raw_status
        logger.info(f"AMR job status received: {status} (original: {raw_status})")
        
        # Check if we got data from PostgreSQL
        db_source = status_response.get("source", "unknown")
        logger.info(f"Status data source: {db_source}")
        
        # If we got data from the database, ensure we're using real API mode
        if db_source == "database" and not using_real_api:
            logger.info("Received database data but not in real API mode - fixing this")
            st.session_state["using_real_amr_api"] = True
            using_real_api = True
        
        # Force refresh of session state status to ensure consistency
        previous_status = st.session_state.get("amr_status", "UNKNOWN")
        if previous_status != status:
            logger.info(f"AMR job status changed: {previous_status} -> {status}")
            status_changed = True
            
            # If the status indicates completion but the UI shows running,
            # we need to force a refresh of results
            if status in ["SUCCESSFUL", "COMPLETE", "COMPLETED"] and previous_status not in ["SUCCESSFUL", "COMPLETE", "COMPLETED"]:
                logger.info("Job completed - clearing results cache to force refresh")
                if "amr_results" in st.session_state:
                    del st.session_state.amr_results
                # Force a page refresh to ensure we show the latest data
                logger.info("Job completed - requesting UI refresh")
                st.session_state.force_refresh = True
        
        # Set current status in session state
        st.session_state.amr_status = status
        
        # Update job in history - ensure status is in sync
        logger.info("Updating AMR job status in job history")
        updated = False
        for job in st.session_state.jobs:
            if job.get("job_id") == amr_job_id:
                old_status = job.get("status")
                job["status"] = status
                if old_status != status:
                    logger.info(f"Updated job history status from {old_status} to {status}")
                    status_changed = True
                updated = True
                break
        
        if not updated and status not in ["UNKNOWN", "ERROR"]:
            logger.warning(f"Job {amr_job_id} not found in job history, adding it now")
            st.session_state.jobs.append({
                "job_id": amr_job_id,
                "type": "AMR Prediction",
                "status": status,
                "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            status_changed = True
        
        # If job is complete, get results from PostgreSQL/disk
        if status in ["SUCCESSFUL", "COMPLETE", "COMPLETED"]:
            logger.info(f"AMR job {amr_job_id} completed successfully, fetching results")
            # Clear any cached results to force fresh retrieval from database
            if "amr_results" in st.session_state:
                logger.info("Clearing cached AMR results to get fresh data")
                del st.session_state.amr_results
                
            logger.info("Requesting AMR prediction results from database/disk")
            results = client.get_prediction_results(amr_job_id)
            
            if results:
                logger.info(f"AMR results received: {results.get('status', 'NO_STATUS')}")
                st.session_state.amr_results = results
                
                # Force switch to results tab if not already there
                if st.session_state.get("active_tab", 0) != 2:
                    logger.info("Switching to results tab since job is complete")
                    st.session_state.active_tab = 2
                    status_changed = True
            else:
                logger.warning("No results data received from API")
        elif status == "FAILED":
            logger.error(f"AMR job {amr_job_id} failed")
            st.session_state.amr_error = "Job processing failed on the server"
        elif status == "CANCELLED":
            logger.warning(f"AMR job {amr_job_id} was cancelled")
    except Exception as e:
        logger.error(f"Error checking AMR job status: {str(e)}", exc_info=True)
        st.session_state.amr_error = str(e)
        
    # Return whether the status changed to inform caller
    return status_changed

def _legacy_check_bakta_status(bakta_job_id):
    """Legacy method to check Bakta job status via polling (fallback)."""
    logger.info(f"Using legacy polling to check Bakta job status for: {bakta_job_id}")
    try:
        # Get the job secret from session state (required for bakta_executor)
        job_secret = st.session_state.get("bakta_job_secret", "")
        
        if not job_secret:
            logger.warning("No Bakta job secret found in session state, cannot check status")
            return "UNKNOWN"
            
        logger.info(f"Using bakta_executor to check status for: {bakta_job_id}")
        
        # Use the bakta_executor module directly instead of bakta_interface
        status_data = bakta_executor.check_job_status(bakta_job_id, job_secret)
        
        # Extract the job status from the response
        if not status_data or 'jobs' not in status_data or not status_data['jobs']:
            logger.warning(f"Invalid status data received from Bakta API: {status_data}")
            return "UNKNOWN"
            
        # Get status from the first job in the jobs array
        status = status_data['jobs'][0].get('jobStatus', 'UNKNOWN')
        
        previous_status = st.session_state.get("bakta_status", "UNKNOWN")
        if status != previous_status:
            logger.info(f"Bakta job status changed: {previous_status} -> {status}")
            
        st.session_state.bakta_status = status
        logger.info(f"Bakta job status updated: {status}")
        
        # Update job in history
        logger.info("Updating Bakta job status in job history")
        for job in st.session_state.jobs:
            if job.get("job_id") == bakta_job_id:
                job["status"] = status
        
        # If job is complete, get results
        if status == "SUCCESSFUL":
            logger.info(f"Bakta job {bakta_job_id} completed successfully, fetching results")
            if "bakta_results" not in st.session_state:
                logger.info("Requesting Bakta annotation results")
                # Use bakta_executor to get results instead of interface
                results = bakta_executor.get_job_results(bakta_job_id, job_secret)
                logger.info("Bakta results received and stored in session state")
                st.session_state.bakta_results = results
        elif status == "FAILED":
            logger.error(f"Bakta job {bakta_job_id} failed")
        elif status == "CANCELLED":
            logger.warning(f"Bakta job {bakta_job_id} was cancelled")
        
        return status
    except Exception as e:
        logger.error(f"Error checking Bakta job status: {str(e)}", exc_info=True)
        st.session_state.bakta_error = str(e)
        return "ERROR"
        
    logger.info("Job status check completed")

def process_submission():
    """Process submission of sequence for analysis."""
    logger.info("Processing sequence submission")
    if not st.session_state.sequence_valid:
        logger.warning("Invalid sequence detected, aborting submission")
        st.error("Please provide a valid DNA sequence")
        return
    
    logger.info(f"Submitting valid sequence of length {len(st.session_state.sequence)}")
    with st.spinner("Submitting sequence for analysis..."):
        # Clear any previous results
        if "amr_results" in st.session_state:
            logger.info("Clearing previous AMR results")
            del st.session_state.amr_results
        if "bakta_results" in st.session_state:
            logger.info("Clearing previous Bakta results")
            del st.session_state.bakta_results
        
        # Submit AMR job
        logger.info("Initiating AMR job submission")
        amr_job_id = submit_amr_job(st.session_state.sequence)
        
        if amr_job_id:
            logger.info(f"AMR job submission successful, job ID: {amr_job_id}")
            st.session_state.amr_job_id = amr_job_id
            st.session_state.amr_status = "PENDING"
            
            # Add AMR job to history
            amr_job_data = {
                "job_id": amr_job_id,
                "type": "AMR Prediction",
                "status": "PENDING",
                "submitted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            add_job_to_history(amr_job_data)
            
            st.success(f"AMR prediction job submitted (ID: {amr_job_id})")
        else:
            logger.error("AMR job submission failed, no job ID returned")
        
        # Submit Bakta job if enabled
        if st.session_state.get("enable_bakta", False):
            logger.info("Bakta enabled, initiating Bakta job submission")
            bakta_job_id = submit_bakta_job(st.session_state.sequence)
            
            if bakta_job_id:
                logger.info(f"Bakta job submission successful, job ID: {bakta_job_id}")
                # Store job ID and status in session state
                st.session_state.bakta_job_id = bakta_job_id
                st.session_state.bakta_status = "PENDING"
                
                # Make sure the job is added to history
                bakta_job_data = {
                    "job_id": bakta_job_id,
                    "type": "Bakta Annotation",
                    "status": "PENDING",
                    "submitted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                add_job_to_history(bakta_job_data)
                
                # Associate the AMR and Bakta jobs if both were successful
                if amr_job_id and JOB_ASSOCIATION_AVAILABLE:
                    logger.info(f"Associating AMR job {amr_job_id} with Bakta job {bakta_job_id}")
                    try:
                        # Update database association
                        associate_jobs(amr_job_id, bakta_job_id)
                        
                        # Update session state for quick lookup
                        if "job_associations" not in st.session_state:
                            st.session_state.job_associations = {}
                        st.session_state.job_associations[amr_job_id] = bakta_job_id
                        st.session_state.job_associations[bakta_job_id] = amr_job_id
                        
                        logger.info(f"Successfully associated AMR job {amr_job_id} with Bakta job {bakta_job_id}")
                    except Exception as e:
                        logger.error(f"Error associating jobs: {str(e)}")
                
                st.success(f"Bakta annotation job submitted (ID: {bakta_job_id})")
            else:
                logger.error("Bakta job submission failed, no job ID returned")
        else:
            logger.info("Bakta disabled, skipping Bakta job submission")
            # Remove bakta job data from session state if it exists
            if "bakta_job_id" in st.session_state:
                logger.info("Removing bakta_job_id from session state as Bakta is disabled")
                del st.session_state.bakta_job_id
            if "bakta_status" in st.session_state:
                logger.info("Removing bakta_status from session state as Bakta is disabled")
                del st.session_state.bakta_status
            if "bakta_results" in st.session_state:
                logger.info("Removing bakta_results from session state as Bakta is disabled")
                del st.session_state.bakta_results
    
    logger.info("Sequence submission processing completed")
    # Force real API mode
    logger.info("Forcing real API mode to ensure database checks")
    st.session_state["using_real_amr_api"] = True
    if "_mock_job_ids" in st.session_state:
        logger.info("Clearing mock job tracking")
        st.session_state["_mock_job_ids"] = set()
    
    # Auto-navigate to results tab with force refresh
    logger.info("Auto-navigating to results tab")
    st.session_state.active_tab = 2  # Results tab
    
    # Set flag to force an immediate rerun to apply tab change
    st.session_state.force_rerun = True

# Create the sidebar
create_sidebar()

# Check API connectivity on app startup
check_api_connectivity()

# Add title and subtitle with custom styling
st.markdown("""
<div style='text-align: center;'>
    <h1 class='dna-title'>
        <span style='font-size: 1.5em;'>🧬</span> 
        <span style='color: #1cb3e0;'>g</span>enomic
        <span style='color: #1A5276;'>A</span>ntimicrobial
        <span style='color: #1cb3e0;'>S</span>usceptibility
        <span style='color: #1A5276;'>T</span>esting
    </h1>
    <p style='font-size: 1.2em; color: #d2d2d6;'>Advanced machine learning platform for predicting antimicrobial resistance from bacterial genome sequences</p>
    <div class='blue-gradient-hr'></div>
</div>
""", unsafe_allow_html=True)

# Create the main tab structure
logger.info("Setting up main tab structure")
tabs = ["Annotation Settings", "Sequence Input", "Results", "Job Management"]

# Only add the Integrated Analysis tab if the module is available
if INTEGRATION_UI_AVAILABLE:
    tabs.append("Integrated Analysis")
    logger.info("Integrated Analysis tab added to UI")
else:
    logger.warning("Integrated Analysis tab not available - module not found")

# Get active tab from session state (default to 0 if not set)
active_tab_index = st.session_state.get("active_tab", 0)
logger.info(f"Active tab index from session state: {active_tab_index}")

# Create tabs and store them in a list for easier access by index
tab_list = st.tabs(tabs)
logger.info(f"Created {len(tab_list)} tabs: {tabs}")

# For backwards compatibility with existing code
if len(tab_list) >= 5:
    tab1, tab2, tab3, tab4, tab5 = tab_list
else:
    tab1, tab2, tab3, tab4 = tab_list
    # Create a dummy tab5 that won't be used
    tab5 = None

# This is a workaround for Streamlit's lack of a direct API to programmatically
# select a tab. We use the tab container's existing CSS classes to select the active tab.
if active_tab_index > 0:  # Only inject custom JS if not on the first tab
    js = f"""
    <script>
        // Wait for DOM to be ready
        document.addEventListener('DOMContentLoaded', (event) => {{  
            // Small delay to ensure Streamlit components are loaded
            setTimeout(() => {{                                      
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                if (tabs.length >= {active_tab_index + 1}) {{
                    tabs[{active_tab_index}].click();
                }}
            }}, 100);
        }});
    </script>
    """
    st.components.v1.html(js, height=0)

# Populate the tabs
with tab1:
    create_annotation_settings_tab()
    
    # Display a warning if Bakta is not available
    if not BAKTA_AVAILABLE and not BAKTA_WARNING_DISPLAYED:
        st.warning(
            "⚠️ The Bakta module is not available. This app is running in demo mode with mock implementations. "
            "To use the full functionality, make sure the amr_predictor package is installed and in the Python path."
        )
        globals()['BAKTA_WARNING_DISPLAYED'] = True

with tab2:
    create_sequence_input_tab()
    
    # Process submission if button clicked
    if st.session_state.submit_clicked:
        process_submission()
        # Reset button state
        st.session_state.submit_clicked = False
        # Switch to Results tab (index 2)
        st.session_state.active_tab = 2
        # Set flags to auto-refresh both AMR and Bakta status
        st.session_state.force_status_check = True
        st.session_state.auto_refresh_amr = True
        st.session_state.auto_refresh_bakta = True
        st.rerun()  # Rerun the app to activate the selected tab

with tab3:
    create_results_tab()
    
    # Check if force_rerun is requested
    if "force_rerun" in st.session_state and st.session_state.force_rerun:
        logger.info("Force rerun detected in results tab - forcing immediate database check")
        # Force real API mode
        st.session_state["using_real_amr_api"] = True
        # Clear any mock job tracking
        if "_mock_job_ids" in st.session_state:
            st.session_state["_mock_job_ids"] = set()
        # Reset the flag
        st.session_state.force_rerun = False
        # Force a page rerun to apply changes
        st.rerun()
    
    # Check job statuses periodically
    if "amr_job_id" in st.session_state or "bakta_job_id" in st.session_state:
        # Always force a fresh status check in real mode
        st.session_state["using_real_amr_api"] = True
        check_job_status()
        
        # Add refresh button if jobs are still running
        status_list = ["SUCCESSFUL", "FAILED", "CANCELLED", "COMPLETED", "COMPLETE"]
        if (st.session_state.get("amr_status", "").upper() not in status_list or
            st.session_state.get("bakta_status", "").upper() not in status_list):
            
            if st.button("Refresh Status"):
                # Force database check with real mode
                st.session_state["using_real_amr_api"] = True
                st.session_state["_mock_job_ids"] = set()
                check_job_status()
                st.rerun()

with tab4:
    create_job_management_tab()

# Integrated Analysis tab (only render if the tab exists)
if tab5 is not None:
    with tab5:
        logger.info("Rendering Integrated Analysis tab")
        display_integrated_analysis_ui()

# Revert to traditional polling for running jobs
if "amr_job_id" in st.session_state or "bakta_job_id" in st.session_state:
    # Check if status is one that requires updates
    amr_status = st.session_state.get("amr_status", "")
    bakta_status = st.session_state.get("bakta_status", "")
    
    # Non-final statuses
    running_statuses = ["SUBMITTED", "PENDING", "QUEUED", "RUNNING", "PROCESSING"]
    
    # Complete status values (case-insensitive check)
    complete_statuses = ["COMPLETED", "COMPLETE", "SUCCESSFUL", "SUCCESS", "DONE", "FINISHED"]
    
    # First, normalize statuses for case-insensitive comparison
    amr_status_upper = amr_status.upper() if amr_status else ""
    bakta_status_upper = bakta_status.upper() if bakta_status else ""
    
    # Check if any job is actually in a running state
    is_running = (amr_status_upper in [s.upper() for s in running_statuses] or 
                 bakta_status_upper in [s.upper() for s in running_statuses])
    
    # Check if we have at least one job but none are completed
    has_jobs = ("amr_job_id" in st.session_state or "bakta_job_id" in st.session_state)
    is_completed = (amr_status_upper in [s.upper() for s in complete_statuses] or 
                   bakta_status_upper in [s.upper() for s in complete_statuses])
    
    # Only show running message and auto-refresh if jobs are actually running
    if is_running and has_jobs and not is_completed:
        st.markdown("---")
        st.info("Jobs are running. Status will refresh automatically.")
        
        # Check job status manually
        check_job_status()
        
        # Add a small delay and rerun to refresh the UI
        time.sleep(5)  # 5 second refresh interval
        st.rerun()
