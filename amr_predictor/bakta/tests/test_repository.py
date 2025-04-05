#!/usr/bin/env python3
"""
Tests for the Bakta repository module.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError
from amr_predictor.bakta.repository import BaktaRepository, RepositoryError
from amr_predictor.bakta.models import (
    BaktaJob, BaktaSequence, BaktaResultFile, BaktaAnnotation, 
    BaktaJobStatusHistory, BaktaResult
)

# Sample data for testing
SAMPLE_FASTA = """>contig1
ATGCATGCATGC
>contig2
GCTAGCTAGCTA
"""

@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    yield tmp_path
    
    # Clean up
    if tmp_path.exists():
        os.unlink(tmp_path)

@pytest.fixture
def repository(temp_db_path):
    """Create a repository with a temporary database."""
    return BaktaRepository(temp_db_path)

@pytest.fixture
def sample_job():
    """Create a sample BaktaJob."""
    return BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config={
            "genus": "Escherichia",
            "species": "coli",
            "strain": "K-12",
            "completeGenome": True,
            "translationTable": 11
        },
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        fasta_path="/path/to/test.fasta"
    )

@pytest.fixture
def sample_annotation():
    """Create a sample BaktaAnnotation."""
    return BaktaAnnotation(
        job_id="test-job-123",
        feature_id="gene1",
        feature_type="CDS",
        contig="contig1",
        start=10,
        end=100,
        strand="+",
        attributes={
            "product": "hypothetical protein",
            "note": "test annotation"
        }
    )

@pytest.fixture
def sample_result_file():
    """Create a sample BaktaResultFile."""
    return BaktaResultFile(
        job_id="test-job-123",
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        downloaded_at="2023-01-01T00:00:00",
        download_url="https://example.com/results/output.gff3"
    )

def test_repository_initialization(temp_db_path):
    """Test repository initialization."""
    # Repository should create a database manager
    repo = BaktaRepository(temp_db_path)
    assert repo.db_manager is not None
    assert isinstance(repo.db_manager, DatabaseManager)
    
    # Database file should exist
    assert temp_db_path.exists()

def test_save_and_get_job(repository, sample_job):
    """Test saving and retrieving a job."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Retrieve job
    job = repository.get_job(sample_job.id)
    
    # Verify job data
    assert job is not None
    assert job.id == sample_job.id
    assert job.name == sample_job.name
    assert job.secret == sample_job.secret
    assert job.status == "INIT"
    assert job.fasta_path == sample_job.fasta_path
    assert job.config == sample_job.config

def test_update_job_status(repository, sample_job):
    """Test updating job status."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Update status to RUNNING
    repository.update_job_status(sample_job.id, "RUNNING", "Job started running")
    
    # Check job status
    job = repository.get_job(sample_job.id)
    assert job.status == "RUNNING"
    
    # Get status history
    history = repository.get_job_status_history(sample_job.id)
    assert len(history) == 2  # INIT, RUNNING
    assert history[0].status == "INIT"
    assert history[1].status == "RUNNING"
    assert history[1].message == "Job started running"

def test_get_jobs(repository, sample_job):
    """Test retrieving jobs."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Create and save another job
    another_job = BaktaJob(
        id="test-job-456",
        name="Another Test Job",
        secret="test-secret-789",
        status="RUNNING",
        config={"genus": "Staphylococcus", "species": "aureus"},
        created_at="2023-01-02T00:00:00",
        updated_at="2023-01-02T00:00:00"
    )
    repository.save_job(
        job_id=another_job.id,
        name=another_job.name,
        secret=another_job.secret,
        status=another_job.status,
        config=another_job.config,
        fasta_path=another_job.fasta_path
    )
    repository.update_job_status(another_job.id, "RUNNING")
    
    # Get all jobs
    jobs = repository.get_jobs()
    assert len(jobs) == 2
    
    # Get jobs by status
    init_jobs = repository.get_jobs(status="INIT")
    assert len(init_jobs) == 1
    assert init_jobs[0].id == sample_job.id
    
    running_jobs = repository.get_jobs(status="RUNNING")
    assert len(running_jobs) == 1
    assert running_jobs[0].id == another_job.id

def test_save_sequences_from_string(repository, sample_job):
    """Test saving sequences from a FASTA string."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save sequences
    sequences = repository.save_sequences(sample_job.id, SAMPLE_FASTA)
    
    # Verify sequences
    assert len(sequences) == 2
    assert sequences[0].header == "contig1"
    assert sequences[0].sequence == "ATGCATGCATGC"
    assert sequences[0].length == 12
    assert sequences[1].header == "contig2"
    assert sequences[1].sequence == "GCTAGCTAGCTA"
    assert sequences[1].length == 12
    
    # Retrieve sequences
    retrieved_sequences = repository.get_sequences(sample_job.id)
    assert len(retrieved_sequences) == 2

def test_save_sequences_from_file(repository, sample_job):
    """Test saving sequences from a FASTA file."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Create a temporary FASTA file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(SAMPLE_FASTA)
        fasta_path = f.name
    
    try:
        # Save sequences from file
        sequences = repository.save_sequences_from_file(sample_job.id, fasta_path)
        
        # Verify sequences
        assert len(sequences) == 2
        assert sequences[0].header == "contig1"
        assert sequences[0].sequence == "ATGCATGCATGC"
    finally:
        # Clean up
        if os.path.exists(fasta_path):
            os.unlink(fasta_path)

