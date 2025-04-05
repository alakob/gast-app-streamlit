#!/usr/bin/env python3
"""
Direct patch for the predict_task function to fix database connections.

This script directly patches the predict_task function in the API file 
to use an independent database connection that won't be affected by 
connection pool issues.
"""
import os
import sys
import re
import shutil
import sqlite3
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"

def backup_file(file_path):
    """Create a timestamped backup of a file"""
    timestamp = Path(file_path).stat().st_mtime
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def patch_predict_task():
    """Patch the predict_task function to use a direct database connection"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Make a backup
    backup_file(API_PATH)
    
    # Read the original file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Find the predict_task function and replace it with an updated version
    predict_task_pattern = re.compile(
        r'async def predict_task\(job_id: str, fasta_path: str, model_name: str, batch_size: int,.*?except Exception as e:.*?error=str\(e\)\s+\)',
        re.DOTALL
    )
    
    match = predict_task_pattern.search(content)
    if not match:
        print("Error: Could not find predict_task function in API file")
        return False
    
    old_predict_task = match.group(0)
    
    # Create the updated predict_task function with a direct database connection
    new_predict_task = '''async def predict_task(job_id: str, fasta_path: str, model_name: str, batch_size: int,
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
    try:
        # Create a direct database connection for the background task
        db_path = os.path.join(os.getcwd(), "data", "db", "predictor.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable optimizations
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        
        # Create a custom update_status function for this task
        def update_status(status, progress=None, error=None, result_file=None, aggregated_result_file=None):
            try:
                cursor = conn.cursor()
                
                # Build the update query
                update_fields = ["status = ?"]
                update_values = [status]
                
                if status in ["Completed", "Failed"]:
                    update_fields.append("end_time = ?")
                    update_values.append(datetime.now().isoformat())
                
                if progress is not None:
                    update_fields.append("progress = ?")
                    update_values.append(progress)
                
                if error is not None:
                    update_fields.append("error = ?")
                    update_values.append(error)
                
                if result_file is not None:
                    update_fields.append("result_file = ?")
                    update_values.append(result_file)
                
                if aggregated_result_file is not None:
                    update_fields.append("aggregated_result_file = ?")
                    update_values.append(aggregated_result_file)
                
                # Format the update query
                update_query = f"UPDATE amr_jobs SET {', '.join(update_fields)} WHERE id = ?"
                update_values.append(job_id)
                
                # Execute update
                cursor.execute(update_query, update_values)
                conn.commit()
                
                if error:
                    logger.error(f"Job {job_id} error: {error}")
                else:
                    logger.info(f"Updated AMR job status: {job_id} -> {status}")
                    
                return True
            except Exception as e:
                logger.error(f"Error updating job status: {str(e)}")
                return False
        
        # Create a custom progress tracker that uses our update function
        class DirectProgressTracker:
            def __init__(self, job_id, total_steps=100):
                self.job_id = job_id
                self.total_steps = total_steps
                self.current_step = 0
                self.progress = 0.0
            
            def update(self, step_increment=1):
                self.current_step += step_increment
                self.progress = min(100.0, (self.current_step / self.total_steps) * 100)
                update_status("Running", progress=self.progress)
                return self.progress
        
        # Create output file path
        output_file = os.path.join(RESULTS_DIR, f"amr_predictions_{job_id}.tsv")
        
        # Initialize our custom progress tracker
        progress_tracker = DirectProgressTracker(job_id=job_id)
        
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
            update_status(
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
                update_status(
                    status="Completed",
                    progress=100.0,
                    result_file=output_file,
                    aggregated_result_file=aggregated_file
                )
            else:
                update_status(
                    status="Completed",
                    progress=100.0,
                    result_file=output_file
                )
        
        # Close our database connection
        conn.close()
    
    except Exception as e:
        logger.error(f"Error in prediction task: {str(e)}")
        try:
            # Try to update job status with our direct connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE amr_jobs SET status = ?, error = ?, end_time = ? WHERE id = ?",
                ("Error", str(e), datetime.now().isoformat(), job_id)
            )
            conn.commit()
            conn.close()
        except Exception as conn_error:
            # If that fails, log it but don't crash
            logger.error(f"Error updating job status after task error: {str(conn_error)}")'''
    
    # Replace the old predict_task with the new one
    updated_content = content.replace(old_predict_task, new_predict_task)
    
    # Write the updated content back to the file
    with open(API_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Successfully patched predict_task function in {API_PATH}")
    return True

if __name__ == "__main__":
    if patch_predict_task():
        print("\nPredict task patched successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to patch predict task. See error messages above.")
        sys.exit(1)
