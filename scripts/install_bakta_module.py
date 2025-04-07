#!/usr/bin/env python3
"""
Script to install and verify the Bakta module in the Docker container.
This script should be run as part of the Docker container startup.
"""
import os
import sys
import subprocess
import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-installer")

def check_bakta_module():
    """Check if the Bakta module is available and properly installed."""
    logger.info("Checking Bakta module availability...")
    
    try:
        import amr_predictor.bakta
        logger.info("✓ Bakta module already available")
        return True
    except ImportError as e:
        logger.warning(f"Bakta module not found: {e}")
        return False

def install_bakta_module():
    """Install the Bakta module if it's not already available."""
    logger.info("Installing Bakta module...")
    
    # Check if we're in development mode with the code directly mounted
    if os.path.exists("/app/amr_predictor/bakta"):
        logger.info("Bakta module source code found at /app/amr_predictor/bakta")
        # Install module in development mode
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "/app"])
            logger.info("✓ Installed Bakta module in development mode")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Bakta module: {e}")
            return False
    else:
        logger.error("Bakta module source code not found at expected location")
        return False

def main():
    """Main function to check and install the Bakta module."""
    logger.info("Starting Bakta module verification")
    
    # Check if the module is already available
    if check_bakta_module():
        logger.info("Bakta module verification complete - module is available")
        return True
    
    # If not available, try to install it
    if install_bakta_module():
        # Verify installation
        if check_bakta_module():
            logger.info("Bakta module successfully installed and verified")
            return True
        else:
            logger.error("Bakta module installation failed verification")
            return False
    
    logger.error("Failed to install Bakta module")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
