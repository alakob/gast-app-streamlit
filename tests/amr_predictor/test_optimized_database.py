"""Tests for the Optimized Database Manager."""

import pytest
from datetime import datetime

from amr_predictor.bakta.database_manager_optimized import OptimizedDatabaseManager


def test_optimized_db_init(temp_db_path):
    """Test initializing the optimized database manager."""
    db_manager = OptimizedDatabaseManager(temp_db_path)
    
    # Verify tables were created
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if bakta_jobs table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bakta_jobs'"
        )
        assert cursor.fetchone() is not None
        
        # Check if bakta_job_params table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bakta_job_params'"
        )
        assert cursor.fetchone() is not None
        
        # Check if indexes were created
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_bakta_jobs_status'"
        )
        assert cursor.fetchone() is not None
    
    # Close connections
    db_manager.close()


def test_save_job(optimized_db_manager):
    """Test saving a job with the optimized database manager."""
    # Create a job
    job_id = "opt-test-job-123"
    job_name = "Optimized Test Job"
    
    # Save the job
    job_data = optimized_db_manager.save_job(
        job_id=job_id,
        job_name=job_name,
        status="Submitted",
        progress=0.0
    )
    
    # Verify job was saved
    assert job_data["id"] == job_id
    assert job_data["job_name"] == job_name
    assert job_data["status"] == "Submitted"
    assert job_data["progress"] == 0.0
    assert "created_at" in job_data
    
    # Retrieve the job to verify
    retrieved_job = optimized_db_manager.get_job(job_id)
    assert retrieved_job["id"] == job_id
    assert retrieved_job["job_name"] == job_name


def test_update_job_status(optimized_db_manager):
    """Test updating a job's status with the optimized database manager."""
    # Create a job
    job_id = "opt-update-job-123"
    job_name = "Optimized Update Job"
    
    optimized_db_manager.save_job(
        job_id=job_id,
        job_name=job_name,
        status="Submitted",
        progress=0.0
    )
    
    # Update the job status
    result = optimized_db_manager.update_job_status(
        job_id=job_id,
        status="Running",
        progress=25.0
    )
    
    # Verify update was successful
    assert result is True
    
    # Retrieve the job to verify update
    job = optimized_db_manager.get_job(job_id)
    assert job["status"] == "Running"
    assert job["progress"] == 25.0
    
    # Update to completed status
    result = optimized_db_manager.update_job_status(
        job_id=job_id,
        status="Completed",
        progress=100.0
    )
    
    # Verify update was successful and completed_at was set
    job = optimized_db_manager.get_job(job_id)
    assert job["status"] == "Completed"
    assert job["progress"] == 100.0
    assert job["completed_at"] is not None


def test_add_job_parameter(optimized_db_manager):
    """Test adding a parameter to a job with the optimized database manager."""
    # Create a job
    job_id = "opt-param-job-123"
    job_name = "Optimized Parameter Job"
    
    optimized_db_manager.save_job(
        job_id=job_id,
        job_name=job_name,
        status="Submitted",
        progress=0.0
    )
    
    # Add a parameter
    result = optimized_db_manager.add_job_parameter(
        job_id=job_id,
        param_name="model_name",
        param_value="test_model"
    )
    
    # Verify parameter was added
    assert result is True
    
    # Get the job to verify parameter
    job = optimized_db_manager.get_job(job_id)
    assert "parameters" in job
    assert job["parameters"]["model_name"] == "test_model"
    
    # Update the parameter
    result = optimized_db_manager.add_job_parameter(
        job_id=job_id,
        param_name="model_name",
        param_value="updated_model"
    )
    
    # Verify parameter was updated
    assert result is True
    
    # Get the job to verify update
    job = optimized_db_manager.get_job(job_id)
    assert job["parameters"]["model_name"] == "updated_model"


