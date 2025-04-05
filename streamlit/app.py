"""
AMR Prediction & Genome Annotation Streamlit App
"""
import streamlit as st
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
import os
import tempfile
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gast-app')

# Import custom modules
import sys
import os

# Add the streamlit directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add the parent directory to the path to make amr_predictor available if present
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Now import the modules
import config
from api_client import create_amr_client, create_bakta_interface, BAKTA_AVAILABLE
from ui_components import (
    create_sidebar,
    create_annotation_settings_tab,
    create_sequence_input_tab,
    create_results_tab,
    create_job_management_tab,
    add_job_to_history
)
from utils import (
    is_valid_dna_sequence,
    get_sequence_statistics,
    parse_fasta_file,
    create_unique_job_name
)

# Display a warning if Bakta is not available
BAKTA_WARNING_DISPLAYED = False

# Set page config
logger.info("Initializing GAST application")
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)
logger.info("Page config set")

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
    st.session_state.enable_bakta = False
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
        client = create_amr_client()
        # Check if we're in mock mode based on session state
        if st.session_state.get("using_real_amr_api", False):
            logger.info("AMR API connected and using real API")
            st.session_state.update_amr_status("Connected", "success")
        else:
            logger.info("AMR API in mock mode")
            st.session_state.update_amr_status("Mock Mode", "warning")
    except Exception as e:
        logger.error(f"AMR API connection failed: {str(e)}")
        st.session_state.update_amr_status(f"Not connected: {str(e)}", "error")
    
    # Check Bakta API if enabled
    if st.session_state.get("enable_bakta", False):
        logger.info("Bakta API enabled, checking connectivity")
        try:
            bakta_client = create_bakta_interface()
            # Check if we're in mock mode based on session state
            if st.session_state.get("using_real_bakta_api", False):
                logger.info("Bakta API connected and using real API")
                st.session_state.update_bakta_status("Connected", "success")
            else:
                logger.info("Bakta API in mock mode")
                st.session_state.update_bakta_status("Mock Mode", "warning")
        except Exception as e:
            logger.error(f"Bakta API connection failed: {str(e)}")
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
        
        return st.session_state.amr_job_id
    
    except Exception as e:
        logger.error(f"Error submitting AMR job: {str(e)}", exc_info=True)
        st.session_state.amr_error = str(e)
        return None

def submit_bakta_job(sequence):
    """
    Submit a sequence for Bakta annotation.
    
    Args:
        sequence: DNA sequence string
    """
    logger.info("Preparing to submit Bakta annotation job")
    
    if not st.session_state.get("enable_bakta", False):
        logger.info("Bakta annotation is disabled, skipping submission")
        return None
    
    try:
        # Create a temporary file for the sequence
        logger.info("Creating temporary FASTA file for sequence")
        with tempfile.NamedTemporaryFile(suffix=".fasta", delete=False) as temp:
            # If sequence is in FASTA format, write as is, otherwise add a header
            if sequence.strip().startswith(">"):
                logger.info("Sequence is in FASTA format, using as-is")
                temp.write(sequence.encode())
            else:
                logger.info("Adding FASTA header to sequence")
                temp.write(f">streamlit_submission\n{sequence}".encode())
            
            temp_path = temp.name
            logger.info(f"Temporary FASTA file created at: {temp_path}")
        
        # Create Bakta interface
        logger.info("Creating Bakta interface")
        bakta_interface = create_bakta_interface()
        
        # Prepare configuration
        bakta_config = st.session_state.bakta_params.copy()
        logger.info(f"Bakta parameters prepared: {bakta_config}")
        
        # Generate a unique job name
        job_name = create_unique_job_name()
        logger.info(f"Generated unique job name: {job_name}")
        
        # Submit job
        logger.info("Submitting job to Bakta API")
        job_id = bakta_interface.submit_job(
            fasta_data=temp_path,
            job_name=job_name,
            config_params=bakta_config
        )
        logger.info(f"Bakta job submitted successfully, job ID: {job_id}")
        
        # Clean up the temporary file
        if os.path.exists(temp_path):
            logger.info(f"Removing temporary FASTA file: {temp_path}")
            os.unlink(temp_path)
        
        # Store job info in session state
        st.session_state.bakta_job_id = job_id
        st.session_state.bakta_status = "PENDING"
        logger.info(f"Bakta job ID {job_id} stored in session state with status: PENDING")
        
        # Add to job history
        job_data = {
            "job_id": job_id,
            "type": "Bakta Annotation",
            "status": "PENDING",
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "params": bakta_config
        }
        logger.info(f"Adding Bakta job to history: {job_id}")
        add_job_to_history(job_data)
        
        return job_id
    
    except Exception as e:
        logger.error(f"Error submitting Bakta job: {str(e)}", exc_info=True)
        st.session_state.bakta_error = str(e)
        return None
    finally:
        # Ensure temp file is removed
        if 'temp_path' in locals() and os.path.exists(temp_path):
            logger.info(f"Cleaning up temporary file in finally block: {temp_path}")
            os.unlink(temp_path)

