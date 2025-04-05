#!/usr/bin/env python3
"""
Tests for the BaktaStorageService.
"""

import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from amr_predictor.bakta.storage import BaktaStorageService
from amr_predictor.bakta.exceptions import BaktaStorageError
from amr_predictor.bakta.models import (
    BaktaJob,
    BaktaResultFile,
    BaktaAnnotation,
    BaktaSequence
)

# Sample data for testing
SAMPLE_JOB_ID = "test-job-123"
SAMPLE_JOB_SECRET = "test-secret-456"
SAMPLE_CONTENT = ">contig1\nATGCATGCATGC"


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    mock = MagicMock()
    
    # Setup get_job to return a valid job
    mock.get_job.return_value = BaktaJob(
        id=SAMPLE_JOB_ID,
        name="Test Job",
        secret=SAMPLE_JOB_SECRET,
        status="COMPLETED",
        config={},
        created_at="2023-01-01T12:00:00",
        updated_at="2023-01-01T12:30:00"
    )
    
    # Setup get_result_files to return a list of result files
    mock.get_result_files.return_value = [
        BaktaResultFile(
            job_id=SAMPLE_JOB_ID,
            file_type="GFF3",
            file_path="/tmp/test.gff3",
            downloaded_at="2023-01-01T12:30:00"
        ),
        BaktaResultFile(
            job_id=SAMPLE_JOB_ID,
            file_type="FASTA",
            file_path="/tmp/test.fasta",
            downloaded_at="2023-01-01T12:30:00"
        )
    ]
    
    return mock


@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    mock = MagicMock()
    
    # Setup get_job_results to return a valid response
    mock.get_job_results.return_value = {
        "ResultFiles": {
            "GFF3": "https://example.com/test.gff3",
            "FASTA": "https://example.com/test.fasta"
        }
    }
    
    # Setup download_result_file to simulate successful download
    mock.download_result_file.return_value = True
    
    return mock


