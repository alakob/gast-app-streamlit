#!/usr/bin/env python3
"""
Mock classes for testing the Bakta module.

This module provides mock implementations of the
Bakta API client, repository, job manager, and other components
for use in testing.
"""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from unittest.mock import MagicMock

from amr_predictor.bakta.models import (
    BaktaJob,
    BaktaAnnotation,
    JobStatus,
    QueryResult
)

# Configure logging
logger = logging.getLogger("bakta-test-mocks")

class MockBaktaManager:
    """Mock implementation of BaktaManager for testing."""
    
    def __init__(self):
        """Initialize the mock manager."""
        self.jobs = {}
        self.results = {}
    
    def create_job(self, *args, **kwargs):
        """Mock method to create a job."""
        job_id = f"mock-job-{len(self.jobs) + 1}"
        job = MagicMock()
        job.id = job_id
        job.name = kwargs.get("name", "Mock Job")
        job.status = "CREATED"
        job.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        job.updated_at = job.created_at
        job.fasta_path = kwargs.get("fasta_path", "mock.fasta")
        job.config = kwargs.get("config", {})
        job.secret = "mock-secret"
        
        self.jobs[job_id] = job
        return job
    
    def start_job(self, job_id):
        """Mock method to start a job."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        job.status = "RUNNING"
        job.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        job.updated_at = job.started_at
        return job
    
    def check_job_status(self, job_id):
        """Mock method to check job status."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        return self.jobs[job_id]

