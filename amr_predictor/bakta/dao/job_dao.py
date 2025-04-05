#!/usr/bin/env python3
"""
Job DAO module for Bakta entities.

This module provides a DAO implementation for BaktaJob entities.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from amr_predictor.bakta.dao.base_dao import BaseDAO, DAOError
from amr_predictor.bakta.models import BaktaJob, BaktaJobStatusHistory
from amr_predictor.bakta.database import BaktaDatabaseError

logger = logging.getLogger("bakta-job-dao")

class JobDAO(BaseDAO[BaktaJob]):
    """
    Data Access Object for BaktaJob entities.
    
    This class provides methods for accessing BaktaJob data in the database.
    """
    
    def get_by_id(self, job_id: str) -> Optional[BaktaJob]:
        """
        Get a job by its ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            BaktaJob instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the job
        """
        try:
            job_dict = self.db_manager.get_job(job_id)
            if job_dict is None:
                return None
            
            return BaktaJob.from_dict(job_dict)
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_id for job {job_id}", e)
    
    def get_all(self, status: Optional[str] = None) -> List[BaktaJob]:
        """
        Get all jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of BaktaJob instances
            
        Raises:
            DAOError: If there is an error retrieving jobs
        """
        try:
            job_dicts = self.db_manager.get_jobs(status)
            return [BaktaJob.from_dict(job_dict) for job_dict in job_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_all jobs with status {status}", e)
    
    def save(self, job: BaktaJob) -> BaktaJob:
        """
        Save a job.
        
        Args:
            job: BaktaJob to save
            
        Returns:
            Saved BaktaJob
            
        Raises:
            DAOError: If there is an error saving the job
        """
        try:
            self.db_manager.save_job(
                job_id=job.job_id,
                job_name=job.name,
                job_secret=job.secret,
                config=job.config,
                fasta_path=job.fasta_path
            )
            
            # Set timestamps if not already set
            now = datetime.now().isoformat()
            if not job.created_at:
                job.created_at = now
            if not job.updated_at:
                job.updated_at = now
            
            return job
        except BaktaDatabaseError as e:
            self._handle_db_error(f"save job {job.job_id}", e)
    
    def update(self, job: BaktaJob) -> BaktaJob:
        """
        Update a job's status.
        
        Args:
            job: BaktaJob to update
            
        Returns:
            Updated BaktaJob
            
        Raises:
            DAOError: If there is an error updating the job
        """
        try:
            # Update job status
            self.db_manager.update_job_status(
                job_id=job.job_id,
                status=job.status,
                message=None  # No message for status update
            )
            
            # Update updated_at timestamp
            job.updated_at = datetime.now().isoformat()
            
            return job
        except BaktaDatabaseError as e:
            self._handle_db_error(f"update job {job.job_id}", e)
    
    def delete(self, job_id: str) -> bool:
        """
        Delete a job by its ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was deleted, False if job was not found
            
        Raises:
            DAOError: If there is an error deleting the job
        """
        try:
            return self.db_manager.delete_job(job_id)
        except BaktaDatabaseError as e:
            self._handle_db_error(f"delete job {job_id}", e)
    
    def get_job_status_history(self, job_id: str) -> List[BaktaJobStatusHistory]:
        """
        Get status history for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaJobStatusHistory instances
            
        Raises:
            DAOError: If there is an error retrieving the status history
        """
        try:
            history_dicts = self.db_manager.get_job_status_history(job_id)
            return [BaktaJobStatusHistory.from_dict(h_dict) for h_dict in history_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_job_status_history for job {job_id}", e)
    
    def save_job_status_history(
        self, 
        job_id: str, 
        status: str, 
        message: Optional[str] = None
    ) -> BaktaJobStatusHistory:
        """
        Save a job status history entry.
        
        Args:
            job_id: Job ID
            status: Job status
            message: Optional message about the status change
            
        Returns:
            Created BaktaJobStatusHistory instance
            
        Raises:
            DAOError: If there is an error saving the status history
        """
        try:
            now = datetime.now().isoformat()
            self.db_manager.save_job_status_history(
                job_id=job_id,
                status=status,
                timestamp=now,
                message=message
            )
            
            return BaktaJobStatusHistory(
                job_id=job_id,
                status=status,
                timestamp=now,
                message=message,
                id=None  # ID is assigned by the database
            )
        except BaktaDatabaseError as e:
            self._handle_db_error(f"save_job_status_history for job {job_id}", e)
    
    def get_jobs_by_status(self, status: str) -> List[BaktaJob]:
        """
        Get jobs by status.
        
        Args:
            status: Job status
            
        Returns:
            List of BaktaJob instances
            
        Raises:
            DAOError: If there is an error retrieving jobs
        """
        return self.get_all(status) 