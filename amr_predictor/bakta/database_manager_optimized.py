#!/usr/bin/env python3
"""
Optimized database manager with connection pooling.

This module provides an optimized version of the DatabaseManager
that uses connection pooling for better performance.
"""
import os
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

from amr_predictor.bakta.database_pool import get_connection, get_connection_pool

# Configure logging
logger = logging.getLogger("database-manager-optimized")

class OptimizedDatabaseManager:
    """
    Optimized database manager that uses connection pooling.
    
    This class extends the functionality of the original DatabaseManager
    while using connection pooling for better performance.
    """
    
    def __init__(self, db_path: Optional[str] = None, pool_min_connections: int = 2, 
                pool_max_connections: int = 5):
        """
        Initialize the optimized database manager.
        
        Args:
            db_path: Path to the SQLite database
            pool_min_connections: Minimum connections in the pool
            pool_max_connections: Maximum connections in the pool
        """
        # Determine database path
        if db_path is None:
            home = os.environ.get('HOME')
            if home is None:
                home = os.getcwd()
            db_path = os.path.join(home, '.bakta', 'bakta.db')
        
        # Store path for reference
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the connection pool
        self.pool = get_connection_pool(
            db_path=db_path,
            min_connections=pool_min_connections,
            max_connections=pool_max_connections
        )
        
        # Initialize database schema
        self._init_db()
        
        logger.info(f"Initialized optimized database manager with connection pool for {db_path}")
    
    def _init_db(self):
        """Initialize the database schema if tables don't exist"""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bakta_jobs (
                id TEXT PRIMARY KEY,
                job_name TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL,
                created_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                error TEXT,
                result_file_path TEXT
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bakta_job_params (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT,
                FOREIGN KEY (job_id) REFERENCES bakta_jobs(id) ON DELETE CASCADE
            )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bakta_jobs_status ON bakta_jobs(status)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bakta_jobs_created_at ON bakta_jobs(created_at)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bakta_job_params_job_id ON bakta_job_params(job_id)
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        with get_connection(self.db_path) as conn:
            yield conn
    
    def save_job(self, job_id: str, job_name: str, status: str = "Submitted", 
                progress: float = 0.0) -> Dict[str, Any]:
        """
        Save a new job to the database.
        
        Args:
            job_id: Unique job ID
            job_name: Name of the job
            status: Initial job status
            progress: Initial progress percentage
            
        Returns:
            Job data dictionary
        """
        job_data = {
            "id": job_id,
            "job_name": job_name,
            "status": status,
            "progress": progress,
            "created_at": datetime.now()
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO bakta_jobs (id, job_name, status, progress, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (job_id, job_name, status, progress, job_data["created_at"])
            )
            
            conn.commit()
            
        return job_data
    
    def update_job_status(self, job_id: str, status: str, progress: float,
                        error: Optional[str] = None, result_file: Optional[str] = None) -> bool:
        """
        Update a job's status and progress.
        
        Args:
            job_id: Job ID to update
            status: New job status
            progress: New progress percentage
            error: Optional error message
            result_file: Optional path to result file
            
        Returns:
            True if successful, False if job not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT id FROM bakta_jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return False
            
            # Build update query
            query = "UPDATE bakta_jobs SET status = ?, progress = ?"
            params = [status, progress]
            
            # Add optional parameters
            if error is not None:
                query += ", error = ?"
                params.append(error)
            
            if result_file is not None:
                query += ", result_file_path = ?"
                params.append(result_file)
            
            # Add completed_at if terminal status
            if status in ["Completed", "Error"]:
                query += ", completed_at = ?"
                params.append(datetime.now())
            
            # Add WHERE clause
            query += " WHERE id = ?"
            params.append(job_id)
            
            # Execute update
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM bakta_jobs WHERE id = ?",
                (job_id,)
            )
            
            row = cursor.fetchone()
            if row is None:
                return None
                
            # Convert to dict
            job_data = dict(row)
            
            # Get job parameters
            cursor.execute(
                "SELECT param_name, param_value FROM bakta_job_params WHERE job_id = ?",
                (job_id,)
            )
            
            params = {}
            for param_row in cursor.fetchall():
                params[param_row["param_name"]] = param_row["param_value"]
                
            if params:
                job_data["parameters"] = params
                
            return job_data
    
    def get_jobs(self, status: Optional[str] = None, limit: int = 100, 
                offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of jobs, optionally filtered by status.
        
        Args:
            status: Filter by job status
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of job data dictionaries
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query based on whether status filter is provided
            if status:
                query = "SELECT * FROM bakta_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params = (status, limit, offset)
            else:
                query = "SELECT * FROM bakta_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params = (limit, offset)
                
            cursor.execute(query, params)
            
            jobs = []
            for row in cursor.fetchall():
                job_data = dict(row)
                jobs.append(job_data)
                
            return jobs
    
    def add_job_parameter(self, job_id: str, param_name: str, param_value: Any) -> bool:
        """
        Add a parameter to a job.
        
        Args:
            job_id: Job ID
            param_name: Parameter name
            param_value: Parameter value (will be converted to string)
            
        Returns:
            True if successful, False if job not found
        """
        # Convert value to string
        param_value_str = str(param_value)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT id FROM bakta_jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return False
                
            # Create a unique ID for the parameter
            param_id = f"{job_id}_{param_name}"
            
            # Check if parameter already exists
            cursor.execute(
                "SELECT id FROM bakta_job_params WHERE job_id = ? AND param_name = ?",
                (job_id, param_name)
            )
            
            if cursor.fetchone() is not None:
                # Update existing parameter
                cursor.execute(
                    "UPDATE bakta_job_params SET param_value = ? WHERE job_id = ? AND param_name = ?",
                    (param_value_str, job_id, param_name)
                )
            else:
                # Insert new parameter
                cursor.execute(
                    "INSERT INTO bakta_job_params (id, job_id, param_name, param_value) VALUES (?, ?, ?, ?)",
                    (param_id, job_id, param_name, param_value_str)
                )
                
            conn.commit()
            return True
    
    def add_job_parameters(self, job_id: str, parameters: Dict[str, Any]) -> bool:
        """
        Add multiple parameters to a job.
        
        Args:
            job_id: Job ID
            parameters: Dictionary of parameter name-value pairs
            
        Returns:
            True if successful, False if job not found
        """
        if not parameters:
            return True
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT id FROM bakta_jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return False
                
            # Begin transaction
            conn.execute("BEGIN")
            
            try:
                for param_name, param_value in parameters.items():
                    # Convert value to string
                    param_value_str = str(param_value)
                    
                    # Create a unique ID for the parameter
                    param_id = f"{job_id}_{param_name}"
                    
                    # Check if parameter already exists
                    cursor.execute(
                        "SELECT id FROM bakta_job_params WHERE job_id = ? AND param_name = ?",
                        (job_id, param_name)
                    )
                    
                    if cursor.fetchone() is not None:
                        # Update existing parameter
                        cursor.execute(
                            "UPDATE bakta_job_params SET param_value = ? WHERE job_id = ? AND param_name = ?",
                            (param_value_str, job_id, param_name)
                        )
                    else:
                        # Insert new parameter
                        cursor.execute(
                            "INSERT INTO bakta_job_params (id, job_id, param_name, param_value) VALUES (?, ?, ?, ?)",
                            (param_id, job_id, param_name, param_value_str)
                        )
                        
                conn.commit()
                return True
                
            except Exception as e:
                # Rollback on error
                conn.rollback()
                logger.error(f"Error adding job parameters: {str(e)}")
                return False
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the database.
        
        Args:
            job_id: Job ID to delete
            
        Returns:
            True if successful, False if job not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Begin transaction
            conn.execute("BEGIN")
            
            try:
                # Delete job parameters (foreign key constraint will handle this,
                # but being explicit for clarity)
                cursor.execute("DELETE FROM bakta_job_params WHERE job_id = ?", (job_id,))
                
                # Delete job
                cursor.execute("DELETE FROM bakta_jobs WHERE id = ?", (job_id,))
                
                # Check if any rows were affected
                deleted = cursor.rowcount > 0
                
                conn.commit()
                return deleted
                
            except Exception as e:
                # Rollback on error
                conn.rollback()
                logger.error(f"Error deleting job: {str(e)}")
                return False
    
    def count_jobs(self, status: Optional[str] = None) -> int:
        """
        Count the number of jobs, optionally filtered by status.
        
        Args:
            status: Filter by job status
            
        Returns:
            Number of jobs
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("SELECT COUNT(*) FROM bakta_jobs WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT COUNT(*) FROM bakta_jobs")
                
            return cursor.fetchone()[0]
    
    def close(self):
        """Close all database connections in the pool"""
        self.pool.close_all()
        logger.info("Closed all database connections")
