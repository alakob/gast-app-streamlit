#!/usr/bin/env python3
"""
Tests for the Bakta models module.
"""

import pytest
import json
from datetime import datetime

from amr_predictor.bakta.models import (
    BaktaJob, BaktaSequence, BaktaResultFile, BaktaAnnotation, 
    BaktaJobStatusHistory, BaktaResult
)

def test_bakta_job_creation():
    """Test BaktaJob creation and attributes."""
    job = BaktaJob(
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
    
    # Test attributes
    assert job.id == "test-job-123"
    assert job.name == "Test Job"
    assert job.secret == "test-secret-456"
    assert job.status == "INIT"
    assert job.config["genus"] == "Escherichia"
    assert job.config["species"] == "coli"
    assert job.created_at == "2023-01-01T00:00:00"
    assert job.updated_at == "2023-01-01T00:00:00"
    assert job.fasta_path == "/path/to/test.fasta"

def test_bakta_job_to_dict():
    """Test BaktaJob to_dict method."""
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config={
            "genus": "Escherichia",
            "species": "coli"
        },
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    job_dict = job.to_dict()
    
    # Test dictionary representation
    assert job_dict["id"] == "test-job-123"
    assert job_dict["name"] == "Test Job"
    assert job_dict["secret"] == "test-secret-456"
    assert job_dict["status"] == "INIT"
    assert job_dict["config"]["genus"] == "Escherichia"
    assert job_dict["config"]["species"] == "coli"
    assert job_dict["created_at"] == "2023-01-01T00:00:00"
    assert job_dict["updated_at"] == "2023-01-01T00:00:00"

def test_bakta_job_from_dict():
    """Test BaktaJob from_dict method."""
    job_dict = {
        "id": "test-job-123",
        "name": "Test Job",
        "secret": "test-secret-456",
        "status": "INIT",
        "config": {
            "genus": "Escherichia",
            "species": "coli"
        },
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "fasta_path": "/path/to/test.fasta"
    }
    
    job = BaktaJob.from_dict(job_dict)
    
    # Test object creation from dictionary
    assert job.id == "test-job-123"
    assert job.name == "Test Job"
    assert job.secret == "test-secret-456"
    assert job.status == "INIT"
    assert job.config["genus"] == "Escherichia"
    assert job.config["species"] == "coli"
    assert job.created_at == "2023-01-01T00:00:00"
    assert job.updated_at == "2023-01-01T00:00:00"
    assert job.fasta_path == "/path/to/test.fasta"

def test_bakta_sequence_creation():
    """Test BaktaSequence creation and attributes."""
    sequence = BaktaSequence(
        job_id="test-job-123",
        header="contig1",
        sequence="ATGCATGCATGC",
        length=12
    )
    
    # Test attributes
    assert sequence.job_id == "test-job-123"
    assert sequence.header == "contig1"
    assert sequence.sequence == "ATGCATGCATGC"
    assert sequence.length == 12

def test_bakta_sequence_to_dict():
    """Test BaktaSequence to_dict method."""
    sequence = BaktaSequence(
        job_id="test-job-123",
        header="contig1",
        sequence="ATGCATGCATGC",
        length=12
    )
    
    sequence_dict = sequence.to_dict()
    
    # Test dictionary representation
    assert sequence_dict["job_id"] == "test-job-123"
    assert sequence_dict["header"] == "contig1"
    assert sequence_dict["sequence"] == "ATGCATGCATGC"
    assert sequence_dict["length"] == 12

def test_bakta_sequence_from_dict():
    """Test BaktaSequence from_dict method."""
    sequence_dict = {
        "job_id": "test-job-123",
        "header": "contig1",
        "sequence": "ATGCATGCATGC",
        "length": 12
    }
    
    sequence = BaktaSequence.from_dict(sequence_dict)
    
    # Test object creation from dictionary
    assert sequence.job_id == "test-job-123"
    assert sequence.header == "contig1"
    assert sequence.sequence == "ATGCATGCATGC"
    assert sequence.length == 12

def test_bakta_sequence_to_fasta():
    """Test BaktaSequence to_fasta method."""
    sequence = BaktaSequence(
        job_id="test-job-123",
        header="contig1",
        sequence="ATGCATGCATGC",
        length=12
    )
    
    fasta = sequence.to_fasta()
    
    # Test FASTA representation
    assert fasta == ">contig1\nATGCATGCATGC"

def test_bakta_result_file_creation():
    """Test BaktaResultFile creation and attributes."""
    result_file = BaktaResultFile(
        job_id="test-job-123",
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        downloaded_at="2023-01-01T00:00:00",
        download_url="https://example.com/results/output.gff3"
    )
    
    # Test attributes
    assert result_file.job_id == "test-job-123"
    assert result_file.file_type == "GFF3"
    assert result_file.file_path == "/path/to/results/output.gff3"
    assert result_file.downloaded_at == "2023-01-01T00:00:00"
    assert result_file.download_url == "https://example.com/results/output.gff3"

def test_bakta_result_file_to_dict():
    """Test BaktaResultFile to_dict method."""
    result_file = BaktaResultFile(
        job_id="test-job-123",
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        downloaded_at="2023-01-01T00:00:00",
        download_url="https://example.com/results/output.gff3"
    )
    
    result_file_dict = result_file.to_dict()
    
    # Test dictionary representation
    assert result_file_dict["job_id"] == "test-job-123"
    assert result_file_dict["file_type"] == "GFF3"
    assert result_file_dict["file_path"] == "/path/to/results/output.gff3"
    assert result_file_dict["downloaded_at"] == "2023-01-01T00:00:00"
    assert result_file_dict["download_url"] == "https://example.com/results/output.gff3"

def test_bakta_result_file_from_dict():
    """Test BaktaResultFile from_dict method."""
    result_file_dict = {
        "job_id": "test-job-123",
        "file_type": "GFF3",
        "file_path": "/path/to/results/output.gff3",
        "downloaded_at": "2023-01-01T00:00:00",
        "download_url": "https://example.com/results/output.gff3"
    }
    
    result_file = BaktaResultFile.from_dict(result_file_dict)
    
    # Test object creation from dictionary
    assert result_file.job_id == "test-job-123"
    assert result_file.file_type == "GFF3"
    assert result_file.file_path == "/path/to/results/output.gff3"
    assert result_file.downloaded_at == "2023-01-01T00:00:00"
    assert result_file.download_url == "https://example.com/results/output.gff3"

def test_bakta_annotation_creation():
    """Test BaktaAnnotation creation and attributes."""
    annotation = BaktaAnnotation(
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
    
    # Test attributes
    assert annotation.job_id == "test-job-123"
    assert annotation.feature_id == "gene1"
    assert annotation.feature_type == "CDS"
    assert annotation.contig == "contig1"
    assert annotation.start == 10
    assert annotation.end == 100
    assert annotation.strand == "+"
    assert annotation.attributes["product"] == "hypothetical protein"
    assert annotation.attributes["note"] == "test annotation"

def test_bakta_annotation_to_dict():
    """Test BaktaAnnotation to_dict method."""
    annotation = BaktaAnnotation(
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
    
    annotation_dict = annotation.to_dict()
    
    # Check if attributes were converted to a JSON string
    assert isinstance(annotation_dict["attributes"], str)
    attributes = json.loads(annotation_dict["attributes"])
    
    # Test dictionary representation
    assert annotation_dict["job_id"] == "test-job-123"
    assert annotation_dict["feature_id"] == "gene1"
    assert annotation_dict["feature_type"] == "CDS"
    assert annotation_dict["contig"] == "contig1"
    assert annotation_dict["start"] == 10
    assert annotation_dict["end"] == 100
    assert annotation_dict["strand"] == "+"
    assert attributes["product"] == "hypothetical protein"
    assert attributes["note"] == "test annotation"

def test_bakta_annotation_from_dict():
    """Test BaktaAnnotation from_dict method."""
    # Test with JSON string attributes
    annotation_dict = {
        "job_id": "test-job-123",
        "feature_id": "gene1",
        "feature_type": "CDS",
        "contig": "contig1",
        "start": 10,
        "end": 100,
        "strand": "+",
        "attributes": json.dumps({
            "product": "hypothetical protein",
            "note": "test annotation"
        })
    }
    
    annotation = BaktaAnnotation.from_dict(annotation_dict)
    
    # Test object creation from dictionary
    assert annotation.job_id == "test-job-123"
    assert annotation.feature_id == "gene1"
    assert annotation.feature_type == "CDS"
    assert annotation.contig == "contig1"
    assert annotation.start == 10
    assert annotation.end == 100
    assert annotation.strand == "+"
    assert annotation.attributes["product"] == "hypothetical protein"
    assert annotation.attributes["note"] == "test annotation"
    
    # Test with dictionary attributes
    annotation_dict2 = {
        "job_id": "test-job-123",
        "feature_id": "gene1",
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
    
    annotation2 = BaktaAnnotation.from_dict(annotation_dict2)
    assert annotation2.attributes["product"] == "hypothetical protein"

def test_bakta_annotation_get_attribute():
    """Test BaktaAnnotation get_attribute method."""
    annotation = BaktaAnnotation(
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
    
    # Test attribute retrieval
    assert annotation.get_attribute("product") == "hypothetical protein"
    assert annotation.get_attribute("note") == "test annotation"
    assert annotation.get_attribute("non_existent") is None
    assert annotation.get_attribute("non_existent", "default") == "default"

def test_bakta_job_status_history_creation():
    """Test BaktaJobStatusHistory creation and attributes."""
    status_history = BaktaJobStatusHistory(
        job_id="test-job-123",
        status="INIT",
        timestamp="2023-01-01T00:00:00",
        message="Job initialized"
    )
    
    # Test attributes
    assert status_history.job_id == "test-job-123"
    assert status_history.status == "INIT"
    assert status_history.timestamp == "2023-01-01T00:00:00"
    assert status_history.message == "Job initialized"

def test_bakta_job_status_history_to_dict():
    """Test BaktaJobStatusHistory to_dict method."""
    status_history = BaktaJobStatusHistory(
        job_id="test-job-123",
        status="INIT",
        timestamp="2023-01-01T00:00:00",
        message="Job initialized"
    )
    
    status_history_dict = status_history.to_dict()
    
    # Test dictionary representation
    assert status_history_dict["job_id"] == "test-job-123"
    assert status_history_dict["status"] == "INIT"
    assert status_history_dict["timestamp"] == "2023-01-01T00:00:00"
    assert status_history_dict["message"] == "Job initialized"

def test_bakta_job_status_history_from_dict():
    """Test BaktaJobStatusHistory from_dict method."""
    status_history_dict = {
        "job_id": "test-job-123",
        "status": "INIT",
        "timestamp": "2023-01-01T00:00:00",
        "message": "Job initialized"
    }
    
    status_history = BaktaJobStatusHistory.from_dict(status_history_dict)
    
    # Test object creation from dictionary
    assert status_history.job_id == "test-job-123"
    assert status_history.status == "INIT"
    assert status_history.timestamp == "2023-01-01T00:00:00"
    assert status_history.message == "Job initialized"

def test_bakta_result_creation():
    """Test BaktaResult creation and its utility methods."""
    # Create sample job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config={"genus": "Escherichia", "species": "coli"},
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-02T00:00:00"
    )
    
    # Create sample sequences
    sequences = [
        BaktaSequence(
            job_id="test-job-123",
            header="contig1",
            sequence="ATGCATGCATGC",
            length=12
        ),
        BaktaSequence(
            job_id="test-job-123",
            header="contig2",
            sequence="GCTAGCTAGCTA",
            length=12
        )
    ]
    
    # Create sample annotations
    annotations = [
        BaktaAnnotation(
            job_id="test-job-123",
            feature_id="gene1",
            feature_type="CDS",
            contig="contig1",
            start=10,
            end=100,
            strand="+",
            attributes={"product": "hypothetical protein"}
        ),
        BaktaAnnotation(
            job_id="test-job-123",
            feature_id="gene2",
            feature_type="tRNA",
            contig="contig1",
            start=200,
            end=300,
            strand="-",
            attributes={"product": "tRNA-Ala"}
        )
    ]
    
    # Create sample result files
    result_files = [
        BaktaResultFile(
            job_id="test-job-123",
            file_type="GFF3",
            file_path="/path/to/results/output.gff3",
            downloaded_at="2023-01-02T00:00:00"
        ),
        BaktaResultFile(
            job_id="test-job-123",
            file_type="JSON",
            file_path="/path/to/results/output.json",
            downloaded_at="2023-01-02T00:00:00"
        )
    ]
    
    # Create BaktaResult
    result = BaktaResult(
        job=job,
        sequences=sequences,
        annotations=annotations,
        result_files=result_files
    )
    
    # Test basic attributes
    assert result.job.id == "test-job-123"
    assert len(result.sequences) == 2
    assert len(result.annotations) == 2
    assert len(result.result_files) == 2
    
    # Test utility methods
    assert len(result.get_annotations_by_type("CDS")) == 1
    assert len(result.get_annotations_by_type("tRNA")) == 1
    assert result.get_result_file_by_type("GFF3") is not None
    assert result.get_result_file_by_type("GFF3").file_path == "/path/to/results/output.gff3"
    assert result.get_result_file_by_type("JSON") is not None
    assert result.get_result_file_by_type("FASTA") is None

def test_bakta_result_to_dict():
    """Test BaktaResult to_dict method."""
    # Create sample job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config={"genus": "Escherichia", "species": "coli"},
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-02T00:00:00"
    )
    
    # Create sample sequences
    sequences = [
        BaktaSequence(
            job_id="test-job-123",
            header="contig1",
            sequence="ATGCATGCATGC",
            length=12
        )
    ]
    
    # Create sample annotations
    annotations = [
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
    ]
    
    # Create sample result files
    result_files = [
        BaktaResultFile(
            job_id="test-job-123",
            file_type="GFF3",
            file_path="/path/to/results/output.gff3",
            downloaded_at="2023-01-02T00:00:00"
        )
    ]
    
    # Create BaktaResult
    result = BaktaResult(
        job=job,
        sequences=sequences,
        annotations=annotations,
        result_files=result_files
    )
    
    # Test to_dict method
    result_dict = result.to_dict()
    
    assert result_dict["job"]["id"] == "test-job-123"
    assert len(result_dict["sequences"]) == 1
    assert result_dict["sequences"][0]["header"] == "contig1"
    assert len(result_dict["annotations"]) == 1
    assert json.loads(result_dict["annotations"][0]["attributes"])["product"] == "hypothetical protein"
    assert len(result_dict["result_files"]) == 1
    assert result_dict["result_files"][0]["file_type"] == "GFF3"

def test_bakta_model_json_serialization():
    """Test that all Bakta models can be serialized to JSON."""
    # Create sample job
    job = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config={"genus": "Escherichia", "species": "coli"},
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )
    
    # Test JSON serialization
    job_json = json.dumps(job.to_dict())
    assert '"id": "test-job-123"' in job_json
    
    # Create sample sequence
    sequence = BaktaSequence(
        job_id="test-job-123",
        header="contig1",
        sequence="ATGCATGCATGC",
        length=12
    )
    
    # Test JSON serialization
    sequence_json = json.dumps(sequence.to_dict())
    assert '"header": "contig1"' in sequence_json
    
    # Create sample annotation
    annotation = BaktaAnnotation(
        job_id="test-job-123",
        feature_id="gene1",
        feature_type="CDS",
        contig="contig1",
        start=10,
        end=100,
        strand="+",
        attributes={"product": "hypothetical protein"}
    )
    
    # Test JSON serialization 
    annotation_dict = annotation.to_dict()
    annotation_json = json.dumps(annotation_dict)
    assert '"feature_id": "gene1"' in annotation_json 