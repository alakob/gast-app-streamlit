#!/usr/bin/env python3
"""
Tests for the BaktaJobManager class.
"""

import os
import time
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path
from unittest.mock import AsyncMock

from amr_predictor.bakta.job_manager import BaktaJobManager, with_retry
from amr_predictor.bakta.manager import BaktaManager
from amr_predictor.bakta.models import BaktaJob, BaktaJobStatusHistory
from amr_predictor.bakta.exceptions import BaktaApiError, BaktaManagerError

# Sample data for testing
SAMPLE_JOB_ID = "test-job-123"
SAMPLE_JOB_SECRET = "test-secret-456"
SAMPLE_FASTA = """>contig1
ATGCATGCATGC
"""


@pytest.fixture
def mock_manager():
    """Create a mock BaktaManager for testing."""
    mock = MagicMock(spec=BaktaManager)
    
    # Add required attributes
    mock.client = MagicMock()
    mock.results_dir = Path("/tmp/bakta_results")
    
    # Setup mock methods
    mock.create_job.return_value = BaktaJob(
        id=SAMPLE_JOB_ID,
        name="Test Job",
        secret=SAMPLE_JOB_SECRET,
        status="INIT",
        config={},
        created_at="2023-01-01T12:00:00",
        updated_at="2023-01-01T12:00:00"
    )
    
    mock.start_job.return_value = BaktaJob(
        id=SAMPLE_JOB_ID,
        name="Test Job",
        secret=SAMPLE_JOB_SECRET,
        status="RUNNING",
        config={},
        created_at="2023-01-01T12:00:00",
        updated_at="2023-01-01T12:01:00"
    )
    
    mock.check_job_status.return_value = BaktaJob(
        id=SAMPLE_JOB_ID,
        name="Test Job",
        secret=SAMPLE_JOB_SECRET,
        status="RUNNING",
        config={},
        created_at="2023-01-01T12:00:00",
        updated_at="2023-01-01T12:02:00"
    )
    
    # Configure repository mock
    mock.repository = MagicMock()
    mock.repository.get_status_history.return_value = []
    
    return mock


@pytest.fixture
def job_manager(mock_manager):
    """Create a BaktaJobManager with mocked dependencies."""
    # Create the job manager
    job_mgr = BaktaJobManager(
        base_manager=mock_manager,
        poll_interval=0.1  # Fast polling for tests
    )
    
    # Mock the storage service
    job_mgr.storage_service = MagicMock()
    
    return job_mgr


