#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bakta-connect')

# Ensure results directory exists
results_dir = '/app/results/bakta'
os.makedirs(results_dir, exist_ok=True)

# Set environment variables if needed
if not os.environ.get('BAKTA_API_URL'):
    os.environ['BAKTA_API_URL'] = 'https://api.bakta.computational.bio/api/v1'
if not os.environ.get('BAKTA_RESULTS_DIR'):
    os.environ['BAKTA_RESULTS_DIR'] = results_dir

# Import our integration point
try:
    # Make sure we can find the modules
    sys.path.append('/app')
    
    # Try to import from standalone script first
    try:
        import submit_bakta
        
        # Create a simple adapter class that matches the expected interface
        class BaktaInterface:
            def __init__(self):
                self.base_url = submit_bakta.BASE_URL
            
            def submit_job(self, fasta_data=None, job_name=None, config_params=None, fasta_content=None):
                # Handle different parameter formats
                if fasta_content is None and fasta_data is not None:
                    if isinstance(fasta_data, str) and os.path.exists(fasta_data):
                        with open(fasta_data, 'r') as f:
                            fasta_content = f.read()
                    else:
                        fasta_content = str(fasta_data)
                
                # Merge config parameters
                config = {}
                if job_name:
                    config['name'] = job_name
                if config_params:
                    config.update(config_params)
                
                # Initialize job
                init_response = submit_bakta.initialize_job()
                job_id = init_response['job']['jobID']
                secret = init_response['job']['secret']
                upload_link = init_response['uploadLinkFasta']
                
                # Upload FASTA
                submit_bakta.upload_fasta(upload_link, fasta_content)
                
                # Start job
                submit_bakta.start_job(job_id, secret)
                
                # Return job ID
                return job_id
        
        # Create global adapter
        bakta_adapter = BaktaInterface()
        
        # Set flag
        BAKTA_AVAILABLE = True
        logger.info(f'Successfully initialized Bakta standalone adapter with URL: {submit_bakta.BASE_URL}')
    except ImportError as e:
        logger.warning(f'Failed to import standalone script: {e}')
        bakta_adapter = None
        BAKTA_AVAILABLE = False
except Exception as e:
    logger.error(f'Error in Bakta connection setup: {e}')
    bakta_adapter = None
    BAKTA_AVAILABLE = False

def create_bakta_interface():
    return bakta_adapter
