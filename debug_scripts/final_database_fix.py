#!/usr/bin/env python3
"""
Comprehensive solution for database connection issues.

This script implements a holistic approach to fix database connection issues:
1. Updates the API initialization to properly manage database connections
2. Ensures SQLite connections have the correct flags for thread safety
3. Implements proper connection pooling patterns
"""
import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
API_PATH = PROJECT_ROOT / "amr_predictor" / "web" / "api.py"
REPO_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "repository.py"
DB_MANAGER_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "database_manager.py"

def backup_file(file_path):
    """Create a backup of a file"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def fix_db_manager():
    """Update the database manager to use connection pooling"""
    if not DB_MANAGER_PATH.exists():
        print(f"Error: Database manager file not found at {DB_MANAGER_PATH}")
        return False
    
    # Create a backup
    backup_file(DB_MANAGER_PATH)
    
    # Read the current file content
    with open(DB_MANAGER_PATH, 'r') as f:
        content = f.read()
    
    # Check if the file already has our connection pool implementation
    if "def _create_connection_pool" not in content:
        # Add connection pool implementation
        class_start_pattern = re.compile(r'class AMRDatabaseManager\(.*?\):.*?def __init__', re.DOTALL)
        match = class_start_pattern.search(content)
        
        if match:
            class_init = match.group(0)
            
            # Replace the class initialization with one that includes connection pooling
            new_init = '''class AMRDatabaseManager():
    """
    Database manager for AMR Predictor.
    
    This class manages database connections and operations for AMR prediction jobs.
    It uses a simple connection pool to improve performance and reliability.
    """
    
    # Class-level connection pool
    _connection_pool = []
    _max_pool_size = 5
    
    @classmethod
    def _create_connection_pool(cls, db_path):
        """Create a pool of database connections"""
        import sqlite3
        import logging
        import threading
        
        # Create connection pool if it doesn't exist
        with threading.Lock():
            if len(cls._connection_pool) < cls._max_pool_size:
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    
                    # Create a new connection
                    conn = sqlite3.connect(db_path, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    
                    # Enable foreign keys
                    conn.execute("PRAGMA foreign_keys = ON")
                    
                    # Add to pool
                    cls._connection_pool.append(conn)
                    logging.debug(f"Created new database connection, pool size: {len(cls._connection_pool)}")
                except Exception as e:
                    logging.error(f"Error creating database connection for pool: {str(e)}")
    
    @classmethod
    def _get_connection_from_pool(cls, db_path):
        """Get a connection from the pool or create a new one"""
        import threading
        
        with threading.Lock():
            if not cls._connection_pool:
                cls._create_connection_pool(db_path)
            
            if cls._connection_pool:
                # Get a connection from the pool
                return cls._connection_pool.pop(0)
            else:
                # Fallback: create a direct connection if pool is empty
                return cls._create_direct_connection(db_path)
    
    @classmethod
    def _return_connection_to_pool(cls, conn):
        """Return a connection to the pool"""
        import threading
        
        with threading.Lock():
            if len(cls._connection_pool) < cls._max_pool_size:
                try:
                    # Test the connection before returning it to the pool
                    conn.execute("SELECT 1")
                    cls._connection_pool.append(conn)
                except:
                    # Connection is not valid, don't add it back
                    try:
                        conn.close()
                    except:
                        pass
            else:
                # Pool is full, close the connection
                try:
                    conn.close()
                except:
                    pass
    
    @staticmethod
    def _create_direct_connection(db_path):
        """Create a direct database connection (not pooled)"""
        import sqlite3
        import logging
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Create a new connection
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            return conn
        except Exception as e:
            logging.error(f"Error creating direct database connection: {str(e)}")
            raise
    
    def __init__'''
            
            # Replace the class initialization with the new one
            updated_content = content.replace(class_init, new_init)
            
            # Update the get_connection method to use the connection pool
            get_conn_pattern = re.compile(r'def get_connection\(self\):.*?return self\.conn', re.DOTALL)
            conn_match = get_conn_pattern.search(updated_content)
            
            if conn_match:
                old_get_conn = conn_match.group(0)
                
                # Create a new get_connection method that uses the connection pool
                new_get_conn = '''def get_connection(self):
        """
        Get a database connection.
        
        This method returns a connection from the pool or creates a new one.
        
        Returns:
            A SQLite connection object
        """
        try:
            # Check if we have a valid connection already
            if hasattr(self, 'conn') and self.conn:
                try:
                    # Test the connection
                    self.conn.execute("SELECT 1")
                    return self.conn
                except Exception:
                    # Connection is invalid, try to close it
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
            
            # Get a connection from the pool
            self.conn = self._get_connection_from_pool(self.db_path)
            return self.conn
        except Exception as e:
            import logging
            logging.error(f"Error getting database connection: {str(e)}")
            # Fallback to direct connection if pool fails
            self.conn = self._create_direct_connection(self.db_path)
            return self.conn'''
                
                # Replace the old get_connection with the new one
                updated_content = updated_content.replace(old_get_conn, new_get_conn)
                
                # Update the get_fresh_connection method
                fresh_conn_pattern = re.compile(r'def get_fresh_connection\(self\):.*?return conn', re.DOTALL)
                fresh_match = fresh_conn_pattern.search(updated_content)
                
                if fresh_match:
                    old_fresh_conn = fresh_match.group(0)
                    
                    # Create a new get_fresh_connection method
                    new_fresh_conn = '''def get_fresh_connection(self):
        """
        Get a fresh SQLite connection.
        
        This method always creates a new connection, bypassing the connection pool.
        Use this when you need to ensure a working connection, especially in background tasks
        or when the cached connection might be closed.
        
        Returns:
            A new SQLite connection object
        """
        return self._create_direct_connection(self.db_path)'''
                    
                    # Replace the old get_fresh_connection with the new one
                    updated_content = updated_content.replace(old_fresh_conn, new_fresh_conn)
                
                # Update the close method to return connections to the pool
                close_pattern = re.compile(r'def close\(self\):.*?self\.conn = None', re.DOTALL)
                close_match = close_pattern.search(updated_content)
                
                if close_match:
                    old_close = close_match.group(0)
                    
                    # Create a new close method that returns the connection to the pool
                    new_close = '''def close(self):
        """Close the database connection or return it to the pool."""
        if hasattr(self, 'conn') and self.conn:
            try:
                # Return the connection to the pool instead of closing it
                self._return_connection_to_pool(self.conn)
            except Exception as e:
                import logging
                logging.warning(f"Error returning connection to pool: {str(e)}")
                # Try to close it if returning to pool fails
                try:
                    self.conn.close()
                except:
                    pass
            self.conn = None'''
                    
                    # Replace the old close with the new one
                    updated_content = updated_content.replace(old_close, new_close)
                
                # Write the updated content back to the file
                with open(DB_MANAGER_PATH, 'w') as f:
                    f.write(updated_content)
                
                print(f"Successfully updated database manager in {DB_MANAGER_PATH}")
                return True
            else:
                print("Error: Could not find class initialization in database manager")
                return False
        else:
            print("Connection pooling already implemented in database manager")
            return True
    
    # Update the get_job method to be more robust
    job_pattern = re.compile(r'def get_job\(self, job_id: str\).*?return .*?job_data', re.DOTALL)
    job_match = job_pattern.search(content)
    
    if job_match:
        old_job = job_match.group(0)
        
        # Create a new get_job method with better error handling
        new_job = '''def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        """
        # Always use a fresh connection for job retrieval to avoid closed connection issues
        conn = self.get_fresh_connection()
        try:
            cursor = conn.cursor()
            
            # Get job data
            cursor.execute(
                """
                SELECT * FROM amr_jobs WHERE id = ?
                """,
                (job_id,)
            )
            
            job_row = cursor.fetchone()
            if not job_row:
                return None
                
            job_data = dict(job_row)
            
            # Map 'id' to 'job_id' for API compatibility
            if 'id' in job_data:
                job_data['job_id'] = job_data['id']
            
            # Get job parameters
            cursor.execute(
                """
                SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = ?
                """,
                (job_id,)
            )
            
            # Add parameters to job data
            for row in cursor.fetchall():
                job_data[row["param_name"]] = row["param_value"]
            
            return job_data
        except Exception as e:
            import logging
            logging.error(f"Error retrieving job {job_id}: {str(e)}")
            raise
        finally:
            # Always close the fresh connection
            try:
                conn.close()
            except:
                pass'''
        
        # Replace the old get_job with the new one
        updated_content = content.replace(old_job, new_job)
        
        # Write the updated content back to the file
        with open(DB_MANAGER_PATH, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated get_job method in {DB_MANAGER_PATH}")
        return True
    else:
        print("Error: Could not find get_job method in database manager")
        return False

def fix_repository():
    """Update the repository to handle database connections properly"""
    if not REPO_PATH.exists():
        print(f"Error: Repository file not found at {REPO_PATH}")
        return False
    
    # Create a backup
    backup_file(REPO_PATH)
    
    # Read the current file content
    with open(REPO_PATH, 'r') as f:
        content = f.read()
    
    # Add a close method to clean up at the end of requests
    close_pattern = re.compile(r'def close\(self\):.*?self\.db_manager\.close\(\)', re.DOTALL)
    close_match = close_pattern.search(content)
    
    # If the close method doesn't exist or we need to update it
    if not close_match:
        # Check if we need to add the method at the end of the class
        class_end_pattern = re.compile(r'class AMRJobRepository.*?def.*?}', re.DOTALL)
        class_match = class_end_pattern.search(content)
        
        if class_match:
            # Find the last method in the class
            methods = re.findall(r'def (\w+)\(self', content)
            if methods:
                last_method = methods[-1]
                last_method_pattern = re.compile(f'def {last_method}.*?}}', re.DOTALL)
                last_match = last_method_pattern.search(content)
                
                if last_match:
                    # Add the close method after the last method
                    new_content = content.replace(
                        last_match.group(0),
                        last_match.group(0) + '''

    def close(self):
        """Close the database manager."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()'''
                    )
                    
                    # Write the updated content back to the file
                    with open(REPO_PATH, 'w') as f:
                        f.write(new_content)
                    
                    print(f"Added close method to repository in {REPO_PATH}")
                    return True
            
            print("Could not find the right location to add close method to repository")
            return False
    else:
        print("Close method already exists in repository")
        return True

def fix_api_initialization():
    """Update the API to properly initialize and clean up database connections"""
    if not API_PATH.exists():
        print(f"Error: API file not found at {API_PATH}")
        return False
    
    # Create a backup
    backup_file(API_PATH)
    
    # Read the current file content
    with open(API_PATH, 'r') as f:
        content = f.read()
    
    # Add startup and shutdown events to manage the repository
    startup_shutdown_pattern = re.compile(r'# Initialize AMR job repository.*?job_repository = AMRJobRepository\(\)\n.*?"Initialized AMR job repository.*?"', re.DOTALL)
    startup_match = startup_shutdown_pattern.search(content)
    
    if startup_match:
        old_init = startup_match.group(0)
        
        # Create new initialization with startup and shutdown events
        new_init = '''# Initialize AMR job repository on demand
job_repository = None

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection on startup."""
    global job_repository
    job_repository = AMRJobRepository()
    logger.info("Initialized AMR job repository for job storage")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown."""
    global job_repository
    if job_repository:
        job_repository.close()
        logger.info("Closed AMR job repository")'''
        
        # Replace the old initialization with the new one
        updated_content = content.replace(old_init, new_init)
        
        # Check for the get_job_status endpoint and update it to handle null repository
        job_status_pattern = re.compile(r'@app\.get\("/jobs/\{job_id\}".*?\).*?async def get_job_status.*?try:.*?job = job_repository\.get_job\(job_id\)', re.DOTALL)
        job_match = job_status_pattern.search(updated_content)
        
        if job_match:
            old_job_status = job_match.group(0)
            
            # Create new job status endpoint that checks if repository is initialized
            new_job_status = old_job_status.replace(
                "job = job_repository.get_job(job_id)",
                "global job_repository\n    if not job_repository:\n        job_repository = AMRJobRepository()\n    job = job_repository.get_job(job_id)"
            )
            
            # Replace the old job status with the new one
            updated_content = updated_content.replace(old_job_status, new_job_status)
        
        # Write the updated content back to the file
        with open(API_PATH, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated API initialization in {API_PATH}")
        return True
    else:
        print("Could not find repository initialization in API file")
        return False

if __name__ == "__main__":
    print("Implementing comprehensive database connection fixes...\n")
    
    db_manager_fixed = fix_db_manager()
    repository_fixed = fix_repository()
    api_fixed = fix_api_initialization()
    
    if db_manager_fixed and repository_fixed and api_fixed:
        print("\nAll database connection fixes implemented successfully!")
    else:
        print("\nSome fixes could not be applied. See messages above for details.")
    
    print("\nPlease restart your API server with:")
    print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
