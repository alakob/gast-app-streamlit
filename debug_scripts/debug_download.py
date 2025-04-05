#!/usr/bin/env python3
"""
Debug and fix the download endpoint to ensure both files are included in the zip.

This script:
1. Checks for completed jobs and their file paths
2. Verifies if the files exist
3. Updates the download endpoint to ensure proper zip creation
"""
import os
import sys
import re
import shutil
import time
import sqlite3
import zipfile
import io
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"

def backup_file(file_path):
    """Create a backup of a file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def check_completed_jobs():
    """Check completed jobs and their file paths"""
    if not DB_PATH.exists():
        print(f"Error: Database file not found at {DB_PATH}")
        return False
    
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get completed jobs
    cursor.execute("SELECT * FROM amr_jobs WHERE status = 'Completed' ORDER BY created_at DESC LIMIT 10")
    completed_jobs = cursor.fetchall()
    
    if not completed_jobs:
        print("No completed jobs found")
        return False
    
    print(f"Found {len(completed_jobs)} completed jobs")
    
    # Check file paths for each job
    for job in completed_jobs:
        job_dict = dict(job)
        job_id = job_dict.get('id')
        print(f"\nJob ID: {job_id}")
        
        # Get all columns and their values
        for key, value in job_dict.items():
            if key in ['result_file', 'aggregated_result_file', 'result_file_path']:
                print(f"  {key}: {value}")
                if value and os.path.exists(value):
                    print(f"  - File exists: Yes")
                    print(f"  - File size: {os.path.getsize(value)} bytes")
                else:
                    print(f"  - File exists: No")
    
    conn.close()
    return True

def update_download_endpoint():
    """Update the download endpoint to fix issues with zip creation"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the zip creation part of the download_result function
    zip_creation_pattern = re.compile(
        r'# Create a zip file in memory.*?# Reset buffer position to the beginning',
        re.DOTALL
    )
    
    match = zip_creation_pattern.search(content)
    if not match:
        print("Error: Could not find zip creation code in API file")
        return False
    
    old_zip_creation = match.group(0)
    
    # Create the updated zip creation code with better debugging and fallbacks
    new_zip_creation = '''# Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add regular file if it exists
            if regular_file_exists:
                regular_file_path = job["result_file"]
                regular_filename = os.path.basename(regular_file_path)
                print(f"Adding regular file to zip: {regular_file_path}")
                zip_file.write(regular_file_path, arcname=regular_filename)
            
            # Add aggregated file if it exists
            if aggregated_file_exists:
                aggregated_file_path = job["aggregated_result_file"]
                aggregated_filename = os.path.basename(aggregated_file_path)
                print(f"Adding aggregated file to zip: {aggregated_file_path}")
                zip_file.write(aggregated_file_path, arcname=aggregated_filename)
            
            # Try alternative paths if available
            if not aggregated_file_exists and "result_file_path" in job and job["result_file_path"]:
                # Try to find aggregated file based on the result_file_path
                result_path = job["result_file_path"]
                if os.path.exists(result_path):
                    print(f"Using result_file_path: {result_path}")
                    result_filename = os.path.basename(result_path)
                    # If not already added, add this file too
                    if not regular_file_exists or result_path != job.get("result_file", ""):
                        zip_file.write(result_path, arcname=result_filename)
                    
                    # Check for aggregated version with _aggregated suffix
                    if result_path.lower().endswith('.tsv'):
                        potential_aggregated = result_path[:-4] + '_aggregated.tsv'
                    else:
                        potential_aggregated = result_path + '_aggregated'
                    
                    if os.path.exists(potential_aggregated):
                        print(f"Found potential aggregated file: {potential_aggregated}")
                        aggregated_filename = os.path.basename(potential_aggregated)
                        zip_file.write(potential_aggregated, arcname=aggregated_filename)
        
        # Reset buffer position to the beginning'''
    
    # Replace the old zip creation code with the new one
    updated_content = content.replace(old_zip_creation, new_zip_creation)
    
    # Also make sure the debug logs will be visible
    if "print(f\"Adding regular file to zip:" in updated_content:
        updated_content = updated_content.replace(
            "import zipfile",
            "import zipfile\nimport logging"
        )
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully updated download endpoint in {API_PATH}")
    return True

def create_test_zip(job_id=None):
    """Create a test zip file with available job files"""
    if not DB_PATH.exists():
        print(f"Error: Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get job data
    if job_id:
        cursor.execute("SELECT * FROM amr_jobs WHERE id = ?", (job_id,))
    else:
        cursor.execute("SELECT * FROM amr_jobs WHERE status = 'Completed' ORDER BY created_at DESC LIMIT 1")
    
    job = cursor.fetchone()
    if not job:
        print("No suitable job found")
        return False
    
    job_dict = dict(job)
    job_id = job_dict.get('id')
    print(f"Creating test zip for job ID: {job_id}")
    
    # Collect all potential result files
    files_to_include = []
    
    # Check result_file
    if job_dict.get('result_file') and os.path.exists(job_dict['result_file']):
        files_to_include.append((job_dict['result_file'], os.path.basename(job_dict['result_file'])))
        print(f"Adding result_file: {job_dict['result_file']}")
    
    # Check aggregated_result_file
    if job_dict.get('aggregated_result_file') and os.path.exists(job_dict['aggregated_result_file']):
        files_to_include.append((job_dict['aggregated_result_file'], os.path.basename(job_dict['aggregated_result_file'])))
        print(f"Adding aggregated_result_file: {job_dict['aggregated_result_file']}")
    
    # Check result_file_path
    if job_dict.get('result_file_path') and os.path.exists(job_dict['result_file_path']):
        result_path = job_dict['result_file_path']
        files_to_include.append((result_path, os.path.basename(result_path)))
        print(f"Adding result_file_path: {result_path}")
        
        # Check for potential aggregated file
        if result_path.lower().endswith('.tsv'):
            potential_aggregated = result_path[:-4] + '_aggregated.tsv'
        else:
            potential_aggregated = result_path + '_aggregated'
        
        if os.path.exists(potential_aggregated):
            files_to_include.append((potential_aggregated, os.path.basename(potential_aggregated)))
            print(f"Adding potential aggregated file: {potential_aggregated}")
    
    # Create test zip file
    if not files_to_include:
        print("No files found to include in the zip")
        return False
    
    # Create the test zip
    zip_path = os.path.join(PROJECT_ROOT, f"test_amr_results_{job_id}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path, arcname in files_to_include:
            zip_file.write(file_path, arcname=arcname)
    
    print(f"Test zip created at: {zip_path}")
    print(f"Zip file size: {os.path.getsize(zip_path)} bytes")
    
    # Check zip contents
    print("\nZip file contents:")
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        for info in zip_file.infolist():
            print(f"  {info.filename} - {info.file_size} bytes")
    
    conn.close()
    return True

if __name__ == "__main__":
    print("Debugging download functionality...\n")
    
    # Check completed jobs and their file paths
    print("=== Checking completed jobs ===")
    check_completed_jobs()
    
    # Create a test zip file
    print("\n=== Creating test zip file ===")
    create_test_zip()
    
    # Update the download endpoint
    print("\n=== Updating download endpoint ===")
    if update_download_endpoint():
        print("\nDownload endpoint updated successfully!")
        print("The endpoint now includes better handling for finding and including both files.")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to update download endpoint. See error messages above.")
        sys.exit(1)
