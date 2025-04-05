"""
Server-Sent Events (SSE) client for real-time job status updates
"""
import logging
import json
import threading
import time
import requests
import streamlit as st
from sseclient.sseclient import SSEClient

logger = logging.getLogger('gast-app')

class SSEStatusListener:
    """
    A class to listen for Server-Sent Events (SSE) for job status updates.
    This provides real-time updates from the API without constant polling.
    """
    
    def __init__(self, api_base_url):
        """
        Initialize the SSE client.
        
        Args:
            api_base_url: Base URL of the API server
        """
        self.api_base_url = api_base_url
        self.threads = {}
        self.active_connections = {}
        self._setup_shutdown_handler()
    
    def _setup_shutdown_handler(self):
        """Set up a handler to close connections when Streamlit session ends"""
        # This will be called when the Streamlit session ends
        if hasattr(st, "session_state") and "sse_connections_initialized" not in st.session_state:
            st.session_state.sse_connections_initialized = True
            st.session_state.sse_listener = self
            
            # Add a clean function to the session state that can be called
            # before the Streamlit session ends
            def _cleanup():
                for job_id in list(self.active_connections.keys()):
                    self.stop_listening(job_id)
            
            st.session_state.sse_cleanup = _cleanup
    
    def start_listening(self, job_id, callback=None):
        """
        Start listening for SSE events for the given job ID.
        
        Args:
            job_id: The job ID to listen for status updates
            callback: Optional callback function to call when a status update is received.
                      If None, will default to updating session state.
        
        Returns:
            bool: True if the listening thread was started, False otherwise
        """
        # Skip if job_id is None or empty
        if not job_id:
            logger.warning("Cannot start SSE listener - empty job_id provided")
            return False
            
        # Skip if already listening
        if job_id in self.threads and self.threads[job_id].is_alive():
            logger.info(f"Already listening for updates on job {job_id}")
            return False
        
        logger.info(f"Starting SSE listener for job {job_id}")
        
        # Default callback function updates session state
        if callback is None:
            callback = self._default_status_callback
        
        try:
            # Start a new thread to listen for SSE events with a short timeout
            # to prevent blocking the main thread
            thread = threading.Thread(
                target=self._listen_for_events,
                args=(job_id, callback),
                daemon=True  # Ensure thread doesn't block app shutdown
            )
            thread.start()
            
            self.threads[job_id] = thread
            logger.info(f"SSE listener thread started for job {job_id}")
            return True
        except Exception as e:
            # Log any errors but don't crash the app
            logger.error(f"Error starting SSE listener: {str(e)}", exc_info=True)
            return False
    
    def stop_listening(self, job_id):
        """
        Stop listening for SSE events for the given job ID.
        
        Args:
            job_id: The job ID to stop listening for
        """
        logger.info(f"Stopping SSE listener for job {job_id}")
        
        # Mark the connection for this job as needing to close
        self.active_connections[job_id] = False
        
        # Wait for the thread to finish if it exists
        if job_id in self.threads:
            if self.threads[job_id].is_alive():
                # Give the thread a moment to notice the connection should close
                time.sleep(0.5)
            # Remove the thread reference
            del self.threads[job_id]
        
        # Remove from active connections if present
        if job_id in self.active_connections:
            del self.active_connections[job_id]
    
    def _default_status_callback(self, job_data):
        """
        Default callback function for status updates.
        Updates the session state with the new job data.
        
        Args:
            job_data: Job data received from the SSE event
        """
        try:
            logger.info(f"Received job status update: {job_data}")
            
            # Determine if this is an AMR or Bakta job based on the data
            job_type = job_data.get("type", "").lower()
            
            if "amr" in job_type or job_data.get("job_id") == st.session_state.get("amr_job_id"):
                # This is an AMR job
                st.session_state.amr_status = job_data.get("status")
                if job_data.get("status") == "SUCCESSFUL" and "results" in job_data:
                    st.session_state.amr_results = job_data.get("results")
                    
                # Update job history
                self._update_job_in_history(job_data.get("job_id"), job_data.get("status"), "AMR Prediction")
                    
            elif "bakta" in job_type or job_data.get("job_id") == st.session_state.get("bakta_job_id"):
                # This is a Bakta job
                st.session_state.bakta_status = job_data.get("status")
                if job_data.get("status") == "SUCCESSFUL" and "results" in job_data:
                    st.session_state.bakta_results = job_data.get("results")
                    
                # Update job history
                self._update_job_in_history(job_data.get("job_id"), job_data.get("status"), "Bakta Annotation")
                
            # Force a Streamlit rerun to update the UI
            if hasattr(st, "rerun"):
                st.rerun()
        except Exception as e:
            logger.error(f"Error in SSE status callback: {str(e)}", exc_info=True)
    
    def _update_job_in_history(self, job_id, status, job_type):
        """Update a job in the job history with new status"""
        if not hasattr(st, "session_state") or "jobs" not in st.session_state:
            return
        
        # Look for the job in the history
        for job in st.session_state.jobs:
            if job.get("job_id") == job_id:
                job["status"] = status
                return
        
        # If not found, add it to the history
        if status != "UNKNOWN" and status != "ERROR":
            logger.info(f"Adding job {job_id} to history")
            from datetime import datetime
            st.session_state.jobs.append({
                "job_id": job_id,
                "type": job_type,
                "status": status,
                "submitted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    def _listen_for_events(self, job_id, callback):
        """
        Listen for SSE events for the given job ID and call the callback function.
        
        Args:
            job_id: The job ID to listen for
            callback: Callback function to call when a status update is received
        """
        logger.info(f"Starting SSE connection for job {job_id}")
        
        # Mark this connection as active
        self.active_connections[job_id] = True
        
        # Create the SSE URL
        url = f"{self.api_base_url}/jobs/{job_id}/stream"
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
        
        error_count = 0
        max_errors = 5
        backoff_time = 1  # Start with 1 second
        
        # Add a timeout for the initial connection
        connection_timeout = 5  # 5 seconds timeout for initial connection
        
        while self.active_connections.get(job_id, False):
            try:
                logger.info(f"Establishing SSE connection to {url}")
                
                # Make the SSE request with shorter initial timeout to avoid blocking
                # If this fails, we'll retry with backoff
                response = requests.get(
                    url, 
                    headers=headers, 
                    stream=True,
                    timeout=connection_timeout
                )
                
                logger.info(f"SSE connection response code: {response.status_code}")
                
                if response.status_code != 200:
                    error_msg = f"Failed to connect to SSE stream: {response.status_code} {response.reason}"
                    logger.error(error_msg)
                    
                    # If we get a 404, the job might not exist yet or the endpoint isn't available
                    if response.status_code == 404:
                        logger.warning(f"SSE endpoint not found for job {job_id}. This might be normal if the job wasn't created yet.")
                        # Wait a bit before retrying
                        time.sleep(2)
                        continue
                    else:
                        raise Exception(error_msg)
                
                # Reset error count and backoff on successful connection
                error_count = 0
                backoff_time = 1
                
                # Log successful connection
                logger.info(f"SSE connection established for job {job_id}")
                
                # Create SSE client
                try:
                    client = SSEClient(response)
                    logger.info(f"SSE client created for job {job_id}")
                except Exception as e:
                    logger.error(f"Error creating SSE client: {str(e)}", exc_info=True)
                    raise
                
                # Process events
                for event in client.events():
                    # Log each event received (in debug mode)
                    logger.debug(f"Received SSE event: {event.event} for job {job_id}")
                    
                    # Check if we should stop listening
                    if not self.active_connections.get(job_id, False):
                        logger.info(f"Stopping SSE listener for job {job_id}")
                        break
                    
                    if event.event == "status_update":
                        # Parse the data and call the callback
                        try:
                            job_data = json.loads(event.data)
                            logger.info(f"Received status update for job {job_id}: {job_data.get('status')}")
                            callback(job_data)
                            
                            # If job is complete, we can stop listening
                            if job_data.get("status") in ["SUCCESSFUL", "FAILED", "CANCELLED", "ERROR", "Completed", "Error"]:
                                logger.info(f"Job {job_id} completed with status {job_data.get('status')}, stopping SSE listener")
                                self.active_connections[job_id] = False
                                break
                            
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in SSE event data: {event.data}")
                    
                    elif event.event == "error":
                        # Handle error events
                        try:
                            error_data = json.loads(event.data)
                            logger.error(f"SSE error event: {error_data}")
                            error_count += 1
                            
                            if error_count >= max_errors:
                                logger.error(f"Too many SSE errors for job {job_id}, stopping listener")
                                self.active_connections[job_id] = False
                                break
                        except Exception as e:
                            logger.error(f"Failed to parse SSE error event: {event.data}, error: {str(e)}")
                
                # If we exit the loop normally, assume job is complete
                if self.active_connections.get(job_id, False):
                    logger.info(f"SSE stream for job {job_id} ended normally")
                    self.active_connections[job_id] = False
                
            except requests.exceptions.Timeout:
                # Special handling for timeouts to avoid blocking the app
                logger.warning(f"SSE connection timeout for job {job_id}. Will retry.")
                # Use a short sleep before retry
                time.sleep(1)
                continue
                
            except Exception as e:
                # If connection fails or is interrupted, implement backoff and retry
                error_count += 1
                logger.error(f"SSE error ({error_count}/{max_errors}): {str(e)}", exc_info=True)
                
                if error_count >= max_errors:
                    logger.error(f"Too many SSE errors for job {job_id}, stopping listener")
                    self.active_connections[job_id] = False
                    break
                
                # Implement exponential backoff with a cap
                logger.info(f"Retrying SSE connection in {backoff_time} seconds")
                time.sleep(backoff_time)
                backoff_time = min(backoff_time * 2, 30)  # Cap at 30 seconds
        
        logger.info(f"SSE listener for job {job_id} has stopped")
        
        # Clean up connections dict
        if job_id in self.active_connections:
            del self.active_connections[job_id]

# Create a singleton instance
def get_sse_listener(api_base_url=None):
    """
    Get the SSE listener instance.
    
    Args:
        api_base_url: Base URL of the API server
        
    Returns:
        SSEStatusListener: The SSE listener instance
    """
    if "sse_listener" not in st.session_state:
        if api_base_url is None:
            # Try to get from config
            import config
            api_base_url = config.AMR_API_URL
            
        st.session_state.sse_listener = SSEStatusListener(api_base_url)
    
    return st.session_state.sse_listener
