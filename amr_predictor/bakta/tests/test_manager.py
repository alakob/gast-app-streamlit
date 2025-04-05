#!/usr/bin/env python3
"""
Tests for the Bakta manager module.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from amr_predictor.bakta.manager import BaktaManager, BaktaManagerError
from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.models import (
    BaktaJob, BaktaSequence, BaktaResultFile, BaktaAnnotation, BaktaResult
)
from amr_predictor.bakta.repository import BaktaRepository, RepositoryError
from amr_predictor.bakta.exceptions import BaktaValidationError, BaktaClientError

# Sample data for testing
SAMPLE_FASTA = """>contig1
ATGCATGCATGC
>contig2
GCTAGCTAGCTA
"""

SAMPLE_CONFIG = {
    "genus": "Escherichia",
    "species": "coli",
    "strain": "K-12",
    "completeGenome": True,
    "translationTable": 11
}

@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def temp_fasta_file(temp_dir):
    """Create a temporary FASTA file."""
    fasta_path = temp_dir / "test.fasta"
    with open(fasta_path, "w") as f:
        f.write(SAMPLE_FASTA)
    return fasta_path

@pytest.fixture
def mock_client():
    """Create a mock BaktaClient."""
    client = Mock(spec=BaktaClient)
    
    # Mock successful job initialization
    client.initialize_job.return_value = {
        "job": {
            "jobID": "test-job-123",
            "secret": "test-secret-456"
        },
        "uploadLinkFasta": "https://example.com/upload/fasta"
    }
    
    # Mock successful upload
    client.upload_fasta.return_value = True
    
    # Mock successful job start
    client.start_job.return_value = {"status": "success"}
    
    # Mock job status
    client.check_job_status.return_value = {
        "jobs": [
            {
                "jobID": "test-job-123", 
                "jobStatus": "COMPLETED"
            }
        ]
    }
    
    # Mock job results
    client.get_job_results.return_value = {
        "jobID": "test-job-123",
        "ResultFiles": {
            "gff3": "https://example.com/results/output.gff3",
            "json": "https://example.com/results/output.json"
        }
    }
    
    # Mock downloading result files
    client.download_result_file.return_value = "/path/to/downloaded/file"
    
    return client

@pytest.fixture
def mock_repository():
    """Create a mock BaktaRepository."""
    repo = Mock(spec=BaktaRepository)
    
    # Mock existing job retrieval
    repo.get_job.return_value = None
    
    # Mock successful job saving
    repo.save_job.return_value = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Mock successful sequences saving
    repo.save_sequences.return_value = [
        BaktaSequence(
            job_id="test-job-123",
            header="contig1",
            sequence="ATGCATGCATGC",
            length=12
        )
    ]
    
    # Mock successful job status update
    repo.update_job_status.return_value = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="RUNNING",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Mock successful result file saving
    repo.save_result_file.return_value = BaktaResultFile(
        job_id="test-job-123",
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        downloaded_at="2023-01-02T00:00:00"
    )
    
    # Mock successful annotations saving
    repo.save_annotations.return_value = True
    
    # Mock successful complete result retrieval
    repo.get_complete_result.return_value = BaktaResult(
        job=BaktaJob(
            id="test-job-123",
            name="Test Job",
            secret="test-secret-456",
            status="COMPLETED",
            config=SAMPLE_CONFIG,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-02T00:00:00"
        ),
        sequences=[
            BaktaSequence(
                job_id="test-job-123",
                header="contig1",
                sequence="ATGCATGCATGC",
                length=12
            )
        ],
        annotations=[
            BaktaAnnotation(
                job_id="test-job-123",
                feature_id="gene1",
                feature_type="CDS",
                contig="contig1",
                start=10,
                end=100,
                strand="+",
                attributes={"product": "hypothetical protein"}
            )
        ],
        result_files=[
            BaktaResultFile(
                job_id="test-job-123",
                file_type="GFF3",
                file_path="/path/to/results/output.gff3",
                downloaded_at="2023-01-02T00:00:00"
            )
        ]
    )
    
    return repo

@pytest.fixture
def manager(mock_client, mock_repository, temp_dir):
    """Create a BaktaManager with mock dependencies."""
    return BaktaManager(
        client=mock_client,
        repository=mock_repository,
        results_dir=temp_dir
    )

def test_manager_initialization():
    """Test manager initialization with default parameters."""
    # Test with default parameters
    manager = BaktaManager()
    assert isinstance(manager.client, BaktaClient)
    assert isinstance(manager.repository, BaktaRepository)
    assert manager.results_dir is not None
    
    # Test with custom parameters
    client = Mock(spec=BaktaClient)
    repo = Mock(spec=BaktaRepository)
    results_dir = tempfile.mkdtemp()
    
    manager = BaktaManager(client=client, repository=repo, results_dir=results_dir)
    assert manager.client is client
    assert manager.repository is repo
    assert manager.results_dir == Path(results_dir)
    
    # Clean up
    os.rmdir(results_dir)

def test_create_job(manager, temp_fasta_file):
    """Test job creation."""
    # Update mock result to include fasta_path
    manager.repository.save_job.return_value = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        fasta_path=str(temp_fasta_file)
    )
    
    # Create job
    job = manager.create_job(
        fasta_path=temp_fasta_file,
        name="Test Job",
        config=SAMPLE_CONFIG
    )
    
    # Verify client was called
    manager.client.initialize_job.assert_called_once()
    
    # Verify repository was called
    manager.repository.save_job.assert_called_once()
    manager.repository.save_sequences_from_file.assert_called_once_with(
        job_id=job.id,
        fasta_path=str(temp_fasta_file)
    )
    
    # Verify job attributes
    assert job.id == "test-job-123"
    assert job.name == "Test Job"
    assert job.secret == "test-secret-456"
    assert job.status == "INIT"
    assert job.config == SAMPLE_CONFIG
    assert job.fasta_path == str(temp_fasta_file)

def test_create_job_with_fasta_string(manager):
    """Test job creation with a FASTA string instead of a file."""
    # Create job
    job = manager.create_job_with_fasta_string(
        fasta_string=SAMPLE_FASTA,
        name="Test Job",
        config=SAMPLE_CONFIG
    )
    
    # Verify client was called
    manager.client.initialize_job.assert_called_once()
    
    # Verify repository was called
    manager.repository.save_job.assert_called_once()
    manager.repository.save_sequences.assert_called_once_with(
        job_id=job.id,
        fasta_string=SAMPLE_FASTA
    )
    
    # Verify job attributes
    assert job.id == "test-job-123"
    assert job.name == "Test Job"
    assert job.secret == "test-secret-456"
    assert job.status == "INIT"
    assert job.config == SAMPLE_CONFIG

def test_start_job(manager):
    """Test starting a job."""
    # Setup mock job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        fasta_path="/path/to/fasta.fasta"
    )
    
    # Mock repository to return our job
    manager.repository.get_job.return_value = job
    
    # Set up mock sequences
    manager.repository.get_sequences.return_value = [
        BaktaSequence(
            job_id="test-job-123",
            header="contig1",
            sequence="ATGCATGCATGC",
            length=12
        )
    ]
    
    # Start job
    result = manager.start_job(job_id="test-job-123")
    
    # Verify client was called
    manager.client.upload_fasta.assert_called_once_with(
        job_id="test-job-123",
        job_secret="test-secret-456",
        fasta_path="/path/to/fasta.fasta"
    )
    manager.client.start_job.assert_called_once_with(
        job_id="test-job-123", 
        job_secret="test-secret-456"
    )
    
    # Verify job status was updated
    manager.repository.update_job_status.assert_called_once_with(
        job_id="test-job-123",
        status="RUNNING"
    )
    
    # Verify job attributes
    assert result.status == "RUNNING"

def test_check_job_status(manager):
    """Test checking job status."""
    # Setup mock job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="RUNNING",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Setup updated job with COMPLETED status
    updated_job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T01:00:00"
    )
    
    # Mock repository to return our job and updated job
    manager.repository.get_job.return_value = job
    manager.repository.update_job_status.return_value = updated_job
    
    # Set client to return COMPLETED status
    manager.client.check_job_status.return_value = {
        "jobs": [
            {
                "jobID": "test-job-123",
                "jobStatus": "COMPLETED"
            }
        ]
    }
    
    # Check job status
    status = manager.check_job_status(job_id="test-job-123")
    
    # Verify client was called
    manager.client.check_job_status.assert_called_once_with(
        job_id="test-job-123", 
        job_secret="test-secret-456"
    )
    
    # Verify job status was updated
    manager.repository.update_job_status.assert_called_once_with(
        job_id="test-job-123",
        status="COMPLETED"
    )
    
    # Verify job attributes
    assert status.status == "COMPLETED"

def test_fetch_job_results(manager, temp_dir):
    """Test fetching job results."""
    # Setup mock job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Mock repository to return our job
    manager.repository.get_job.return_value = job
    
    # Mock client result files
    result_files = {
        "jobID": "test-job-123",
        "ResultFiles": {
            "gff3": "https://example.com/results/output.gff3",
            "json": "https://example.com/results/output.json"
        }
    }
    manager.client.get_job_results.return_value = result_files
    
    # Mock download paths
    gff_path = temp_dir / "output.gff3"
    json_path = temp_dir / "output.json"
    
    # Reset the results_dir for the test
    manager.results_dir = temp_dir
    
    # Create the job results directory
    job_results_dir = temp_dir / "test-job-123"
    job_results_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock download_result_file to return paths
    def mock_download(url, output_path, show_progress=True):
        if "gff3" in url:
            # Create the mock file
            with open(output_path, 'w') as f:
                f.write("Mock GFF3 content")
            return True
        elif "json" in url:
            # Create the mock file
            with open(output_path, 'w') as f:
                f.write("Mock JSON content")
            return True
        return False
    
    manager.client.download_result_file = mock_download
    
    # Fetch job results
    results = manager.fetch_job_results(job_id="test-job-123")
    
    # Verify client was called
    manager.client.get_job_results.assert_called_once_with(
        job_id="test-job-123", 
        job_secret="test-secret-456"
    )
    
    # Verify repository was called
    assert manager.repository.save_result_file.call_count == 2
    
    # Verify job status was updated
    manager.repository.update_job_status.assert_called_once_with(
        job_id="test-job-123",
        status="PROCESSED"
    )
    
    # Verify results
    assert len(results) == 2
    assert "gff3" in results
    assert "json" in results

def test_process_annotations(manager, temp_dir):
    """Test processing annotations from GFF3 file."""
    # Create mock GFF3 file
    gff_path = temp_dir / "test-job-123_output.gff3"
    with open(gff_path, "w") as f:
        f.write("""##gff-version 3
