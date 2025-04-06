"""
Module to override the Bakta API URL at runtime.
This ensures we're always connecting to the correct endpoint.
"""

import os
import logging
import sys
from pathlib import Path

# Configure logging
logger = logging.getLogger("bakta-override")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def override_bakta_urls():
    """
    Forcibly override the Bakta API URLs in the running application.
    This function patches the BaktaClient class at runtime to use the correct URLs.
    """
    try:
        # Import the necessary module
        import amr_predictor.bakta.client as client
        from amr_predictor.bakta.client import BaktaClient
        
        # Check current URLs
        logger.info(f"Current BASE_URLS: {BaktaClient.BASE_URLS}")
        
        # Get URLs from environment
        dev_url = os.environ.get("BAKTA_API_URL_DEV", "https://dev-api.bakta.computational.bio/api/v1")
        staging_url = os.environ.get("BAKTA_API_URL_TEST", "https://staging-api.bakta.computational.bio/api/v1")
        prod_url = os.environ.get("BAKTA_API_URL_PROD", "https://bakta.computational.bio/api/v1")
        
        # Override the BASE_URLS attribute at runtime
        BaktaClient.BASE_URLS = {
            "dev": dev_url,
            "staging": staging_url,
            "prod": prod_url
        }
        
        # For good measure, override the client module's BASE_URLS directly
        setattr(client.BaktaClient, 'BASE_URLS', BaktaClient.BASE_URLS)
        
        # Force environment variable
        os.environ["BAKTA_USE_REAL_API"] = "1"
        
        logger.info(f"✓ Successfully overrode Bakta API URLs: {BaktaClient.BASE_URLS}")
        return True
    except Exception as e:
        logger.error(f"Failed to override Bakta API URLs: {e}")
        return False

# Call the override function when this module is imported
override_successful = override_bakta_urls()
