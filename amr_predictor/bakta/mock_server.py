#!/usr/bin/env python3
"""
Mock implementation for Bakta API to allow for local development and testing.
This module intercepts and handles requests to the Bakta API when the real API
is not available or connection fails.
"""

import os
import json
import uuid
import logging
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

from amr_predictor.bakta.models import BaktaJob, JobStatus, BaktaFileType

# Configure logging
logger = logging.getLogger("bakta-mock")

class BaktaMockServer:
    """
    Mock implementation of the Bakta API server.
    Simulates the behavior of the Bakta API for local development and testing.
    """
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        Initialize the mock server with optional results directory.
        
        Args:
            results_dir: Directory to store mock results
        """
        self.results_dir = results_dir or os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # In-memory job storage
        self.jobs: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"✓ Initialized Bakta mock server with results dir: {self.results_dir}")
    
    def authenticate(self, api_key: str) -> Dict[str, Any]:
        """
        Simulate authentication to the Bakta API.
        
        Args:
            api_key: API key for authentication
            
        Returns:
            Dict with access token and expiry
        """
        logger.info(f"Mock authentication with API key: {api_key[:5]}...")
        return {
            "access_token": f"mock_token_{uuid.uuid4()}",
            "expires_in": 3600
        }
    
    def submit_job(self, fasta_data: Union[str, Path], job_name: str, config: Dict) -> str:
        """
        Submit a mock job to the Bakta API.
        
        Args:
            fasta_data: Path to FASTA file or FASTA content
            job_name: Name for the job
            config: Job configuration parameters
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Store job metadata
        self.jobs[job_id] = {
            "id": job_id,
            "name": job_name,
            "status": JobStatus.CREATED.value,
            "created_at": time.time(),
            "updated_at": time.time(),
            "config": config,
            "progress": 0
        }
        
        # Create results directory
        job_dir = Path(self.results_dir) / job_id
        job_dir.mkdir(exist_ok=True)
        
        # Store input FASTA
        fasta_path = job_dir / "input.fasta"
        if isinstance(fasta_data, Path) or os.path.exists(str(fasta_data)):
            with open(fasta_data, 'r') as f:
                fasta_content = f.read()
        else:
            fasta_content = fasta_data
        
        with open(fasta_path, 'w') as f:
            f.write(fasta_content)
        
        logger.info(f"✓ Submitted mock job: {job_id} ({job_name})")
        
        # Start mock processing in the "background"
        self._start_processing(job_id)
        
        return job_id
    
    def _start_processing(self, job_id: str):
        """
        Start mock processing for a job.
        In a real implementation, this would be a background task.
        
        Args:
            job_id: Job ID to process
        """
        # Update job status
        self.jobs[job_id]["status"] = JobStatus.RUNNING.value
        self.jobs[job_id]["updated_at"] = time.time()
        self.jobs[job_id]["progress"] = 10
        
        # In real implementation, this would start a background task
        # For mock, we just simulate status updates over time
        
        # Generate mock results on first call
        self._generate_mock_results(job_id)
    
    def _generate_mock_results(self, job_id: str):
        """
        Generate mock annotation results.
        
        Args:
            job_id: Job ID to generate results for
        """
        job_dir = Path(self.results_dir) / job_id
        
        # Generate a simple GFF3 file
        gff_path = job_dir / f"{job_id}.gff3"
        with open(gff_path, 'w') as f:
            f.write("""##gff-version 3
##sequence-region contig1 1 10000
contig1\tBakta\tCDS\t1000\t2000\t.\t+\t0\tID=CDS_1;product=Hypothetical protein
contig1\tBakta\tgene\t3000\t4000\t.\t+\t0\tID=gene_1;Name=dnaA;product=DNA replication initiator
contig1\tBakta\trRNA\t5000\t6000\t.\t-\t0\tID=rRNA_1;product=16S ribosomal RNA
""")
        
        # Generate a simple JSON results file
        json_path = job_dir / f"{job_id}.json"
        with open(json_path, 'w') as f:
            json.dump({
                "jobId": job_id,
                "name": self.jobs[job_id]["name"],
                "annotations": [
                    {
                        "id": "CDS_1",
                        "type": "CDS",
                        "start": 1000,
                        "end": 2000,
                        "strand": "+",
                        "product": "Hypothetical protein"
                    },
                    {
                        "id": "gene_1",
                        "type": "gene",
                        "start": 3000,
                        "end": 4000,
                        "strand": "+",
                        "name": "dnaA",
                        "product": "DNA replication initiator"
                    },
                    {
                        "id": "rRNA_1",
                        "type": "rRNA",
                        "start": 5000,
                        "end": 6000,
                        "strand": "-",
                        "product": "16S ribosomal RNA"
                    }
                ],
                "statistics": {
                    "totalSequences": 1,
                    "totalGenes": 3,
                    "cds": 1,
                    "rRNA": 1,
                    "gene": 1
                }
            }, f, indent=2)
        
        # Update job metadata to set as completed after a delay
        self.jobs[job_id]["progress"] = 100
        self.jobs[job_id]["status"] = JobStatus.COMPLETED.value
        self.jobs[job_id]["updated_at"] = time.time()
        
        logger.info(f"✓ Generated mock results for job: {job_id}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a job.
        
        Args:
            job_id: Job ID to get status for
            
        Returns:
            Dict with job status information
        """
        if job_id not in self.jobs:
            logger.warning(f"Job not found: {job_id}")
            return {"status": JobStatus.NOT_FOUND.value}
        
        job = self.jobs[job_id]
        
        # If job is running, update progress
        if job["status"] == JobStatus.RUNNING.value:
            progress = job["progress"]
            # Simulate progress increase
            if progress < 100:
                progress += random.randint(5, 15)
                if progress >= 100:
                    progress = 100
                    job["status"] = JobStatus.COMPLETED.value
                job["progress"] = progress
                job["updated_at"] = time.time()
        
        return {
            "id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"]
        }
    
    def get_job_results(self, job_id: str, file_type: BaktaFileType = BaktaFileType.JSON) -> str:
        """
        Get the results of a completed job.
        
        Args:
            job_id: Job ID to get results for
            file_type: Type of result file to retrieve
            
        Returns:
            File content as string
        """
        if job_id not in self.jobs:
            logger.warning(f"Job not found: {job_id}")
            raise FileNotFoundError(f"Job not found: {job_id}")
        
        job = self.jobs[job_id]
        if job["status"] != JobStatus.COMPLETED.value:
            logger.warning(f"Job not completed: {job_id} (status: {job['status']})")
            raise RuntimeError(f"Job not completed: {job_id}")
        
        # Get the appropriate file extension
        ext = file_type.value.lower()
        
        # Construct path to result file
        job_dir = Path(self.results_dir) / job_id
        result_path = job_dir / f"{job_id}.{ext}"
        
        if not result_path.exists():
            logger.warning(f"Result file not found: {result_path}")
            raise FileNotFoundError(f"Result file not found: {result_path}")
        
        # Return file content
        with open(result_path, 'r') as f:
            content = f.read()
        
        return content

# Create a global instance
mock_server = BaktaMockServer()

def get_mock_server() -> BaktaMockServer:
    """
    Get the mock server instance.
    
    Returns:
        Mock server instance
    """
    global mock_server
    return mock_server
