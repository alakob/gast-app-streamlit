#!/usr/bin/env python3
"""
Tests for the Bakta database module.
"""

import os
import json
import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError

# Sample data for testing
SAMPLE_JOB_ID = "test-job-123"
SAMPLE_JOB_NAME = "Test Job"
SAMPLE_SECRET = "test-secret-456"
SAMPLE_CONFIG = {
    "genus": "Escherichia",
    "species": "coli",
    "strain": "K-12",
    "completeGenome": True,
    "translationTable": 11
}

SAMPLE_SEQUENCE = {
    "header": "contig1",
    "sequence": "ATGCATGCATGC",
    "length": 12
}

SAMPLE_ANNOTATION = {
    "feature_id": "gene123",
    "feature_type": "CDS",
    "contig": "contig1",
    "start": 10,
    "end": 100,
    "strand": "+",
    "attributes": {
        "product": "hypothetical protein",
        "note": "test annotation"
    }
}

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
def db_manager(temp_db_path):
    """Create a database manager with a temporary database."""
    return DatabaseManager(temp_db_path)

def test_database_initialization(temp_db_path):
    """Test database initialization."""
    # Initialize database
    db_manager = DatabaseManager(temp_db_path)
    
    # Database file should exist
    assert temp_db_path.exists()
    
    # Database should have tables
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    
    assert "bakta_jobs" in tables
    assert "bakta_sequences" in tables
    assert "bakta_result_files" in tables
    assert "bakta_annotations" in tables
    assert "bakta_job_status_history" in tables
    
    conn.close()

def test_save_and_get_job(db_manager):
    """Test saving and retrieving a job."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG,
        fasta_path="/path/to/test.fasta"
    )
    
    # Retrieve job
    job = db_manager.get_job(SAMPLE_JOB_ID)
    
    # Verify job data
    assert job is not None
    assert job["id"] == SAMPLE_JOB_ID
    assert job["name"] == SAMPLE_JOB_NAME
    assert job["secret"] == SAMPLE_SECRET
    assert job["status"] == "INIT"
    assert job["fasta_path"] == "/path/to/test.fasta"
    assert job["config"] == SAMPLE_CONFIG

def test_update_job_status(db_manager):
    """Test updating job status."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG
    )
    
    # Update status to RUNNING
    db_manager.update_job_status(SAMPLE_JOB_ID, "RUNNING", "Job started running")
    
    # Check job status
    job = db_manager.get_job(SAMPLE_JOB_ID)
    assert job["status"] == "RUNNING"
    assert job["started_at"] is not None
    
    # Update status to SUCCESSFUL
    db_manager.update_job_status(SAMPLE_JOB_ID, "SUCCESSFUL", "Job completed successfully")
    
    # Check job status
    job = db_manager.get_job(SAMPLE_JOB_ID)
    assert job["status"] == "SUCCESSFUL"
    assert job["completed_at"] is not None
    
    # Check status history
    history = db_manager.get_job_status_history(SAMPLE_JOB_ID)
    assert len(history) == 3  # INIT, RUNNING, SUCCESSFUL
    assert history[0]["status"] == "INIT"
    assert history[1]["status"] == "RUNNING"
    assert history[2]["status"] == "SUCCESSFUL"

def test_get_jobs_by_status(db_manager):
    """Test retrieving jobs filtered by status."""
    # Save jobs with different statuses
    db_manager.save_job(
        job_id="job1",
        job_name="Job 1",
        job_secret="secret1",
        config=SAMPLE_CONFIG
    )
    db_manager.save_job(
        job_id="job2",
        job_name="Job 2",
        job_secret="secret2",
        config=SAMPLE_CONFIG
    )
    
    # Update statuses
    db_manager.update_job_status("job1", "RUNNING")
    db_manager.update_job_status("job2", "SUCCESSFUL")
    
    # Get all jobs
    all_jobs = db_manager.get_jobs()
    assert len(all_jobs) == 2
    
    # Get running jobs
    running_jobs = db_manager.get_jobs(status="RUNNING")
    assert len(running_jobs) == 1
    assert running_jobs[0]["id"] == "job1"
    
    # Get successful jobs
    successful_jobs = db_manager.get_jobs(status="SUCCESSFUL")
    assert len(successful_jobs) == 1
    assert successful_jobs[0]["id"] == "job2"

