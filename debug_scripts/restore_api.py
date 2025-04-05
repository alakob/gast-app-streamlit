#!/usr/bin/env python3
"""
Restore the API file from a backup and implement a cleaner fix for the download endpoint.

This script:
1. Restores the API file from a backup
2. Implements a clean version of the download endpoint with both option
"""
import sys
import re
import shutil
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def restore_api_from_backup():
    """Restore the API file from an earlier backup"""
    # Find the oldest backup that doesn't have our recent changes
    backup_files = list(PROJECT_ROOT.glob("amr_predictor/web/api.py.backup-*"))
    backup_files.sort(key=lambda x: x.stat().st_mtime)  # Sort by modification time
    
    # Use the first backup which should be the oldest/cleanest
    if backup_files:
        backup_file = backup_files[0]
        print(f"Restoring from backup: {backup_file}")
        shutil.copy2(backup_file, API_PATH)
        print(f"API file restored from backup")
        return True
    else:
        print("No backup files found")
        return False

def implement_download_endpoint():
    """Implement a clean version of the download endpoint with 'both' option"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the download_result function
    download_result_pattern = re.compile(
        r'@app\.get\("/jobs/{job_id}/download"\).*?return FileResponse\(path=file_path, filename=os\.path\.basename\(file_path\)\)',
        re.DOTALL
    )
    
    match = download_result_pattern.search(content)
    if not match:
        print("Error: Could not find download_result function in API file")
        return False
    
    old_download_result = match.group(0)
    
    # Create the updated download_result function with a 'both' option
    new_download_result = '''@app.get("/jobs/{job_id}/download")
async def download_result(
    job_id: str = Path(..., description="Job ID to download results for"),
    file_type: str = Query("regular", description="Type of file to download: 'regular', 'aggregated', or 'both'")
):
    """
    Download the result file(s) for a job.
    
    Args:
        job_id: Job ID to download results for
        file_type: Type of file to download ('regular', 'aggregated', or 'both')
        
    Returns:
        File response with the requested result file(s)
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
    job = job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.get("status") != "Completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed")
    
    # Check if both result files exist
    regular_file_exists = job.get("result_file") and os.path.exists(job.get("result_file", ""))
    aggregated_file_exists = job.get("aggregated_result_file") and os.path.exists(job.get("aggregated_result_file", ""))
    
    # Handle the 'both' option to download both files as a zip
    if file_type.lower() == "both":
        # Ensure at least one file exists
        if not regular_file_exists and not aggregated_file_exists:
            raise HTTPException(status_code=404, detail=f"No result files found for job {job_id}")
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add regular file if it exists
            if regular_file_exists:
                regular_file_path = job["result_file"]
                regular_filename = os.path.basename(regular_file_path)
                zip_file.write(regular_file_path, arcname=regular_filename)
            
            # Add aggregated file if it exists
            if aggregated_file_exists:
                aggregated_file_path = job["aggregated_result_file"]
                aggregated_filename = os.path.basename(aggregated_file_path)
                zip_file.write(aggregated_file_path, arcname=aggregated_filename)
        
        # Reset buffer position to the beginning
        zip_buffer.seek(0)
        
        # Create a streaming response with the zip file
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=amr_results_{job_id}.zip"}
        )
    
    # Handle individual file downloads
    elif file_type.lower() == "aggregated":
        if not aggregated_file_exists:
            raise HTTPException(status_code=404, detail=f"Aggregated result file for job {job_id} not found")
        file_path = job["aggregated_result_file"]
    else:  # Default to regular file
        if not regular_file_exists:
            raise HTTPException(status_code=404, detail=f"Result file for job {job_id} not found")
        file_path = job["result_file"]
    
    return FileResponse(path=file_path, filename=os.path.basename(file_path))'''
    
    # Replace the old download_result with the new one
    updated_content = content.replace(old_download_result, new_download_result)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully implemented download endpoint in {API_PATH}")
    return True

if __name__ == "__main__":
    # First restore from backup
    if restore_api_from_backup():
        # Then implement a clean version of the download endpoint
        if implement_download_endpoint():
            print("\nDownload endpoint implemented successfully!")
            print("You can now download both files using: /jobs/{job_id}/download?file_type=both")
            print("Please restart your API server with:")
            print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
        else:
            print("\nFailed to implement download endpoint. See error messages above.")
            sys.exit(1)
    else:
        print("\nFailed to restore API file. See error messages above.")
        sys.exit(1)
