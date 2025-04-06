#!/usr/bin/env python3
"""
Bakta Integration Patch for Streamlit App

This module serves as a patch to fix Bakta integration issues in the Streamlit app.
It should be imported early in the app initialization process.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-integration-patch")

# Apply Docker environment fixes
logger.info("Loading Bakta Docker environment fixes...")
try:
    from streamlit.bakta_docker_fix import BaktaDockerFix, FIXES_APPLIED
    logger.info(f"Docker environment fixes applied: {FIXES_APPLIED}")
except ImportError as e:
    logger.error(f"Failed to load Docker environment fixes: {str(e)}")
    
# Set up the adapter integration
logger.info("Setting up Bakta unified adapter...")
try:
    # Create an alias/patch for the unified adapter
    import sys
    from importlib import import_module
    
    # Try to import the unified adapter
    try:
        from amr_predictor.bakta.unified_adapter import BaktaUnifiedAdapter, get_adapter, run_async
        ADAPTER_AVAILABLE = True
        logger.info("Unified adapter loaded successfully")
    except ImportError:
        logger.warning("Could not import unified adapter directly")
        ADAPTER_AVAILABLE = False
    
    # Replace/patch the client and job_manager modules
    if ADAPTER_AVAILABLE:
        # Create a patched version of the modules
        import types
        
        # Create or update a patched client module
        try:
            # Try to import the original module
            bakta_client = import_module('amr_predictor.bakta.client')
            
            # Add the adapter class
            bakta_client.BaktaUnifiedAdapter = BaktaUnifiedAdapter
            bakta_client.get_adapter = get_adapter
            bakta_client.run_async = run_async
            
            logger.info("Patched BaktaClient module with unified adapter")
        except ImportError:
            logger.warning("Could not patch BaktaClient module")
        
        # Create or update a patched job_manager module
        try:
            # Try to import the original module
            job_manager = import_module('amr_predictor.bakta.job_manager')
            
            # Add the adapter class
            job_manager.BaktaUnifiedAdapter = BaktaUnifiedAdapter
            job_manager.get_adapter = get_adapter
            job_manager.run_async = run_async
            
            # Patch the BaktaJobManager to use the adapter
            original_init = job_manager.BaktaJobManager.__init__
            
            def patched_init(self, *args, **kwargs):
                # Call original init
                original_init(self, *args, **kwargs)
                # Add adapter instance
                self.adapter = get_adapter(
                    api_key=self.api_key,
                    environment=self.environment
                )
                
            job_manager.BaktaJobManager.__init__ = patched_init
            logger.info("Patched BaktaJobManager with unified adapter")
        except ImportError:
            logger.warning("Could not patch BaktaJobManager module")
            
except Exception as e:
    logger.error(f"Failed to set up adapter integration: {str(e)}")

# Fix Streamlit session state handling
logger.info("Patching Streamlit session state for Bakta integration...")
try:
    import streamlit as st
    
    # Create an init_bakta_session function that we'll inject
    def init_bakta_session():
        """Initialize session state variables for Bakta integration."""
        if 'bakta_adapter' not in st.session_state:
            try:
                from amr_predictor.bakta.unified_adapter import get_adapter
                api_key = os.environ.get("BAKTA_API_KEY", "")
                env = os.environ.get("ENVIRONMENT", "prod")
                st.session_state.bakta_adapter = get_adapter(api_key=api_key, environment=env)
                logger.info("Added Bakta adapter to session state")
            except ImportError:
                logger.warning("Could not add Bakta adapter to session state")
        
        # Initialize basic job tracking state
        if 'bakta_job_id' not in st.session_state:
            st.session_state.bakta_job_id = None
        
        if 'bakta_job_status' not in st.session_state:
            st.session_state.bakta_job_status = None
        
        if 'bakta_job_name' not in st.session_state:
            st.session_state.bakta_job_name = None
            
        # Fix result paths in Docker environment
        if 'bakta_result_files' in st.session_state:
            # Get the current files
            result_files = st.session_state.bakta_result_files
            
            # Check if we need to fix paths
            if result_files and any('/app/results/' in path for path in result_files.values()):
                logger.info("Fixing Docker paths in result files")
                try:
                    from streamlit.bakta_docker_fix import map_docker_path
                    # Map each path
                    fixed_files = {
                        file_type: map_docker_path(path) 
                        for file_type, path in result_files.items()
                    }
                    st.session_state.bakta_result_files = fixed_files
                    logger.info("Fixed Docker paths in result files")
                except ImportError:
                    logger.warning("Could not fix Docker paths in result files")
    
    # Replace the original init_bakta_state function if possible
    try:
        import streamlit.bakta_ui as bakta_ui
        bakta_ui.init_bakta_state = init_bakta_session
        logger.info("Patched init_bakta_state function")
    except (ImportError, AttributeError):
        logger.warning("Could not patch init_bakta_state function")
        
except Exception as e:
    logger.error(f"Failed to patch Streamlit session state: {str(e)}")

logger.info("Bakta integration patch applied. The app should now be able to connect to the Bakta API correctly.")
