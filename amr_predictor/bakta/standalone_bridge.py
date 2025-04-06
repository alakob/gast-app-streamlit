#!/usr/bin/env python3
"""
Bridge adapter that uses the standalone Bakta script's implementation.
This provides a direct way to use the standalone script's functionality
in the module context.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Ensure the script is importable
sys.path.append('/app')

# Import the standalone script
try:
    import submit_bakta
    STANDALONE_AVAILABLE = True
except ImportError as e:
    logging.error(f'Failed to import standalone Bakta script: {e}')
    STANDALONE_AVAILABLE = False

class StandaloneBridgeAdapter:
    """Adapter that uses the standalone script's implementation."""
    
    def __init__(self, api_key: Optional[str] = None, environment: str = 'prod'):
        self.api_key = api_key or os.environ.get('BAKTA_API_KEY', '')
        self.environment = environment
        self.base_url = submit_bakta.BASE_URL if STANDALONE_AVAILABLE else ''
        
        # Log initialization
        logging.info(f'Initialized StandaloneBridgeAdapter with URL: {self.base_url}')
    
    async def submit_job(self, sequence_data: Union[str, bytes], config: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a job using the standalone script's implementation."""
        if not STANDALONE_AVAILABLE:
            raise ImportError('Standalone Bakta script is not available')
        
        # Create a temporary file for the sequence
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            if isinstance(sequence_data, bytes):
                sequence_data = sequence_data.decode('utf-8')
            f.write(sequence_data)
            temp_path = f.name
        
        try:
            # Initialize job
            init_response = submit_bakta.initialize_job()
            job_id = init_response['job']['jobID']
            secret = init_response['job']['secret']
            upload_link = init_response['uploadLinkFasta']
            
            # Upload FASTA
            submit_bakta.upload_fasta(upload_link, sequence_data)
            
            # Start job
            submit_bakta.start_job(job_id, secret)
            
            # Return job details
            return {
                'id': job_id,
                'secret': secret,
                'name': config.get('name', 'bakta_job'),
                'status': 'SUBMITTED'
            }
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def check_job_status(self, job_id: str, secret: str) -> Dict[str, Any]:
        """Check job status using the standalone script."""
        if not STANDALONE_AVAILABLE:
            raise ImportError('Standalone Bakta script is not available')
        
        return submit_bakta.check_job_status(job_id, secret)
    
    async def get_job_results(self, job_id: str, secret: str) -> Dict[str, Any]:
        """Get job results using the standalone script."""
        if not STANDALONE_AVAILABLE:
            raise ImportError('Standalone Bakta script is not available')
        
        return submit_bakta.get_job_results(job_id, secret)
    
    async def download_all_results(self, results: Dict[str, Any], 
                                  output_dir: Union[str, Path] = None) -> Dict[str, str]:
        """Download all result files using the standalone script."""
        if not STANDALONE_AVAILABLE:
            raise ImportError('Standalone Bakta script is not available')
        
        # Use default results directory if not specified
        if output_dir is None:
            output_dir = os.environ.get('BAKTA_RESULTS_DIR', '/app/results/bakta')
        
        # Ensure the directory exists
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return submit_bakta.download_all_results(results, str(output_dir))

# Function to get an instance of the adapter
def get_bridge_adapter(api_key: Optional[str] = None, 
                      environment: str = 'prod') -> StandaloneBridgeAdapter:
    """Get an instance of the StandaloneBridgeAdapter."""
    return StandaloneBridgeAdapter(api_key, environment)

# Helper function to run async functions
def run_async(func, *args, **kwargs):
    """Run an async function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func(*args, **kwargs))
    finally:
        loop.close()
