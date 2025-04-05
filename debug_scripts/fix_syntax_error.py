#!/usr/bin/env python3
"""
Fix syntax error in the modified API file.

This script repairs the syntax error in the predict_task function that was
introduced by the previous fix.
"""
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

def fix_syntax_error():
    """Fix the syntax error in the API file"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    create_backup(API_PATH)
    
    # Read the entire file as lines to preserve line numbers
    with open(API_PATH, 'r') as f:
        lines = f.readlines()
    
    # Write a completely new, corrected version of the file
    with open(API_PATH, 'w') as f:
        for i, line in enumerate(lines):
            # Replace WebProgressTracker._update_job_status method
            if "def _update_job_status(self, tracker):" in line:
                # Write the corrected method
                f.write("    def _update_job_status(self, tracker):\n")
                f.write("        \"\"\"\n")
                f.write("        Update the job status in the database.\n")
                f.write("        \n")
                f.write("        Args:\n")
                f.write("            tracker: The progress tracker\n")
                f.write("        \"\"\"\n")
                f.write("        # Create a local repository instance to ensure fresh connection\n")
                f.write("        local_repository = AMRJobRepository()\n")
                f.write("        \n")
                f.write("        try:\n")
                f.write("            # Update progress in database\n")
                f.write("            local_repository.update_job_status(\n")
                f.write("                job_id=self.job_id,\n")
                f.write("                status=\"Running\",\n")
                f.write("                progress=tracker.progress\n")
                f.write("            )\n")
                f.write("        except Exception as e:\n")
                f.write("            logger.error(f\"Error updating job status: {str(e)}\")\n")
                
                # Skip existing method lines
                while i < len(lines) - 1 and not lines[i+1].strip().startswith("# Background task functions"):
                    i += 1
                continue
            
            # Replace the predict_task function
            elif "async def predict_task" in line:
                # Write the corrected function
                f.write("async def predict_task(job_id: str, fasta_path: str, model_name: str, batch_size: int,\n")
                f.write("                     segment_length: int, segment_overlap: int, use_cpu: bool,\n")
                f.write("                     resistance_threshold: float, enable_sequence_aggregation: bool):\n")
                f.write("    \"\"\"\n")
                f.write("    Background task for running AMR prediction.\n")
                f.write("    \n")
                f.write("    Args:\n")
                f.write("        job_id: Job ID for tracking\n")
                f.write("        fasta_path: Path to the FASTA file\n")
                f.write("        model_name: HuggingFace model name or path\n")
                f.write("        batch_size: Batch size for predictions\n")
                f.write("        segment_length: Maximum segment length, 0 to disable splitting\n")
                f.write("        segment_overlap: Overlap between segments\n")
                f.write("        use_cpu: Whether to force CPU inference instead of GPU\n")
                f.write("        resistance_threshold: Threshold for resistance classification (default: 0.5)\n")
                f.write("        enable_sequence_aggregation: Whether to enable sequence-level aggregation of results\n")
                f.write("    \"\"\"\n")
                f.write("    # Create a local repository instance for this background task\n")
                f.write("    task_job_repository = AMRJobRepository()\n")
                f.write("    \n")
                f.write("    try:\n")
                f.write("        # Create output file path\n")
                f.write("        output_file = os.path.join(RESULTS_DIR, f\"amr_predictions_{job_id}.tsv\")\n")
                f.write("        \n")
                f.write("        # Initialize progress tracker\n")
                f.write("        progress_tracker = WebProgressTracker(job_id=job_id)\n")
                f.write("        \n")
                f.write("        # Initialize pipeline\n")
                f.write("        pipeline = PredictionPipeline(\n")
                f.write("            model_name=model_name,\n")
                f.write("            batch_size=batch_size,\n")
                f.write("            segment_length=segment_length,\n")
                f.write("            segment_overlap=segment_overlap,\n")
                f.write("            device=\"cpu\" if use_cpu else None,\n")
                f.write("            progress_tracker=progress_tracker,\n")
                f.write("            enable_sequence_aggregation=enable_sequence_aggregation,\n")
                f.write("            resistance_threshold=resistance_threshold\n")
                f.write("        )\n")
                f.write("        \n")
                f.write("        # Process the FASTA file\n")
                f.write("        results = pipeline.process_fasta_file(fasta_path, output_file)\n")
                f.write("        \n")
                f.write("        # Update job status\n")
                f.write("        if \"error\" in results and results[\"error\"]:\n")
                f.write("            task_job_repository.update_job_status(\n")
                f.write("                job_id=job_id,\n")
                f.write("                status=\"Error\",\n")
                f.write("                error=results[\"error\"]\n")
                f.write("            )\n")
                f.write("        else:\n")
                f.write("            # Get the aggregated file path from pipeline results if available\n")
                f.write("            aggregated_file = None\n")
                f.write("            if enable_sequence_aggregation:\n")
                f.write("                # Check if the pipeline has the aggregated file path in its results\n")
                f.write("                if \"aggregated_output_file\" in results and results[\"aggregated_output_file\"]:\n")
                f.write("                    aggregated_file = results[\"aggregated_output_file\"]\n")
                f.write("                    # Verify the file exists\n")
                f.write("                    if not os.path.exists(aggregated_file):\n")
                f.write("                        logger.warning(f\"Aggregated file not found at {aggregated_file}\")\n")
                f.write("                        aggregated_file = None\n")
                f.write("                else:\n")
                f.write("                    # Fallback: Use naming convention to find aggregated file\n")
                f.write("                    base_output_file = output_file\n")
                f.write("                    if base_output_file.lower().endswith('.tsv'):\n")
                f.write("                        aggregated_file = base_output_file[:-4] + '_aggregated.tsv'\n")
                f.write("                    else:\n")
                f.write("                        aggregated_file = base_output_file + '_aggregated.tsv'\n")
                f.write("                    \n")
                f.write("                    # Verify the file exists\n")
                f.write("                    if not os.path.exists(aggregated_file):\n")
                f.write("                        logger.warning(f\"Expected aggregated file not found at {aggregated_file}\")\n")
                f.write("                        aggregated_file = None\n")
                f.write("            \n")
                f.write("            # Update job status in database\n")
                f.write("            # If aggregated file exists, include it in the update\n")
                f.write("            if aggregated_file:\n")
                f.write("                task_job_repository.update_job_status(\n")
                f.write("                    job_id=job_id,\n")
                f.write("                    status=\"Completed\",\n")
                f.write("                    progress=100.0,\n")
                f.write("                    result_file=output_file,\n")
                f.write("                    aggregated_result_file=aggregated_file\n")
                f.write("                )\n")
                f.write("            else:\n")
                f.write("                task_job_repository.update_job_status(\n")
                f.write("                    job_id=job_id,\n")
                f.write("                    status=\"Completed\",\n")
                f.write("                    progress=100.0,\n")
                f.write("                    result_file=output_file\n")
                f.write("                )\n")
                f.write("    \n")
                f.write("    except Exception as e:\n")
                f.write("        logger.error(f\"Error in prediction task: {str(e)}\")\n")
                f.write("        task_job_repository.update_job_status(\n")
                f.write("            job_id=job_id,\n")
                f.write("            status=\"Error\",\n")
                f.write("            error=str(e)\n")
                f.write("        )\n")
                
                # Skip existing function lines
                while i < len(lines) - 1 and not (lines[i+1].startswith("\n") and ("async def aggregate_task" in lines[i+2] or "def aggregate_task" in lines[i+2])):
                    i += 1
                continue
                
            # Fix the other background tasks in a similar way
            elif "async def aggregate_task" in line or "async def process_sequence_task" in line or "async def visualize_task" in line:
                task_name = line.strip().split("async def ")[1].split("(")[0]
                
                # Get the function signature
                signature = line
                
                # Write the corrected function start
                f.write(signature)
                
                # Add local repository creation
                f.write("    # Create a local repository instance for this background task\n")
                f.write("    task_job_repository = AMRJobRepository()\n")
                f.write("    \n")
                f.write("    try:\n")
                
                # Skip to the try block and continue with original code but replace job_repository
                in_try_block = False
                while i < len(lines) - 1:
                    i += 1
                    if lines[i].strip() == "try:":
                        in_try_block = True
                        continue  # Skip the try line as we've already written it
                    
                    if in_try_block:
                        # Replace job_repository with task_job_repository
                        if "job_repository.update_job_status" in lines[i]:
                            modified_line = lines[i].replace("job_repository.update_job_status", 
                                                         "task_job_repository.update_job_status")
                            f.write(modified_line)
                        else:
                            f.write(lines[i])
                    
                    # Stop when we reach the next function or end of file
                    if i < len(lines) - 1 and lines[i].strip() == "" and ("async def" in lines[i+1] or "def" in lines[i+1] or "@app." in lines[i+1]):
                        break
                
                continue
            
            # Write the line as is
            f.write(line)
    
    print(f"Successfully fixed syntax error in {API_PATH}")
    return True

if __name__ == "__main__":
    if fix_syntax_error():
        print("\nSyntax error fixed successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to fix syntax error. See error messages above.")
        sys.exit(1)
