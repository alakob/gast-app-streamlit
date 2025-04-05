#!/usr/bin/env python3
"""
Fix connection handling in the database manager to ensure connections remain open 
in background tasks.

This script introduces a new method get_fresh_connection in the AMRDatabaseManager
class to always get a fresh connection from the pool when needed during background
tasks and modifies the prediction_task to create its own repository instance.
"""
import os
import sys
import re
import shutil
import time
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def add_get_fresh_connection_method():
    """Add get_fresh_connection method to AMRDatabaseManager"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: File not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    create_backup(DB_MANAGER_PATH)
    
    # Read the entire file
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Find the get_connection method
    get_connection_pattern = re.compile(
        r'def get_connection\(self\):(.*?)return get_connection\(self\.db_path\)',
        re.DOTALL
    )
    
    match = get_connection_pattern.search(content)
    if not match:
        print("Error: Could not find get_connection method in the database manager")
        return False
    
    old_get_connection = match.group(0)
    
    # Create a new method get_fresh_connection right after the get_connection method
    new_methods = f'''def get_connection(self):
        """Get a connection from the pool"""
        return get_connection(self.db_path)
    
    def get_fresh_connection(self):
        """
        Get a fresh connection directly from sqlite3.
        
        This is useful for background tasks that need to ensure 
        the connection is not closed by other operations.
        
        Returns:
            A new sqlite3 connection that should be closed by the caller
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn'''
    
    # Replace the old method with the new methods
    new_content = content.replace(old_get_connection, new_methods)
    
    # Write the updated content back to the file
    with open(DB_MANAGER_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully added get_fresh_connection method to {DB_MANAGER_PATH}")
    return True

def modify_prediction_task():
    """Modify the prediction_task to use fresh connections"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    create_backup(API_PATH)
    
    # Read the entire file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the predict_task function
    predict_task_pattern = re.compile(
        r'async def predict_task\(.*?\):.*?except Exception as e:.*?error=str\(e\)\s+\)',
        re.DOTALL
    )
    
    match = predict_task_pattern.search(content)
    if not match:
        print("Error: Could not find predict_task function in the API file")
        return False
    
    old_task = match.group(0)
    
    # Create an updated version of the function with a local repository instance
    new_task = '''async def predict_task(job_id: str, fasta_path: str, model_name: str, batch_size: int,
                     segment_length: int, segment_overlap: int, use_cpu: bool,
                     resistance_threshold: float, enable_sequence_aggregation: bool):
    """
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
    """
    # Create a local repository instance for this background task
    # This ensures we have a fresh database connection for this task
    task_job_repository = AMRJobRepository()
    
    try:
        # Create output file path
        output_file = os.path.join(RESULTS_DIR, f"amr_predictions_{job_id}.tsv")
        
        # Initialize progress tracker that uses our task-specific repository
        progress_tracker = WebProgressTracker(job_id=job_id)
        
        # Initialize pipeline
        pipeline = PredictionPipeline(
            model_name=model_name,
            batch_size=batch_size,
            segment_length=segment_length,
            segment_overlap=segment_overlap,
            device="cpu" if use_cpu else None,
            progress_tracker=progress_tracker,
            enable_sequence_aggregation=enable_sequence_aggregation,
            resistance_threshold=resistance_threshold
        )
        
        # Process the FASTA file
        results = pipeline.process_fasta_file(fasta_path, output_file)
        
        # Update job status
        if "error" in results and results["error"]:
            task_job_repository.update_job_status(
                job_id=job_id,
                status="Error",
                error=results["error"]
            )
        else:
            # Get the aggregated file path from pipeline results if available
            aggregated_file = None
            if enable_sequence_aggregation:
                # Check if the pipeline has the aggregated file path in its results
                if "aggregated_output_file" in results and results["aggregated_output_file"]:
                    aggregated_file = results["aggregated_output_file"]
                    # Verify the file exists
                    if not os.path.exists(aggregated_file):
                        logger.warning(f"Aggregated file not found at {aggregated_file}")
                        aggregated_file = None
                else:
                    # Fallback: Use naming convention to find aggregated file
                    base_output_file = output_file
                    if base_output_file.lower().endswith('.tsv'):
                        aggregated_file = base_output_file[:-4] + '_aggregated.tsv'
                    else:
                        aggregated_file = base_output_file + '_aggregated.tsv'
                    
                    # Verify the file exists
                    if not os.path.exists(aggregated_file):
                        logger.warning(f"Expected aggregated file not found at {aggregated_file}")
                        aggregated_file = None
            
            # Update job status in database
            # If aggregated file exists, include it in the update
            if aggregated_file:
                task_job_repository.update_job_status(
                    job_id=job_id,
                    status="Completed",
                    progress=100.0,
                    result_file=output_file,
                    aggregated_result_file=aggregated_file
                )
            else:
                task_job_repository.update_job_status(
                    job_id=job_id,
                    status="Completed",
                    progress=100.0,
                    result_file=output_file
                )
    
    except Exception as e:
        logger.error(f"Error in prediction task: {str(e)}")
        task_job_repository.update_job_status(
            job_id=job_id,
            status="Error",
            error=str(e)
        )'''
    
    # Replace the old task with the new task
    new_content = content.replace(old_task, new_task)
    
    # Also update the WebProgressTracker class to use a local repository
    tracker_pattern = re.compile(
        r'def _update_job_status\(self, tracker\):(.*?)job_repository\.update_job_status\(',
        re.DOTALL
    )
    
    match = tracker_pattern.search(new_content)
    if match:
        old_tracker = match.group(0)
        new_tracker = '''def _update_job_status(self, tracker):
        """
        Update the job status in the database.
        
        Args:
            tracker: The progress tracker
        """
        # Create a local repository instance to ensure fresh connection
        local_repository = AMRJobRepository()
        
        try:
            # Update progress in database
            local_repository.update_job_status('''
        
        # Replace the tracker method
        new_content = new_content.replace(old_tracker, new_tracker)
    
    # Do the same for other background tasks
    for task_name in ["aggregate_task", "process_sequence_task", "visualize_task"]:
        task_pattern = re.compile(
            f'async def {task_name}\\(.*?\\):.*?except Exception as e:.*?error=str\\(e\\)\\s+\\)',
            re.DOTALL
        )
        
        match = task_pattern.search(new_content)
        if match:
            old_task = match.group(0)
            
            # Add local repository creation
            local_repo_line = f'''async def {task_name}('''
            local_repo_creation = f'''async def {task_name}('''
            
            # Find end of function args
            function_args_end = old_task.find('):')
            if function_args_end > 0:
                function_args = old_task[len(local_repo_line):function_args_end]
                function_definition = old_task[function_args_end+2:]
                
                # Create the pattern to insert at the start of the function body
                local_repo_creation = f'''async def {task_name}({function_args}):
    # Create a local repository instance for this background task
    task_job_repository = AMRJobRepository()
    '''
                
                # Build the new task with the local repository
                new_task_content = local_repo_creation + function_definition
                
                # Replace job_repository with task_job_repository
                new_task_content = new_task_content.replace("job_repository.update_job_status", 
                                                           "task_job_repository.update_job_status")
                
                # Replace the old task with the new task
                new_content = new_content.replace(old_task, new_task_content)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully modified background tasks in {API_PATH}")
    return True

if __name__ == "__main__":
    success = True
    
    # Add get_fresh_connection method
    if not add_get_fresh_connection_method():
        success = False
    
    # Modify prediction task
    if not modify_prediction_task():
        success = False
    
    if success:
        print("\nDatabase connection handling fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix database connection handling. See error messages above.")
        sys.exit(1)
