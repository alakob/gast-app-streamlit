"""Tests for the AMR Job DAO."""

import pytest
from datetime import datetime, timedelta

from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob, AMRJobParams


def test_save_job(amr_job_dao, test_job):
    """Test saving a job to the database."""
    # Save the job
    saved_job = amr_job_dao.save(test_job)
    
    # Verify it was saved with the same ID
    assert saved_job.id == test_job.id
    
    # Retrieve the job to verify it exists
    retrieved_job = amr_job_dao.get_by_id(test_job.id)
    assert retrieved_job is not None
    assert retrieved_job.id == test_job.id
    assert retrieved_job.job_name == test_job.job_name
    assert retrieved_job.status == test_job.status
    assert retrieved_job.progress == test_job.progress


def test_get_by_id_not_found(amr_job_dao):
    """Test getting a job by ID when it doesn't exist."""
    job = amr_job_dao.get_by_id("non-existent-id")
    assert job is None


def test_update_job(amr_job_dao, saved_test_job):
    """Test updating a job in the database."""
    # Update job properties
    saved_test_job.status = "Running"
    saved_test_job.progress = 50.0
    
    # Save the updated job
    updated_job = amr_job_dao.update(saved_test_job)
    
    # Verify the updates
    assert updated_job.status == "Running"
    assert updated_job.progress == 50.0
    
    # Retrieve to confirm updates
    retrieved_job = amr_job_dao.get_by_id(saved_test_job.id)
    assert retrieved_job.status == "Running"
    assert retrieved_job.progress == 50.0


def test_update_status(amr_job_dao, saved_test_job):
    """Test updating just the status of a job."""
    # Update status
    amr_job_dao.update_status(
        saved_test_job.id,
        status="Completed",
        progress=100.0,
        completed_at=datetime.now()
    )
    
    # Retrieve to confirm updates
    retrieved_job = amr_job_dao.get_by_id(saved_test_job.id)
    assert retrieved_job.status == "Completed"
    assert retrieved_job.progress == 100.0
    assert retrieved_job.completed_at is not None


def test_update_params(amr_job_dao, saved_test_job):
    """Test updating job parameters."""
    # Create new params
    new_params = AMRJobParams(
        model_name="updated_model",
        batch_size=16,
        segment_length=8000,
        segment_overlap=100,
        use_cpu=False
    )
    
    # Update params
    saved_test_job.params = new_params
    updated_job = amr_job_dao.update(saved_test_job)
    
    # Verify params were updated
    assert updated_job.params.model_name == "updated_model"
    assert updated_job.params.batch_size == 16
    assert updated_job.params.segment_length == 8000
    
    # Retrieve to confirm updates
    retrieved_job = amr_job_dao.get_by_id(saved_test_job.id)
    assert retrieved_job.params.model_name == "updated_model"
    assert retrieved_job.params.batch_size == 16
    assert retrieved_job.params.segment_length == 8000


def test_delete_job(amr_job_dao, saved_test_job):
    """Test deleting a job from the database."""
    # Delete the job
    result = amr_job_dao.delete(saved_test_job.id)
    assert result is True
    
    # Verify it's gone
    retrieved_job = amr_job_dao.get_by_id(saved_test_job.id)
    assert retrieved_job is None


def test_delete_nonexistent_job(amr_job_dao):
    """Test deleting a job that doesn't exist."""
    result = amr_job_dao.delete("non-existent-id")
    assert result is False


def test_get_all(populated_db):
    """Test retrieving all jobs."""
    jobs = populated_db.get_all()
    assert len(jobs) == 3


def test_get_all_with_status(populated_db):
    """Test retrieving jobs filtered by status."""
    # Get only completed jobs
    completed_jobs = populated_db.get_all(status="Completed")
    assert len(completed_jobs) == 1
    assert completed_jobs[0].status == "Completed"
    
    # Get only error jobs
    error_jobs = populated_db.get_all(status="Error")
    assert len(error_jobs) == 1
    assert error_jobs[0].status == "Error"


def test_get_all_with_limit(populated_db):
    """Test retrieving jobs with limit."""
    # Get with limit of 2
    limited_jobs = populated_db.get_all(limit=2)
    assert len(limited_jobs) == 2


def test_count_by_status(populated_db):
    """Test counting jobs by status."""
    # Count completed jobs
    completed_count = populated_db.count_by_status("Completed")
    assert completed_count == 1
    
    # Count error jobs
    error_count = populated_db.count_by_status("Error")
    assert error_count == 1
    
    # Count submitted jobs
    submitted_count = populated_db.count_by_status("Submitted")
    assert submitted_count == 1
    
    # Count non-existent status
    nonexistent_count = populated_db.count_by_status("NonExistentStatus")
    assert nonexistent_count == 0


def test_find_stalled_jobs(amr_job_dao, saved_test_job):
    """Test finding stalled jobs."""
    # Make the job appear old
    job_id = saved_test_job.id
    
    # Update the created_at date to make it appear stalled
    with amr_job_dao.db_manager._get_connection() as conn:
        old_date = datetime.now() - timedelta(days=3)
        conn.execute(
            "UPDATE amr_jobs SET created_at = ? WHERE id = ?",
            (old_date, job_id)
        )
        conn.commit()
    
    # Find stalled jobs
    stalled_time = datetime.now() - timedelta(days=2)
    stalled_jobs = amr_job_dao.find_stalled_jobs(
        statuses=["Submitted"], 
        older_than=stalled_time
    )
    
    assert len(stalled_jobs) == 1
    assert stalled_jobs[0].id == job_id
