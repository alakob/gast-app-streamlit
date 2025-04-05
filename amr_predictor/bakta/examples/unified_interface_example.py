#!/usr/bin/env python3
"""
Example demonstrating the unified Bakta interface.

This script shows how to use the BaktaUnifiedInterface to submit jobs,
retrieve results, and query annotations.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any

# Import the unified interface
from amr_predictor.bakta.unified_interface import (
    BaktaUnifiedInterface,
    create_bakta_interface
)
from amr_predictor.bakta.dao.query_builder import (
    FilterOperator,
    LogicalOperator
)
from amr_predictor.bakta.query_interface import SortOrder
from amr_predictor.bakta.models import JobStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bakta-example")

# Path to sample genome
SAMPLE_GENOME = Path(__file__).parent / "sample_genome.fasta"

async def run_full_workflow(fasta_file: Path):
    """
    Demonstrate a full workflow using the unified interface.
    
    Args:
        fasta_file: Path to FASTA file to analyze
    """
    # Initialize the unified interface
    # In a real application, you would set the API key in an environment variable
    api_key = os.environ.get("BAKTA_API_KEY")
    if not api_key:
        logger.error("BAKTA_API_KEY environment variable not set")
        sys.exit(1)

    async with BaktaUnifiedInterface(api_key=api_key) as bakta:
        try:
            # Step 1: Submit a job
            logger.info(f"Submitting job for {fasta_file}")
            job_id = await bakta.submit_job(
                fasta_file=fasta_file,
                job_name="Unified Interface Example",
                min_contig_length=200
            )
            logger.info(f"Job submitted with ID: {job_id}")
            
            # Step 2: Wait for job completion
            logger.info("Waiting for job to complete...")
            status = await bakta.wait_for_job(
                job_id=job_id,
                polling_interval=30,  # Check every 30 seconds
                timeout=1800  # 30 minutes timeout
            )
            
            if status != JobStatus.COMPLETED:
                logger.error(f"Job failed with status: {status}")
                return
            
            logger.info("Job completed successfully!")
            
            # Step 3: Download results
            output_dir = Path("bakta_results")
            output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Downloading results to {output_dir}")
            result_files = await bakta.download_results(
                job_id=job_id,
                output_dir=output_dir
            )
            
            logger.info(f"Downloaded {len(result_files)} result files:")
            for file_type, file_path in result_files.items():
                logger.info(f"  {file_type}: {file_path}")
            
            # Step 4: Import results into database
            gff_file = result_files.get("gff3")
            json_file = result_files.get("json")
            
            if gff_file and json_file:
                logger.info("Importing results into database")
                count = await bakta.import_results(
                    job_id=job_id,
                    gff_file=gff_file,
                    json_file=json_file
                )
                logger.info(f"Imported {count} annotations")
            else:
                logger.warning("Missing result files for import")
                return
            
            # Step 5: Query annotations
            # Get summary information
            feature_types = bakta.get_feature_types(job_id)
            contigs = bakta.get_contigs(job_id)
            
            logger.info(f"Found {len(feature_types)} feature types: {', '.join(feature_types)}")
            logger.info(f"Found {len(contigs)} contigs: {', '.join(contigs[:5])}...")
            
            # Count annotations by type
            for feature_type in feature_types:
                count = bakta.count_annotations(job_id, feature_type)
                logger.info(f"  {feature_type}: {count} annotations")
            
            # Query CDS annotations with pagination
            logger.info("Querying CDS annotations (first 10):")
            options = bakta.create_query_options(
                sort_by="start",
                sort_order=SortOrder.ASC,
                limit=10,
                offset=0
            )
            
            result = bakta.get_annotations(job_id, "CDS", options)
            logger.info(f"Retrieved {len(result.items)} of {result.total_count} CDS annotations")
            
            # Display some results
            for i, annotation in enumerate(result.items, 1):
                logger.info(f"  {i}. {annotation.feature_id}: {annotation.start}-{annotation.end} "
                           f"({annotation.attributes.get('product', 'Unknown')})")
            
            # Query in a range
            if contigs:
                contig = contigs[0]
                start = 1000
                end = 5000
                logger.info(f"Querying annotations in range {contig}:{start}-{end}")
                
                range_results = bakta.get_annotations_in_range(job_id, contig, start, end)
                logger.info(f"Found {len(range_results)} annotations in range")
                
                # Display results
                for i, annotation in enumerate(range_results[:5], 1):
                    logger.info(f"  {i}. {annotation.feature_type} {annotation.feature_id}: "
                               f"{annotation.start}-{annotation.end}")
            
            # Complex query with multiple conditions
            logger.info("Performing complex query:")
            
            # Create a query builder
            builder = bakta.create_query_builder(logical_operator=LogicalOperator.AND)
            
            # Add conditions
            builder.add_condition("feature_type", FilterOperator.IN, ["CDS", "gene"])
            builder.add_condition("strand", FilterOperator.EQUALS, "+")
            
            # Add attribute condition
            if "CDS" in feature_types:
                builder.add_condition("product", FilterOperator.CONTAINS, "protein", is_attribute=True)
            
            # Create options with the conditions
            complex_options = bakta.create_query_options(
                sort_by="start",
                limit=5
            )
            complex_options.filters = builder.conditions
            
            # Execute the query
            complex_result = bakta.get_annotations(job_id, options=complex_options)
            logger.info(f"Complex query found {complex_result.total_count} matching annotations")
            
            # Display some results
            for i, annotation in enumerate(complex_result.items, 1):
                product = annotation.attributes.get("product", "Unknown")
                logger.info(f"  {i}. {annotation.feature_type} {annotation.feature_id}: "
                           f"{annotation.start}-{annotation.end} ({product})")
            
            logger.info("Unified interface workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            raise

async def check_existing_job(job_id: str):
    """
    Demonstrate how to check and analyze an existing job.
    
    Args:
        job_id: Existing job ID to check
    """
    # Create interface with factory function
    bakta = create_bakta_interface()
    
    try:
        # Get job status
        status = await bakta.get_job_status(job_id)
        logger.info(f"Job {job_id} status: {status}")
        
        if status == JobStatus.COMPLETED:
            # Get feature summary
            feature_types = bakta.get_feature_types(job_id)
            total_annotations = bakta.count_annotations(job_id)
            
            logger.info(f"Job has {total_annotations} total annotations")
            logger.info(f"Feature types: {', '.join(feature_types)}")
            
            # Get annotation counts by type
            for feature_type in feature_types:
                count = bakta.count_annotations(job_id, feature_type)
                logger.info(f"  {feature_type}: {count}")
    finally:
        # Close the interface
        bakta.close()

def main():
    """Main entry point for the example script."""
    if len(sys.argv) > 1:
        # If job ID is provided, check existing job
        job_id = sys.argv[1]
        asyncio.run(check_existing_job(job_id))
    else:
        # If FASTA file exists, run full workflow
        if SAMPLE_GENOME.exists():
            asyncio.run(run_full_workflow(SAMPLE_GENOME))
        else:
            logger.error(f"Sample genome file not found: {SAMPLE_GENOME}")
            logger.info("Please provide a FASTA file path or existing job ID")
            sys.exit(1)

if __name__ == "__main__":
    main() 