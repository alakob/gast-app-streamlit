"""
Database manager for AMR Predictor.

This module provides database management for the AMR Predictor,
handling database connections and database operations.
"""
import os
import sys
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import threading
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment (dev, test, or prod)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

class AMRDatabaseManager:
    """
    Database manager for AMR Predictor.
    
    This class manages database connections and operations for the AMR Predictor,
    using PostgreSQL with connection pooling for improved reliability and performance.
    """
    
    _instance = None
    _pool = None
    _pool_lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern for the database manager."""
        if cls._instance is None:
            cls._instance = super(AMRDatabaseManager, cls).__new__(cls)
            cls._initialize_pool()
        return cls._instance
    
    @classmethod
    def _initialize_pool(cls):
        """Initialize the connection pool."""
        if cls._pool is None:
            with cls._pool_lock:
                if cls._pool is None:
                    try:
                        # Get PostgreSQL connection parameters
                        pg_host = os.getenv('PG_HOST', 'localhost')
                        pg_port = os.getenv('PG_PORT', '5432')
                        pg_user = os.getenv('PG_USER', 'postgres')
                        pg_password = os.getenv('PG_PASSWORD', '')
                        
                        # Get database name based on environment
                        if ENVIRONMENT == 'dev':
                            database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
                        elif ENVIRONMENT == 'test':
                            database = os.getenv('PG_DATABASE_TEST', 'amr_predictor_test')
                        elif ENVIRONMENT == 'prod':
                            database = os.getenv('PG_DATABASE_PROD', 'amr_predictor_prod')
                        else:
                            logger.warning(f"Unknown environment: {ENVIRONMENT}, defaulting to dev")
                            database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
                        
                        logger.info(f"Initializing database connection pool for {ENVIRONMENT} environment: {database}")
                        
                        # Create the connection pool (min=2, max=20 connections)
                        cls._pool = pool.ThreadedConnectionPool(
                            minconn=2,
                            maxconn=20,
                            host=pg_host,
                            port=pg_port,
                            user=pg_user,
                            password=pg_password,
                            database=database
                        )
                        
                        logger.info("Database connection pool initialized successfully")
                    except Exception as e:
                        logger.error(f"Error initializing database connection pool: {str(e)}")
                        raise
    
    def __init__(self):
        """Initialize the database manager."""
        # Ensure the pool is initialized
        if self.__class__._pool is None:
            self.__class__._initialize_pool()
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            A database connection from the pool
        """
        try:
            conn = self.__class__._pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {str(e)}")
            raise
    
    def release_connection(self, conn):
        """
        Release a connection back to the pool.
        
        Args:
            conn: The connection to release
        """
        try:
            self.__class__._pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error releasing connection to pool: {str(e)}")
    
    def ensure_tables_exist(self):
        """Ensure that the required database tables exist."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create amr_jobs table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS amr_jobs (
                id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50) NOT NULL,
                progress FLOAT DEFAULT 0,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                result_file VARCHAR(255),
                aggregated_result_file VARCHAR(255),
                error TEXT,
                additional_info JSONB
            )
            """)
            
            # Create amr_job_parameters table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS amr_job_parameters (
                id SERIAL PRIMARY KEY,
                job_id VARCHAR(255) REFERENCES amr_jobs(id) ON DELETE CASCADE,
                param_name VARCHAR(255) NOT NULL,
                param_value TEXT,
                UNIQUE(job_id, param_name)
            )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON amr_jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_parameters ON amr_job_parameters(job_id)")
            
            conn.commit()
            logger.info("Database tables verified/created successfully")
        except Exception as e:
            logger.error(f"Error ensuring tables exist: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.release_connection(conn)
    
    def save_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Save a job to the database.
        
        Args:
            job_data: Job data dictionary with all field values
            
        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            # Get required fields
            job_id = job_data.get('job_id')
            if not job_id:
                logger.error("Missing job_id in job data")
                return False
            
            # Get a connection from the pool
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Extract core job fields from job_data
            status = job_data.get('status', 'Pending')
            progress = job_data.get('progress', 0.0)
            start_time = job_data.get('start_time')
            end_time = job_data.get('end_time')
            result_file = job_data.get('result_file')
            aggregated_result_file = job_data.get('aggregated_result_file')
            error = job_data.get('error')
            
            # Handle additional_info (convert to JSON)
            additional_info = {}
            for key, value in job_data.items():
                # Skip core job fields that are stored in specific columns
                if key not in ['job_id', 'id', 'status', 'progress', 'start_time', 'end_time', 
                              'result_file', 'aggregated_result_file', 'error']:
                    additional_info[key] = value
            
            # Check if job already exists
            cursor.execute("SELECT 1 FROM amr_jobs WHERE id = %s", (job_id,))
            job_exists = cursor.fetchone() is not None
            
            if job_exists:
                # Update existing job
                cursor.execute("""
                UPDATE amr_jobs 
                SET status = %s, progress = %s, start_time = %s, end_time = %s,
                    result_file = %s, aggregated_result_file = %s, error = %s, additional_info = %s
                WHERE id = %s
                """, (
                    status, progress, start_time, end_time, 
                    result_file, aggregated_result_file, error, 
                    json.dumps(additional_info), job_id
                ))
            else:
                # Insert new job
                cursor.execute("""
                INSERT INTO amr_jobs (id, status, progress, start_time, end_time, 
                                    result_file, aggregated_result_file, error, additional_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    job_id, status, progress, start_time, end_time,
                    result_file, aggregated_result_file, error,
                    json.dumps(additional_info)
                ))
            
            # Save job parameters (excluding fields already stored in amr_jobs)
            for key, value in job_data.items():
                # Skip core job fields and null values
                if key not in ['job_id', 'id', 'status', 'progress', 'start_time', 'end_time', 
                              'result_file', 'aggregated_result_file', 'error', 'additional_info'] and value is not None:
                    # Check if parameter already exists
                    cursor.execute("""
                    SELECT 1 FROM amr_job_parameters 
                    WHERE job_id = %s AND param_name = %s
                    """, (job_id, key))
                    param_exists = cursor.fetchone() is not None
                    
                    if param_exists:
                        # Update existing parameter
                        cursor.execute("""
                        UPDATE amr_job_parameters 
                        SET param_value = %s
                        WHERE job_id = %s AND param_name = %s
                        """, (str(value), job_id, key))
                    else:
                        # Insert new parameter
                        cursor.execute("""
                        INSERT INTO amr_job_parameters (job_id, param_name, param_value)
                        VALUES (%s, %s, %s)
                        """, (job_id, key, str(value)))
            
            # Commit the transaction
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving job {job_data.get('job_id')}: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def update_job_status(self, job_id: str, status: str, progress: float = None, 
                         error: str = None, result_file: str = None,
                         aggregated_result_file: str = None) -> bool:
        """
        Update the status of a job.
        
        Args:
            job_id: Job ID to update
            status: New status value
            progress: Progress percentage (0-100)
            error: Error message if any
            result_file: Path to result file if available
            aggregated_result_file: Path to aggregated result file if available
            
        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build update query dynamically based on provided parameters
            update_fields = ["status = %s"]
            params = [status]
            
            if progress is not None:
                update_fields.append("progress = %s")
                params.append(progress)
            
            if status == "Completed" or status == "Error":
                update_fields.append("end_time = %s")
                params.append(datetime.now())
            
            if error is not None:
                update_fields.append("error = %s")
                params.append(error)
            
            if result_file is not None:
                update_fields.append("result_file = %s")
                params.append(result_file)
                
            if aggregated_result_file is not None:
                update_fields.append("aggregated_result_file = %s")
                params.append(aggregated_result_file)
            
            # Add job_id to parameters list
            params.append(job_id)
            
            # Execute the update
            query = f"UPDATE amr_jobs SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, params)
            
            # Commit the transaction
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data dictionary or None if not found
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            
            # Use RealDictCursor to get results as dictionaries
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get job data
            cursor.execute("""
            SELECT * FROM amr_jobs WHERE id = %s
            """, (job_id,))
            
            job_row = cursor.fetchone()
            if not job_row:
                return None
                
            # Convert to regular Python dict
            job_data = dict(job_row)
            
            # Get job parameters
            cursor.execute("""
            SELECT param_name, param_value FROM amr_job_parameters WHERE job_id = %s
            """, (job_id,))
            
            # Add parameters to job data
            for row in cursor.fetchall():
                job_data[row["param_name"]] = row["param_value"]
            
            # Parse additional_info from JSON if needed
            if job_data.get('additional_info'):
                if isinstance(job_data['additional_info'], str):
                    try:
                        job_data['additional_info'] = json.loads(job_data['additional_info'])
                    except:
                        pass
            
            # Map 'id' to 'job_id' for API compatibility
            if 'id' in job_data and 'job_id' not in job_data:
                job_data['job_id'] = job_data['id']
            
            return job_data
        except Exception as e:
            logger.error(f"Error retrieving job {job_id}: {str(e)}")
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_jobs(self, limit: int = 100, offset: int = 0, status: str = None) -> List[Dict[str, Any]]:
        """
        Get a list of jobs with optional filtering by status.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Offset for pagination
            status: Filter jobs by status
            
        Returns:
            List of job data dictionaries
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            
            # Use RealDictCursor to get results as dictionaries
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query based on filters
            query = "SELECT * FROM amr_jobs"
            params = []
            
            if status:
                query += " WHERE status = %s"
                params.append(status)
            
            # Add ordering and pagination
            query += " ORDER BY start_time DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            # Execute query
            cursor.execute(query, params)
            
            # Fetch and process results
            jobs = []
            for row in cursor.fetchall():
                job_data = dict(row)
                
                # Parse additional_info from JSON if needed
                if job_data.get('additional_info'):
                    if isinstance(job_data['additional_info'], str):
                        try:
                            job_data['additional_info'] = json.loads(job_data['additional_info'])
                        except:
                            pass
                
                # Map 'id' to 'job_id' for API compatibility
                if 'id' in job_data and 'job_id' not in job_data:
                    job_data['job_id'] = job_data['id']
                
                jobs.append(job_data)
            
            return jobs
        except Exception as e:
            logger.error(f"Error retrieving jobs: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def add_job_parameter(self, job_id: str, param_name: str, param_value: Any) -> bool:
        """
        Add a parameter to a job.
        
        Args:
            job_id: Job ID
            param_name: Parameter name
            param_value: Parameter value
            
        Returns:
            True if successful, False if job not found
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert any non-string values to JSON strings
            if not isinstance(param_value, str):
                param_value = json.dumps(param_value)
            
            # Check if job exists
            cursor.execute("SELECT 1 FROM amr_jobs WHERE id = %s", (job_id,))
            if cursor.fetchone() is None:
                logger.warning(f"Cannot add parameter to non-existent job: {job_id}")
                return False
            
            # Insert or update parameter
            cursor.execute("""
            INSERT INTO amr_job_parameters (job_id, param_name, param_value)
            VALUES (%s, %s, %s)
            ON CONFLICT (job_id, param_name) DO UPDATE SET param_value = EXCLUDED.param_value
            """, (job_id, param_name, param_value))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding job parameter: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def add_job_parameters(self, job_id: str, parameters: Dict[str, Any]) -> bool:
        """
        Add multiple parameters to a job.
        
        Args:
            job_id: Job ID
            parameters: Dictionary of parameters
            
        Returns:
            True if successful, False if job not found
        """
        conn = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT 1 FROM amr_jobs WHERE id = %s", (job_id,))
            if cursor.fetchone() is None:
                logger.warning(f"Cannot add parameters to non-existent job: {job_id}")
                return False
            
            # Add each parameter
            for param_name, param_value in parameters.items():
                # Convert any non-string values to JSON strings
                if not isinstance(param_value, str):
                    param_value = json.dumps(param_value)
                
                cursor.execute("""
                INSERT INTO amr_job_parameters (job_id, param_name, param_value)
                VALUES (%s, %s, %s)
                ON CONFLICT (job_id, param_name) DO UPDATE SET param_value = EXCLUDED.param_value
                """, (job_id, param_name, param_value))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding job parameters: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def close(self):
        """Close the database connection pool."""
        if self.__class__._pool is not None:
            with self.__class__._pool_lock:
                if self.__class__._pool is not None:
                    self.__class__._pool.closeall()
                    self.__class__._pool = None
                    logger.info("Database connection pool closed")

# Create and initialize the database manager
db_manager = AMRDatabaseManager()

# Ensure tables exist on startup
try:
    db_manager.ensure_tables_exist()
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
