#!/usr/bin/env python3
"""
Test script to verify job creation and file download functionality.

This script:
1. Creates a new prediction job using a sample FASTA file
2. Monitors the job status until completion
3. Tests the download endpoint with the 'both' option
"""
import os
import time
import json
import requests
import tempfile
from pathlib import Path

# API settings
API_URL = "http://localhost:8000"
PREDICT_ENDPOINT = f"{API_URL}/predict"
JOBS_ENDPOINT = f"{API_URL}/jobs"

# Sample FASTA data for testing (short sequence)
SAMPLE_FASTA = """>Sample_Sequence
ATGACCATGATTACGGATTCACTGGCCGTCGTTTTACAACGTCGTGACTGGGAAAACCCTGGCGTTACCCAACTTAATCGCCTTGCAGCACATCCCCCTTTCGCC
AGCTGGCGTAATAGCGAAGAGGCCCGCACCGATCGCCCTTCCCAACAGTTGCGCAGCCTGAATGGCGAATGGCGCCTGATGCGGTATTTTCTCCTTACGCATC
TGTGCGGTATTTCACACCGCATATGGTGCACTCTCAGTACAATCTGCTCTGATGCCGCATAGTTAAGCCAGCCCCGACACCCGCCAACACCCGCTGACGCGCCC
"""

def create_test_fasta():
    """Create a temporary FASTA file for testing"""
    fd, filepath = tempfile.mkstemp(suffix=".fasta")
    with os.fdopen(fd, 'w') as f:
        f.write(SAMPLE_FASTA)
    return filepath

def create_job(fasta_file):
    """Create a new prediction job"""
    print(f"Creating new prediction job...")
    
    # Prepare the multipart form data
    files = {'file': open(fasta_file, 'rb')}
    data = {
        'model_name': 'alakob/DraGNOME-2.5b-v1',
        'batch_size': 8,
        'segment_length': 6000,
        'segment_overlap': 1200,
        'use_cpu': True,
        'resistance_threshold': 0.5,
        'enable_sequence_aggregation': True
    }
    
    # Submit the job
    response = requests.post(PREDICT_ENDPOINT, files=files, data=data)
    if response.status_code != 200:
        print(f"Error creating job: {response.text}")
        return None
    
    job_data = response.json()
    job_id = job_data.get('job_id')
    print(f"Job created successfully with ID: {job_id}")
    print(f"Initial status: {job_data.get('status')}")
    return job_id

def monitor_job(job_id, timeout=300, interval=5):
    """Monitor job status until completion or error"""
    print(f"Monitoring job {job_id}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Get job status
        response = requests.get(f"{JOBS_ENDPOINT}/{job_id}")
        if response.status_code != 200:
            print(f"Error checking job status: {response.text}")
            return False
        
        job_data = response.json()
        status = job_data.get('status')
        progress = job_data.get('progress', 0)
        print(f"Job status: {status}, Progress: {progress:.1f}%")
        
        # Check if job is done
        if status == "Completed":
            print(f"Job completed successfully!")
            print(f"Result file: {job_data.get('result_file')}")
            print(f"Aggregated result file: {job_data.get('aggregated_result_file')}")
            return True
        elif status == "Error":
            print(f"Job failed with error: {job_data.get('error')}")
            return False
        
        # Wait before checking again
        time.sleep(interval)
    
    print(f"Timeout reached after {timeout} seconds")
    return False

def test_download_both(job_id):
    """Test downloading both result files as a zip"""
    print(f"Testing download with 'both' option for job {job_id}...")
    
    # Download the combined zip file
    response = requests.get(f"{JOBS_ENDPOINT}/{job_id}/download?file_type=both", stream=True)
    if response.status_code != 200:
        print(f"Error downloading files: {response.text}")
        return False
    
    # Save the zip file
    zip_path = f"test_download_{job_id}.zip"
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Files downloaded successfully to {zip_path}")
    print(f"File size: {os.path.getsize(zip_path)} bytes")
    
    # List the contents of the zip file using Python's zipfile module
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        print("Zip file contents:")
        for file_info in zip_ref.infolist():
            print(f"  {file_info.filename} - {file_info.file_size} bytes")
    
    return True

def main():
    """Main test function"""
    print("Starting API test...")
    
    # Create test FASTA file
    fasta_file = create_test_fasta()
    print(f"Created test FASTA file: {fasta_file}")
    
    try:
        # Create a new job
        job_id = create_job(fasta_file)
        if not job_id:
            print("Failed to create job")
            return
        
        # Monitor job until completion
        job_completed = monitor_job(job_id)
        if not job_completed:
            print("Job monitoring failed")
            return
        
        # Test downloading both files
        download_success = test_download_both(job_id)
        if not download_success:
            print("Download test failed")
            return
        
        print("\nAll tests completed successfully!")
        print(f"Job ID: {job_id}")
        print(f"Download available at: {JOBS_ENDPOINT}/{job_id}/download?file_type=both")
        
    finally:
        # Clean up test FASTA file
        try:
            os.remove(fasta_file)
            print(f"Removed test FASTA file: {fasta_file}")
        except:
            pass

if __name__ == "__main__":
    main()
