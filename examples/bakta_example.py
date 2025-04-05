#!/usr/bin/env python3
"""
Example script demonstrating how to use the Bakta integration.

This script shows the complete workflow for processing bacterial genomic data
using the Bakta annotation service:
1. Create and configure a Bakta job
2. Submit the job to the Bakta API
3. Monitor job status
4. Download and process results
5. Retrieve processed annotations and sequences
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

# Add parent directory to path so we can import amr_predictor
sys.path.append(str(Path(__file__).parent.parent))

from amr_predictor.bakta import (
    BaktaManager,
    BaktaStorageService,
    create_config,
    validate_fasta
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bakta-example")

# Sample FASTA content (shortened for example purposes)
SAMPLE_FASTA = """>Ecoli
ATGAACCTATTTATTGCCATGGTACGAAGGGAATTTTGCTGGATTAGTGACCGTAGGGCCAGC
AATTGAACCGAAGCAAATCGAATTTTCTGCTTCTTACGCAGATGTTCTCTTTGGTCAAAGATA
TGATGGTAAAACCGTGAAAGTAGATTTAGAGTCATGTGAAGATATCTTCAAAATTGAAGGAGA
AGCGCTACATATTCCGCAAGTACGCGGATATTTAATTACTGACGAAGCTGCCCGTGCGCGTTA
TGAGGATTTAACTACGCTTGCAACACCAGGTCTTTTAACTAAAACTAAAGTGGATCAATTGAA
"""

async def main():
    """Run the example Bakta workflow."""
    
    # Create results directory
    results_dir = Path("./bakta_results")
    results_dir.mkdir(exist_ok=True)
    
    # Initialize the Bakta manager
    manager = BaktaManager()
    
    # Create a job configuration
    config = create_config(
        organism="Escherichia coli",
        min_contig_length=200,
        gram="negative",
        locus_tag="ECOLI",
        genus="Escherichia",
        species="coli"
    )
    
    try:
        # Validate FASTA content first
        logger.info("Validating FASTA data...")
        validate_fasta(SAMPLE_FASTA)
        
        # Create a new job with the FASTA content
        logger.info("Creating a new Bakta job...")
        job = manager.create_job(
            name="Example Bakta Job",
            config=config,
            fasta_content=SAMPLE_FASTA
        )
        
        job_id = job.id
        logger.info(f"Created job with ID: {job_id}")
        
        # Start the job
        logger.info("Starting the job...")
        manager.start_job(job_id)
        
        # Monitor job status
        status = manager.check_job_status(job_id)
        logger.info(f"Initial job status: {status}")
        
        # Poll for job completion (this would typically be done with a background task,
        # but we're using a simple polling approach for the example)
        max_attempts = 30
        attempts = 0
        
        while status != "COMPLETED" and attempts < max_attempts:
            attempts += 1
            time.sleep(2)  # Check every 2 seconds
            status = manager.check_job_status(job_id)
            logger.info(f"Job status: {status}")
            
            if status in ["FAILED", "ERROR"]:
                logger.error(f"Job failed with status: {status}")
                sys.exit(1)
        
        if status != "COMPLETED":
            logger.warning("Job did not complete in time. Exiting.")
            sys.exit(1)
        
        # Create a storage service to process results
        storage_service = BaktaStorageService(
            repository=manager.repository,
            client=manager.client,
            results_dir=results_dir
        )
        
        # Download the result files
        logger.info("Downloading result files...")
        downloaded_files = storage_service.download_result_files(job_id)
        logger.info(f"Downloaded {len(downloaded_files)} files: {', '.join(downloaded_files.keys())}")
        
        # Process the files asynchronously
        logger.info("Processing result files...")
        processing_results = await storage_service.async_process_all_files(job_id)
        
        logger.info("Processing complete!")
        logger.info(f"Processed {processing_results['annotations']} annotations and "
                   f"{processing_results['sequences']} sequences with "
                   f"{processing_results['errors']} errors")
        
        # Get the processed results
        result = manager.get_result(job_id)
        
        logger.info(f"Annotations: {len(result.annotations)}")
        if result.annotations:
            logger.info("Sample annotation:")
            sample_annotation = result.annotations[0]
            logger.info(f"  Feature ID: {sample_annotation.feature_id}")
            logger.info(f"  Feature Type: {sample_annotation.feature_type}")
            logger.info(f"  Position: {sample_annotation.contig}:{sample_annotation.start}-{sample_annotation.end} ({sample_annotation.strand})")
        
        logger.info(f"Sequences: {len(result.sequences)}")
        if result.sequences:
            logger.info("Sample sequence:")
            sample_sequence = result.sequences[0]
            logger.info(f"  Header: {sample_sequence.header}")
            logger.info(f"  Length: {sample_sequence.length} bp")
        
    except Exception as e:
        logger.error(f"Error in Bakta workflow: {str(e)}")
        sys.exit(1)
    
    logger.info("Example completed successfully!")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 