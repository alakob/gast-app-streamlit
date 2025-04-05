#!/usr/bin/env python3
"""
Simple fix for the database connection issue in background tasks.

This script makes a minimal change to the predict_task function to create a new
job repository instance for the background task.
"""
import os
import sys
import shutil
import time
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_predict_task():
    """Make a simple fix to create a new repository instance for background tasks"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    create_backup(API_PATH)
    
    # Read the file content
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Add a local repository creation at the beginning of predict_task
    old_predict_task_start = """async def predict_task(job_id: str, fasta_path: str, model_name: str, batch_size: int,
                     segment_length: int, segment_overlap: int, use_cpu: bool,
                     resistance_threshold: float, enable_sequence_aggregation: bool):
    \"\"\"
    Background task for running AMR prediction.
    
    Args:
        job_id: Job ID for tracking
        fasta_path: Path to the FASTA file
        model_name: HuggingFace model name or path
        batch_size: Batch size for predictions
        segment_length: Maximum segment length, 0 to disable splitting
        segment_overlap: Overlap between segments
        use_cpu: Whether to force CPU inference instead of GPU
        resistance_threshold: Threshold for resistance classification (default: 0.5)
        enable_sequence_aggregation: Whether to enable sequence-level aggregation of results
    \"\"\"
    try:"""
    
    new_predict_task_start = """async def predict_task(job_id: str, fasta_path: str, model_name: str, batch_size: int,
                     segment_length: int, segment_overlap: int, use_cpu: bool,
                     resistance_threshold: float, enable_sequence_aggregation: bool):
    \"\"\"
    Background task for running AMR prediction.
    
    Args:
        job_id: Job ID for tracking
        fasta_path: Path to the FASTA file
        model_name: HuggingFace model name or path
        batch_size: Batch size for predictions
        segment_length: Maximum segment length, 0 to disable splitting
        segment_overlap: Overlap between segments
        use_cpu: Whether to force CPU inference instead of GPU
        resistance_threshold: Threshold for resistance classification (default: 0.5)
        enable_sequence_aggregation: Whether to enable sequence-level aggregation of results
    \"\"\"
    # Create a fresh repository instance for the background task
    bg_job_repository = AMRJobRepository()
    
    try:"""
    
    # Replace all occurrences of job_repository with bg_job_repository in the predict_task function
    lines = content.split('\n')
    in_predict_task = False
    in_job_repository_usage = False
    result_lines = []
    
    for line in lines:
        if "async def predict_task" in line:
            in_predict_task = True
            result_lines.append(line)
        elif in_predict_task and "async def" in line:
            # We've reached the next function
            in_predict_task = False
            result_lines.append(line)
        elif in_predict_task and "job_repository.update_job_status" in line:
            # Replace job_repository with bg_job_repository
            modified_line = line.replace("job_repository.update_job_status", "bg_job_repository.update_job_status")
            result_lines.append(modified_line)
        else:
            result_lines.append(line)
    
    # Join the lines back together
    modified_content = '\n'.join(result_lines)
    
    # Replace the try line with our new code that creates the repository
    modified_content = modified_content.replace(old_predict_task_start, new_predict_task_start)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(modified_content)
    
    print(f"Successfully modified predict_task in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_predict_task():
        print("\nBackground task fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix background task. See error messages above.")
        sys.exit(1)
