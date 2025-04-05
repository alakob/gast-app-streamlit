#!/usr/bin/env python3
"""
Script to annotate a FASTA sequence using the Bakta API.
"""

import requests
import json
import time
import sys
import os
from pathlib import Path

# Bakta API base URL
BASE_URL = "https://api.bakta.computational.bio/api/v1"

def initialize_job():
    """Initialize a new Bakta annotation job"""
    init_url = f"{BASE_URL}/job/init"
    
    payload = {
        "name": "OXA-264_analysis",
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

def download_all_results(results, output_dir="bakta_results"):
    """Download all result files from the results response"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # File type to extension mapping
    extension_map = {
        "EMBL": "embl",
        "FAA": "faa",
        "FAAHypothetical": "hypotheticals.faa",
        "FFN": "ffn",
        "FNA": "fna",
        "GBFF": "gbff",
        "GFF3": "gff3",
        "JSON": "json",
        "PNGCircularPlot": "png",
        "SVGCircularPlot": "svg",
        "TSV": "tsv",
        "TSVHypothetical": "hypotheticals.tsv",
        "TSVInference": "inference.tsv",
        "TXTLogs": "txt"
    }
    
    successful_downloads = 0
    total_files = len(results["ResultFiles"])
    
    print(f"\nDownloading {total_files} result files to '{output_dir}/' directory:")
    
    # Download each result file
    for file_type, url in results["ResultFiles"].items():
        if file_type in extension_map:
            output_path = os.path.join(output_dir, f"result.{extension_map[file_type]}")
            print(f"Downloading {file_type} to {output_path}...")
            
            if download_result_file(url, output_path):
                successful_downloads += 1
                print(f"✓ Successfully downloaded {file_type}")
            else:
                print(f"✗ Failed to download {file_type}")
        else:
            print(f"Unknown file type: {file_type}, URL: {url}")
    
    print(f"\nDownloaded {successful_downloads}/{total_files} files to '{output_dir}/' directory")
    return successful_downloads

def poll_job_status(job_id, secret, max_retries=12, sleep_time=10):
    """Poll the job status until it's completed or failed"""
    for i in range(max_retries):
        status_response = check_job_status(job_id, secret)
        job_status = status_response["jobs"][0]["jobStatus"]
        
        print(f"Current status: {job_status} (Check {i+1}/{max_retries})")
        
        if job_status == "SUCCESSFUL":
            print("\nJob completed successfully!")
            try:
                results = get_job_results(job_id, secret)
                print("\nResults URLs:")
                for file_type, url in results["ResultFiles"].items():
                    print(f"{file_type}: {url}")
                
                # Download all result files
                download_all_results(results)
            except Exception as e:
                print(f"Error getting results: {str(e)}")
            return status_response
            
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
            return status_response
        
        print(f"Waiting {sleep_time} seconds before checking again...")
        time.sleep(sleep_time)
    
    print(f"Max retries ({max_retries}) reached. The job is still running.")
    return check_job_status(job_id, secret)

def read_fasta_from_file(file_path):
    """Read FASTA content from a file"""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading FASTA file: {str(e)}")
        sys.exit(1)

def annotate_sequence(fasta_content):
    """Annotate a FASTA sequence using Bakta API"""
    print("Initializing Bakta job...")
    init_response = initialize_job()
    
    job_id = init_response["job"]["jobID"]
    secret = init_response["job"]["secret"]
    upload_link = init_response["uploadLinkFasta"]
    
    print(f"Job ID: {job_id}")
    print(f"Secret: {secret}")
    
    print("Uploading sequence...")
    upload_fasta(upload_link, fasta_content)
    
    print("Starting annotation job...")
    start_job(job_id, secret)
    
    print("Job successfully started!")
    print("\nTracking job status...")
    
    # Poll for job completion
    final_status = poll_job_status(job_id, secret)
    job_status = final_status["jobs"][0]["jobStatus"]
    
    print("\nTo view your job results, visit:")
    print(f"https://bakta.computational.bio/annotation/{job_id}?secret={secret}")
    
    # Save job info to a file for easy reference
    with open("bakta_job_info.txt", "w") as f:
        f.write(f"Job ID: {job_id}\n")
        f.write(f"Secret: {secret}\n")
        f.write(f"URL: https://bakta.computational.bio/annotation/{job_id}?secret={secret}\n")
        f.write(f"Final Status: {job_status}\n")
    
    return job_id, secret

def main():
    # Extract from the test.fasta file in the dataset
    fasta_content = """>OXA-264:27215228mrsa_S13_L001_R1_001_(paired)_contig_1
ATGAAGCTATCAAAATTATACACCCTCACTGTGCTCTTAGGATTTGGATTAAGCGGTGTC
GCCTGCCAGCATATCCATACTCCAGTCTTATTCAATCAAATTGAAAACGATCAAACAAAG
CAGATCGCTTCCTTGTTTGAGAATGTTCAAACAACAGGTGTTCTAATTACCTTTGATGGA
CAGGCGTATAAAGCATACGGTAATGATCTGAATCGTGCCAAAACTGCGTATATCCCAGCA
TCTACTTTCAAAATATTAAATGCTTTGATTGGCATTGAACATGATAAAACTTCACCAAAT
GAAGTATTTAAGTGGGATGGTCAGAAGCGTGCTTTTGAAAGTTGGGAAAAAGATCTGACT
TTAGCTGAAGCCATGCAAGCTTCTGCTGTACCTGTTTATCAAGCGCTTGCCCAGAGAATC
GGATTGGATTTGATGGCAAAGGAAGTCAAAAGAGTCGGCTTCGGTAATACACGCATCGGA
ACACAAGTTGATAACTTCTGGCTCATTGGACCTTTAAAGATCACGCCAATCGAAGAAGCT
CAATTTGCTTACAGGCTTGCGAAACAGGAGTTACCATTTACCCCAAAAACACAACAGCAA
GTGATTGATATGCTGCTGGTGGATGAAATACGGGGAACTAAAGTTTACGCCAAAAGTGGT
TGGGGAATGGATATTACTCCGCAAGTAGGATGGTGGACTGGATGGATTGAAGATCCGAAC
GGAAAAGTGATCGCTTTTTCTCTCAATATGGAAATGAATCAACCTGCGCATGCAGCTGCA
CGTAAAGAAGTTGTTTATCAGGCACTTACGCAATTGAAATTGTTGTAA"""
    
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Reading sequence from file: {file_path}")
        fasta_content = read_fasta_from_file(file_path)
    
    annotate_sequence(fasta_content)

if __name__ == "__main__":
    main() 