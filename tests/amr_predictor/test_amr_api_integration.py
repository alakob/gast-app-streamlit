"""Tests for the AMR API Integration."""

import os
import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi import status

from amr_predictor.models.amr_job import AMRJobStatus


def test_create_amr_job(test_client, auth_headers, monkeypatch):
    """Test creating a new AMR job through the API."""
    # Mock the background task processing
    with patch('amr_predictor.api.amr_db_integration.process_amr_job') as mock_process:
        # Create a temp file for testing
        temp_file_content = b"Test file content"
        temp_file_name = "test_input.fasta"
        
        # Prepare request
        files = {"input_file": (temp_file_name, temp_file_content)}
        data = {"job_name": "API Test Job"}
        
        # Make request to create job
        response = test_client.post(
            "/amr/jobs",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        job_data = response.json()
        assert job_data["job_name"] == "API Test Job"
        assert job_data["status"] == AMRJobStatus.SUBMITTED
        assert job_data["progress"] == 0.0
        
        # Verify background task was called
        mock_process.assert_called_once()


def test_get_amr_job(test_client, auth_headers, saved_test_job):
    """Test getting information about an AMR job."""
    # Get job info
    response = test_client.get(
        f"/amr/jobs/{saved_test_job.id}",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    job_data = response.json()
    assert job_data["id"] == saved_test_job.id
    assert job_data["job_name"] == saved_test_job.job_name
    assert job_data["status"] == saved_test_job.status


def test_list_amr_jobs(test_client, auth_headers, populated_db):
    """Test listing AMR jobs."""
    # Get all jobs
    response = test_client.get(
        "/amr/jobs",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 3  # We have at least 3 jobs from populated_db
    
    # Verify filtering by status
    response = test_client.get(
        "/amr/jobs?status=Completed",
        headers=auth_headers
    )
    completed_jobs = response.json()
    assert all(job["status"] == "Completed" for job in completed_jobs)
    
    response = test_client.get(
        "/amr/jobs?status=Error",
        headers=auth_headers
    )
    error_jobs = response.json()
    assert all(job["status"] == "Error" for job in error_jobs)


def test_get_job_result(test_client, auth_headers, saved_completed_job, monkeypatch):
    """Test getting job result file."""
    # Create a temporary result file
    result_content = b"Test result content"
    result_dir = f"results/{saved_completed_job.id}"
    os.makedirs(result_dir, exist_ok=True)
    
    result_file_path = f"{result_dir}/result.txt"
    with open(result_file_path, "wb") as f:
        f.write(result_content)
    
    # Update the job with the result file path
    saved_completed_job.result_file_path = result_file_path
    
    # Mock the DAO's get_by_id to return our updated job
    def mock_get_by_id(self, job_id):
        if job_id == saved_completed_job.id:
            return saved_completed_job
        return None
    
    monkeypatch.setattr("amr_predictor.dao.amr_job_dao.AMRJobDAO.get_by_id", mock_get_by_id)
    
    # Request the result file
    response = test_client.get(
        f"/amr/jobs/{saved_completed_job.id}/result",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    assert response.content == result_content
    
    # Clean up
    if os.path.exists(result_file_path):
        os.unlink(result_file_path)
    if os.path.exists(result_dir):
        os.rmdir(result_dir)


def test_delete_job(test_client, auth_headers, saved_test_job):
    """Test deleting an AMR job."""
    # Delete job
    response = test_client.delete(
        f"/amr/jobs/{saved_test_job.id}",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["success"] is True
    
    # Verify job is gone
    response = test_client.get(
        f"/amr/jobs/{saved_test_job.id}",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_archive_job(test_client, auth_headers, saved_completed_job, temp_archive_dir, monkeypatch):
    """Test archiving an AMR job."""
    # Mock the job archiver's archive_job method
    def mock_archive_job(self, job):
        job.status = AMRJobStatus.ARCHIVED
        return True
    
    monkeypatch.setattr("amr_predictor.maintenance.job_archiver.JobArchiver.archive_job", mock_archive_job)
    
    # Archive job
    response = test_client.post(
        f"/amr/jobs/{saved_completed_job.id}/archive",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["success"] is True
    
    # Verify job status is updated
    response = test_client.get(
        f"/amr/jobs/{saved_completed_job.id}",
        headers=auth_headers
    )
    job_data = response.json()
    assert job_data["status"] == AMRJobStatus.ARCHIVED


def test_maintenance_endpoints_require_admin(test_client, auth_headers):
    """Test that maintenance endpoints require admin privileges."""
    # Try to run archive old jobs
    response = test_client.post(
        "/amr/maintenance/archive-old-jobs",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify response requires admin
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Try to run cleanup old jobs
    response = test_client.post(
        "/amr/maintenance/cleanup-old-jobs",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify response requires admin
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_maintenance_endpoints_with_admin(test_client, admin_auth_headers, monkeypatch):
    """Test maintenance endpoints with admin privileges."""
    # Mock the job archiver methods
    def mock_archive_old_jobs(self, max_jobs):
        return 3  # Pretend 3 jobs were archived
    
    def mock_cleanup_old_jobs(self, max_jobs):
        return 2, {"Completed": 1, "Error": 1}  # Pretend 2 jobs were deleted
    
    monkeypatch.setattr("amr_predictor.maintenance.job_archiver.JobArchiver.archive_old_jobs", mock_archive_old_jobs)
    monkeypatch.setattr("amr_predictor.maintenance.job_archiver.JobArchiver.cleanup_old_jobs", mock_cleanup_old_jobs)
    
    # Run archive old jobs
    response = test_client.post(
        "/amr/maintenance/archive-old-jobs",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["success"] is True
    assert result["archived_count"] == 3
    
    # Run cleanup old jobs
    response = test_client.post(
        "/amr/maintenance/cleanup-old-jobs",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["success"] is True
    assert result["total_deleted"] == 2
    assert result["by_status"] == {"Completed": 1, "Error": 1}
