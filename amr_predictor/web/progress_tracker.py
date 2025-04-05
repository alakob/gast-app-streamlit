#!/usr/bin/env python3
"""
Progress tracking for AMR jobs with database updates.

This module provides progress trackers that update job status in both
the in-memory dictionary and the database for a smooth transition.
"""
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob, AMRJobParams

class DatabaseProgressTracker:
    """
    Progress tracker that updates job status in the database.
    """
    
    def __init__(self, job_id: str, db_manager: DatabaseManager = None):
        """
        Initialize the database progress tracker.
        
        Args:
            job_id: The job ID to update
            db_manager: Database manager instance (will create one if None)
        """
        self.job_id = job_id
        self.db_manager = db_manager or DatabaseManager()
        self.job_dao = AMRJobDAO(self.db_manager)
        
        # Track internal state
        self.percentage = 0.0
        self.status = "Submitted"
        self.additional_info = {}
        self.error = None
    
    def update(self, percentage: float, status: str = None, additional_info: Dict[str, Any] = None, 
              error: str = None):
        """
        Update the job status.
        
        Args:
            percentage: Progress percentage (0-100)
            status: Optional new status
            additional_info: Optional additional information
            error: Optional error message
        """
        # Update internal state
        self.percentage = percentage
        if status:
            self.status = status
        if additional_info:
            if self.additional_info:
                self.additional_info.update(additional_info)
            else:
                self.additional_info = additional_info
        if error:
            self.error = error
            self.status = "Error"
        
        # Update in database
        completed_at = None
        if self.status in ["Completed", "Error"]:
            completed_at = datetime.now()
            
        self.job_dao.update_status(
            self.job_id,
            status=self.status,
            progress=self.percentage,
            error=self.error,
            completed_at=completed_at
        )

class LegacyCompatibleProgressTracker:
    """
    Progress tracker that updates both in-memory jobs dictionary and database.
    This provides backward compatibility during transition.
    """
    
    def __init__(self, job_id: str, jobs_dict: Dict[str, Any], db_manager: DatabaseManager = None):
        """
        Initialize the legacy-compatible progress tracker.
        
        Args:
            job_id: The job ID to update
            jobs_dict: The legacy in-memory jobs dictionary
            db_manager: Database manager instance (will create one if None)
        """
        self.job_id = job_id
        self.jobs_dict = jobs_dict
        self.db_manager = db_manager or DatabaseManager()
        self.job_dao = AMRJobDAO(self.db_manager)
        
        # Track internal state
        self.percentage = 0.0
        self.status = "Submitted"
        self.additional_info = {}
        self.error = None
    
    def update(self, percentage: float, status: str = None, additional_info: Dict[str, Any] = None, 
              error: str = None):
        """
        Update the job status in both in-memory dictionary and database.
        
        Args:
            percentage: Progress percentage (0-100)
            status: Optional new status
            additional_info: Optional additional information
            error: Optional error message
        """
        # Update internal state
        self.percentage = percentage
        if status:
            self.status = status
        if additional_info:
            if self.additional_info:
                self.additional_info.update(additional_info)
            else:
                self.additional_info = additional_info
        if error:
            self.error = error
            self.status = "Error"
        
        # Update in-memory status (legacy)
        if self.job_id in self.jobs_dict:
            self.jobs_dict[self.job_id].update({
                "progress": self.percentage,
                "status": self.status
            })
            
            if self.additional_info:
                if "additional_info" not in self.jobs_dict[self.job_id]:
                    self.jobs_dict[self.job_id]["additional_info"] = {}
                self.jobs_dict[self.job_id]["additional_info"].update(self.additional_info)
            
            if self.error:
                self.jobs_dict[self.job_id]["error"] = self.error
                self.jobs_dict[self.job_id]["status"] = "Error"
                self.jobs_dict[self.job_id]["end_time"] = datetime.now().isoformat()
                
            elif self.status == "Completed":
                self.jobs_dict[self.job_id]["status"] = "Completed"
                self.jobs_dict[self.job_id]["progress"] = 100.0
                self.jobs_dict[self.job_id]["end_time"] = datetime.now().isoformat()
        
        # Update database (new)
        completed_at = None
        if self.status in ["Completed", "Error"]:
            completed_at = datetime.now()
            
        self.job_dao.update_status(
            self.job_id,
            status=self.status,
            progress=self.percentage,
            error=self.error,
            completed_at=completed_at
        )
