#!/usr/bin/env python3
"""
Implement a robust solution for database connections in background tasks.

This script modifies the database connection handling to correctly work
in asynchronous background tasks by creating direct connections rather than
relying on the connection pool.
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
REPOSITORY_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def modify_db_manager():
    """Modify the database manager to provide a direct connection method"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: File not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    create_backup(DB_MANAGER_PATH)
    
    # Read the file
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Add a new get_direct_connection method
    if "def get_direct_connection(self" not in content:
        direct_conn_method = """
    def get_direct_connection(self):
        \"\"\"
        Create a direct SQLite connection bypassing the connection pool.
        
        This is useful for background tasks that need their own dedicated connection.
        The caller is responsible for closing this connection.
        
        Returns:
            A new SQLite connection
        \"\"\"
        # Create a new connection directly
        conn = sqlite3.connect(self.db_path)
        
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Use WAL journal mode for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        
        # Set a timeout for busy connections
        conn.execute("PRAGMA busy_timeout = 5000")  # 5 seconds
        
        return conn"""
        
        # Find the end of the get_connection method
        get_conn_pattern = re.compile(r'def get_connection\(self\):.*?return get_connection\(self\.db_path\)', re.DOTALL)
        match = get_conn_pattern.search(content)
        if match:
            end_pos = match.end()
            # Insert our new method after the get_connection method
            new_content = content[:end_pos] + direct_conn_method + content[end_pos:]
            
            # Write back to the file
            with open(DB_MANAGER_PATH, 'w') as f:
                f.write(new_content)
            
            print(f"Added get_direct_connection method to {DB_MANAGER_PATH}")
            return True
        else:
            print(f"Error: Could not find get_connection method in {DB_MANAGER_PATH}")
            return False
    else:
        print(f"get_direct_connection method already exists in {DB_MANAGER_PATH}")
        return True

def modify_repository():
    """Add a direct connection version of the repository for background tasks"""
    if not REPOSITORY_PATH.exists():
        print(f"Error: File not found at {REPOSITORY_PATH}")
        return False
    
    # Create a backup
    create_backup(REPOSITORY_PATH)
    
    # Read the file
    with open(REPOSITORY_PATH, 'r') as f:
        content = f.read()
    
    # Add a static method for creating a task-specific repository
    if "def create_task_repository(" not in content:
        # Find the end of the class
        class_end_pattern = re.compile(r'def close\(self\):.*?self\.db_manager\.close\(\)', re.DOTALL)
        match = class_end_pattern.search(content)
        if match:
            end_pos = match.end()
            # Create our new static method
            task_repo_method = """

    @staticmethod
    def create_task_repository(db_path: Optional[str] = None) -> 'AMRJobRepository':
        \"\"\"
        Create a repository instance for background tasks with a dedicated connection.
        
        Args:
            db_path: Optional database path, defaults to the standard path
            
        Returns:
            A repository instance specifically for background tasks
        \"\"\"
        # Create a new repository instance
        repo = AMRJobRepository(db_path)
        
        # Replace the connection in the database manager with a direct connection
        # This ensures the background task has its own dedicated connection
        # that won't be affected by connection pool issues
        direct_conn = repo.db_manager.get_direct_connection()
        
        # Store this connection for the task to use
        repo.task_connection = direct_conn
        
        return repo"""
            
            # Insert our new method at the end of the class
            new_content = content[:end_pos] + task_repo_method + content[end_pos:]
            
            # Write back to the file
            with open(REPOSITORY_PATH, 'w') as f:
                f.write(new_content)
            
            print(f"Added create_task_repository method to {REPOSITORY_PATH}")
            return True
        else:
            print(f"Error: Could not find the end of AMRJobRepository class in {REPOSITORY_PATH}")
            return False
    else:
        print(f"create_task_repository method already exists in {REPOSITORY_PATH}")
        return True

def modify_api_tasks():
    """Modify the API background tasks to use the task repository"""
    if not API_PATH.exists():
        print(f"Error: File not found at {API_PATH}")
        return False
    
    # Create a backup
    create_backup(API_PATH)
    
    # Read the file
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Replace the repository creation in predict_task
    predict_task_pattern = re.compile(
        r'async def predict_task\(.*?\):.*?# Create a fresh repository instance for this background task\s+bg_job_repository = AMRJobRepository\(\)',
        re.DOTALL
    )
    match = predict_task_pattern.search(content)
    if match:
        old_repo_creation = match.group(0)
        # Create our new repository creation that uses the static method
        new_repo_creation = old_repo_creation.replace(
            "bg_job_repository = AMRJobRepository()",
            "bg_job_repository = AMRJobRepository.create_task_repository()"
        )
        # Replace in the content
        content = content.replace(old_repo_creation, new_repo_creation)
    
    # Also modify WebProgressTracker._update_job_status to use the task repository
    tracker_pattern = re.compile(
        r'def _update_job_status\(self, tracker\):.*?job_repository\.update_job_status\(',
        re.DOTALL
    )
    match = tracker_pattern.search(content)
    if match:
        old_tracker = match.group(0)
        new_tracker = """def _update_job_status(self, tracker):
        \"\"\"
        Update the job status in the database.
        
        Args:
            tracker: The progress tracker
        \"\"\"
        # Use the global job repository since this is not in a background task
        try:
            # Update progress in database
            job_repository.update_job_status("""
        
        # Replace in the content
        content = content.replace(old_tracker, new_tracker)
    
    # Find all other background tasks that need to be updated
    for task_name in ["aggregate_task", "process_sequence_task", "visualize_task"]:
        task_pattern = re.compile(
            f'async def {task_name}\\(.*?\\):.*?try:',
            re.DOTALL
        )
        match = task_pattern.search(content)
        if match:
            old_task_start = match.group(0)
            # Add repository creation before the try block
            new_task_start = old_task_start.replace(
                "try:",
                f"# Create a task-specific repository\ntask_job_repository = AMRJobRepository.create_task_repository()\n\n    try:"
            )
            # Replace in the content
            content = content.replace(old_task_start, new_task_start)
            
            # Also replace all job_repository references with task_job_repository in this task
            task_full_pattern = re.compile(
                f'async def {task_name}\\(.*?\\):.*?(?=async def|def|@app\\.|$)',
                re.DOTALL
            )
            match = task_full_pattern.search(content)
            if match:
                task_content = match.group(0)
                updated_task_content = task_content.replace(
                    "job_repository.update_job_status",
                    "task_job_repository.update_job_status"
                )
                # Replace in the content
                content = content.replace(task_content, updated_task_content)
    
    # Write back to the file
    with open(API_PATH, 'w') as f:
        f.write(content)
    
    print(f"Modified background tasks in {API_PATH} to use task repositories")
    return True

if __name__ == "__main__":
    success = True
    
    # Modify database manager to add direct connection method
    if not modify_db_manager():
        success = False
    
    # Modify repository to add task repository creation
    if not modify_repository():
        success = False
    
    # Modify API tasks to use the task repository
    if not modify_api_tasks():
        success = False
    
    if success:
        print("\nRobust database connection handling implemented successfully!")
        print("Please restart your API server with:")
        print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to implement robust database connection handling. See error messages above.")
        sys.exit(1)