@pytest.fixture
def storage_service(mock_repository, mock_client):
    """Create a storage service for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        service = BaktaStorageService(
            repository=mock_repository,
            client=mock_client,
            results_dir=temp_dir
        )
        yield service


class TestBaktaStorageService:
    """Tests for the BaktaStorageService class."""
    
    def test_initialization(self, mock_repository, mock_client):
        """Test that the storage service initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BaktaStorageService(
                repository=mock_repository,
                client=mock_client,
                results_dir=temp_dir
            )
            
            assert service.repository == mock_repository
            assert service.client == mock_client
            assert service.results_dir == Path(temp_dir)
            assert not service.running
            assert len(service.workers) == 0
    
    def test_download_result_files(self, storage_service, mock_repository, mock_client):
        """Test downloading result files for a job."""
        with patch('amr_predictor.bakta.storage.Path.mkdir'):
            # Call the method
            result = storage_service.download_result_files(SAMPLE_JOB_ID)
            
            # Check that client methods were called with correct parameters
            mock_repository.get_job.assert_called_once_with(SAMPLE_JOB_ID)
            mock_client.get_job_results.assert_called_once_with(
                job_id=SAMPLE_JOB_ID,
                job_secret=SAMPLE_JOB_SECRET
            )
            
            # Check that download was attempted for each file
            assert mock_client.download_result_file.call_count == 2
            
            # Check that result files were saved in repository
            assert mock_repository.save_result_file.call_count == 2
            
            # Check that job status was updated
            mock_repository.update_job_status.assert_called_once_with(
                SAMPLE_JOB_ID, "PROCESSING"
            )
            
            # Check returned result
            assert len(result) == 2
            assert "GFF3" in result
            assert "FASTA" in result
    
    def test_download_result_files_with_filter(self, storage_service, mock_repository, mock_client):
        """Test downloading specific result files for a job."""
        with patch('amr_predictor.bakta.storage.Path.mkdir'):
            # Call the method with a filter
            result = storage_service.download_result_files(SAMPLE_JOB_ID, file_types=["GFF3"])
            
            # Check that only GFF3 file was downloaded
            assert len(result) == 1
            assert "GFF3" in result
            assert "FASTA" not in result
    
    def test_download_result_files_error(self, storage_service, mock_repository, mock_client):
        """Test error handling when downloading result files."""
        # Make get_job return None to simulate job not found
        mock_repository.get_job.return_value = None
        
        # Call the method and expect an error
        with pytest.raises(BaktaStorageError, match="Job not found"):
            storage_service.download_result_files(SAMPLE_JOB_ID)
    
    def test_start_stop_workers(self, storage_service):
        """Test starting and stopping worker threads."""
        # Start workers
        storage_service.start_workers()
        
        # Check that workers are running
        assert storage_service.running
        assert len(storage_service.workers) == storage_service.num_workers
        
        # Stop workers
        storage_service.stop_workers()
        
        # Check that workers have stopped
        assert not storage_service.running
    
    def test_queue_file_for_processing(self, storage_service):
        """Test queueing a file for processing."""
        # Mock the start_workers method
        storage_service.start_workers = MagicMock()
        
        # Call the method
        storage_service.queue_file_for_processing(
            job_id=SAMPLE_JOB_ID,
            file_path="/tmp/test.gff3",
            file_type="GFF3"
        )
        
        # Check that workers were started
        storage_service.start_workers.assert_called_once()
        
        # Check that file was added to queue
        assert storage_service.queue.qsize() == 1
    
    @patch('amr_predictor.bakta.storage.get_parser_for_file')
    @patch('amr_predictor.bakta.storage.get_transformer_for_format')
    def test_process_file(self, mock_get_transformer, mock_get_parser, storage_service):
        """Test processing a single file."""
        # Create mock parser and transformer
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {"format": "gff3", "features": []}
        
        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = [
            BaktaAnnotation(
                job_id=SAMPLE_JOB_ID,
                feature_id="gene1",
                feature_type="gene",
                contig="contig1",
                start=100,
                end=300,
                strand="+",
                attributes={}
            )
        ]
        
        # Setup mocks
        mock_get_parser.return_value = mock_parser
        mock_get_transformer.return_value = mock_transformer
        
        # Call the method
        storage_service._process_file(
            job_id=SAMPLE_JOB_ID,
            file_path="/tmp/test.gff3",
            file_type="GFF3"
        )
        
        # Check that parser and transformer were called
        mock_get_parser.assert_called_once_with("/tmp/test.gff3")
        mock_parser.parse.assert_called_once()
        mock_get_transformer.assert_called_once_with("gff3", SAMPLE_JOB_ID)
        mock_transformer.transform.assert_called_once_with({"format": "gff3", "features": []})
        
        # Check that annotations were saved
        storage_service.repository.save_annotations.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_process_all_files(self, storage_service, mock_repository):
        """Test processing all result files for a job asynchronously."""
        # Create mock for _async_process_file with AsyncMock
        from unittest.mock import AsyncMock
        
        # Create a proper async mock that returns a result
        mock_result = {"annotations": 10, "sequences": 0}
        storage_service._async_process_file = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await storage_service.async_process_all_files(SAMPLE_JOB_ID)
        
        # Check that repository methods were called
        mock_repository.get_result_files.assert_called_once_with(SAMPLE_JOB_ID)
        
        # Check that _async_process_file was called for each file
        assert storage_service._async_process_file.call_count == 2
        
        # Check that job status was updated
        mock_repository.update_job_status.assert_called_once_with(
            SAMPLE_JOB_ID, "PROCESSED"
        )
        
        # Check returned result
        assert result["annotations"] == 20  # 10 from each file
        assert result["sequences"] == 0
        assert result["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_async_process_file(self, storage_service):
        """Test processing a single file asynchronously."""
        # Need to patch several functions
        with patch('amr_predictor.bakta.storage.get_parser_for_file') as mock_get_parser, \
             patch('amr_predictor.bakta.storage.get_transformer_for_format') as mock_get_transformer, \
             patch('asyncio.to_thread') as mock_to_thread:
            
            # Create mock parser and transformer
            mock_parser = MagicMock()
            mock_parser.parse.return_value = {"format": "fasta", "sequences": []}
            
            mock_transformer = MagicMock()
            mock_transformer.transform.return_value = [
                BaktaSequence(
                    job_id=SAMPLE_JOB_ID,
                    header="contig1",
                    sequence="ATGC",
                    length=4
                )
            ]
            
            # Setup mocks
            mock_get_parser.return_value = mock_parser
            mock_get_transformer.return_value = mock_transformer
            mock_to_thread.return_value = None
            
            # Call the method
            result = await storage_service._async_process_file(
                job_id=SAMPLE_JOB_ID,
                file_path="/tmp/test.fasta",
                file_type="FASTA"
            )
            
            # Check that parser and transformer were called
            mock_get_parser.assert_called_once_with("/tmp/test.fasta")
            mock_parser.parse.assert_called_once()
            mock_get_transformer.assert_called_once_with("fasta", SAMPLE_JOB_ID)
            mock_transformer.transform.assert_called_once_with({"format": "fasta", "sequences": []})
            
            # Check that to_thread was called to save sequences
            assert mock_to_thread.called
            
            # Check returned result
            assert result["sequences"] == 1 