class MockBaktaJobManager:
    """Mock implementation of BaktaJobManager for testing."""
    
    def __init__(self, **kwargs):
        """Initialize the mock job manager."""
        self.manager = MockBaktaManager()
        self.jobs = {}
        self.history = {}
        self.results = {}
    
    def submit_job(self, fasta_path, name, config=None, **kwargs):
        """Mock method to submit a job."""
        if config is None:
            config = {}
        
        job = self.manager.create_job(
            fasta_path=fasta_path,
            name=name,
            config=config
        )
        
        # Start the job
        job = self.manager.start_job(job.id)
        
        # Store the job
        self.jobs[job.id] = job
        
        # Add to history
        if job.id not in self.history:
            self.history[job.id] = []
        self.history[job.id].append({"status": job.status, "time": job.updated_at})
        
        return job
    
    def check_job_status(self, job_id):
        """Mock method to check job status."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        # Simulate job progression
        job = self.jobs[job_id]
        if job.status == "RUNNING" and "completed" not in job.__dict__:
            # Auto-complete job after first status check
            job.status = "COMPLETED"
            job.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            job.updated_at = job.completed_at
            job.completed = True
            
            # Add to history
            self.history[job.id].append({"status": job.status, "time": job.updated_at})
        
        return job
    
    def wait_for_completion(self, job_id, timeout=None):
        """Mock method to wait for job completion."""
        return self.check_job_status(job_id)
    
    def process_job_results(self, job_id):
        """Mock method to process job results."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        if job.status != "COMPLETED":
            raise ValueError(f"Job {job_id} is not completed")
        
        # Create result files
        result_files = [
            "mock_result.gff3",
            "mock_result.json",
            "mock_result.faa"
        ]
        
        # Create result
        result = {
            "job_id": job_id,
            "downloaded_files": result_files,
            "annotations": 10,
            "sequences": 5,
            "errors": []
        }
        
        self.results[job_id] = result
        return result
    
    def get_jobs(self, limit=10):
        """Mock method to get jobs."""
        return list(self.jobs.values())[:limit]
    
    def get_result(self, job_id):
        """Mock method to get job result."""
        if job_id not in self.results:
            raise ValueError(f"Result for job {job_id} not found")
        
        return self.results[job_id]
    
    def get_status_history(self, job_id):
        """Mock method to get job status history."""
        if job_id not in self.history:
            return []
        
        return self.history[job_id]
    
    def delete_job(self, job_id):
        """Mock method to delete a job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
        if job_id in self.history:
            del self.history[job_id]
        if job_id in self.results:
            del self.results[job_id]

class MockBaktaRepository:
    """Mock implementation of BaktaRepository for testing."""
    
    def __init__(self, **kwargs):
        """Initialize the mock repository."""
        self.annotations = {}
        self.jobs = {}
    
    def query_annotations(
        self,
        job_id,
        conditions=None,
        sort_by=None,
        sort_order="asc",
        limit=None,
        offset=0
    ):
        """Mock method to query annotations."""
        if job_id not in self.annotations:
            return []
        
        # Return mock annotations
        annotations = self._create_mock_annotations(job_id, 10)
        
        # Apply offset and limit
        if offset >= len(annotations):
            return []
        
        start = offset
        end = None if limit is None else start + limit
        
        return annotations[start:end]
    
    def count_annotations(self, job_id, conditions=None):
        """Mock method to count annotations."""
        if job_id not in self.annotations:
            return 0
        
        return len(self._create_mock_annotations(job_id, 10))
    
    def get_feature_types(self, job_id):
        """Mock method to get feature types."""
        return ["CDS", "tRNA", "rRNA"]
    
    def import_results(self, job_id, gff_annotations, json_data):
        """Mock method to import results."""
        # Store annotations
        self.annotations[job_id] = self._create_mock_annotations(job_id, 10)
        return len(self.annotations[job_id])
    
    async def get_jobs(self, limit=10):
        """Mock method to get jobs."""
        # Create mock jobs
        jobs = []
        for i in range(min(limit, 5)):
            job_id = f"mock-job-{i+1}"
            job = BaktaJob(
                id=job_id,
                name=f"Mock Job {i+1}",
                status="COMPLETED",
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                fasta_path="mock.fasta",
                config={},
                secret="mock-secret"
            )
            jobs.append(job)
        
        return jobs
    
    def close(self):
        """Mock method to close the repository."""
        pass
    
    def _create_mock_annotations(self, job_id, count):
        """Create mock annotations for testing."""
        annotations = []
        for i in range(count):
            feature_type = "CDS" if i % 3 == 0 else "tRNA" if i % 3 == 1 else "rRNA"
            strand = "+" if i % 2 == 0 else "-"
            
            annotation = BaktaAnnotation(
                id=f"mock-ann-{job_id}-{i+1}",
                job_id=job_id,
                feature_id=f"{feature_type}_{i+1}",
                feature_type=feature_type,
                contig="contig_1",
                start=i * 100 + 1,
                end=i * 100 + 100,
                strand=strand,
                attributes={"product": f"mock product {i+1}"}
            )
            annotations.append(annotation)
        
        return annotations

class MockGFF3Parser:
    """Mock implementation of GFF3Parser for testing."""
    
    def __init__(self, file_path=None, content=None):
        """Initialize the parser with a file path or content."""
        self.file_path = file_path
        self.content = content
    
    def parse(self, file_path=None):
        """Mock method to parse GFF3 file."""
        # If file_path is provided during parse, use it
        if file_path is not None:
            self.file_path = file_path
        # Return mock data for testing
        return {
            "format": "gff3",
            "metadata": {"version": "3"},
            "sequences": {"contig_1": {"id": "contig_1", "start": 1, "end": 1000, "length": 1000}},
            "features": [
                {
                    "seqid": "contig_1",
                    "source": "bakta",
                    "type": "CDS",
                    "start": 100,
                    "end": 400,
                    "strand": "+",
                    "attributes": {"ID": "CDS_1", "product": "hypothetical protein"}
                },
                {
                    "seqid": "contig_1",
                    "source": "bakta",
                    "type": "tRNA",
                    "start": 500,
                    "end": 600,
                    "strand": "-",
                    "attributes": {"ID": "tRNA_1", "product": "tRNA-Ala"}
                }
            ]
        }

class MockJSONParser:
    """Mock implementation of JSONParser for testing."""
    
    def __init__(self, file_path=None, content=None):
        """Initialize the parser with a file path or content."""
        self.file_path = file_path
        self.content = content
    
    def parse(self, file_path=None):
        """Mock method to parse JSON file."""
        # If file_path is provided during parse, use it
        if file_path is not None:
            self.file_path = file_path
        # Return mock data for testing
        return {
            "name": "Mock Genome",
            "genus": "Mockeria",
            "species": "testis",
            "contigs": [
                {
                    "id": "contig_1",
                    "length": 1000,
                    "coverage": 50.0
                }
            ],
            "features": {
                "CDS": 1,
                "tRNA": 1
            }
        } 