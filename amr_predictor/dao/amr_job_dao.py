#!/usr/bin/env python3
"""
Data Access Object for AMR jobs.

This module provides a DAO for managing AMR jobs in the database.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError
from amr_predictor.models.amr_job import AMRJob, AMRJobParams
from amr_predictor.bakta.database_extensions import extend_database_manager

# Configure logging
logger = logging.getLogger("amr-job-dao")

class AMRJobDAO:
    """
    Data Access Object for AMR jobs.
    
    This class provides methods for managing AMR jobs in the database.
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        Initialize the DAO.
        
        Args:
            db_manager: DatabaseManager instance (will create one if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        # Ensure the database manager has AMR methods
        extend_database_manager(self.db_manager)
    
    def _handle_db_error(self, operation: str, error: Exception) -> None:
        """Handle database errors"""
        error_msg = f"Database error during {operation}: {str(error)}"
        logger.error(error_msg)
        # Reraise for critical operations, log for less critical ones
        if isinstance(error, BaktaDatabaseError):
            raise error
    
    def save(self, job: AMRJob) -> AMRJob:
        """
        Save a new AMR job to the database.
        
        Args:
            job: The job to save
            
        Returns:
            The saved job
            
        Raises:
            BaktaDatabaseError: If the job could not be saved
        """
        try:
            return self.db_manager.save_amr_job(job)
        except Exception as e:
            self._handle_db_error("save", e)
            raise
    
    def update(self, job: AMRJob) -> AMRJob:
        """
        Update an existing AMR job.
        
        Args:
            job: The job to update
            
        Returns:
            The updated job
            
        Raises:
            BaktaDatabaseError: If the job could not be updated
        """
        try:
            return self.db_manager.update_amr_job(job)
        except Exception as e:
            self._handle_db_error("update", e)
            raise
    
    def update_status(self, id: str, status: str, progress: Optional[float] = None,
                    error: Optional[str] = None, completed_at: Optional[datetime] = None) -> bool:
        """
        Update the status of a job.
        
        Args:
            id: The job ID
            status: The new status
            progress: Optional progress percentage
            error: Optional error message
            completed_at: Optional completion timestamp
            
        Returns:
            True if successful
        """
        try:
            return self.db_manager.update_amr_job_status(id, status, progress, error, completed_at)
        except Exception as e:
            self._handle_db_error("update_status", e)
            return False
    
    def get_by_id(self, id: str) -> Optional[AMRJob]:
        """
        Get a job by ID.
        
        Args:
            id: The job ID
            
        Returns:
            The job or None if not found
        """
        try:
            return self.db_manager.get_amr_job(id)
        except Exception as e:
            self._handle_db_error("get_by_id", e)
            return None
    
    def get_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[AMRJob]:
        """
        Get jobs for a user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of jobs
        """
        try:
            return self.db_manager.get_amr_jobs_by_user(user_id, limit, offset)
        except Exception as e:
            self._handle_db_error("get_by_user", e)
            return []
    
    def get_all(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[AMRJob]:
        """
        Get all jobs with optional status filtering.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Pagination offset
            status: Optional status filter
            
        Returns:
            List of jobs
        """
        try:
            return self.db_manager.get_all_amr_jobs(limit, offset, status)
        except Exception as e:
            self._handle_db_error("get_all", e)
            return []
    
    def delete(self, id: str) -> bool:
        """
        Delete a job by ID.
        
        Args:
            id: The job ID
            
        Returns:
            True if successful, False if job not found
        """
        try:
            return self.db_manager.delete_amr_job(id)
        except Exception as e:
            self._handle_db_error("delete", e)
            return False
    
    def save_params(self, job_id: str, params: AMRJobParams) -> bool:
        """
        Save or update job parameters.
        
        Args:
            job_id: The job ID
            params: The parameters to save
            
        Returns:
            True if successful
        """
        try:
            return self.db_manager.save_amr_job_params(job_id, params)
        except Exception as e:
            self._handle_db_error("save_params", e)
            return False
    
    def get_params(self, job_id: str) -> Optional[AMRJobParams]:
        """
        Get job parameters.
        
        Args:
            job_id: The job ID
            
        Returns:
            The parameters or None if not found
        """
        try:
            return self.db_manager.get_amr_job_params(job_id)
        except Exception as e:
            self._handle_db_error("get_params", e)
            return None