def test_save_and_get_result_file(repository, sample_job, sample_result_file):
    """Test saving and retrieving result files."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save result file
    repository.save_result_file(sample_result_file)
    
    # Create and save another result file
    another_result_file = BaktaResultFile(
        job_id=sample_job.id,
        file_type="JSON",
        file_path="/path/to/results/output.json",
        downloaded_at="2023-01-01T00:00:00",
        download_url="https://example.com/results/output.json"
    )
    repository.save_result_file(another_result_file)
    
    # Get all result files
    result_files = repository.get_result_files(sample_job.id)
    assert len(result_files) == 2
    
    # Get result files by type
    gff_files = repository.get_result_files(sample_job.id, file_type="GFF3")
    assert len(gff_files) == 1
    assert gff_files[0].file_type == "GFF3"
    assert gff_files[0].file_path == sample_result_file.file_path

def test_save_and_get_annotations(repository, sample_job, sample_annotation):
    """Test saving and retrieving annotations."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save annotation
    repository.save_annotations([sample_annotation])
    
    # Create and save another annotation
    another_annotation = BaktaAnnotation(
        job_id=sample_job.id,
        feature_id="gene2",
        feature_type="tRNA",
        contig="contig1",
        start=200,
        end=300,
        strand="-",
        attributes={
            "product": "tRNA-Ala",
            "note": "test annotation 2"
        }
    )
    repository.save_annotations([another_annotation])
    
    # Get all annotations
    annotations = repository.get_annotations(sample_job.id)
    assert len(annotations) == 2
    
    # Get annotations by type
    cds_annotations = repository.get_annotations(sample_job.id, feature_type="CDS")
    assert len(cds_annotations) == 1
    assert cds_annotations[0].feature_type == "CDS"
    assert cds_annotations[0].feature_id == sample_annotation.feature_id

def test_get_complete_result(repository, sample_job, sample_annotation, sample_result_file):
    """Test retrieving a complete result."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save sequence
    repository.save_sequences(sample_job.id, SAMPLE_FASTA)
    
    # Save annotation
    repository.save_annotations([sample_annotation])
    
    # Save result file
    repository.save_result_file(sample_result_file)
    
    # Get complete result
    result = repository.get_complete_result(sample_job.id)
    
    # Verify result
    assert result is not None
    assert result.job.id == sample_job.id
    assert len(result.sequences) == 2
    assert len(result.annotations) == 1
    assert len(result.result_files) == 1
    
    # Verify methods on result
    assert len(result.get_annotations_by_type("CDS")) == 1
    assert len(result.get_annotations_by_type("tRNA")) == 0
    assert result.get_result_file_by_type("GFF3") is not None
    assert result.get_result_file_by_type("JSON") is None

def test_delete_job(repository, sample_job):
    """Test deleting a job."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save sequence
    repository.save_sequences(sample_job.id, SAMPLE_FASTA)
    
    # Verify job exists
    assert repository.get_job(sample_job.id) is not None
    
    # Delete job
    result = repository.delete_job(sample_job.id)
    assert result is True
    
    # Verify job is deleted
    assert repository.get_job(sample_job.id) is None
    
    # Deleting again should return False
    result = repository.delete_job(sample_job.id)
    assert result is False

def test_error_handling(repository):
    """Test error handling in the repository."""
    # Test with non-existent job
    assert repository.get_job("non-existent-job") is None
    
    # Test with invalid FASTA
    with pytest.raises(RepositoryError):
        repository.save_sequences("job-id", "This is not a valid FASTA")
    
    # Test with database error
    with patch.object(repository.db_manager, 'save_job', side_effect=BaktaDatabaseError("Database error")):
        with pytest.raises(RepositoryError):
            repository.save_job(
                job_id="test-job",
                name="Test Job",
                secret="test-secret",
                status="INIT",
                config={},
                fasta_path=None
            )

def test_empty_annotations(repository, sample_job):
    """Test saving empty annotations list."""
    # Save job
    repository.save_job(
        job_id=sample_job.id,
        name=sample_job.name,
        secret=sample_job.secret,
        status=sample_job.status,
        config=sample_job.config,
        fasta_path=sample_job.fasta_path
    )
    
    # Save empty annotations list
    repository.save_annotations([])
    
    # Should not raise any errors 