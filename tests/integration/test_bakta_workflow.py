#!/usr/bin/env python3
"""
Integration tests for the Bakta annotation workflow.

This module provides integration tests for the Bakta annotation workflow,
including job submission, status checking, result downloading, and annotation parsing.
"""

import os
import sys
import asyncio
import unittest
from pathlib import Path
import tempfile
import shutil
import json
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path for importing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from amr_predictor.bakta.job_manager import BaktaJobManager
from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.repository_postgres import BaktaRepository
from amr_predictor.bakta.database_postgres import DatabaseManager
from amr_predictor.bakta.models import BaktaJob, BaktaAnnotation
from amr_predictor.bakta.exceptions import BaktaException, BaktaJobError

# Test fixtures
TEST_FASTA_CONTENT = """>Seq1 example sequence
ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT
CGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
>Seq2 example sequence
GCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCAT
GCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC
"""

TEST_CONFIG = {
    "genus": "Test",
    "species": "testus",
    "strain": "test123",
    "completeGenome": False,
    "dermType": "DIDERM",
    "translationTable": 11
}

TEST_GFF_CONTENT = """##gff-version 3
contig_1\tBakta\tCDS\t1\t300\t.\t+\t0\tID=test_cds_1;product=Hypothetical protein;locus_tag=TESTLOCUS_00001
contig_1\tBakta\ttRNA\t400\t475\t.\t-\t.\tID=test_trna_1;product=tRNA-Ala;locus_tag=TESTLOCUS_00002
contig_1\tBakta\trRNA\t600\t1100\t.\t+\t.\tID=test_rrna_1;product=16S ribosomal RNA;locus_tag=TESTLOCUS_00003
"""

TEST_JSON_CONTENT = """{
    "genome": {
        "genus": "Test",
        "species": "testus",
        "strain": "test123"
    },
    "stats": {
        "size": 450,
        "contigs": 2,
        "genes": 3,
        "cds": 1,
        "rnas": 2
    },
    "features": [
        {
            "id": "test_cds_1",
            "type": "cds",
            "contig": "contig_1",
            "start": 1,
            "stop": 300,
            "strand": "+",
            "product": "Hypothetical protein",
            "locus_tag": "TESTLOCUS_00001"
        },
        {
            "id": "test_trna_1",
            "type": "trna",
            "contig": "contig_1",
            "start": 400,
            "stop": 475,
            "strand": "-",
            "product": "tRNA-Ala",
            "locus_tag": "TESTLOCUS_00002"
        },
        {
            "id": "test_rrna_1",
            "type": "rrna",
            "contig": "contig_1",
            "start": 600,
            "stop": 1100,
            "strand": "+",
            "product": "16S ribosomal RNA",
            "locus_tag": "TESTLOCUS_00003"
        }
    ]
}"""

