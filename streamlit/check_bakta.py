#!/usr/bin/env python3
"""Simple script to diagnose Bakta module import issues."""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-check")

logger.info("Checking for Bakta module")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")

try:
    import amr_predictor.bakta
    logger.info("✓ Successfully imported amr_predictor.bakta")
    print("BAKTA MODULE AVAILABLE")
except ImportError as e:
    logger.error(f"✗ Failed to import amr_predictor.bakta: {str(e)}")
    print("BAKTA MODULE NOT AVAILABLE")

# Try to fix by directly adding to PYTHONPATH
module_dir = "/app"
if module_dir not in sys.path:
    logger.info(f"Adding {module_dir} to sys.path")
    sys.path.insert(0, module_dir)

try:
    import amr_predictor.bakta
    logger.info("✓ Successfully imported amr_predictor.bakta after path fix")
    print("BAKTA MODULE AVAILABLE AFTER PATH FIX")
except ImportError as e:
    logger.error(f"✗ Still failed to import amr_predictor.bakta: {str(e)}")
    print("BAKTA MODULE STILL NOT AVAILABLE")
