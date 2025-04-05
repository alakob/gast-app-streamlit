#!/usr/bin/env python3
"""
Error handling example for the Bakta API client.

This script demonstrates how to use the Bakta API client with proper error handling
and validation.
"""

import sys
import time
from pathlib import Path
from amr_predictor.bakta.client import (
    BaktaClient, 
    BaktaApiError,
    BaktaNetworkError,
    BaktaResponseError,
    BaktaValidationError,
    BaktaAuthenticationError,
    BaktaResourceNotFoundError,
    BaktaJobError
)
from amr_predictor.bakta.config import create_config, get_api_url
from amr_predictor.bakta.validation import validate_fasta

def handle_validation_errors():
    """Example of handling validation errors"""
    print("\n=== Validation Error Examples ===")
    
    # Example 1: Invalid FASTA sequence
    invalid_fasta = """>Invalid Sequence with spaces and special chars
    ATGCGTX$
    """
    
    is_valid, error_msg = validate_fasta(invalid_fasta)
    if not is_valid:
        print(f"FASTA validation failed: {error_msg}")
    
    # Example 2: Try to submit invalid FASTA via client
    try:
        client = BaktaClient()
        init_response = client.initialize_job(name="invalid_test")
        
        job_id = init_response["job"]["jobID"]
        secret = init_response["job"]["secret"]
        upload_link = init_response["uploadLinkFasta"]
        
        # This will raise a BaktaValidationError
        client.upload_fasta(upload_link, invalid_fasta)
    except BaktaValidationError as e:
        print(f"Caught BaktaValidationError: {str(e)}")
    
    # Example 3: Invalid configuration
    try:
        client = BaktaClient()
        init_response = client.initialize_job(name="invalid_config_test")
        
        job_id = init_response["job"]["jobID"]
        secret = init_response["job"]["secret"]
        
        # Create an invalid configuration (translation_table must be one of [1, 4, 11])
        invalid_config = create_config(
            genus="Test",
            species="test",
            translation_table=99  # Invalid translation table
        )
        
        # This will raise a BaktaValidationError
        client.start_job(job_id, secret, invalid_config)
    except BaktaValidationError as e:
        print(f"Caught BaktaValidationError with invalid config: {str(e)}")

def handle_authentication_errors():
    """Example of handling authentication errors"""
    print("\n=== Authentication Error Examples ===")
    
    client = BaktaClient()
    
    # Example: Wrong secret for a valid job ID
    try:
        # Using a valid job ID but an invalid secret
        job_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"  # Example job ID
        wrong_secret = "wrong_secret"
        
        # This will raise a BaktaAuthenticationError
        client.check_job_status(job_id, wrong_secret)
    except BaktaAuthenticationError as e:
        print(f"Caught BaktaAuthenticationError: {str(e)}")
    except BaktaApiError as e:
        print(f"Caught generic API error: {str(e)}")

def handle_resource_not_found_errors():
    """Example of handling resource not found errors"""
    print("\n=== Resource Not Found Error Examples ===")
    
    client = BaktaClient()
    
    # Example: Non-existent job ID
    try:
        # Using a non-existent job ID
        non_existent_job_id = "00000000-0000-0000-0000-000000000000"
        fake_secret = "fake_secret"
        
        # This will raise a BaktaResourceNotFoundError
        client.get_job_results(non_existent_job_id, fake_secret)
    except BaktaResourceNotFoundError as e:
        print(f"Caught BaktaResourceNotFoundError: {str(e)}")
    except BaktaApiError as e:
        print(f"Caught generic API error: {str(e)}")

def handle_network_errors():
    """Example of handling network errors"""
    print("\n=== Network Error Examples ===")
    
    # Example: Invalid API URL
    try:
        # Create a client with an invalid base URL
        client = BaktaClient(base_url="https://invalid-url.example.com/api")
        
        # This will raise a BaktaNetworkError
        client.get_version_info()
    except BaktaNetworkError as e:
        print(f"Caught BaktaNetworkError: {str(e)}")

