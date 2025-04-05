"""End-to-end job lifecycle tests for the Bakta API integration.

These tests verify the complete job lifecycle, including:
- End-to-end job processing
- Recovery from simulated failures
- Concurrent job submission and processing
- Job state transition tracking
"""

import asyncio
import concurrent.futures
import os
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from amr_predictor.bakta import (
    BaktaJobManager,
    BaktaManager,
    BaktaClient,
    BaktaJob,
    BaktaStorageService,
    create_config,
    validate_fasta,
    BaktaApiError,
    BaktaManagerError
)

# Sample test data
SAMPLE_JOB_ID = "test-job-123"
SAMPLE_JOB_SECRET = "test-secret-456"
SAMPLE_FASTA_CONTENT = """>contig1 Test sequence
ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA
CCCAGGCTTACCTGAACAACGGTTAATAGCCGCGCCGGTCGCGTCCCATCCCGGCCAGCGTTAACG
GCGGTTTGCAGCTGTTGCATGATGAACAAAGCAACAACAACGACAATCTGCGCGTTCGTTACGCAG
GTGTTTCGATACAGCCTGGCAAGTTCGCGCGAGAAACCGAATCCCGTCTTCACGCGGGTACCGAGA
TCCTGATGTCCGAACAATGGTTCCTGGCGGTTAGCCAGACCACCGATCTGCGTGACGGTCTGTACC
AGACCCGTCAGCAGTTCGAAGCACAGGCTCAAACGTCAGGCAGCAGCGTCTAACGTGAAAGCCGGG
GCTGAAAACGTCTACCTGACGGTAATGTCTGCTCCGAATAACAGCGCATTACCTTATGCGGACCAT
TTCTCCGGTTCCGGCCTGCAATCCGTGTTCGATAACGCGCTGATGCGTCGTATTGCCGGACAGGGT
TGGTAA
"""

@pytest.fixture
def mock_manager():
    """Create a mock BaktaManager for testing."""
    mock = MagicMock(spec=BaktaManager)
    mock.client = MagicMock(spec=BaktaClient)
    mock.repository = MagicMock()
    mock.results_dir = Path("/tmp/bakta_results")
    return mock

