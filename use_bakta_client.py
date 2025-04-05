#!/usr/bin/env python3
"""
Script that uses direct Bakta API calls to annotate a sequence.
This implementation matches the actual Bakta API which doesn't require an API key.
"""

import sys
import os
import requests
import json
import time
from pathlib import Path

# Bakta API base URL
BASE_URL = "https://api.bakta.computational.bio/api/v1"

def read_fasta_file(file_path):
    """Read a FASTA file and return its contents"""
    with open(file_path, 'r') as f:
        return f.read()

def initialize_job(name="OXA-264_analysis"):
    """Initialize a new Bakta annotation job"""
    init_url = f"{BASE_URL}/job/init"
    
    payload = {
        "name": name,
        "repliconTableType": "CSV"
    }
    
    response = requests.post(init_url, json=payload)
    
    if response.status_code != 200:
        print(f"Error initializing job: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return response.json()

def upload_fasta(upload_link, sequence):
    """Upload the FASTA sequence data"""
    response = requests.put(upload_link, data=sequence)
    
    if response.status_code != 200:
        print(f"Error uploading FASTA: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return True

def start_job(job_id, secret):
    """Start the annotation job"""
    start_url = f"{BASE_URL}/job/start"
    
    payload = {
        "config": {
            "completeGenome": False,
            "compliant": True,
            "dermType": None,
            "genus": "Unspecified",
            "hasReplicons": False,
            "keepContigHeaders": True,
            "locus": "OXA264",
            "locusTag": "OXA264",
            "minContigLength": 0,
            "plasmid": "",
            "prodigalTrainingFile": None,
            "species": "Unspecified",
            "strain": "OXA-264",
            "translationTable": 11
        },
        "job": {
            "jobID": job_id,
            "secret": secret
        }
    }
    
    response = requests.post(start_url, json=payload)
    
    if response.status_code != 200:
        print(f"Error starting job: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return True

def check_job_status(job_id, secret):
    """Check the status of the job"""
    list_url = f"{BASE_URL}/job/list"
    
    payload = {
        "jobs": [
            {
                "jobID": job_id,
                "secret": secret
            }
        ]
    }
    
    response = requests.post(list_url, json=payload)
    
    if response.status_code != 200:
        print(f"Error checking job status: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return response.json()

def get_job_logs(job_id, secret):
    """Get the logs of a job"""
    logs_url = f"{BASE_URL}/job/logs?jobID={job_id}&secret={secret}"
    
    response = requests.get(logs_url)
    
    if response.status_code != 200:
        print(f"Error getting job logs: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return response.text

def get_job_results(job_id, secret):
    """Get the results of a completed job"""
    result_url = f"{BASE_URL}/job/result"
    
    payload = {
        "jobID": job_id,
        "secret": secret
    }
    
    response = requests.post(result_url, json=payload)
    
    if response.status_code != 200:
        print(f"Error getting job results: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return response.json()

def download_result_file(url, output_path):
    """Download a result file from the given URL"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Calculate percentage and print progress
                        progress = int(50 * downloaded / total_size)
                        sys.stdout.write(f"\r[{'=' * progress}{' ' * (50 - progress)}] {downloaded}/{total_size} bytes ")
                        sys.stdout.flush()
                sys.stdout.write('\n')
        return True
    except Exception as e:
        print(f"Error downloading {url} to {output_path}: {str(e)}")
        return False

def poll_job_status(job_id, secret, max_retries=12, sleep_time=10):
    """Poll the job status until it's completed or failed"""
    for i in range(max_retries):
        status_response = check_job_status(job_id, secret)
        job_status = status_response["jobs"][0]["jobStatus"]
        
        print(f"Current status: {job_status} (Check {i+1}/{max_retries})")
        
        if job_status == "SUCCESSFUL":
            print("\nJob completed successfully!")
            return {"status": "SUCCESSFUL", "response": status_response}
            
        elif job_status == "ERROR":
            print("\nJob failed. Fetching logs for more information...")
            try:
                logs = get_job_logs(job_id, secret)
                print("\nJob Logs:")
                print("="*80)
                print(logs)
                print("="*80)
            except Exception as e:
                print(f"Error getting logs: {str(e)}")
            return {"status": "ERROR", "response": status_response, "logs": logs}
        
        print(f"Waiting {sleep_time} seconds before checking again...")
        time.sleep(sleep_time)
    
    print(f"Max retries ({max_retries}) reached. The job is still running.")
    return {"status": "RUNNING", "response": check_job_status(job_id, secret)}

def main():
    # Check if a file was provided
    if len(sys.argv) < 2:
        print("Usage: python use_bakta_client.py <fasta_file>")
        sys.exit(1)
    
    fasta_file = sys.argv[1]
    
    # Check if the file exists
    if not os.path.exists(fasta_file):
        print(f"Error: The file {fasta_file} does not exist.")
        sys.exit(1)
    
    try:
        # Read the FASTA sequence
        sequence = read_fasta_file(fasta_file)
        
        # Step 1: Initialize a job
        print("Initializing Bakta job...")
        init_response = initialize_job(name="oxa264_annotation")
        
        job_id = init_response["job"]["jobID"]
        secret = init_response["job"]["secret"]
        upload_link = init_response["uploadLinkFasta"]
        
        print(f"Job ID: {job_id}")
        print(f"Secret: {secret}")
        
        # Step 2: Upload the FASTA sequence
        print("Uploading sequence...")
        upload_fasta(upload_link, sequence)
        
        # Step 3: Start the annotation job
        print("Starting annotation job...")
        start_job(job_id, secret)
        
        print("Job successfully started!")
        print("\nTracking job status...")
        
        # Step 4: Poll for job completion
        final_status = poll_job_status(job_id, secret)
        
        # Step 5: Download results if job was successful
        if final_status["status"] == "SUCCESSFUL":
            # Create results directory
            results_dir = Path("bakta_client_results")
            results_dir.mkdir(exist_ok=True)
            
            # Get results
            print("Retrieving results...")
            results = get_job_results(job_id, secret)
            
            # Download result files
            print("Downloading result files...")
            for file_type, file_url in results["ResultFiles"].items():
                # Convert file type to lowercase and handle special cases
                output_filename = f"result.{file_type.lower()}"
                if file_type == "FAAHypothetical":
                    output_filename = "result.hypotheticals.faa"
                elif file_type == "TSVHypothetical":
                    output_filename = "result.hypotheticals.tsv"
                elif file_type == "TSVInference":
                    output_filename = "result.inference.tsv"
                elif file_type == "PNGCircularPlot":
                    output_filename = "result.png"
                elif file_type == "SVGCircularPlot":
                    output_filename = "result.svg"
                    
                output_path = results_dir / output_filename
                print(f"Downloading {file_type} to {output_path}...")
                
                if download_result_file(file_url, str(output_path)):
                    print(f"✓ Successfully downloaded {file_type}")
                else:
                    print(f"✗ Failed to download {file_type}")
            
            print(f"\nResults are available in: {results_dir}")
        
        # Save job info
        with open("bakta_client_job_info.txt", "w") as f:
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Secret: {secret}\n")
            f.write(f"URL: https://bakta.computational.bio/annotation/{job_id}?secret={secret}\n")
        
        print("\nTo view your job results, visit:")
        print(f"https://bakta.computational.bio/annotation/{job_id}?secret={secret}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 