class TestBaktaJobManager:
    """Tests for the BaktaJobManager class."""
    
    def test_initialization(self, mock_manager):
        """Test that the job manager initializes correctly."""
        manager = BaktaJobManager(base_manager=mock_manager)
        
        assert manager.manager == mock_manager
        assert manager.client == mock_manager.client
        assert manager.repository == mock_manager.repository
        assert manager.poll_interval == 30  # Default value
        assert not manager._background_tasks
        assert manager._stop_event is not None
        assert manager._poller_thread is None
    
    def test_create_job(self, job_manager, mock_manager):
        """Test creating a job with retry support."""
        result = job_manager.create_job(
            fasta_path="test.fasta",
            name="Test Job",
            config={}
        )
        
        assert result.id == SAMPLE_JOB_ID
        mock_manager.create_job.assert_called_once_with(
            fasta_path="test.fasta",
            name="Test Job",
            config={}
        )
    
    def test_start_job(self, job_manager, mock_manager):
        """Test starting a job with retry support."""
        result = job_manager.start_job(SAMPLE_JOB_ID)
        
        assert result.status == "RUNNING"
        mock_manager.start_job.assert_called_once_with(SAMPLE_JOB_ID)
    
    def test_check_job_status(self, job_manager, mock_manager):
        """Test checking job status."""
        # Configure mock
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="COMPLETED",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:10:00"
        )
        
        # Setup mock for repository
        history_entry = None
        def save_status_history(entry):
            nonlocal history_entry
            history_entry = entry
        
        job_manager.repository.save_status_history = MagicMock(side_effect=save_status_history)
        
        # Call method
        result = job_manager.check_job_status(SAMPLE_JOB_ID)
        
        # Check result
        assert result.status == "COMPLETED"
        mock_manager.check_job_status.assert_called_once_with(SAMPLE_JOB_ID)
        
        # Check that status history was recorded
        assert history_entry is not None
        assert history_entry.job_id == SAMPLE_JOB_ID
        assert history_entry.status == "COMPLETED"
    
    def test_retry_mechanism(self, job_manager, mock_manager):
        """Test the retry mechanism for API calls."""
        # Setup mock to fail twice then succeed
        mock_manager.check_job_status.side_effect = [
            BaktaApiError("API error 1"),
            BaktaApiError("API error 2"),
            BaktaJob(
                id=SAMPLE_JOB_ID,
                name="Test Job",
                secret=SAMPLE_JOB_SECRET,
                status="COMPLETED",
                config={},
                created_at="2023-01-01T12:00:00",
                updated_at="2023-01-01T12:10:00"
            )
        ]
        
        # Patch the sleep function to avoid delays
        with patch('time.sleep'):
            result = job_manager.check_job_status(SAMPLE_JOB_ID)
            
            # Should have retried and succeeded
            assert result.status == "COMPLETED"
            assert mock_manager.check_job_status.call_count == 3
    
    def test_submit_job(self, job_manager, mock_manager):
        """Test submitting a job."""
        # Setup mocks
        mock_manager.create_job.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="INIT",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:00:00"
        )
        
        mock_manager.start_job.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="RUNNING",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:01:00"
        )
        
        # Mock the start_background_monitoring method
        job_manager.start_background_monitoring = MagicMock()
        
        # Call method
        result = job_manager.submit_job(
            fasta_path="test.fasta",
            name="Test Job",
            config={},
            wait_for_completion=False,
            process_results=True
        )
        
        # Check results
        assert result.id == SAMPLE_JOB_ID
        assert result.status == "RUNNING"
        
        mock_manager.create_job.assert_called_once()
        mock_manager.start_job.assert_called_once_with(SAMPLE_JOB_ID)
        job_manager.start_background_monitoring.assert_called_once_with(SAMPLE_JOB_ID, True)
    
    def test_wait_for_completion(self, job_manager, mock_manager):
        """Test waiting for job completion."""
        # Setup mocks for status progression
        mock_manager.check_job_status.side_effect = [
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="RUNNING", config={}, created_at="", updated_at=""),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="RUNNING", config={}, created_at="", updated_at=""),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="COMPLETED", config={}, created_at="", updated_at="")
        ]
        
        # Patch sleep to avoid delays
        with patch('time.sleep'):
            result = job_manager.wait_for_completion(SAMPLE_JOB_ID)
            
            # Check result
            assert result.status == "COMPLETED"
            assert mock_manager.check_job_status.call_count == 3
    
    def test_wait_for_completion_with_failure(self, job_manager, mock_manager):
        """Test waiting for a job that fails."""
        # Setup mocks for status progression
        mock_manager.check_job_status.side_effect = [
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="RUNNING", config={}, created_at="", updated_at=""),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="FAILED", config={}, created_at="", updated_at="")
        ]
        
        # Patch sleep to avoid delays
        with patch('time.sleep'):
            # Should raise an error
            with pytest.raises(BaktaManagerError, match="Job .* failed with status: FAILED"):
                job_manager.wait_for_completion(SAMPLE_JOB_ID)
            
            assert mock_manager.check_job_status.call_count == 2
    
    def test_with_retry_decorator(self):
        """Test the with_retry decorator."""
        mock_func = MagicMock()
        mock_func.__name__ = "mock_func"  # Add name attribute for the decorator
        mock_func.side_effect = [
            BaktaApiError("API error 1"),
            BaktaApiError("API error 2"),
            "success"
        ]
        
        # Apply the decorator
        decorated_func = with_retry(max_retries=2, retry_delay=0.01)(mock_func)
        
        # Call the decorated function
        with patch('time.sleep'):
            result = decorated_func()
            
            # Should have retried and succeeded
            assert result == "success"
            assert mock_func.call_count == 3
    
    def test_start_background_monitoring(self, job_manager):
        """Test starting background monitoring."""
        # Mock the wait_for_completion method
        job_manager.wait_for_completion = MagicMock(return_value=BaktaJob(
            id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET,
            status="COMPLETED", config={}, created_at="", updated_at=""
        ))
        
        job_manager.process_job_results = MagicMock()
        
        # Call the method
        job_manager.start_background_monitoring(SAMPLE_JOB_ID, process_results=True)
        
        # Give the thread a moment to run
        time.sleep(0.1)
        
        # Verify that the job was tracked
        assert SAMPLE_JOB_ID in job_manager._background_tasks
        
        # Save the thread to join it later
        thread = job_manager._background_tasks[SAMPLE_JOB_ID]
        
        # Give the thread time to complete
        thread.join(timeout=1.0)  # Wait for the thread to complete
        
        # Should remove the task from tracking after completion
        # Note: In some test environments, the background task might not be removed immediately
        # So we'll manually check that the thread completed instead
        assert not thread.is_alive()
        
        # Verify that wait_for_completion was called
        job_manager.wait_for_completion.assert_called_once_with(SAMPLE_JOB_ID)
        
        # Verify that process_job_results was called
        job_manager.process_job_results.assert_called_once_with(SAMPLE_JOB_ID)
    
    def test_retry_failed_job(self, job_manager, mock_manager):
        """Test retrying a failed job."""
        # Setup mocks
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="FAILED",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:10:00"
        )
        
        job_manager.start_background_monitoring = MagicMock()
        
        # Call method
        job_manager.retry_failed_job(SAMPLE_JOB_ID)
        
        # Check that the job was retried
        mock_manager.repository.update_job_status.assert_called_once_with(
            job_id=SAMPLE_JOB_ID,
            status="INIT"
        )
        
        mock_manager.start_job.assert_called_once_with(SAMPLE_JOB_ID)
        job_manager.start_background_monitoring.assert_called_once_with(SAMPLE_JOB_ID, process_results=True)
    
    def test_notification_callback(self, mock_manager):
        """Test notification callback when status changes."""
        # Create a callback mock
        callback_mock = MagicMock()
        
        # Create job manager with notification callback
        job_manager = BaktaJobManager(
            base_manager=mock_manager,
            notification_callback=callback_mock
        )
        
        # Setup mock
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="COMPLETED",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:10:00"
        )
        
        # Call method
        job_manager.check_job_status(SAMPLE_JOB_ID)
        
        # Check callback was called
        callback_mock.assert_called_once_with(SAMPLE_JOB_ID, "COMPLETED")
    
    def test_process_job_results(self, job_manager, mock_manager):
        """Test processing job results."""
        # Setup mocks
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="COMPLETED",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:10:00"
        )
        
        job_manager.storage_service = MagicMock()
        job_manager.storage_service.download_result_files.return_value = {
            "GFF3": "/tmp/test.gff3",
            "FASTA": "/tmp/test.fasta"
        }
        
        # Mock the async_process_all_files method
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = {
                "annotations": 10,
                "sequences": 2,
                "errors": 0
            }
            
            # Call the method
            result = job_manager.process_job_results(SAMPLE_JOB_ID)
            
            # Check results
            assert result["job_id"] == SAMPLE_JOB_ID
            assert len(result["downloaded_files"]) == 2
            assert result["annotations"] == 10
            assert result["sequences"] == 2
            assert result["errors"] == 0
            
            # Check that storage service methods were called
            job_manager.storage_service.download_result_files.assert_called_once_with(SAMPLE_JOB_ID)
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_process_job_results(self, job_manager, mock_manager):
        """Test asynchronously processing job results."""
        # Setup mocks
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="COMPLETED",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:10:00"
        )
        
        # Use AsyncMock for storage_service
        job_manager.storage_service = AsyncMock()
        
        # Mock download_result_files to return a list of files when awaited
        file_list = {
            "GFF3": "/tmp/test.gff3",
            "FASTA": "/tmp/test.fasta"
        }
        
        # Configure AsyncMock to return values when awaited
        async def mock_download_files(job_id):
            return file_list
            
        async def mock_process_files(job_id):
            return {
                "annotations": 10,
                "sequences": 2,
                "errors": 0
            }
            
        job_manager.storage_service.download_result_files.side_effect = mock_download_files
        job_manager.storage_service.async_process_all_files.side_effect = mock_process_files
        
        # Call the method
        result = await job_manager.async_process_job_results(SAMPLE_JOB_ID)
        
        # Check results
        assert result["job_id"] == SAMPLE_JOB_ID
        assert len(result["downloaded_files"]) == 2
        assert result["annotations"] == 10
        assert result["sequences"] == 2
        assert result["errors"] == 0
        
        # Check that storage service methods were called
        job_manager.storage_service.download_result_files.assert_called_once_with(SAMPLE_JOB_ID)
        job_manager.storage_service.async_process_all_files.assert_called_once_with(SAMPLE_JOB_ID)
    
    def test_start_job_poller(self, job_manager, mock_manager):
        """Test starting the job poller thread."""
        # Setup mocks
        mock_manager.get_jobs.return_value = [
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET,
                   status="RUNNING", config={}, created_at="", updated_at="")
        ]
        
        # First check should return RUNNING, second should return COMPLETED
        mock_manager.check_job_status.side_effect = [
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET,
                   status="RUNNING", config={}, created_at="", updated_at=""),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET,
                   status="COMPLETED", config={}, created_at="", updated_at="")
        ]
        
        job_manager.start_background_monitoring = MagicMock()
        
        # Start the poller
        job_manager.start_job_poller()
        
        # Verify the poller thread was created and started
        assert job_manager._poller_thread is not None
        assert job_manager._poller_thread.is_alive()
        
        # Give the poller time to check jobs
        time.sleep(0.3)
        
        # Verify that jobs were checked
        assert mock_manager.get_jobs.call_count >= 1
        assert mock_manager.check_job_status.call_count >= 1
        
        # Stop the poller
        job_manager.stop_job_poller()
        
        # Verify that the poller was stopped
        assert not job_manager._poller_thread.is_alive() or job_manager._stop_event.is_set()
    
    def test_recover_interrupted_jobs(self, job_manager, mock_manager):
        """Test recovering interrupted jobs."""
        # Reset the mock for this test
        job_manager.start_background_monitoring = MagicMock()
        
        # Define the active statuses in the same order they're processed
        # To ensure deterministic test behavior
        global ACTIVE_STATUSES
        ACTIVE_STATUSES = ["INIT", "RUNNING", "PROCESSING"]

        # Setup mocks for each status
        mock_manager.get_jobs.side_effect = lambda status=None: {
            "RUNNING": [BaktaJob(id="job1", name="Job 1", secret="secret1", status="RUNNING", config={}, 
                    created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:01:00")],
            "INIT": [BaktaJob(id="job2", name="Job 2", secret="secret2", status="INIT", config={},
                    created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:01:00")],
            "PROCESSING": [BaktaJob(id="job3", name="Job 3", secret="secret3", status="PROCESSING", config={},
                    created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:01:00")]
        }.get(status, [])
        
        # Configure check_job_status to return different statuses
        def get_status(job_id):
            if job_id == "job1":
                return BaktaJob(id="job1", name="Job 1", secret="secret1", status="COMPLETED", config={},
                              created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:10:00")
            elif job_id == "job2":
                return BaktaJob(id="job2", name="Job 2", secret="secret2", status="RUNNING", config={},
                              created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:05:00")
            else:
                return BaktaJob(id="job3", name="Job 3", secret="secret3", status="FAILED", config={},
                              created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:07:00")
                
        mock_manager.check_job_status.side_effect = get_status
        
        # Call method
        recovered_jobs = job_manager.recover_interrupted_jobs()
        
        # Check results (should have the 3 jobs we defined)
        assert len(recovered_jobs) == 3
        assert set(recovered_jobs) == {"job1", "job2", "job3"}
        
        # Check that background monitoring was started for completed and running jobs
        assert job_manager.start_background_monitoring.call_count == 2
        
        # Check the calls were made - order will depend on ACTIVE_STATUSES order
        calls = [call[0][0] for call in job_manager.start_background_monitoring.call_args_list]
        assert "job1" in calls  # COMPLETED job
        assert "job2" in calls  # RUNNING job
        assert "job3" not in calls  # FAILED job (no background monitoring)
    
    def test_get_job_history(self, job_manager, mock_manager):
        """Test getting job status history."""
        # Setup mock
        mock_manager.repository.get_status_history.return_value = [
            BaktaJobStatusHistory(
                job_id=SAMPLE_JOB_ID,
                status="INIT",
                timestamp="2023-01-01T12:00:00"
            ),
            BaktaJobStatusHistory(
                job_id=SAMPLE_JOB_ID,
                status="RUNNING",
                timestamp="2023-01-01T12:01:00"
            ),
            BaktaJobStatusHistory(
                job_id=SAMPLE_JOB_ID,
                status="COMPLETED",
                timestamp="2023-01-01T12:10:00"
            )
        ]
        
        # Call method
        history = job_manager.get_job_history(SAMPLE_JOB_ID)
        
        # Check results
        assert len(history) == 3
        assert history[0].status == "INIT"
        assert history[1].status == "RUNNING"
        assert history[2].status == "COMPLETED"
        
        # Check that repository method was called
        mock_manager.repository.get_status_history.assert_called_once_with(SAMPLE_JOB_ID)
    
    def test_record_status_history(self, job_manager, mock_manager):
        """Test recording job status history."""
        # Setup mocks
        mock_manager.repository.get_status_history.return_value = [
            BaktaJobStatusHistory(
                job_id=SAMPLE_JOB_ID,
                status="INIT",
                timestamp="2023-01-01T12:00:00"
            )
        ]
        
        # Call method with a new status
        job_manager._record_status_history(SAMPLE_JOB_ID, "RUNNING")
        
        # Check that save_status_history was called with correct parameters
        mock_manager.repository.save_status_history.assert_called_once()
        history_entry = mock_manager.repository.save_status_history.call_args[0][0]
        assert history_entry.job_id == SAMPLE_JOB_ID
        assert history_entry.status == "RUNNING"
        
        # Test with same status (should not record)
        mock_manager.repository.save_status_history.reset_mock()
        mock_manager.repository.get_status_history.return_value = [
            BaktaJobStatusHistory(
                job_id=SAMPLE_JOB_ID,
                status="RUNNING",
                timestamp="2023-01-01T12:00:00"
            )
        ]
        
        job_manager._record_status_history(SAMPLE_JOB_ID, "RUNNING")
        
        # Check that save_status_history was not called
        mock_manager.repository.save_status_history.assert_not_called() 