@pytest.fixture
def sample_fasta_file():
    """Create a temporary FASTA file with test sequence."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(SAMPLE_FASTA_CONTENT)
        fasta_path = Path(f.name)
    yield fasta_path
    if fasta_path.exists():
        fasta_path.unlink()

@pytest.fixture
def job_manager(mock_manager):
    """Create a BaktaJobManager for testing."""
    manager = BaktaJobManager(
        base_manager=mock_manager,
        poll_interval=0.1,  # Use a short poll interval for faster tests
        max_retries=3
    )
    manager.storage_service = MagicMock(spec=BaktaStorageService)
    yield manager
    manager.stop_job_poller()

class TestEndToEndJobProcessing:
    """Tests for end-to-end job processing."""
    
    def test_complete_job_lifecycle(self, job_manager, mock_manager, sample_fasta_file):
        """Test the complete job lifecycle from submission to result processing."""
        # Mock the manager responses
        job_id = SAMPLE_JOB_ID
        secret = SAMPLE_JOB_SECRET
        
        # Mock repository to return current job status
        stored_status = {"current": None}
        def get_job(job_id):
            job = MagicMock()
            job.status = stored_status["current"]
            return job
        mock_manager.repository.get_job.side_effect = get_job
        
        def update_job_status(job_id, status):
            stored_status["current"] = status
            return MagicMock(id=job_id, status=status)
        mock_manager.repository.update_job_status.side_effect = update_job_status
        
        # Mock create_job to return a job object
        mock_manager.create_job.return_value = BaktaJob(
            id=job_id,
            name="Test Job",
            secret=secret,
            status="INIT",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:00:00"
        )
        
        # Mock start_job to return a running job
        mock_manager.start_job.return_value = BaktaJob(
            id=job_id,
            name="Test Job",
            secret=secret,
            status="RUNNING",
            config={},
            created_at="2023-01-01T12:00:00",
            updated_at="2023-01-01T12:01:00"
        )
        
        # Mock check_job_status to simulate a job completing after a few checks
        status_sequence = [
            BaktaJob(id=job_id, name="Test Job", secret=secret, status="RUNNING", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:01:00"),
            BaktaJob(id=job_id, name="Test Job", secret=secret, status="RUNNING", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:02:00"),
            BaktaJob(id=job_id, name="Test Job", secret=secret, status="COMPLETED", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:03:00")
        ]
        mock_manager.check_job_status.side_effect = status_sequence
        
        # Mock process_job_results
        job_manager.process_job_results = MagicMock()
        
        # Configure test to track status changes
        status_changes = []
        def status_callback(job_id, old_status, new_status):
            status_changes.append((job_id, old_status, new_status))
        
        job_manager.set_notification_callback(status_callback)
        
        # Submit the job
        config = create_config(genus="Test", species="example", strain="strain1")
        result = job_manager.submit_job(
            fasta_path=str(sample_fasta_file),
            name="Test Job",
            config=config,
            wait_for_completion=True,
            process_results=True
        )
        
        # Verify the job was created, started, and monitored
        assert result.id == job_id
        assert result.status == "COMPLETED"
        
        # Verify the manager methods were called
        mock_manager.create_job.assert_called_once()
        mock_manager.start_job.assert_called_once_with(job_id)
        assert mock_manager.check_job_status.call_count == 3
        
        # We expect status transitions to be tracked
        assert len(status_changes) > 0
        
        # The last status change should be to COMPLETED
        assert status_changes[-1][2] == "COMPLETED"
        
        # Verify results were processed
        job_manager.process_job_results.assert_called_once_with(job_id)

class TestRecoveryMechanisms:
    """Tests for failure recovery mechanisms."""
    
    def test_transient_api_error_recovery(self, job_manager, mock_manager):
        """Test recovery from transient API errors."""
        # Mock check_job_status to fail twice then succeed
        mock_manager.check_job_status.side_effect = [
            BaktaApiError("Temporary connection error"),
            BaktaApiError("Temporary connection error"),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test Job", secret=SAMPLE_JOB_SECRET, 
                   status="COMPLETED", config={}, created_at="", updated_at="")
        ]
        
        # Call the method with retry enabled
        job = job_manager.check_job_status(SAMPLE_JOB_ID)
        
        # Verify the method was retried and eventually succeeded
        assert job.id == SAMPLE_JOB_ID
        assert job.status == "COMPLETED"
        assert mock_manager.check_job_status.call_count == 3
    
    def test_job_interrupt_recovery(self, job_manager, mock_manager):
        """Test recovery of interrupted jobs."""
        # Set up mocks for interrupted jobs in different states
        mock_manager.get_jobs.side_effect = lambda status=None: {
            "RUNNING": [BaktaJob(id="job1", name="Job 1", secret="secret1", status="RUNNING", 
                               config={}, created_at="", updated_at="")],
            "INIT": [BaktaJob(id="job2", name="Job 2", secret="secret2", status="INIT", 
                            config={}, created_at="", updated_at="")]
        }.get(status, [])
        
        # Setup status checks to return different statuses
        def get_status(job_id):
            if job_id == "job1":
                return BaktaJob(id="job1", name="Job 1", secret="secret1", status="COMPLETED", 
                              config={}, created_at="", updated_at="")
            else:
                return BaktaJob(id="job2", name="Job 2", secret="secret2", status="RUNNING", 
                              config={}, created_at="", updated_at="")
        
        mock_manager.check_job_status.side_effect = get_status
        
        # Mock the background monitoring method
        job_manager.start_background_monitoring = MagicMock()
        
        # Test the recovery method
        recovered_jobs = job_manager.recover_interrupted_jobs()
        
        # Verify jobs were recovered correctly
        assert len(recovered_jobs) == 2
        assert "job1" in recovered_jobs
        assert "job2" in recovered_jobs
        
        # Verify that background monitoring was started for the jobs
        assert job_manager.start_background_monitoring.call_count == 2
    
    def test_retry_failed_job(self, job_manager, mock_manager):
        """Test retrying a failed job."""
        # Set up a failed job
        failed_job = BaktaJob(id=SAMPLE_JOB_ID, name="Failed Job", secret=SAMPLE_JOB_SECRET, 
                            status="FAILED", config={}, created_at="", updated_at="")
        mock_manager.check_job_status.return_value = failed_job
        
        # Mock status update
        mock_manager.repository.update_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID, name="Failed Job", secret=SAMPLE_JOB_SECRET, 
            status="INIT", config={}, created_at="", updated_at=""
        )
        
        # Mock the job restart
        mock_manager.start_job.return_value = BaktaJob(
            id=SAMPLE_JOB_ID, name="Failed Job", secret=SAMPLE_JOB_SECRET, 
            status="RUNNING", config={}, created_at="", updated_at=""
        )
        
        # Mock background monitoring
        job_manager.start_background_monitoring = MagicMock()
        
        # Retry the failed job
        result = job_manager.retry_failed_job(SAMPLE_JOB_ID)
        
        # Verify the job was retried correctly
        assert result.id == SAMPLE_JOB_ID
        assert result.status == "RUNNING"
        
        # Verify the right methods were called
        mock_manager.repository.update_job_status.assert_called_once_with(
            job_id=SAMPLE_JOB_ID, status="INIT"
        )
        mock_manager.start_job.assert_called_once_with(SAMPLE_JOB_ID)
        job_manager.start_background_monitoring.assert_called_once_with(SAMPLE_JOB_ID, process_results=True)

class TestConcurrentProcessing:
    """Tests for concurrent job processing."""
    
    def test_concurrent_job_submission(self, job_manager, mock_manager, sample_fasta_file):
        """Test submitting multiple jobs concurrently."""
        # Mock the manager methods to handle multiple jobs
        job_counter = 0
        
        def create_job(fasta_path, name, config):
            nonlocal job_counter
            job_counter += 1
            return BaktaJob(
                id=f"job-{job_counter}",
                name=name,
                secret=f"secret-{job_counter}",
                status="INIT",
                config=config,
                created_at="2023-01-01T12:00:00",
                updated_at="2023-01-01T12:00:00"
            )
        
        def start_job(job_id):
            return BaktaJob(
                id=job_id,
                name=f"Test Job {job_id}",
                secret=f"secret-{job_id.split('-')[1]}",
                status="RUNNING",
                config={},
                created_at="2023-01-01T12:00:00", 
                updated_at="2023-01-01T12:01:00"
            )
        
        mock_manager.create_job.side_effect = create_job
        mock_manager.start_job.side_effect = start_job
        job_manager.start_background_monitoring = MagicMock()
        
        # Create config
        config = create_config(genus="Test", species="example")
        
        # Submit multiple jobs concurrently
        jobs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    job_manager.submit_job,
                    fasta_path=str(sample_fasta_file),
                    name=f"Concurrent Job {i}",
                    config=config,
                    wait_for_completion=False,
                    process_results=True
                )
                for i in range(3)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                jobs.append(future.result())
        
        # Verify all jobs were created and started
        assert len(jobs) == 3
        assert len({job.id for job in jobs}) == 3  # All jobs have unique IDs
        assert all(job.status == "RUNNING" for job in jobs)
        
        # Verify methods were called the right number of times
        assert mock_manager.create_job.call_count == 3
        assert mock_manager.start_job.call_count == 3
        assert job_manager.start_background_monitoring.call_count == 3
    
    def test_job_poller_with_multiple_jobs(self, job_manager, mock_manager):
        """Test the job poller handling multiple active jobs."""
        # Use a separate test class to reset state
        job_manager.stop_job_poller()  # Make sure poller is stopped
        
        # Setup active jobs
        active_jobs = [
            BaktaJob(id=f"job-{i}", name=f"Job {i}", secret=f"secret-{i}", 
                   status="RUNNING", config={}, created_at="", updated_at="")
            for i in range(3)
        ]
        
        # Track jobs currently being polled
        active_job_set = {"job-0", "job-1", "job-2"}
        
        # Mock get_jobs to return active jobs, but remove them once "completed"
        def get_active_jobs(status=None):
            return [job for job in active_jobs if job.id in active_job_set and job.status == status]
            
        mock_manager.get_jobs.side_effect = get_active_jobs
        
        # Track job completions
        completed_jobs = set()
        
        # Mock check_job_status to simulate jobs completing one after the other
        def check_status(job_id):
            # Immediately complete job-0, but delay others
            if job_id == "job-0" or job_id in completed_jobs:
                completed_jobs.add(job_id)
                return BaktaJob(id=job_id, name=f"Job {job_id}", secret="secret",
                              status="COMPLETED", config={}, created_at="", updated_at="")
            else:
                return BaktaJob(id=job_id, name=f"Job {job_id}", secret="secret",
                              status="RUNNING", config={}, created_at="", updated_at="")
        
        mock_manager.check_job_status.side_effect = check_status
        
        # Mock background monitoring to mark jobs as processed
        def start_monitoring(job_id, process_results):
            # Remove job from active set after a short delay
            time.sleep(0.1)
            active_job_set.remove(job_id)
            completed_jobs.add(job_id)
            
        job_manager.start_background_monitoring = MagicMock(side_effect=start_monitoring)
        
        # Start with a shorter poll interval
        job_manager.poll_interval = 0.1
        
        # Start the poller
        job_manager.start_job_poller()
        
        # Wait for first job to be processed
        time.sleep(0.3)
        
        # Stop the poller before we check results
        job_manager.stop_job_poller()
        
        # Verify at least one job was processed
        assert job_manager.start_background_monitoring.call_count >= 1
        
        # Verify at least job-0 was processed
        processed_jobs = {call[0][0] for call in job_manager.start_background_monitoring.call_args_list}
        assert "job-0" in processed_jobs

@pytest.mark.asyncio
class TestAsyncProcessing:
    """Tests for asynchronous processing."""
    
    async def test_async_process_job_results(self, job_manager, mock_manager):
        """Test asynchronous processing of job results."""
        # Setup completed job
        mock_manager.check_job_status.return_value = BaktaJob(
            id=SAMPLE_JOB_ID,
            name="Test Job",
            secret=SAMPLE_JOB_SECRET,
            status="COMPLETED",
            config={},
            created_at="",
            updated_at=""
        )
        
        # Setup storage service
        storage_service = AsyncMock()
        
        async def mock_download_files(job_id):
            return {
                "GFF3": "/path/to/results/file.gff3",
                "JSON": "/path/to/results/file.json",
                "FASTA": "/path/to/results/file.fasta"
            }
        
        async def mock_process_files(job_id):
            return {
                "annotations": 15,
                "sequences": 2,
                "errors": 0
            }
            
        storage_service.download_result_files.side_effect = mock_download_files
        storage_service.async_process_all_files.side_effect = mock_process_files
        
        job_manager.storage_service = storage_service
        
        # Call the async method
        result = await job_manager.async_process_job_results(SAMPLE_JOB_ID)
        
        # Verify the result
        assert result["job_id"] == SAMPLE_JOB_ID
        assert len(result["downloaded_files"]) == 3
        assert result["annotations"] == 15
        assert result["sequences"] == 2
        assert result["errors"] == 0
        
        # Verify that storage service methods were called
        storage_service.download_result_files.assert_called_once_with(SAMPLE_JOB_ID)
        storage_service.async_process_all_files.assert_called_once_with(SAMPLE_JOB_ID)

class TestStateTracking:
    """Tests for job state tracking."""
    
    def test_job_status_history(self, job_manager, mock_manager):
        """Test tracking of job status changes."""
        # Setup mock history
        history_entries = [
            {"job_id": SAMPLE_JOB_ID, "status": "INIT", "timestamp": "2023-01-01T12:00:00"},
            {"job_id": SAMPLE_JOB_ID, "status": "RUNNING", "timestamp": "2023-01-01T12:01:00"},
            {"job_id": SAMPLE_JOB_ID, "status": "COMPLETED", "timestamp": "2023-01-01T12:10:00"}
        ]
        
        mock_manager.repository.get_status_history.return_value = [
            MagicMock(job_id=entry["job_id"], status=entry["status"], timestamp=entry["timestamp"])
            for entry in history_entries
        ]
        
        # Get the job history
        history = job_manager.get_job_history(SAMPLE_JOB_ID)
        
        # Verify history was retrieved
        assert len(history) == 3
        assert [h.status for h in history] == ["INIT", "RUNNING", "COMPLETED"]
        
        # Test recording a new status
        mock_manager.repository.get_status_history.return_value = [
            MagicMock(job_id=SAMPLE_JOB_ID, status="COMPLETED", timestamp="2023-01-01T12:10:00")
        ]
        
        # Record a new status (should be added)
        job_manager._record_status_history(SAMPLE_JOB_ID, "PROCESSED")
        
        # Verify status was recorded
        mock_manager.repository.save_status_history.assert_called_once()
        history_entry = mock_manager.repository.save_status_history.call_args[0][0]
        assert history_entry.job_id == SAMPLE_JOB_ID
        assert history_entry.status == "PROCESSED"
        
        # Record same status again (should not be added)
        mock_manager.repository.save_status_history.reset_mock()
        mock_manager.repository.get_status_history.return_value = [
            MagicMock(job_id=SAMPLE_JOB_ID, status="PROCESSED", timestamp="2023-01-01T12:15:00")
        ]
        
        job_manager._record_status_history(SAMPLE_JOB_ID, "PROCESSED")
        mock_manager.repository.save_status_history.assert_not_called()
    
    def test_notification_system(self, job_manager, mock_manager):
        """Test the status change notification system."""
        # Setup callback
        callback_calls = []
        def status_callback(job_id, old_status, new_status):
            callback_calls.append((job_id, old_status, new_status))
        
        job_manager.set_notification_callback(status_callback)
        
        # Mock status changes
        mock_manager.check_job_status.side_effect = [
            BaktaJob(id=SAMPLE_JOB_ID, name="Test", secret="secret", status="INIT", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:00:00"),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test", secret="secret", status="RUNNING", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:01:00"),
            BaktaJob(id=SAMPLE_JOB_ID, name="Test", secret="secret", status="COMPLETED", 
                   config={}, created_at="2023-01-01T12:00:00", updated_at="2023-01-01T12:02:00")
        ]
        
        # Setup repository to track the current status
        stored_status = {"current": None}
        def get_job(job_id):
            job = MagicMock()
            job.status = stored_status["current"]
            return job
        mock_manager.repository.get_job.side_effect = get_job
        
        def update_job_status(job_id, status):
            stored_status["current"] = status
            return MagicMock(id=job_id, status=status)
        mock_manager.repository.update_job_status.side_effect = update_job_status
        
        # Check status multiple times to trigger transitions
        for _ in range(3):
            job_manager.check_job_status(SAMPLE_JOB_ID)
        
        # Verify callbacks were triggered for status changes
        assert len(callback_calls) > 0
        
        # Verify the final status is COMPLETED
        assert callback_calls[-1][2] == "COMPLETED" 