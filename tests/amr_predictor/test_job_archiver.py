"""Tests for the Job Archiver and Lifecycle Management."""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from amr_predictor.maintenance.job_archiver import JobArchiver
from amr_predictor.config.job_lifecycle_config import JobLifecycleConfig
from amr_predictor.models.amr_job import AMRJob


def test_find_jobs_for_archiving(job_archiver, saved_completed_job):
    """Test finding jobs eligible for archiving."""
    # Override the min age for archiving to 1 day to make our test job eligible
    job_archiver.config.config["archiving"]["min_age_days"] = 1
    
    # Find jobs for archiving
    eligible_jobs = job_archiver.find_jobs_for_archiving()
    
    # Verify our completed job is eligible
    assert len(eligible_jobs) == 1
    assert eligible_jobs[0].id == saved_completed_job.id


def test_find_jobs_for_archiving_none_eligible(job_archiver, saved_completed_job):
    """Test when no jobs are eligible for archiving."""
    # Set min age high enough that no jobs will be eligible
    job_archiver.config.config["archiving"]["min_age_days"] = 100
    
    # Find jobs for archiving
    eligible_jobs = job_archiver.find_jobs_for_archiving()
    
    # Verify no jobs are eligible
    assert len(eligible_jobs) == 0


def test_archive_job(job_archiver, saved_completed_job, temp_archive_dir):
    """Test archiving a single job."""
    # Create a temporary file to simulate a result file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test result content")
        temp_file_path = temp_file.name
    
    # Update the job with the temp file
    saved_completed_job.result_file_path = temp_file_path
    job_archiver.job_dao.update(saved_completed_job)
    
    # Archive the job
    result = job_archiver.archive_job(saved_completed_job)
    
    # Verify job was archived
    assert result is True
    
    # Get updated job from database
    archived_job = job_archiver.job_dao.get_by_id(saved_completed_job.id)
    
    # Verify status was updated
    assert archived_job.status == "Archived"
    
    # Verify archive directory was created
    job_archive_dir = Path(temp_archive_dir) / saved_completed_job.id
    assert job_archive_dir.exists()
    
    # If compression is enabled, verify result file was compressed
    if job_archiver.config.should_compress_results():
        # Check that a zip file exists
        archive_files = list(job_archive_dir.glob("*.zip"))
        assert len(archive_files) > 0
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


def test_archive_old_jobs(job_archiver, saved_completed_job):
    """Test archiving old jobs."""
    # Override the min age for archiving to make our test job eligible
    job_archiver.config.config["archiving"]["min_age_days"] = 1
    
    # Create a temporary file to simulate a result file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test result content")
        temp_file_path = temp_file.name
    
    # Update the job with the temp file
    saved_completed_job.result_file_path = temp_file_path
    job_archiver.job_dao.update(saved_completed_job)
    
    # Archive old jobs
    count = job_archiver.archive_old_jobs(max_jobs=10)
    
    # Verify one job was archived
    assert count == 1
    
    # Get updated job from database
    archived_job = job_archiver.job_dao.get_by_id(saved_completed_job.id)
    
    # Verify status was updated
    assert archived_job.status == "Archived"
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


def test_archive_disabled(job_archiver, saved_completed_job):
    """Test when archiving is disabled."""
    # Disable archiving
    job_archiver.config.config["archiving"]["enabled"] = False
    
    # Try to archive old jobs
    count = job_archiver.archive_old_jobs(max_jobs=10)
    
    # Verify no jobs were archived
    assert count == 0
    
    # Verify job status was not changed
    job = job_archiver.job_dao.get_by_id(saved_completed_job.id)
    assert job.status == "Completed"


def test_find_jobs_for_deletion(job_archiver, saved_completed_job, saved_error_job):
    """Test finding jobs eligible for deletion."""
    # Override retention periods to make our test jobs eligible
    job_archiver.config.config["retention_periods"]["Completed"] = 1
    job_archiver.config.config["retention_periods"]["Error"] = 1
    
    # Make the jobs appear old enough for deletion
    with job_archiver.db_manager._get_connection() as conn:
        # Make completed job appear old
        old_date = datetime.now() - timedelta(days=5)
        conn.execute(
            "UPDATE amr_jobs SET completed_at = ? WHERE id = ?",
            (old_date, saved_completed_job.id)
        )
        
        # Make error job appear old
        conn.execute(
            "UPDATE amr_jobs SET completed_at = ? WHERE id = ?",
            (old_date, saved_error_job.id)
        )
        
        conn.commit()
    
    # Find jobs for deletion
    jobs_by_status = job_archiver.find_jobs_for_deletion()
    
    # Verify both jobs are eligible for deletion
    assert "Completed" in jobs_by_status
    assert "Error" in jobs_by_status
    assert len(jobs_by_status["Completed"]) == 1
    assert len(jobs_by_status["Error"]) == 1
    assert jobs_by_status["Completed"][0].id == saved_completed_job.id
    assert jobs_by_status["Error"][0].id == saved_error_job.id


def test_delete_job(job_archiver, saved_completed_job):
    """Test deleting a job."""
    # Create a temporary file to simulate a result file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test result content")
        temp_file_path = temp_file.name
    
    # Update the job with the temp file
    saved_completed_job.result_file_path = temp_file_path
    job_archiver.job_dao.update(saved_completed_job)
    
    # Delete the job
    result = job_archiver.delete_job(saved_completed_job)
    
    # Verify job was deleted
    assert result is True
    
    # Verify job is no longer in database
    job = job_archiver.job_dao.get_by_id(saved_completed_job.id)
    assert job is None
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


def test_cleanup_old_jobs(job_archiver, saved_completed_job, saved_error_job):
    """Test cleaning up old jobs."""
    # Override retention periods to make our test jobs eligible
    job_archiver.config.config["retention_periods"]["Completed"] = 1
    job_archiver.config.config["retention_periods"]["Error"] = 1
    
    # Make the jobs appear old enough for deletion
    with job_archiver.db_manager._get_connection() as conn:
        # Make completed job appear old
        old_date = datetime.now() - timedelta(days=5)
        conn.execute(
            "UPDATE amr_jobs SET completed_at = ? WHERE id = ?",
            (old_date, saved_completed_job.id)
        )
        
        # Make error job appear old
        conn.execute(
            "UPDATE amr_jobs SET completed_at = ? WHERE id = ?",
            (old_date, saved_error_job.id)
        )
        
        conn.commit()
    
    # Clean up old jobs
    total, by_status = job_archiver.cleanup_old_jobs(max_jobs=10)
    
    # Verify jobs were deleted
    assert total == 2
    assert "Completed" in by_status
    assert "Error" in by_status
    assert by_status["Completed"] == 1
    assert by_status["Error"] == 1
    
    # Verify jobs are no longer in database
    assert job_archiver.job_dao.get_by_id(saved_completed_job.id) is None
    assert job_archiver.job_dao.get_by_id(saved_error_job.id) is None


def test_cleanup_disabled(job_archiver, saved_completed_job):
    """Test when cleanup is disabled."""
    # Disable cleanup
    job_archiver.config.config["cleanup"]["enabled"] = False
    
    # Try to clean up old jobs
    total, by_status = job_archiver.cleanup_old_jobs(max_jobs=10)
    
    # Verify no jobs were deleted
    assert total == 0
    assert not by_status
    
    # Verify job still exists
    job = job_archiver.job_dao.get_by_id(saved_completed_job.id)
    assert job is not None