def proper_error_handling_example():
    """Example of proper error handling in a complete workflow"""
    print("\n=== Complete Workflow with Proper Error Handling ===")
    
    # Valid FASTA sequence
    valid_fasta = """>OXA-264
ATGAAGCTATCAAAATTATACACCCTCACTGTGCTCTTAGGATTTGGATTAAGCGGTGTC
GCCTGCCAGCATATCCATACTCCAGTCTTATTCAATCAAATTGAAAACGATCAAACAAAG
"""
    
    # Validate FASTA before submission
    is_valid, error_msg = validate_fasta(valid_fasta)
    if not is_valid:
        print(f"FASTA validation failed: {error_msg}")
        return
    
    # Get the API URL for the environment
    try:
        api_url = get_api_url("prod")
    except ValueError as e:
        print(f"Invalid environment: {str(e)}")
        return
    
    # Create client
    client = BaktaClient(base_url=api_url)
    
    try:
        # Step 1: Initialize a job
        print("Initializing Bakta job...")
        init_response = client.initialize_job(name="error_handling_example")
        
        job_id = init_response["job"]["jobID"]
        secret = init_response["job"]["secret"]
        upload_link = init_response["uploadLinkFasta"]
        
        print(f"Job ID: {job_id}")
        print(f"Secret: {secret}")
        
        # Step 2: Upload the FASTA sequence
        print("Uploading sequence...")
        client.upload_fasta(upload_link, valid_fasta)
        
        # Step 3: Create a valid configuration
        config = create_config(
            genus="Example",
            species="demonstration",
            strain="OXA-264",
            locus="OXA264",
            locus_tag="OXA264",
            translation_table=11
        )
        
        # Step 4: Start the annotation job
        print("Starting annotation job...")
        client.start_job(job_id, secret, config)
        
        print("Job successfully started!")
        print("\nTracking job status...")
        
        # Step 5: Poll for job completion (with shorter timeout for example)
        try:
            final_status = client.poll_job_status(
                job_id, 
                secret, 
                max_retries=3, 
                sleep_time=5,
                auto_download=True,
                output_dir="error_handling_example_results"
            )
            
            # Find the job in the response
            job_info = None
            for job in final_status["jobs"]:
                if job["jobID"] == job_id:
                    job_info = job
                    break
            
            if job_info:
                job_status = job_info["jobStatus"]
                print(f"Final job status: {job_status}")
                
                # Create results directory
                results_dir = Path("error_handling_example_results")
                results_dir.mkdir(exist_ok=True)
                
                # Save job info to a file for easy reference
                with open(results_dir / "job_info.txt", "w") as f:
                    f.write(f"Job ID: {job_id}\n")
                    f.write(f"Secret: {secret}\n")
                    f.write(f"URL: https://bakta.computational.bio/annotation/{job_id}?secret={secret}\n")
                    f.write(f"Final Status: {job_status}\n")
            else:
                print(f"Job {job_id} not found in the status response")
                
        except BaktaJobError as e:
            print(f"Job failed: {str(e)}")
        except BaktaResourceNotFoundError as e:
            print(f"Job not found: {str(e)}")
        except BaktaAuthenticationError as e:
            print(f"Authentication failed: {str(e)}")
        except BaktaValidationError as e:
            print(f"Validation error during polling: {str(e)}")
        except BaktaNetworkError as e:
            print(f"Network error during polling: {str(e)}")
        except BaktaResponseError as e:
            print(f"Response error during polling: {str(e)}")
        except Exception as e:
            print(f"Unexpected error during polling: {str(e)}")
        
    except BaktaValidationError as e:
        print(f"Validation error: {str(e)}")
    except BaktaNetworkError as e:
        print(f"Network error: {str(e)}")
    except BaktaResponseError as e:
        print(f"API response error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

def error_retry_example():
    """Example of retrying after transient errors"""
    print("\n=== Error Retry Example ===")
    
    client = BaktaClient()
    
    # Example: Retry logic for network errors
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Attempt to get version info (simulating any API call)
            print(f"Attempt {attempt + 1} of {max_retries}...")
            version_info = client.get_version_info()
            print(f"Success! Bakta version: {version_info}")
            break  # Success, exit the retry loop
        except BaktaNetworkError as e:
            print(f"Network error: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Optional: Exponential backoff
                retry_delay *= 2
            else:
                print(f"Max retries ({max_retries}) reached. Giving up.")
        except BaktaApiError as e:
            # Don't retry for non-network errors
            print(f"API error (not retrying): {str(e)}")
            break

def main():
    """Run the error handling examples"""
    print("=== Bakta API Client Error Handling Examples ===")
    
    try:
        # Run the examples
        handle_validation_errors()
        handle_authentication_errors()
        handle_resource_not_found_errors()
        handle_network_errors()
        error_retry_example()
        proper_error_handling_example()
        
        print("\nAll examples completed!")
    except Exception as e:
        print(f"Unexpected error in main: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 