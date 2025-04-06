#!/usr/bin/env python3
"""
Setup Bakta environment variables and adapter integration.
"""
import os
import sys
import logging

logger = logging.getLogger('bakta-env-setup')

# Create results directory if it doesn't exist
results_dir = '/app/results/bakta'
os.makedirs(results_dir, exist_ok=True)
logger.info(f'Ensured Bakta results directory exists: {results_dir}')

# Import the unified adapter if available
try:
    sys.path.append('/app')
    from amr_predictor.bakta.unified_adapter import get_adapter, run_async
    
    # Create a global adapter instance
    bakta_adapter = get_adapter()
    logger.info(f'Initialized Bakta adapter with URL: {bakta_adapter.base_url}')
    
    # Make the adapter available globally
    __all__ = ['bakta_adapter', 'run_async']
except ImportError as e:
    logger.warning(f'Failed to import Bakta unified adapter: {e}')
    bakta_adapter = None
