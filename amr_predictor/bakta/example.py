#!/usr/bin/env python3
"""
Example usage of the Bakta API client.

This script demonstrates how to use the Bakta API client to submit a genome
for annotation and retrieve the results.
"""

import sys
from pathlib import Path
from amr_predictor.bakta.client import BaktaClient, BaktaApiError
from amr_predictor.bakta.config import create_config, get_api_url

def main():
    """Example of using the Bakta API client"""
    try:
        # Get the API URL for the production environment
        api_url = get_api_url("prod")
        
        # Initialize the client
        client = BaktaClient(base_url=api_url)
        
        # Example FASTA sequence (shortened for demonstration)
        sequence = """>OXA-264
ATGAAGCTATCAAAATTATACACCCTCACTGTGCTCTTAGGATTTGGATTAAGCGGTGTC
GCCTGCCAGCATATCCATACTCCAGTCTTATTCAATCAAATTGAAAACGATCAAACAAAG
CAGATCGCTTCCTTGTTTGAGAATGTTCAAACAACAGGTGTTCTAATTACCTTTGATGGA
CAGGCGTATAAAGCATACGGTAATGATCTGAATCGTGCCAAAACTGCGTATATCCCAGCA
"""
        
        # Step 1: Initialize a job
        print("Initializing Bakta job...")
        init_response = client.initialize_job(name="example_annotation", replicon_table_type="CSV")
        
        job_id = init_response["job"]["jobID"]
        secret = init_response["job"]["secret"]
        upload_link = init_response["uploadLinkFasta"]
        
        print(f"Job ID: {job_id}")
        print(f"Secret: {secret}")
        
        # Step 2: Upload the FASTA sequence
        print("Uploading sequence...")
        client.upload_fasta(upload_link, sequence)
        
        # Step 3: Create a custom configuration
        config = create_config(
            genus="Example",
            species="demonstration",
            strain="OXA-264",
            locus="OXA264",
            locus_tag="OXA264",
            complete_genome=False,
            translation_table=11
        )
        
        # Step 4: Start the annotation job
        print("Starting annotation job...")
        client.start_job(job_id, secret, config)
        
        print("Job successfully started!")
        print("\nTracking job status...")
        
        # Step 5: Poll for job completion (with shorter timeout for example)
        final_status = client.poll_job_status(job_id, secret, max_retries=3, sleep_time=5)
        job_status = final_status["jobs"][0]["jobStatus"]
        
        # Step 6: Display results URL and save job info
        print("\nTo view your job results, visit:")
        print(f"https://bakta.computational.bio/annotation/{job_id}?secret={secret}")
        
        # Create results directory
        results_dir = Path("bakta_results")
        results_dir.mkdir(exist_ok=True)
        
        # Save job info to a file for easy reference
        with open(results_dir / "job_info.txt", "w") as f:
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Secret: {secret}\n")
            f.write(f"URL: https://bakta.computational.bio/annotation/{job_id}?secret={secret}\n")
            f.write(f"Final Status: {job_status}\n")
        
        return job_id, secret
        
    except BaktaApiError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 