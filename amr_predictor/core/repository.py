#!/usr/bin/env python3
"""
Repository for AMR prediction jobs.

This module provides a database repository for AMR prediction jobs.
"""
import os
import logging
import psycopg2
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from ..core.database_manager import AMRDatabaseManager

# Configure logging
logger = logging.getLogger("amr-repository")

class AMRJobRepository:
    """
    Repository for AMR prediction jobs.
    
    This class provides methods for storing and retrieving AMR prediction jobs.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the AMR job repository.
        
        Args:
            db_path: Ignored for PostgreSQL, kept for backwards compatibility
        """
        self.db_manager = AMRDatabaseManager()
        logger.info("Initialized AMR job repository")
    
    def create_job(self, job_id: str, initial_status: str = "Submitted", 
                   additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new job record.
        
        Args:
            job_id: Unique job ID
            initial_status: Initial job status
            additional_info: Additional information about the job
            
        Returns:
            The created job data
        """
        # Create job data dictionary for PostgreSQL interface
        job_data_dict = {
            'id': job_id,  # PostgreSQL uses 'id' field
            'job_id': job_id,  # For API compatibility
            'status': initial_status,
            'progress': 0.0,
            'start_time': datetime.now(),
            'additional_info': additional_info
        }
        
        # Create basic job record
        job_data = self.db_manager.save_job(job_data_dict)
        
        logger.info(f"Created AMR job: {job_id}")
        return job_data
    
    def update_job_status(self, job_id: str, status: str, progress: float = None,
                         error: Optional[str] = None, result_file: Optional[str] = None,
                         aggregated_result_file: Optional[str] = None) -> bool:
        """
        Update a job's status.
        
        Args:
            job_id: Job ID to update
            status: New job status
            progress: New progress percentage
            error: Error message (if applicable)
            result_file: Path to result file (if available)
            aggregated_result_file: Path to aggregated result file (if available)
            
        Returns:
            True if successful, False if job not found
        """
        result = self.db_manager.update_job_status(
            job_id=job_id,
            status=status,
            progress=progress,
            error=error,
            result_file=result_file,
            aggregated_result_file=aggregated_result_file
        )
        
        if result:
            logger.info(f"Updated AMR job status: {job_id} -> {status}")
            if error:
                logger.error(f"Job {job_id} error: {error}")
        else:
            logger.warning(f"Failed to update job status for non-existent job: {job_id}")
            
        return result
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by ID.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            Job data or None if not found
        """
        try:
            job_data = self.db_manager.get_job(job_id)
            
            if job_data is None:
                logger.warning(f"Job not found: {job_id}")
                return None
            
            # Convert datetime objects to strings for API compatibility
            if 'start_time' in job_data and isinstance(job_data['start_time'], datetime):
                job_data['start_time'] = job_data['start_time'].isoformat()
                
            if 'end_time' in job_data and job_data['end_time'] and isinstance(job_data['end_time'], datetime):
                job_data['end_time'] = job_data['end_time'].isoformat()
                
            return job_data
        except psycopg2.Error as e:
            if "connection" in str(e).lower():
                logger.warning(f"Reconnecting to database for job {job_id}")
                # Create a fresh connection
                from ..core.database_manager import AMRDatabaseManager
                fresh_db = AMRDatabaseManager()
                return fresh_db.get_job(job_id)
            else:
                # Re-raise if it's a different error
                raise
    
    def get_jobs(self, status: Optional[str] = None, limit: int = 100,
                offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of jobs.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Pagination offset
            
        Returns:
            List of job data dictionaries
        """
        jobs = self.db_manager.get_jobs(status=status, limit=limit, offset=offset)
        
        # Convert datetime objects to strings for API compatibility
        for job in jobs:
            if 'start_time' in job and isinstance(job['start_time'], datetime):
                job['start_time'] = job['start_time'].isoformat()
                
            if 'end_time' in job and job['end_time'] and isinstance(job['end_time'], datetime):
                job['end_time'] = job['end_time'].isoformat()
                
        return jobs
    
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
        return self.db_manager.add_job_parameter(job_id, param_name, param_value)
    
    def add_job_parameters(self, job_id: str, parameters: Dict[str, Any]) -> bool:
        """
        Add multiple parameters to a job.
        
        Args:
            job_id: Job ID
            parameters: Dictionary of parameters
            
        Returns:
            True if successful, False if job not found
        """
        return self.db_manager.add_job_parameters(job_id, parameters)
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job ID to delete
            
        Returns:
            True if successful, False if job not found
        """
        result = self.db_manager.delete_job(job_id)
        
        if result:
            logger.info(f"Deleted AMR job: {job_id}")
        else:
            logger.warning(f"Failed to delete non-existent job: {job_id}")
            
        return result
    
    def close(self):
        """Close the database manager."""
        self.db_manager.close()
