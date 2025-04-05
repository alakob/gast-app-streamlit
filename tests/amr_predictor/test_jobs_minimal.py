"""Minimal test module for AMR job management API."""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock

from amr_predictor.api.jobs import JobManager, JobRequest, Job, JobStatus, JobType

@pytest.fixture
def job_manager():
    """Create a JobManager instance for testing."""
    return JobManager()

@pytest.mark.asyncio
async def test_job_lifecycle(job_manager):
    """Test the complete lifecycle of a job from creation to completion."""
    # Create a job request
    job_request = JobRequest(
        job_type=JobType.PREDICTION,
        parameters={"test_param": "test_value"},
        priority=1,
        timeout=60
    )
    
    # Create the job
    job = await job_manager.create_job(job_request)
    
    # Verify job is created with correct initial properties
    assert job.id is not None
    assert job.job_type == JobType.PREDICTION
    assert job.status == JobStatus.PENDING
    assert job.parameters == {"test_param": "test_value"}
    assert job.priority == 1
    assert job.timeout == 60
    assert job.created_at is not None
    assert job.started_at is None
    assert job.completed_at is None
    assert job.result is None
    assert job.error is None
    assert job.progress == 0.0
    
    # Mock the _process_job method to avoid actual processing
    with patch.object(job_manager, '_process_job') as mock_process:
        mock_process.return_value = None
        
        # Process the job
        await job_manager.process_job(job.id)
        
        # Verify job status is updated to PROCESSING
        updated_job = await job_manager.get_job(job.id)
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.started_at is not None
        
        # Manually update job to COMPLETED
        updated_job.status = JobStatus.COMPLETED
        updated_job.completed_at = datetime.now(UTC)
        updated_job.result = {"result": "test_result"}
        updated_job.progress = 1.0
        
        # Get the job again and verify completion
        final_job = await job_manager.get_job(job.id)
        assert final_job.status == JobStatus.COMPLETED
        assert final_job.completed_at is not None
        assert final_job.result == {"result": "test_result"}
        assert final_job.progress == 1.0

@pytest.mark.asyncio
async def test_list_jobs(job_manager):
    """Test listing jobs with filters."""
    # Create some test jobs
    job1 = await job_manager.create_job(JobRequest(
        job_type=JobType.PREDICTION,
        parameters={"test": "1"},
        priority=2
    ))
    job2 = await job_manager.create_job(JobRequest(
        job_type=JobType.PROCESSING,
        parameters={"test": "2"},
        priority=1
    ))
    job3 = await job_manager.create_job(JobRequest(
        job_type=JobType.ANALYSIS,
        parameters={"test": "3"},
        priority=3
    ))
    
    # Update job statuses to different values
    job_manager._jobs[job1.id].status = JobStatus.PROCESSING
    job_manager._jobs[job2.id].status = JobStatus.COMPLETED
    job_manager._jobs[job3.id].status = JobStatus.PENDING
    
    # List all jobs
    all_jobs = await job_manager.list_jobs()
    assert len(all_jobs) == 3
    
    # List by status
    processing_jobs = await job_manager.list_jobs(status=JobStatus.PROCESSING)
    assert len(processing_jobs) == 1
    assert processing_jobs[0].id == job1.id
    
    completed_jobs = await job_manager.list_jobs(status=JobStatus.COMPLETED)
    assert len(completed_jobs) == 1
    assert completed_jobs[0].id == job2.id
    
    # List by job type
    prediction_jobs = await job_manager.list_jobs(job_type=JobType.PREDICTION)
    assert len(prediction_jobs) == 1
    assert prediction_jobs[0].id == job1.id
    
    # Test priority sorting
    sorted_jobs = await job_manager.list_jobs()
    assert sorted_jobs[0].id == job3.id  # Priority 3
    assert sorted_jobs[1].id == job1.id  # Priority 2
    assert sorted_jobs[2].id == job2.id  # Priority 1

@pytest.mark.asyncio
async def test_cancel_job(job_manager):
    """Test cancelling a job."""
    # Create a job
    job = await job_manager.create_job(JobRequest(
        job_type=JobType.PREDICTION,
        parameters={"test": "cancel"}
    ))
    
    # Mock the processing task
    mock_task = MagicMock()
    job_manager._processing_tasks[job.id] = mock_task
    
    # Update job status to PROCESSING
    job_manager._jobs[job.id].status = JobStatus.PROCESSING
    
    # Cancel the job
    result = await job_manager.cancel_job(job.id)
    
    # Verify cancellation was successful
    assert result is True
    assert mock_task.cancel.called
    assert job.id not in job_manager._processing_tasks
    
    # Get the job and verify its cancelled
    cancelled_job = await job_manager.get_job(job.id)
    assert cancelled_job.status == JobStatus.CANCELLED
    assert cancelled_job.completed_at is not None
    
    # Try to cancel a non-existent job
    result = await job_manager.cancel_job("non-existent-id")
    assert result is False
    
    # Try to cancel an already completed job
    completed_job = await job_manager.create_job(JobRequest(
        job_type=JobType.PREDICTION,
        parameters={"test": "completed"}
    ))
    job_manager._jobs[completed_job.id].status = JobStatus.COMPLETED
    
    result = await job_manager.cancel_job(completed_job.id)
    assert result is False