def check_job_status():
    """Check the status of submitted jobs."""
    logger.info("Checking status of submitted jobs")
    
    # Check AMR job status
    if "amr_job_id" in st.session_state:
        amr_job_id = st.session_state.amr_job_id
        logger.info(f"Checking AMR job status for ID: {amr_job_id}")
        try:
            logger.info("Creating AMR API client for status check")
            client = create_amr_client()
            logger.info(f"Requesting status for AMR job: {amr_job_id}")
            status_response = client.get_prediction_status(amr_job_id)
            
            status = status_response.get("status")
            logger.info(f"AMR job status received: {status}")
            
            # Force refresh of session state status to ensure consistency
            previous_status = st.session_state.get("amr_status", "UNKNOWN")
            if status != previous_status:
                logger.info(f"AMR job status changed: {previous_status} -> {status}")
                
                # If the status indicates completion but the UI shows running,
                # we need to force a refresh
                if status == "SUCCESSFUL" and previous_status != "SUCCESSFUL":
                    logger.info("Job completed - clearing results cache to force refresh")
                    if "amr_results" in st.session_state:
                        del st.session_state.amr_results
            
            # Set current status in session state
            st.session_state.amr_status = status
            
            # Update job in history - ensure status is in sync
            logger.info("Updating AMR job status in job history")
            updated = False
            for job in st.session_state.jobs:
                if job.get("job_id") == amr_job_id:
                    job["status"] = status
                    updated = True
                    break
            
            if not updated and status != "UNKNOWN" and status != "ERROR":
                logger.warning(f"Job {amr_job_id} not found in job history, adding it now")
                st.session_state.jobs.append({
                    "job_id": amr_job_id,
                    "type": "AMR Prediction",
                    "status": status,
                    "submitted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # If job is complete, get results
            if status == "SUCCESSFUL":
                logger.info(f"AMR job {amr_job_id} completed successfully, fetching results")
                if "amr_results" not in st.session_state:
                    logger.info("Requesting AMR prediction results")
                    results = client.get_prediction_results(amr_job_id)
                    logger.info(f"AMR results received: {results.get('status', 'NO_STATUS')}")
                    st.session_state.amr_results = results
            elif status == "FAILED":
                logger.error(f"AMR job {amr_job_id} failed")
                st.session_state.amr_error = "Job processing failed on the server"
            elif status == "CANCELLED":
                logger.warning(f"AMR job {amr_job_id} was cancelled")
        except Exception as e:
            logger.error(f"Error checking AMR job status: {str(e)}", exc_info=True)
            st.session_state.amr_error = str(e)
    else:
        logger.info("No AMR job ID in session state, skipping AMR status check")
    
    # Check Bakta job status
    if "bakta_job_id" in st.session_state:
        bakta_job_id = st.session_state.bakta_job_id
        logger.info(f"Checking Bakta job status for ID: {bakta_job_id}")
        try:
            logger.info("Creating Bakta API interface for status check")
            bakta_interface = create_bakta_interface()
            logger.info(f"Requesting status for Bakta job: {bakta_job_id}")
            status = bakta_interface.get_job_status(bakta_job_id)
            
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
                    results = bakta_interface.get_job_results(bakta_job_id)
                    logger.info("Bakta results received and stored in session state")
                    st.session_state.bakta_results = results
            elif status == "FAILED":
                logger.error(f"Bakta job {bakta_job_id} failed")
            elif status == "CANCELLED":
                logger.warning(f"Bakta job {bakta_job_id} was cancelled")
        except Exception as e:
            logger.error(f"Error checking Bakta job status: {str(e)}", exc_info=True)
            st.session_state.bakta_error = str(e)
    else:
        logger.info("No Bakta job ID in session state, skipping Bakta status check")
        
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
    # Auto-navigate to results tab
    logger.info("Auto-navigating to results tab")
    st.session_state.active_tab = 2  # Results tab

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

# Get active tab from session state (default to 0 if not set)
active_tab_index = st.session_state.get("active_tab", 0)
logger.info(f"Active tab index from session state: {active_tab_index}")

# Create tabs and store them in a list for easier access by index
tab_list = st.tabs(tabs)
logger.info(f"Created {len(tab_list)} tabs: {tabs}")

# For backwards compatibility with existing code
tab1, tab2, tab3, tab4 = tab_list

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
        st.rerun()  # Rerun the app to activate the selected tab

with tab3:
    create_results_tab()
    
    # Check job statuses periodically
    if "amr_job_id" in st.session_state or "bakta_job_id" in st.session_state:
        check_job_status()
        
        # Add refresh button if jobs are still running
        if (st.session_state.get("amr_status") not in ["SUCCESSFUL", "FAILED", "CANCELLED"] or
            st.session_state.get("bakta_status") not in ["SUCCESSFUL", "FAILED", "CANCELLED"]):
            
            if st.button("Refresh Status"):
                check_job_status()
                st.rerun()

with tab4:
    create_job_management_tab()

# Add auto-refresh for running jobs
if "amr_job_id" in st.session_state or "bakta_job_id" in st.session_state:
    # Check if status is one that requires auto-refresh
    amr_status = st.session_state.get("amr_status", "")
    bakta_status = st.session_state.get("bakta_status", "")
    
    # Non-final statuses that need refreshing
    running_statuses = ["SUBMITTED", "PENDING", "QUEUED", "RUNNING", "PROCESSING", ""]
    
    # Check if any job is in a running state
    is_running = (amr_status in running_statuses or bakta_status in running_statuses)
    
    if is_running:
        st.markdown("---")
        st.info("Jobs are still running. Status will refresh automatically.")
        
        # Explicitly check job status before rerunning
        check_job_status()
        
        # Wait before rerunning
        time.sleep(5)  # Wait 5 seconds
        st.rerun()
