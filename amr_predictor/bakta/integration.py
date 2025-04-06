#!/usr/bin/env python3
"""
Simple integration point for the Bakta API.
This module selects the best implementation strategy based on what's available.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, Union

# Configure logging
logger = logging.getLogger('bakta-integration')

# Try the standalone bridge first (most reliable)
try:
    from amr_predictor.bakta.standalone_bridge import get_bridge_adapter, run_async
    logger.info('Using standalone bridge adapter for Bakta integration')
    get_adapter = get_bridge_adapter
except ImportError:
    # Try the unified adapter
    try:
        from amr_predictor.bakta.unified_adapter import get_adapter, run_async
        logger.info('Using unified adapter for Bakta integration')
    except ImportError:
        # Create a basic fallback
        logger.warning('No Bakta adapters available, using mock implementation')
        
        # Simple mock implementation
        class MockAdapter:
            def __init__(self, *args, **kwargs):
                self.base_url = 'mock://bakta.api'
            
            async def submit_job(self, *args, **kwargs):
                return {'id': 'mock-job-id', 'status': 'PENDING'}
        
        def get_adapter(*args, **kwargs):
            return MockAdapter(*args, **kwargs)
        
        def run_async(func, *args, **kwargs):
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()

# Create a convenience function for direct use
def submit_bakta_job(sequence: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a Bakta annotation job.
    
    Args:
        sequence: FASTA sequence data
        config: Job configuration
        
    Returns:
        Dictionary with job details
    """
    adapter = get_adapter()
    return run_async(adapter.submit_job, sequence, config)

def check_bakta_status(job_id: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """
    Check the status of a Bakta job.
    
    Args:
        job_id: Job ID
        secret: Job secret (if required)
        
    Returns:
        Dictionary with job status
    """
    adapter = get_adapter()
    return run_async(adapter.check_job_status, job_id, secret)

# Export key functions
__all__ = ['get_adapter', 'run_async', 'submit_bakta_job', 'check_bakta_status']
