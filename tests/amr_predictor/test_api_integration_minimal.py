"""Minimal integration test module for AMR API components."""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock, AsyncMock

from amr_predictor.api.jobs import JobManager, JobRequest, Job, JobStatus, JobType
from amr_predictor.monitoring.metrics import MetricsTracker, OperationMetric

class TestIntegration:
    """Test interactions between different components of the AMR API."""
    
    @pytest.fixture
    def metrics_tracker(self):
        """Create a MetricsTracker instance for testing."""
        return MetricsTracker(max_history=100)
    
    @pytest.fixture
    def job_manager(self):
        """Create a JobManager instance for testing."""
        return JobManager()
    
    @pytest.mark.asyncio
    async def test_job_processing_with_metrics(self, job_manager, metrics_tracker):
        """Test that job processing operations are tracked in metrics."""
        # Create a job request
        job_request = JobRequest(
            job_type=JobType.PREDICTION,
            parameters={"sequence": "ATCG"},
            priority=1,
            timeout=60
        )
        
        # Create a job
        job = await job_manager.create_job(job_request)
        
        # Override the _process_job method to record metrics
        original_process_job = job_manager._process_job
        
        async def mock_process_with_metrics(job_obj):
            """Wrap job processing with metrics tracking."""
            start_time = datetime.now(UTC)
            try:
                # Record the start of the operation
                operation_name = f"process_{job_obj.job_type.value}_job"
                
                # Simulate some processing time
                await asyncio.sleep(0.1)
                
                # Call the original method
                await original_process_job(job_obj)
                
                # Mark as success
                success = True
                error_message = None
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Calculate duration in milliseconds
                end_time = datetime.now(UTC)
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # Record the operation in metrics
                metrics_tracker.record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_message
                )
        
        # Replace the method temporarily
        with patch.object(job_manager, '_process_job', side_effect=mock_process_with_metrics):
            # Process the job
            await job_manager.process_job(job.id)
            
            # Verify job was processed
            processed_job = await job_manager.get_job(job.id)
            assert processed_job.status == JobStatus.COMPLETED
            
            # Verify metrics were recorded
            operation_name = f"process_{job.job_type.value}_job"
            metrics = metrics_tracker.get_metrics(operation_name)
            
            assert len(metrics) == 1
            assert metrics[0].operation_name == operation_name
            assert metrics[0].success is True
            assert metrics[0].duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_with_metrics(self, job_manager, metrics_tracker):
        """Test error handling during job processing with metrics recording."""
        # Create a job
        job_request = JobRequest(
            job_type=JobType.PREDICTION,
            parameters={"sequence": "INVALID"},
            priority=1
        )
        job = await job_manager.create_job(job_request)
        
        # Override processing to simulate an error and record metrics
        async def mock_process_with_error(job_obj):
            """Simulate processing error and record metrics."""
            start_time = datetime.now(UTC)
            operation_name = f"process_{job_obj.job_type.value}_job"
            
            try:
                # Simulate processing that fails
                await asyncio.sleep(0.1)
                raise ValueError("Invalid sequence data")
            except Exception as e:
                # Handle the error in job
                job_obj.status = JobStatus.FAILED
                job_obj.error = str(e)
                job_obj.completed_at = datetime.now(UTC)
                
                # Record in metrics
                duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                metrics_tracker.record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
                
                # Don't re-raise, just simulate the job failing but API handling it
        
        # Patch the method
        with patch.object(job_manager, '_process_job', side_effect=mock_process_with_error):
            # Process job
            await job_manager.process_job(job.id)
            
            # Verify job status
            failed_job = await job_manager.get_job(job.id)
            assert failed_job.status == JobStatus.FAILED
            assert "Invalid sequence data" in failed_job.error
            
            # Verify metrics were recorded with error
            operation_name = f"process_{job.job_type.value}_job"
            metrics = metrics_tracker.get_metrics(operation_name)
            
            assert len(metrics) == 1
            assert metrics[0].operation_name == operation_name
            assert metrics[0].success is False
            assert "Invalid sequence data" in metrics[0].error_message
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_metrics(self, job_manager, metrics_tracker):
        """Test batch processing of multiple jobs with metrics tracking."""
        # Create multiple jobs
        job_requests = [
            JobRequest(job_type=JobType.PREDICTION, parameters={"seq": f"seq_{i}"}, priority=1)
            for i in range(3)
        ]
        
        jobs = []
        for req in job_requests:
            job = await job_manager.create_job(req)
            jobs.append(job)
        
        # Track batch operation metrics
        batch_start_time = datetime.now(UTC)
        processed_count = 0
        error_count = 0
        
        # Process each job with metrics
        for job in jobs:
            start_time = datetime.now(UTC)
            operation_name = f"process_{job.job_type.value}_job"
            
            try:
                # Mark job as processing
                job_manager._jobs[job.id].status = JobStatus.PROCESSING
                job_manager._jobs[job.id].started_at = datetime.now(UTC)
                
                # Simulate processing
                await asyncio.sleep(0.05)
                
                # Complete job
                job_manager._jobs[job.id].status = JobStatus.COMPLETED
                job_manager._jobs[job.id].completed_at = datetime.now(UTC)
                job_manager._jobs[job.id].result = {"result": f"Result for {job.id}"}
                job_manager._jobs[job.id].progress = 1.0
                
                processed_count += 1
                success = True
                error_message = None
            except Exception as e:
                job_manager._jobs[job.id].status = JobStatus.FAILED
                job_manager._jobs[job.id].error = str(e)
                job_manager._jobs[job.id].completed_at = datetime.now(UTC)
                
                error_count += 1
                success = False
                error_message = str(e)
            finally:
                # Record individual job metrics
                duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                metrics_tracker.record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_message
                )
        
        # Record overall batch metrics
        batch_duration_ms = (datetime.now(UTC) - batch_start_time).total_seconds() * 1000
        metrics_tracker.record_operation(
            operation_name="batch_process_jobs",
            duration_ms=batch_duration_ms,
            success=(error_count == 0),
            error_message=f"Processed {processed_count} jobs with {error_count} errors" if error_count > 0 else None
        )
        
        # Verify all jobs were processed correctly
        for job_id in [job.id for job in jobs]:
            processed_job = await job_manager.get_job(job_id)
            assert processed_job.status == JobStatus.COMPLETED
            assert processed_job.result is not None
        
        # Verify individual job metrics
        prediction_metrics = metrics_tracker.get_metrics("process_prediction_job")
        assert len(prediction_metrics) == 3
        for metric in prediction_metrics:
            assert metric.success is True
            
        # Verify batch metrics
        batch_metrics = metrics_tracker.get_metrics("batch_process_jobs")
        assert len(batch_metrics) == 1
        assert batch_metrics[0].success is True