class TestBaktaWorkflow(unittest.TestCase):
    """Integration tests for the Bakta annotation workflow."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory for test files
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create mock FASTA file
        self.fasta_path = self.test_dir / "test.fasta"
        with open(self.fasta_path, "w") as f:
            f.write(TEST_FASTA_CONTENT)
            
        # Create mock result files
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.gff_path = self.results_dir / "results.gff3"
        with open(self.gff_path, "w") as f:
            f.write(TEST_GFF_CONTENT)
            
        self.json_path = self.results_dir / "results.json"
        with open(self.json_path, "w") as f:
            f.write(TEST_JSON_CONTENT)
            
        # Set up test environment
        os.environ["ENVIRONMENT"] = "test"
        os.environ["BAKTA_API_URL_TEST"] = "https://test-api.bakta.computational.bio/api/v1"
        os.environ["BAKTA_API_KEY"] = "test_api_key"
        
        # Create mock repository, client, and job manager
        self.mock_repository = self.create_mock_repository()
        self.mock_client = self.create_mock_client()
        self.job_manager = BaktaJobManager(
            client=self.mock_client,
            repository=self.mock_repository,
            results_dir=self.results_dir,
            environment="test"
        )
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temp directory
        shutil.rmtree(self.test_dir)
        
    def create_mock_repository(self):
        """Create a mock repository for testing."""
        mock_repo = AsyncMock(spec=BaktaRepository)
        
        # Set up get_job to return a mock job
        mock_repo.get_job.return_value = BaktaJob(
            id="test-job-123",
            name="Test Job",
            status="COMPLETED",
            config=TEST_CONFIG,
            secret="test-secret",
            fasta_path=str(self.fasta_path),
            created_at="2023-01-01T00:00:00Z"
        )
        
        # Set up get_feature_types to return mock feature types
        mock_repo.get_feature_types.return_value = ["CDS", "tRNA", "rRNA"]
        
        # Set up query_annotations to return mock annotations
        mock_repo.query_annotations.return_value = [
            BaktaAnnotation(
                id=1,
                job_id="test-job-123",
                feature_id="test_cds_1",
                feature_type="CDS",
                contig="contig_1",
                start=1,
                end=300,
                strand="+",
                attributes={
                    "product": "Hypothetical protein",
                    "locus_tag": "TESTLOCUS_00001"
                }
            ),
            BaktaAnnotation(
                id=2,
                job_id="test-job-123",
                feature_id="test_trna_1",
                feature_type="tRNA",
                contig="contig_1",
                start=400,
                end=475,
                strand="-",
                attributes={
                    "product": "tRNA-Ala",
                    "locus_tag": "TESTLOCUS_00002"
                }
            )
        ]
        
        # Set up count_annotations to return mock count
        mock_repo.count_annotations.return_value = 2
        
        return mock_repo
    
    def create_mock_client(self):
        """Create a mock API client for testing."""
        mock_client = AsyncMock(spec=BaktaClient)
        
        # Set up submit_job to return mock job data
        mock_client.submit_job.return_value = {
            "id": "test-job-123",
            "secret": "test-secret"
        }
        
        # Set up get_job_status to return mock status
        mock_client.get_job_status.return_value = {
            "status": "finished"
        }
        
        # Set up get_job_results to return mock download URLs
        mock_client.get_job_results.return_value = {
            "gff3": "https://example.com/results.gff3",
            "json": "https://example.com/results.json"
        }
        
        return mock_client
    
    async def test_submit_job(self):
        """Test job submission."""
        # Submit job
        job = await self.job_manager.submit_job(
            job_name="Test Job",
            fasta_path=self.fasta_path,
            config=TEST_CONFIG
        )
        
        # Verify job was submitted correctly
        self.mock_client.submit_job.assert_called_once()
        self.mock_repository.save_job.assert_called_once()
        
        # Check job properties
        self.assertEqual(job.id, "test-job-123")
        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.status, "CREATED")
        self.assertEqual(job.secret, "test-secret")
    
    async def test_get_job_status(self):
        """Test getting job status."""
        # Get status
        status = await self.job_manager.get_job_status("test-job-123")
        
        # Verify status was retrieved correctly
        self.mock_client.get_job_status.assert_called_once()
        self.mock_repository.update_job_status.assert_called_once()
        
        # Check status
        self.assertEqual(status, "COMPLETED")
    
    async def test_get_job(self):
        """Test getting job details."""
        # Get job
        job = await self.job_manager.get_job("test-job-123")
        
        # Verify job was retrieved correctly
        self.mock_repository.get_job.assert_called_once()
        
        # Check job properties
        self.assertEqual(job.id, "test-job-123")
        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.status, "COMPLETED")
    
    async def test_download_results(self):
        """Test downloading job results."""
        # Mock the download process to use our test files
        with patch("aiohttp.ClientSession") as mock_session:
            # Configure mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b"mock content"
            
            # Configure mock context managers
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Download results
            result_files = await self.job_manager.download_results("test-job-123")
            
            # Verify results were downloaded correctly
            self.mock_client.get_job_results.assert_called_once()
            self.mock_repository.save_result_file.assert_called()
            
            # Check result files
            self.assertTrue("gff3" in result_files)
            self.assertTrue("json" in result_files)
    
    async def test_import_annotations(self):
        """Test importing annotations from result files."""
        # Import annotations
        count = await self.job_manager.import_annotations(
            job_id="test-job-123",
            gff_file=self.gff_path,
            json_file=self.json_path
        )
        
        # Verify annotations were imported correctly
        self.mock_repository.import_results.assert_called_once()
        
        # The mock repository is set up to return 100 from import_results
        self.assertIsNotNone(count)
    
    async def test_get_annotations(self):
        """Test getting annotations."""
        # Get annotations
        annotations = await self.job_manager.get_annotations(
            job_id="test-job-123",
            feature_type="CDS",
            limit=10,
            offset=0
        )
        
        # Verify annotations were retrieved correctly
        self.mock_repository.query_annotations.assert_called_once()
        
        # Check annotations
        self.assertEqual(len(annotations), 2)  # Our mock returns 2 annotations
        self.assertEqual(annotations[0].feature_type, "CDS")
        self.assertEqual(annotations[0].feature_id, "test_cds_1")
    
    async def test_get_feature_types(self):
        """Test getting feature types."""
        # Get feature types
        feature_types = await self.job_manager.get_feature_types("test-job-123")
        
        # Verify feature types were retrieved correctly
        self.mock_repository.get_feature_types.assert_called_once()
        
        # Check feature types
        self.assertEqual(feature_types, ["CDS", "tRNA", "rRNA"])
    
    async def test_complete_workflow(self):
        """Test the complete workflow from submission to results."""
        # 1. Submit job
        job = await self.job_manager.submit_job(
            job_name="Test Workflow Job",
            fasta_path=self.fasta_path,
            config=TEST_CONFIG
        )
        
        # 2. Check status until completed
        status = await self.job_manager.get_job_status(job.id)
        self.assertEqual(status, "COMPLETED")
        
        # 3. Download results
        with patch("aiohttp.ClientSession") as mock_session:
            # Configure mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b"mock content"
            
            # Configure mock context managers
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Download results
            result_files = await self.job_manager.download_results(job.id)
            
            # Check result files
            self.assertTrue("gff3" in result_files)
            self.assertTrue("json" in result_files)
        
        # 4. Import annotations
        count = await self.job_manager.import_annotations(
            job_id=job.id,
            gff_file=self.gff_path,
            json_file=self.json_path
        )
        self.assertIsNotNone(count)
        
        # 5. Get annotations
        annotations = await self.job_manager.get_annotations(
            job_id=job.id,
            limit=10,
            offset=0
        )
        self.assertEqual(len(annotations), 2)

# Run tests
if __name__ == "__main__":
    # Set up asyncio test loop
    def run_async_test(test_case, test_name):
        test_method = getattr(test_case, test_name)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_method())
        finally:
            loop.close()
    
    # Create test suite with async methods
    suite = unittest.TestSuite()
    test_case = TestBaktaWorkflow("test_submit_job")
    test_case.test_submit_job = lambda: run_async_test(test_case, "test_submit_job")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_get_job_status")
    test_case.test_get_job_status = lambda: run_async_test(test_case, "test_get_job_status")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_get_job")
    test_case.test_get_job = lambda: run_async_test(test_case, "test_get_job")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_download_results")
    test_case.test_download_results = lambda: run_async_test(test_case, "test_download_results")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_import_annotations")
    test_case.test_import_annotations = lambda: run_async_test(test_case, "test_import_annotations")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_get_annotations")
    test_case.test_get_annotations = lambda: run_async_test(test_case, "test_get_annotations")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_get_feature_types")
    test_case.test_get_feature_types = lambda: run_async_test(test_case, "test_get_feature_types")
    suite.addTest(test_case)
    
    test_case = TestBaktaWorkflow("test_complete_workflow")
    test_case.test_complete_workflow = lambda: run_async_test(test_case, "test_complete_workflow")
    suite.addTest(test_case)
    
    # Run tests
    runner = unittest.TextTestRunner()
    runner.run(suite)
