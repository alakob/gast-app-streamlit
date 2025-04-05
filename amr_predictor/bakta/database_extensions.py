#!/usr/bin/env python3
"""
Extensions to the DatabaseManager for AMR-specific functionality.

This module extends the Bakta DatabaseManager with methods for handling AMR prediction jobs.
"""
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError
from amr_predictor.models.amr_job import AMRJob, AMRJobParams

logger = logging.getLogger("amr-database")

class AMRDatabaseExtensions:
    """
    Extensions to the DatabaseManager for AMR jobs.
    
    This class adds AMR-specific methods to the DatabaseManager,
    allowing for handling AMR prediction jobs without modifying
    the original Bakta code.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize with a DatabaseManager instance.
        
        Args:
            db_manager: The DatabaseManager to extend
        """
        self.db_manager = db_manager
        
        # Ensure AMR tables exist
        self._create_amr_tables()
    
    def _create_amr_tables(self):
        """Create AMR-specific tables if they don't exist"""
        try:
            # Use the connection context manager properly with 'with' statement
            with self.db_manager._get_connection() as conn:
                # Create AMR jobs table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS amr_jobs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        job_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress REAL DEFAULT 0.0,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        error TEXT,
                        input_file_path TEXT,
                        result_file_path TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    )
                """)
                
                # Create AMR job parameters table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS amr_job_params (
                        job_id TEXT PRIMARY KEY,
                        model_name TEXT NOT NULL,
                        batch_size INTEGER NOT NULL,
                        segment_length INTEGER NOT NULL,
                        segment_overlap INTEGER NOT NULL,
                        use_cpu INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (job_id) REFERENCES amr_jobs(id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_amr_jobs_user_id ON amr_jobs(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_amr_jobs_status ON amr_jobs(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_amr_jobs_created_at ON amr_jobs(created_at)")
                
                # Commit is handled by the context manager, but we'll be explicit
                conn.commit()
            
            logger.info("AMR tables created or verified")
            
        except sqlite3.Error as e:
            error_msg = f"Failed to create AMR tables: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_amr_job(self, job: AMRJob) -> AMRJob:
        """
        Save an AMR job to the database.
        
        Args:
            job: The AMR job to save
            
        Returns:
            The saved job
            
        Raises:
            BaktaDatabaseError: If the job could not be saved
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Insert job
            conn.execute(
                """
                INSERT INTO amr_jobs 
                (id, user_id, job_name, status, progress, created_at, 
                 started_at, completed_at, error, input_file_path, result_file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.user_id,
                    job.job_name,
                    job.status,
                    job.progress,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error,
                    job.input_file_path,
                    job.result_file_path
                )
            )
            
            # Save parameters if provided
            if job.params:
                self.save_amr_job_params(job.id, job.params)
                
            conn.commit()
            logger.debug(f"Saved AMR job {job.id}")
            
            return job
            
        except sqlite3.Error as e:
            error_msg = f"Failed to save AMR job {job.id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def update_amr_job(self, job: AMRJob) -> AMRJob:
        """
        Update an existing AMR job.
        
        Args:
            job: The AMR job to update
            
        Returns:
            The updated job
            
        Raises:
            BaktaDatabaseError: If the job could not be updated
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Update job
            conn.execute(
                """
                UPDATE amr_jobs SET
                user_id = ?,
                job_name = ?,
                status = ?,
                progress = ?,
                started_at = ?,
                completed_at = ?,
                error = ?,
                input_file_path = ?,
                result_file_path = ?
                WHERE id = ?
                """,
                (
                    job.user_id,
                    job.job_name,
                    job.status,
                    job.progress,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error,
                    job.input_file_path,
                    job.result_file_path,
                    job.id
                )
            )
            
            # Update parameters if provided
            if job.params:
                self.save_amr_job_params(job.id, job.params)
                
            conn.commit()
            logger.debug(f"Updated AMR job {job.id}")
            
            return job
            
        except sqlite3.Error as e:
            error_msg = f"Failed to update AMR job {job.id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def update_amr_job_status(self, job_id: str, status: str, progress: Optional[float] = None,
                             error: Optional[str] = None, completed_at: Optional[datetime] = None) -> bool:
        """
        Update an AMR job's status.
        
        Args:
            job_id: The job ID
            status: The new status
            progress: Optional progress update (0-100)
            error: Optional error message
            completed_at: Optional completion timestamp
            
        Returns:
            True if successful
            
        Raises:
            BaktaDatabaseError: If the status could not be updated
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Build update query dynamically based on provided parameters
            update_parts = ["status = ?"]
            params = [status]
            
            if progress is not None:
                update_parts.append("progress = ?")
                params.append(progress)
                
            if error is not None:
                update_parts.append("error = ?")
                params.append(error)
                
            if completed_at is not None:
                update_parts.append("completed_at = ?")
                params.append(completed_at.isoformat())
                
            # Add job_id as the last parameter
            params.append(job_id)
            
            # Execute update
            conn.execute(
                f"""
                UPDATE amr_jobs SET {', '.join(update_parts)} WHERE id = ?
                """,
                tuple(params)
            )
                
            conn.commit()
            logger.debug(f"Updated AMR job {job_id} status to {status}")
            
            return True
            
        except sqlite3.Error as e:
            error_msg = f"Failed to update AMR job status for {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_amr_job(self, job_id: str) -> Optional[AMRJob]:
        """
        Get an AMR job by ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            The job or None if not found
            
        Raises:
            BaktaDatabaseError: If there was an error retrieving the job
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Get job
            cursor = conn.execute(
                """
                SELECT * FROM amr_jobs WHERE id = ?
                """,
                (job_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            job_dict = dict(row)
            job = AMRJob.from_db_row(job_dict)
            
            # Get parameters
            cursor = conn.execute(
                """
                SELECT * FROM amr_job_params WHERE job_id = ?
                """,
                (job_id,)
            )
            
            params_row = cursor.fetchone()
            if params_row:
                params_dict = dict(params_row)
                job.params = AMRJobParams.from_db_row(params_dict)
                
            return job
            
        except sqlite3.Error as e:
            error_msg = f"Failed to get AMR job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_amr_jobs_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[AMRJob]:
        """
        Get AMR jobs for a user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of jobs to return
            offset: Query offset for pagination
            
        Returns:
            List of jobs
            
        Raises:
            BaktaDatabaseError: If there was an error retrieving the jobs
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Get jobs
            cursor = conn.execute(
                """
                SELECT * FROM amr_jobs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset)
            )
            
            jobs = []
            for row in cursor.fetchall():
                job_dict = dict(row)
                job = AMRJob.from_db_row(job_dict)
                jobs.append(job)
                
            # Get parameters for each job
            for job in jobs:
                cursor = conn.execute(
                    """
                    SELECT * FROM amr_job_params WHERE job_id = ?
                    """,
                    (job.id,)
                )
                
                params_row = cursor.fetchone()
                if params_row:
                    params_dict = dict(params_row)
                    job.params = AMRJobParams.from_db_row(params_dict)
                    
            return jobs
            
        except sqlite3.Error as e:
            error_msg = f"Failed to get AMR jobs for user {user_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_all_amr_jobs(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[AMRJob]:
        """
        Get all AMR jobs with optional filtering.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Query offset for pagination
            status: Optional status filter
            
        Returns:
            List of jobs
            
        Raises:
            BaktaDatabaseError: If there was an error retrieving the jobs
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Build query based on whether status filter is provided
            if status:
                query = """
                    SELECT * FROM amr_jobs 
                    WHERE status = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """
                params = (status, limit, offset)
            else:
                query = """
                    SELECT * FROM amr_jobs 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """
                params = (limit, offset)
                
            # Get jobs
            cursor = conn.execute(query, params)
            
            jobs = []
            for row in cursor.fetchall():
                job_dict = dict(row)
                job = AMRJob.from_db_row(job_dict)
                jobs.append(job)
                
            # Get parameters for each job
            for job in jobs:
                cursor = conn.execute(
                    """
                    SELECT * FROM amr_job_params WHERE job_id = ?
                    """,
                    (job.id,)
                )
                
                params_row = cursor.fetchone()
                if params_row:
                    params_dict = dict(params_row)
                    job.params = AMRJobParams.from_db_row(params_dict)
                    
            return jobs
            
        except sqlite3.Error as e:
            error_msg = f"Failed to get AMR jobs: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_amr_job_params(self, job_id: str, params: AMRJobParams) -> bool:
        """
        Save or update parameters for an AMR job.
        
        Args:
            job_id: The job ID
            params: The parameters to save
            
        Returns:
            True if successful
            
        Raises:
            BaktaDatabaseError: If the parameters could not be saved
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Check if parameters exist
            cursor = conn.execute(
                """
                SELECT 1 FROM amr_job_params WHERE job_id = ?
                """,
                (job_id,)
            )
            
            if cursor.fetchone():
                # Update existing parameters
                conn.execute(
                    """
                    UPDATE amr_job_params SET
                    model_name = ?,
                    batch_size = ?,
                    segment_length = ?,
                    segment_overlap = ?,
                    use_cpu = ?
                    WHERE job_id = ?
                    """,
                    (
                        params.model_name,
                        params.batch_size,
                        params.segment_length,
                        params.segment_overlap,
                        1 if params.use_cpu else 0,
                        job_id
                    )
                )
            else:
                # Insert new parameters
                conn.execute(
                    """
                    INSERT INTO amr_job_params
                    (job_id, model_name, batch_size, segment_length, segment_overlap, use_cpu)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        params.model_name,
                        params.batch_size,
                        params.segment_length,
                        params.segment_overlap,
                        1 if params.use_cpu else 0
                    )
                )
                
            conn.commit()
            logger.debug(f"Saved parameters for AMR job {job_id}")
            
            return True
            
        except sqlite3.Error as e:
            error_msg = f"Failed to save parameters for AMR job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_amr_job_params(self, job_id: str) -> Optional[AMRJobParams]:
        """
        Get parameters for an AMR job.
        
        Args:
            job_id: The job ID
            
        Returns:
            The parameters or None if not found
            
        Raises:
            BaktaDatabaseError: If there was an error retrieving the parameters
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Get parameters
            cursor = conn.execute(
                """
                SELECT * FROM amr_job_params WHERE job_id = ?
                """,
                (job_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            params_dict = dict(row)
            return AMRJobParams.from_db_row(params_dict)
            
        except sqlite3.Error as e:
            error_msg = f"Failed to get parameters for AMR job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def delete_amr_job(self, job_id: str) -> bool:
        """
        Delete an AMR job and its parameters.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if job was deleted, False if job was not found
            
        Raises:
            BaktaDatabaseError: If the job could not be deleted
        """
        try:
            conn = self.db_manager._get_connection()
            
            # Delete job (parameters will be deleted via CASCADE)
            cursor = conn.execute(
                """
                DELETE FROM amr_jobs WHERE id = ?
                """,
                (job_id,)
            )
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.debug(f"Deleted AMR job {job_id}")
            
            return deleted
            
        except sqlite3.Error as e:
            error_msg = f"Failed to delete AMR job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)

# Monkey patch the DatabaseManager to add AMR methods
def extend_database_manager(db_manager: DatabaseManager):
    """
    Extend a DatabaseManager instance with AMR methods.
    
    Args:
        db_manager: The DatabaseManager to extend
    """
    extensions = AMRDatabaseExtensions(db_manager)
    
    # Add AMR methods to the DatabaseManager
    db_manager.save_amr_job = extensions.save_amr_job
    db_manager.update_amr_job = extensions.update_amr_job
    db_manager.update_amr_job_status = extensions.update_amr_job_status
    db_manager.get_amr_job = extensions.get_amr_job
    db_manager.get_amr_jobs_by_user = extensions.get_amr_jobs_by_user
    db_manager.get_all_amr_jobs = extensions.get_all_amr_jobs
    db_manager.save_amr_job_params = extensions.save_amr_job_params
    db_manager.get_amr_job_params = extensions.get_amr_job_params
    db_manager.delete_amr_job = extensions.delete_amr_job
    
    # Create tables
    extensions._create_amr_tables()
    
    return db_manager