def test_add_job_parameters(optimized_db_manager):
    """Test adding multiple parameters to a job with the optimized database manager."""
    # Create a job
    job_id = "opt-params-job-123"
    job_name = "Optimized Parameters Job"
    
    optimized_db_manager.save_job(
        job_id=job_id,
        job_name=job_name,
        status="Submitted",
        progress=0.0
    )
    
    # Add multiple parameters
    params = {
        "model_name": "test_model",
        "batch_size": "8",
        "segment_length": "6000",
        "use_cpu": "True"
    }
    
    result = optimized_db_manager.add_job_parameters(
        job_id=job_id,
        parameters=params
    )
    
    # Verify parameters were added
    assert result is True
    
    # Get the job to verify parameters
    job = optimized_db_manager.get_job(job_id)
    assert "parameters" in job
    
    # Check each parameter
    for param_name, param_value in params.items():
        assert job["parameters"][param_name] == param_value


def test_get_jobs(optimized_db_manager):
    """Test getting multiple jobs with the optimized database manager."""
    # Create multiple jobs with different statuses
    optimized_db_manager.save_job(
        job_id="opt-job-1",
        job_name="Job 1",
        status="Submitted",
        progress=0.0
    )
    
    optimized_db_manager.save_job(
        job_id="opt-job-2",
        job_name="Job 2",
        status="Running",
        progress=50.0
    )
    
    optimized_db_manager.save_job(
        job_id="opt-job-3",
        job_name="Job 3",
        status="Completed",
        progress=100.0
    )
    
    # Get all jobs
    all_jobs = optimized_db_manager.get_jobs()
    assert len(all_jobs) == 3
    
    # Get jobs by status
    submitted_jobs = optimized_db_manager.get_jobs(status="Submitted")
    assert len(submitted_jobs) == 1
    assert submitted_jobs[0]["id"] == "opt-job-1"
    
    running_jobs = optimized_db_manager.get_jobs(status="Running")
    assert len(running_jobs) == 1
    assert running_jobs[0]["id"] == "opt-job-2"
    
    completed_jobs = optimized_db_manager.get_jobs(status="Completed")
    assert len(completed_jobs) == 1
    assert completed_jobs[0]["id"] == "opt-job-3"
    
    # Test limit
    limited_jobs = optimized_db_manager.get_jobs(limit=2)
    assert len(limited_jobs) == 2


def test_delete_job(optimized_db_manager):
    """Test deleting a job with the optimized database manager."""
    # Create a job
    job_id = "opt-delete-job-123"
    job_name = "Optimized Delete Job"
    
    optimized_db_manager.save_job(
        job_id=job_id,
        job_name=job_name,
        status="Submitted",
        progress=0.0
    )
    
    # Add a parameter
    optimized_db_manager.add_job_parameter(
        job_id=job_id,
        param_name="test_param",
        param_value="test_value"
    )
    
    # Delete the job
    result = optimized_db_manager.delete_job(job_id)
    
    # Verify deletion was successful
    assert result is True
    
    # Try to get the job to verify it's gone
    job = optimized_db_manager.get_job(job_id)
    assert job is None


def test_count_jobs(optimized_db_manager):
    """Test counting jobs with the optimized database manager."""
    # Create jobs with different statuses
    optimized_db_manager.save_job(
        job_id="count-job-1",
        job_name="Count Job 1",
        status="Submitted",
        progress=0.0
    )
    
    optimized_db_manager.save_job(
        job_id="count-job-2",
        job_name="Count Job 2",
        status="Running",
        progress=50.0
    )
    
    optimized_db_manager.save_job(
        job_id="count-job-3",
        job_name="Count Job 3",
        status="Completed",
        progress=100.0
    )
    
    # Count all jobs
    total_count = optimized_db_manager.count_jobs()
    assert total_count == 3
    
    # Count by status
    submitted_count = optimized_db_manager.count_jobs(status="Submitted")
    assert submitted_count == 1
    
    running_count = optimized_db_manager.count_jobs(status="Running")
    assert running_count == 1
    
    completed_count = optimized_db_manager.count_jobs(status="Completed")
    assert completed_count == 1
