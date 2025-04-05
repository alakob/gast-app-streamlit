#!/usr/bin/env python3
"""Example script demonstrating the complete Bakta annotation workflow.

This script shows how to:
1. Create a Bakta client
2. Submit a job with a FASTA file
3. Poll for job completion
4. Download and save results

Usage:
    python run_bakta_job.py path/to/sequence.fasta output_directory

Requirements:
    - A valid FASTA file
    - Internet connection
    - Optional API key (set via BAKTA_API_KEY environment variable)
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Import the Bakta client package
from amr_predictor.bakta import (
    BaktaClient, 
    create_config,
    validate_fasta,
    get_api_url,
    BaktaException,
    BaktaValidationError,
    BaktaApiError
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bakta-example")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a Bakta annotation job")
    
    parser.add_argument("fasta_file", type=str, help="Path to the FASTA file to annotate")
    parser.add_argument("output_dir", type=str, help="Directory to save the results")
    
    parser.add_argument("--genus", type=str, default="Escherichia", 
                        help="Genus name (default: Escherichia)")
    parser.add_argument("--species", type=str, default="coli", 
                        help="Species name (default: coli)")
    parser.add_argument("--strain", type=str, default="", 
                        help="Strain name (optional)")
    parser.add_argument("--complete", action="store_true", 
                        help="Flag if the genome is complete (default: False)")
    parser.add_argument("--translation-table", type=int, default=11, 
                        help="Translation table to use (default: 11)")
    parser.add_argument("--locus", type=str, default="", 
                        help="Locus prefix (optional)")
    parser.add_argument("--locus-tag", type=str, default="", 
                        help="Locus tag prefix (optional)")
    
    parser.add_argument("--environment", type=str, choices=["prod", "staging", "dev", "local"], 
                        default="prod", help="API environment to use")
    parser.add_argument("--timeout", type=int, default=300, 
                        help="API request timeout in seconds (default: 300)")
    parser.add_argument("--poll-interval", type=int, default=30, 
                        help="Interval in seconds to check job status (default: 30)")
    parser.add_argument("--max-poll-time", type=int, default=3600, 
                        help="Maximum time in seconds to poll for job completion (default: 3600)")
    
    return parser.parse_args()

def run_bakta_job(args):
    """Run a complete Bakta annotation job workflow."""
    logger.info(f"Starting Bakta annotation for file: {args.fasta_file}")
    
    # Validate the FASTA file
    try:
        logger.info("Validating FASTA file...")
        validate_fasta(args.fasta_file)
    except BaktaValidationError as e:
        logger.error(f"FASTA validation failed: {str(e)}")
        return 1
    
    # Create the output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the configuration
    logger.info("Creating job configuration...")
    config = create_config(
        genus=args.genus,
        species=args.species,
        strain=args.strain,
        locus=args.locus,
        locus_tag=args.locus_tag,
        complete_genome=args.complete,
        translation_table=args.translation_table
    )
    
    # Create the client
    logger.info(f"Initializing Bakta client for {args.environment} environment...")
    api_url = get_api_url(args.environment)
    api_key = os.environ.get("BAKTA_API_KEY")
    
    client = BaktaClient(api_url=api_url, api_key=api_key, timeout=args.timeout)
    
    try:
        # Initialize job
        logger.info("Initializing job...")
        job_name = f"bakta_job_{Path(args.fasta_file).stem}"
        job_result = client.initialize_job(job_name)
        
        job_id = job_result["job_id"]
        secret = job_result["secret"]
        upload_link = job_result["upload_link"]
        
        logger.info(f"Job created with ID: {job_id}")
        
        # Upload FASTA file
        logger.info("Uploading FASTA file...")
        client.upload_fasta(upload_link, args.fasta_file)
        
        # Start the job
        logger.info("Starting job processing...")
        client.start_job(job_id, secret, config)
        
        # Poll for job completion
        logger.info("Job started, polling for completion...")
        elapsed_time = 0
        status = "PENDING"
        
        while elapsed_time < args.max_poll_time:
            status = client.check_job_status(job_id, secret)
            logger.info(f"Current job status: {status}")
            
            if status == "SUCCESSFUL":
                logger.info("Job completed successfully!")
                break
            elif status in ["FAILED", "CANCELLED"]:
                logger.error(f"Job failed with status: {status}")
                return 1
            
            # Wait before polling again
            logger.info(f"Waiting {args.poll_interval} seconds before next status check...")
            time.sleep(args.poll_interval)
            elapsed_time += args.poll_interval
        
        if status != "SUCCESSFUL":
            logger.error("Maximum polling time reached, job did not complete in time")
            return 1
        
        # Get job results
        logger.info("Retrieving job results...")
        results = client.get_job_results(job_id, secret)
        
        # Download result files
        logger.info(f"Downloading result files to {output_dir}...")
        for file_name, file_url in results["result_files"].items():
            output_file = output_dir / file_name
            logger.info(f"Downloading {file_name}...")
            
            client.download_result_file(file_url, str(output_file))
            logger.info(f"Downloaded {file_name} to {output_file}")
        
        logger.info("All results downloaded successfully")
        logger.info(f"Results are available in: {output_dir}")
        return 0
        
    except BaktaApiError as e:
        logger.error(f"API Error: {str(e)}")
        return 1
    except BaktaException as e:
        logger.error(f"Bakta Error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    exit_code = run_bakta_job(args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 