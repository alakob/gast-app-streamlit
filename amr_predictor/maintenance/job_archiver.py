#!/usr/bin/env python3
"""
Job archiver and cleanup utility.

This module handles archiving and cleaning up AMR jobs
based on configurable lifecycle policies.
"""
import os
import time
import shutil
import zipfile
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob
from amr_predictor.config.job_lifecycle_config import JobLifecycleConfig

# Configure logging
logger = logging.getLogger("job-archiver")

class JobArchiver:
    """
    Manages job archiving and cleanup based on configured policies.
    """
    
    def __init__(self, config: JobLifecycleConfig = None, db_manager: DatabaseManager = None,
                archive_dir: str = "archive"):
        """
        Initialize the job archiver.
        
        Args:
            config: Job lifecycle configuration
            db_manager: Database manager instance
            archive_dir: Directory for archived job files
        """
        self.config = config or JobLifecycleConfig()
        self.db_manager = db_manager or DatabaseManager()
        self.job_dao = AMRJobDAO(self.db_manager)
        
        # Create archive directory if not exists
        self.archive_dir = Path(archive_dir)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def find_jobs_for_archiving(self) -> List[AMRJob]:
        """
        Find jobs eligible for archiving based on configuration.
        
        Returns:
            List of jobs eligible for archiving
        """
        # Calculate cutoff date
        min_age_days = self.config.get_min_age_for_archiving()
        cutoff_date = datetime.now() - timedelta(days=min_age_days)
        
        # Find completed jobs older than cutoff date
        eligible_jobs = []
        all_jobs = self.job_dao.get_all(limit=1000, status="Completed")  # Get completed jobs
        
        for job in all_jobs:
            # Check if old enough
            if job.completed_at and job.completed_at < cutoff_date:
                eligible_jobs.append(job)
                
        logger.info(f"Found {len(eligible_jobs)} jobs eligible for archiving")
        return eligible_jobs
    
    def archive_job(self, job: AMRJob) -> bool:
        """
        Archive a single job.
        
        Args:
            job: Job to archive
            
        Returns:
            True if successfully archived
        """
        try:
            # 1. Create archive directory for this job
            job_archive_dir = self.archive_dir / job.id
            os.makedirs(job_archive_dir, exist_ok=True)
            
            # 2. Compress results if configured
            if self.config.should_compress_results() and job.result_file_path:
                if os.path.exists(job.result_file_path):
                    archive_path = job_archive_dir / f"{os.path.basename(job.result_file_path)}.zip"
                    
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(job.result_file_path, arcname=os.path.basename(job.result_file_path))
                    
                    # Update job with archive path
                    job.result_file_path = str(archive_path)
                    
                    # Delete original file
                    os.remove(job.result_file_path)
                    logger.debug(f"Archived and compressed result file for job {job.id}")
            
            # 3. Copy input file if it exists
            if job.input_file_path and os.path.exists(job.input_file_path):
                shutil.copy2(job.input_file_path, job_archive_dir)
                
                # Update job with archive path
                job.input_file_path = str(job_archive_dir / os.path.basename(job.input_file_path))
                
                # Delete original file
                os.remove(job.input_file_path)
                logger.debug(f"Archived input file for job {job.id}")
            
            # 4. Update job status to Archived
            job.status = "Archived"
            self.job_dao.update(job)
            
            logger.info(f"Successfully archived job {job.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving job {job.id}: {str(e)}")
            return False
    
    def archive_old_jobs(self, max_jobs: int = 10) -> int:
        """
        Archive jobs older than the configured threshold.
        
        Args:
            max_jobs: Maximum number of jobs to archive in this run
            
        Returns:
            Number of successfully archived jobs
        """
        if not self.config.is_archiving_enabled():
            logger.info("Archiving is disabled in configuration")
            return 0
            
        # Find eligible jobs
        eligible_jobs = self.find_jobs_for_archiving()
        
        # Limit to max_jobs
        jobs_to_archive = eligible_jobs[:max_jobs]
        logger.info(f"Processing {len(jobs_to_archive)} of {len(eligible_jobs)} eligible jobs")
        
        # Archive each job
        success_count = 0
        for job in jobs_to_archive:
            if self.archive_job(job):
                success_count += 1
                
        logger.info(f"Successfully archived {success_count} jobs")
        return success_count
    
    def find_jobs_for_deletion(self) -> Dict[str, List[AMRJob]]:
        """
        Find jobs eligible for deletion based on retention policies.
        
        Returns:
            Dictionary of job lists by status
        """
        now = datetime.now()
        result = {}
        
        # Check each status type
        for status, days in self.config.config["retention_periods"].items():
            cutoff_date = now - timedelta(days=days)
            old_jobs = []
            
            if status == "Archived":
                # For archived jobs, use completed_at date
                all_jobs = self.job_dao.get_all(limit=1000, status=status)
                for job in all_jobs:
                    if job.completed_at and job.completed_at < cutoff_date:
                        old_jobs.append(job)
            
            elif status in ["Completed", "Error"]:
                # Use completed_at date
                all_jobs = self.job_dao.get_all(limit=1000, status=status)
                for job in all_jobs:
                    if job.completed_at and job.completed_at < cutoff_date:
                        old_jobs.append(job)
            
            else:
                # For other statuses (like stalled jobs), use created_at
                all_jobs = self.job_dao.get_all(limit=1000, status=status)
                for job in all_jobs:
                    # Check if job is stalled (hasn't been updated in a while)
                    if job.created_at < cutoff_date:
                        old_jobs.append(job)
            
            if old_jobs:
                result[status] = old_jobs
                logger.info(f"Found {len(old_jobs)} '{status}' jobs eligible for deletion")
                
        return result
    
    def delete_job(self, job: AMRJob) -> bool:
        """
        Permanently delete a job and its files.
        
        Args:
            job: Job to delete
            
        Returns:
            True if successfully deleted
        """
        try:
            # Delete input file if it exists
            if job.input_file_path and os.path.exists(job.input_file_path):
                os.remove(job.input_file_path)
                logger.debug(f"Deleted input file for job {job.id}")
            
            # Delete result file if it exists
            if job.result_file_path and os.path.exists(job.result_file_path):
                os.remove(job.result_file_path)
                logger.debug(f"Deleted result file for job {job.id}")
            
            # Delete job archive directory if it exists
            job_archive_dir = self.archive_dir / job.id
            if job_archive_dir.exists():
                shutil.rmtree(job_archive_dir)
                logger.debug(f"Deleted archive directory for job {job.id}")
            
            # Delete from database
            success = self.job_dao.delete(job.id)
            if success:
                logger.info(f"Deleted job {job.id} from database")
            else:
                logger.warning(f"Failed to delete job {job.id} from database")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting job {job.id}: {str(e)}")
            return False
    
    def cleanup_old_jobs(self, max_jobs: int = 50) -> Tuple[int, Dict[str, int]]:
        """
        Clean up jobs older than their retention periods.
        
        Args:
            max_jobs: Maximum number of jobs to clean up in this run
            
        Returns:
            Total deleted jobs count and count by status
        """
        if not self.config.is_cleanup_enabled():
            logger.info("Cleanup is disabled in configuration")
            return 0, {}
        
        # Find eligible jobs
        jobs_by_status = self.find_jobs_for_deletion()
        
        # Track deletion counts
        total_deleted = 0
        deleted_by_status = {}
        jobs_remaining = max_jobs
        
        # Delete jobs by status, respecting max limit
        for status, jobs in jobs_by_status.items():
            deleted_count = 0
            
            # Limit jobs to process
            jobs_to_delete = jobs[:jobs_remaining]
            
            # Delete each job
            for job in jobs_to_delete:
                if self.delete_job(job):
                    deleted_count += 1
                    total_deleted += 1
                    jobs_remaining -= 1
                    
                # Stop if reached max
                if jobs_remaining <= 0:
                    break
            
            if deleted_count > 0:
                deleted_by_status[status] = deleted_count
            
            # Stop if reached max
            if jobs_remaining <= 0:
                break
        
        logger.info(f"Cleaned up {total_deleted} jobs")
        return total_deleted, deleted_by_status
