#!/usr/bin/env python3
"""
Example script demonstrating how to use the BaktaJobManager.

This script shows how to use the BaktaJobManager for:
1. Creating and submitting jobs
2. Setting up job status notifications
3. Background job monitoring
4. Job status history tracking
5. Error handling and recovery
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add parent directory to path so we can import amr_predictor
sys.path.append(str(Path(__file__).parent.parent))

from amr_predictor.bakta import (
    BaktaJobManager,
    create_config,
    validate_fasta
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bakta-job-manager-example")

# Sample FASTA content (shortened for example purposes)
SAMPLE_FASTA = """>Ecoli
ATGAACCTATTTATTGCCATGGTACGAAGGGAATTTTGCTGGATTAGTGACCGTAGGGCCAGC
AATTGAACCGAAGCAAATCGAATTTTCTGCTTCTTACGCAGATGTTCTCTTTGGTCAAAGATA
TGATGGTAAAACCGTGAAAGTAGATTTAGAGTCATGTGAAGATATCTTCAAAATTGAAGGAGA
AGCGCTACATATTCCGCAAGTACGCGGATATTTAATTACTGACGAAGCTGCCCGTGCGCGTTA
TGAGGATTTAACTACGCTTGCAACACCAGGTCTTTTAACTAAAACTAAAGTGGATCAATTGAA
"""

def job_notification_callback(job_id, status):
    """
    Callback function for job status notifications.
    
    Args:
        job_id: ID of the job that changed status
        status: New status of the job
    """
    logger.info(f"JOB NOTIFICATION: Job {job_id} changed status to {status}")


def main():
    """Run the example demonstrating BaktaJobManager features."""
    
    # Create results directory
    results_dir = Path("./bakta_results")
    results_dir.mkdir(exist_ok=True)
    
    # Initialize the BaktaJobManager with notification callback
    job_manager = BaktaJobManager(
        poll_interval=10,  # Check job status every 10 seconds
        max_retries=3,     # Retry API calls up to 3 times
        notification_callback=job_notification_callback
    )
    
    try:
        # Start the background job poller
        logger.info("Starting background job poller...")
        job_manager.start_job_poller()
        
        # Check for any interrupted jobs that need recovery
        logger.info("Checking for interrupted jobs...")
        recovered_jobs = job_manager.recover_interrupted_jobs()
        if recovered_jobs:
            logger.info(f"Recovered {len(recovered_jobs)} interrupted jobs: {', '.join(recovered_jobs)}")
        else:
            logger.info("No interrupted jobs found.")
        
        # Create a job configuration
        config = create_config(
            organism="Escherichia coli",
            min_contig_length=200,
            gram="negative",
            locus_tag="ECOLI",
            genus="Escherichia",
            species="coli"
        )
        
        # Validate FASTA content
        logger.info("Validating FASTA data...")
        validate_fasta(SAMPLE_FASTA)
        
        # Create a temporary FASTA file
        with open("./temp_sample.fasta", "w") as f:
            f.write(SAMPLE_FASTA)
        
        # Submit the job asynchronously
        logger.info("Submitting job...")
        job = job_manager.submit_job(
            fasta_path="./temp_sample.fasta",
            name="Example JobManager Job",
            config=config,
            wait_for_completion=False,  # Don't wait - use background monitoring
            process_results=True        # Process results automatically when complete
        )
        
        logger.info(f"Submitted job with ID: {job.id}")
        logger.info("Job is being monitored in the background.")
        
        # Wait for a bit to demonstrate background processing
        logger.info("Main thread continues execution while job runs in background...")
        for i in range(3):
            logger.info(f"Main thread doing other work... ({i+1}/3)")
            time.sleep(2)
        
        # Get current job status
        job = job_manager.check_job_status(job.id)
        logger.info(f"Current job status: {job.status}")
        
        # Get job history
        history = job_manager.get_job_history(job.id)
        logger.info(f"Job status history ({len(history)} entries):")
        for entry in history:
            logger.info(f"  {entry.timestamp}: {entry.status}")
        
        # Demonstrate handling job failure (for example purposes)
        if job.status in ["FAILED", "ERROR"]:
            logger.info("Job failed, demonstrating retry functionality...")
            job_manager.retry_failed_job(job.id)
            logger.info(f"Retried job {job.id}")
        
        logger.info("Example will wait for 30 seconds for background job to progress...")
        time.sleep(30)
        
        # Check final status
        job = job_manager.check_job_status(job.id)
        logger.info(f"Job status after waiting: {job.status}")
        
        # If job completed, get the result
        if job.status in ["COMPLETED", "PROCESSED"]:
            result = job_manager.get_result(job.id)
            logger.info(f"Job has {len(result.annotations)} annotations and {len(result.sequences)} sequences")
            
            if result.annotations:
                logger.info(f"Sample annotation: {result.annotations[0].feature_id} ({result.annotations[0].feature_type})")
            
            if result.sequences:
                logger.info(f"Sample sequence: {result.sequences[0].header} ({result.sequences[0].length} bp)")
        
        # Clean up
        os.remove("./temp_sample.fasta")
        
    except Exception as e:
        logger.error(f"Error in job manager example: {str(e)}")
        raise
    finally:
        # Always stop the job poller before exiting
        logger.info("Stopping background job poller...")
        job_manager.stop_job_poller()
    
    logger.info("Job manager example completed.")


if __name__ == "__main__":
    main() 