def test_save_and_get_sequences(db_manager):
    """Test saving and retrieving sequences."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG
    )
    
    # Save sequences
    sequences = [
        {
            "header": "contig1",
            "sequence": "ATGCATGCATGC",
            "length": 12
        },
        {
            "header": "contig2",
            "sequence": "GCTAGCTAGCTA",
            "length": 12
        }
    ]
    db_manager.save_sequences(SAMPLE_JOB_ID, sequences)
    
    # Retrieve sequences
    retrieved_sequences = db_manager.get_sequences(SAMPLE_JOB_ID)
    
    # Verify sequences
    assert len(retrieved_sequences) == 2
    assert retrieved_sequences[0]["header"] == "contig1"
    assert retrieved_sequences[0]["sequence"] == "ATGCATGCATGC"
    assert retrieved_sequences[0]["length"] == 12
    assert retrieved_sequences[1]["header"] == "contig2"
    assert retrieved_sequences[1]["sequence"] == "GCTAGCTAGCTA"
    assert retrieved_sequences[1]["length"] == 12

def test_save_and_get_result_files(db_manager):
    """Test saving and retrieving result files."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG
    )
    
    # Save result files
    db_manager.save_result_file(
        job_id=SAMPLE_JOB_ID,
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        download_url="https://example.com/results/output.gff3"
    )
    db_manager.save_result_file(
        job_id=SAMPLE_JOB_ID,
        file_type="JSON",
        file_path="/path/to/results/output.json",
        download_url="https://example.com/results/output.json"
    )
    
    # Retrieve all result files
    all_files = db_manager.get_result_files(SAMPLE_JOB_ID)
    assert len(all_files) == 2
    
    # Retrieve filtered result files
    gff_files = db_manager.get_result_files(SAMPLE_JOB_ID, file_type="GFF3")
    assert len(gff_files) == 1
    assert gff_files[0]["file_type"] == "GFF3"
    assert gff_files[0]["file_path"] == "/path/to/results/output.gff3"
    assert gff_files[0]["download_url"] == "https://example.com/results/output.gff3"

def test_save_and_get_annotations(db_manager):
    """Test saving and retrieving annotations."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG
    )
    
    # Save annotations
    annotations = [
        {
            "feature_id": "gene1",
            "feature_type": "CDS",
            "contig": "contig1",
            "start": 10,
            "end": 100,
            "strand": "+",
            "attributes": json.dumps({
                "product": "hypothetical protein",
                "note": "test annotation 1"
            })
        },
        {
            "feature_id": "gene2",
            "feature_type": "tRNA",
            "contig": "contig1",
            "start": 200,
            "end": 300,
            "strand": "-",
            "attributes": json.dumps({
                "product": "tRNA-Ala",
                "note": "test annotation 2"
            })
        }
    ]
    db_manager.save_annotations(SAMPLE_JOB_ID, annotations)
    
    # Retrieve all annotations
    all_annotations = db_manager.get_annotations(SAMPLE_JOB_ID)
    assert len(all_annotations) == 2
    
    # Retrieve filtered annotations
    cds_annotations = db_manager.get_annotations(SAMPLE_JOB_ID, feature_type="CDS")
    assert len(cds_annotations) == 1
    assert cds_annotations[0]["feature_type"] == "CDS"
    assert cds_annotations[0]["feature_id"] == "gene1"
    assert json.loads(cds_annotations[0]["attributes"])["product"] == "hypothetical protein"
    
    # Check tRNA annotation
    trna_annotations = db_manager.get_annotations(SAMPLE_JOB_ID, feature_type="tRNA")
    assert len(trna_annotations) == 1
    assert trna_annotations[0]["feature_type"] == "tRNA"
    assert trna_annotations[0]["feature_id"] == "gene2"
    assert json.loads(trna_annotations[0]["attributes"])["product"] == "tRNA-Ala"

def test_delete_job(db_manager):
    """Test deleting a job and its associated data."""
    # Save job
    db_manager.save_job(
        job_id=SAMPLE_JOB_ID,
        job_name=SAMPLE_JOB_NAME,
        job_secret=SAMPLE_SECRET,
        config=SAMPLE_CONFIG
    )
    
    # Save sequences
    db_manager.save_sequences(SAMPLE_JOB_ID, [SAMPLE_SEQUENCE])
    
    # Save annotations
    db_manager.save_annotations(SAMPLE_JOB_ID, [SAMPLE_ANNOTATION])
    
    # Save result file
    db_manager.save_result_file(
        job_id=SAMPLE_JOB_ID,
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        download_url="https://example.com/results/output.gff3"
    )
    
    # Verify data exists
    assert db_manager.get_job(SAMPLE_JOB_ID) is not None
    assert len(db_manager.get_sequences(SAMPLE_JOB_ID)) == 1
    assert len(db_manager.get_annotations(SAMPLE_JOB_ID)) == 1
    assert len(db_manager.get_result_files(SAMPLE_JOB_ID)) == 1
    
    # Delete job
    result = db_manager.delete_job(SAMPLE_JOB_ID)
    assert result is True
    
    # Verify all data is deleted
    assert db_manager.get_job(SAMPLE_JOB_ID) is None
    assert len(db_manager.get_sequences(SAMPLE_JOB_ID)) == 0
    assert len(db_manager.get_annotations(SAMPLE_JOB_ID)) == 0
    assert len(db_manager.get_result_files(SAMPLE_JOB_ID)) == 0
    
    # Try to delete again (should return False)
    result = db_manager.delete_job(SAMPLE_JOB_ID)
    assert result is False

def test_error_handling(db_manager, temp_db_path):
    """Test error handling in the database manager."""
    # Test with invalid job ID
    with pytest.raises(BaktaDatabaseError):
        db_manager.save_job(
            job_id=None,  # This will cause an error because job_id is required
            job_name=SAMPLE_JOB_NAME,
            job_secret=SAMPLE_SECRET,
            config=SAMPLE_CONFIG
        )
    
    # Test with corrupted database
    with open(temp_db_path, 'w') as f:
        f.write("This is not a valid SQLite database")
    
    # Operations should raise BaktaDatabaseError
    with pytest.raises(BaktaDatabaseError):
        db_manager.get_job(SAMPLE_JOB_ID) 