##sequence-region contig1 1 12
contig1\tBakta\tCDS\t1\t9\t.\t+\t0\tID=gene1;product=hypothetical protein
contig1\tBakta\ttRNA\t10\t12\t.\t-\t0\tID=gene2;product=tRNA-Ala
""")
    
    # Process annotations
    annotations = manager.process_annotations(
        job_id="test-job-123",
        gff_file_path=str(gff_path)
    )
    
    # Verify repository was called
    assert manager.repository.save_annotations.call_count == 1
    
    # Verify annotations
    assert len(annotations) == 2
    assert annotations[0].feature_type == "CDS"
    assert annotations[1].feature_type == "tRNA"

def test_get_result(manager):
    """Test getting complete result."""
    # Get result
    result = manager.get_result(job_id="test-job-123")
    
    # Verify repository was called
    manager.repository.get_complete_result.assert_called_once_with("test-job-123")
    
    # Verify result
    assert result is not None
    assert result.job.id == "test-job-123"
    assert len(result.sequences) == 1
    assert len(result.annotations) == 1
    assert len(result.result_files) == 1

def test_get_jobs(manager):
    """Test getting all jobs."""
    # Mock repository to return jobs
    jobs = [
        BaktaJob(
            id="test-job-123",
            name="Test Job 1",
            secret="test-secret-123",
            status="COMPLETED",
            config=SAMPLE_CONFIG,
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-02T00:00:00"
        ),
        BaktaJob(
            id="test-job-456",
            name="Test Job 2",
            secret="test-secret-456",
            status="RUNNING",
            config=SAMPLE_CONFIG,
            created_at="2023-01-03T00:00:00",
            updated_at="2023-01-03T00:00:00"
        )
    ]
    manager.repository.get_jobs.return_value = jobs
    
    # Get all jobs
    result = manager.get_jobs()
    
    # Verify repository was called
    manager.repository.get_jobs.assert_called_once_with(
        status=None,
        limit=None,
        offset=None
    )
    
    # Verify result
    assert len(result) == 2
    assert result[0].id == "test-job-123"
    assert result[1].id == "test-job-456"
    
    # Get jobs with status filter
    manager.repository.get_jobs.reset_mock()
    manager.repository.get_jobs.return_value = [jobs[0]]
    
    result = manager.get_jobs(status="COMPLETED")
    
    # Verify repository was called with filter
    manager.repository.get_jobs.assert_called_once_with(
        status="COMPLETED",
        limit=None,
        offset=None
    )
    
    # Verify result
    assert len(result) == 1
    assert result[0].id == "test-job-123"

def test_delete_job(manager):
    """Test deleting a job."""
    # Mock repository to return True for delete_job
    manager.repository.delete_job.return_value = True
    
    # Delete job
    result = manager.delete_job(job_id="test-job-123")
    
    # Verify repository was called
    manager.repository.delete_job.assert_called_once_with("test-job-123")
    
    # Verify result
    assert result is True

def test_run_complete_workflow(manager, temp_fasta_file):
    """Test running the complete Bakta workflow."""
    # Create initial job
    init_job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        fasta_path=str(temp_fasta_file)
    )
    
    # Create running job
    running_job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="RUNNING",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T01:00:00",
        fasta_path=str(temp_fasta_file)
    )
    
    # Create completed job
    completed_job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T02:00:00",
        fasta_path=str(temp_fasta_file)
    )
    
    # Set up mock response sequence
    manager.repository.save_job.return_value = init_job
    
    # Need to side_effect check_job_status to return running first, then completed
    status_responses = [running_job, completed_job]
    
    def side_effect_check_status(job_id):
        return status_responses.pop(0)
    
    # Mock methods that would be called in the workflow
    with patch.object(manager, 'create_job', return_value=init_job) as mock_create_job, \
         patch.object(manager, 'start_job', return_value=running_job) as mock_start_job, \
         patch.object(manager, 'check_job_status', side_effect=side_effect_check_status) as mock_check_status, \
         patch.object(manager, 'fetch_job_results', return_value={"gff3": "/path/to/results/output.gff3"}) as mock_fetch_results, \
         patch.object(manager, 'process_annotations', return_value=[]) as mock_process_annotations, \
         patch.object(manager, 'get_result', return_value=manager.repository.get_complete_result.return_value) as mock_get_result:
        
        # Run complete workflow
        result = manager.run_complete_workflow(
            fasta_path=temp_fasta_file,
            name="Test Job",
            config=SAMPLE_CONFIG
        )
        
        # Verify all methods were called
        mock_create_job.assert_called_once_with(
            fasta_path=temp_fasta_file,
            name="Test Job",
            config=SAMPLE_CONFIG
        )
        mock_start_job.assert_called_once_with(init_job.id)
        assert mock_check_status.call_count == 2
        mock_fetch_results.assert_called_once_with(completed_job.id)
        mock_process_annotations.assert_called_once_with(completed_job.id, "/path/to/results/output.gff3")
        mock_get_result.assert_called_once_with(completed_job.id)
        
        # Verify result
        assert result is not None

def test_error_handling(manager, temp_fasta_file):
    """Test error handling in the manager."""
    # Test with non-existent job
    manager.repository.get_job.return_value = None
    with pytest.raises(BaktaManagerError):
        manager.start_job(job_id="non-existent-job")
    
    # Test with client errors
    manager.repository.get_job.return_value = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Test client.upload_fasta error
    manager.client.upload_fasta.side_effect = BaktaClientError("Upload failed")
    with pytest.raises(BaktaManagerError):
        manager.start_job(job_id="test-job-123")
    
    # Test with invalid FASTA
    manager.client.upload_fasta.side_effect = None  # Reset
    manager.repository.save_sequences_from_file.side_effect = BaktaValidationError("Invalid FASTA")
    with pytest.raises(BaktaManagerError):
        manager.create_job(
            fasta_path=temp_fasta_file,
            name="Test Job",
            config=SAMPLE_CONFIG
        )
    
    # Test with repository errors
    manager.repository.save_sequences_from_file.side_effect = None  # Reset
    manager.repository.save_job.side_effect = RepositoryError("Database error")
    with pytest.raises(BaktaManagerError):
        manager.create_job(
            fasta_path=temp_fasta_file,
            name="Test Job",
            config=SAMPLE_CONFIG
        ) 