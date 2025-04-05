#!/usr/bin/env python3
"""
Test fixtures for Bakta tests.

This module provides fixtures for setting up test environments,
temporary directories, and test data for Bakta tests.
"""

import os
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any, Tuple, List, Optional, Generator
import logging
import shutil

from amr_predictor.bakta import BaktaClient
from amr_predictor.bakta.repository import BaktaRepository
from amr_predictor.bakta.models import (
    BaktaJob, BaktaSequence, BaktaAnnotation, BaktaResultFile
)

# Test data paths
CURRENT_DIR = Path(__file__).parent
TEST_DATA_DIR = CURRENT_DIR / "data"

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

# Sample API response content
SAMPLE_INIT_RESPONSE = {
    "job": {
        "jobID": "test-job-id",
        "secret": "test-job-secret"
    },
    "uploadLinkFasta": "https://example.com/upload/fasta"
}

SAMPLE_JOB_STATUS_RESPONSE = {
    "jobs": [
        {
            "jobID": "test-job-id",
            "jobStatus": "COMPLETED"
        }
    ]
}

SAMPLE_RESULT_FILE_CONTENT = {
    "jobID": "test-job-id",
    "ResultFiles": {
        "gff3": "https://example.com/results/output.gff3",
        "json": "https://example.com/results/output.json"
    }
}

# Sample job configuration
SAMPLE_JOB_RESPONSE = {
    "job": {
        "jobID": "123e4567-e89b-12d3-a456-426614174000",
        "secret": "sample-secret"
    },
    "uploadLinkFasta": "https://example.com/upload/fasta",
    "uploadLinkProdigal": "https://example.com/upload/prodigal",
    "uploadLinkReplicons": "https://example.com/upload/replicons"
}

# Sample job status response
SAMPLE_STATUS_RESPONSES = {
    "INIT": {
        "jobs": [
            {
                "jobID": "123e4567-e89b-12d3-a456-426614174000",
                "jobStatus": "INIT",
                "started": "2023-01-01T00:00:00Z",
                "updated": "2023-01-01T00:00:01Z",
                "name": "test_job"
            }
        ],
        "failedJobs": []
    },
    "RUNNING": {
        "jobs": [
            {
                "jobID": "123e4567-e89b-12d3-a456-426614174000",
                "jobStatus": "RUNNING",
                "started": "2023-01-01T00:00:00Z",
                "updated": "2023-01-01T00:00:05Z",
                "name": "test_job"
            }
        ],
        "failedJobs": []
    },
    "SUCCESSFUL": {
        "jobs": [
            {
                "jobID": "123e4567-e89b-12d3-a456-426614174000",
                "jobStatus": "SUCCESSFUL",
                "started": "2023-01-01T00:00:00Z",
                "updated": "2023-01-01T00:00:10Z",
                "name": "test_job"
            }
        ],
        "failedJobs": []
    },
    "ERROR": {
        "jobs": [
            {
                "jobID": "123e4567-e89b-12d3-a456-426614174000",
                "jobStatus": "ERROR",
                "started": "2023-01-01T00:00:00Z",
                "updated": "2023-01-01T00:00:15Z",
                "name": "test_job"
            }
        ],
        "failedJobs": []
    }
}

# Sample job results response
SAMPLE_RESULTS_RESPONSE = {
    "ResultFiles": {
        "EMBL": "https://example.com/results/output.embl",
        "FAA": "https://example.com/results/output.faa",
        "FAAHypothetical": "https://example.com/results/output.hypothetical.faa",
        "FFN": "https://example.com/results/output.ffn",
        "FNA": "https://example.com/results/output.fna",
        "GBFF": "https://example.com/results/output.gbff",
        "GFF3": "https://example.com/results/output.gff3",
        "JSON": "https://example.com/results/output.json",
        "PNGCircularPlot": "https://example.com/results/output.png",
        "SVGCircularPlot": "https://example.com/results/output.svg",
        "TSV": "https://example.com/results/output.tsv",
        "TSVHypothetical": "https://example.com/results/output.hypothetical.tsv",
        "TSVInference": "https://example.com/results/output.inference.tsv",
        "TXTLogs": "https://example.com/results/output.txt"
    },
    "jobID": "123e4567-e89b-12d3-a456-426614174000",
    "name": "test_job",
    "started": "2023-01-01T00:00:00Z",
    "updated": "2023-01-01T00:00:10Z"
}

# Sample logs response
SAMPLE_LOGS_RESPONSE = """
Bakta Command: bakta --tmp-dir /cache --threads 8 --prefix result -o /results --db /db/db --genus Escherichia --species coli --strain K-12 --locus ECO --locus-tag ECO --complete --translation-table 11 /data/fastadata.fasta --force
Parse genome sequences...
    imported: 86
    filtered & revised: 86
    contigs: 86

Start annotation...
predict tRNAs...
    found: 78
predict tmRNAs...
    found: 1
predict rRNAs...
    found: 3
"""

# Register integration marker
def pytest_addoption(parser):
    """Add custom command line options to pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that interact with the Bakta API"
    )
    parser.addoption(
        "--bakta-api-key",
        action="store",
        default=None,
        help="API key to use for Bakta API tests"
    )
    parser.addoption(
        "--bakta-environment",
        action="store",
        default="dev",
        help="Bakta environment to use for tests (dev, staging, prod)"
    )

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "client: mark test as requiring a BaktaClient")
    config.addinivalue_line("markers", "repository: mark test as requiring a BaktaRepository")
    config.addinivalue_line("markers", "database: mark test as requiring a database")
    config.addinivalue_line(
        "markers", "system: mark a test as a system integration test"
    )

def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is specified."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="Need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bakta-tests")

@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test artifacts.
    
    Yields:
        Path to the temporary directory
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="bakta_test_")
    temp_path = Path(temp_dir)
    
    logger.info(f"Created temporary directory: {temp_path}")
    
    yield temp_path
    
    # Clean up unless KEEP_TEST_FILES is set
    if os.environ.get("KEEP_TEST_FILES") != "1":
        shutil.rmtree(temp_path, ignore_errors=True)
        logger.info(f"Removed temporary directory: {temp_path}")
    else:
        logger.info(f"Kept temporary directory: {temp_path}")

@pytest.fixture(scope="session")
def temp_db_path(temp_dir: Path) -> Path:
    """
    Create a path for a temporary SQLite database.
    
    Args:
        temp_dir: Temporary directory from the temp_dir fixture
    
    Returns:
        Path to the SQLite database file
    """
    db_path = temp_dir / "test_bakta.db"
    return db_path

@pytest.fixture
def temp_file():
    """Create a temporary file."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file_path = Path(tmp_file.name)
    
    yield file_path
    
    # Clean up
    if file_path.exists():
        os.unlink(file_path)

@pytest.fixture
def temp_fasta_file(temp_dir):
    """Create a temporary FASTA file with sample content."""
    fasta_path = temp_dir / "test.fasta"
    with open(fasta_path, "w") as f:
        f.write(SAMPLE_FASTA)
    yield fasta_path
    if fasta_path.exists():
        os.unlink(fasta_path)

@pytest.fixture
def sample_job():
    """Create a sample BaktaJob instance."""
    return BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="INIT",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00",
        fasta_path="/path/to/test.fasta"
    )

@pytest.fixture
def sample_sequence():
    """Create a sample BaktaSequence instance."""
    return BaktaSequence(
        job_id="test-job-123",
        header="contig1",
        sequence="ATGCATGCATGC",
        length=12,
        gc_content=0.5,
        n_count=0
    )

@pytest.fixture
def sample_annotation():
    """Create a sample BaktaAnnotation instance."""
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
    """Create a sample BaktaResultFile instance."""
    return BaktaResultFile(
        job_id="test-job-123",
        file_type="GFF3",
        file_path="/path/to/results/output.gff3",
        downloaded_at="2023-01-01T00:00:00",
        download_url="https://example.com/results/output.gff3"
    )

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
    
    # Mock job retrieval
    repo.get_job.return_value = BaktaJob(
        id="test-job-123",
        name="Test Job",
        secret="test-secret-456",
        status="COMPLETED",
        config=SAMPLE_CONFIG,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-02T00:00:00"
    )
    
    # Mock sequence retrieval
    repo.get_sequences.return_value = [
        BaktaSequence(
            job_id="test-job-123",
            header="contig1",
            sequence="ATGCATGCATGC",
            length=12
        )
    ]
    
    # Mock job status update
    repo.update_job_status.return_value = True
    
    return repo

@pytest.fixture
def bakta_data_dir() -> Path:
    """Return the path to the test data directory."""
    return TEST_DATA_DIR

@pytest.fixture
def bakta_init_response() -> Dict[str, Any]:
    """Return a sample job initialization response."""
    return SAMPLE_INIT_RESPONSE

@pytest.fixture
def bakta_job_status_response() -> Dict[str, Any]:
    """Return a sample job status response."""
    return SAMPLE_JOB_STATUS_RESPONSE

@pytest.fixture
def bakta_result_file_response() -> Dict[str, Any]:
    """Return a sample result file response."""
    return SAMPLE_RESULT_FILE_CONTENT

@pytest.fixture
def mock_response():
    """Create a mock response object for HTTP requests."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    response.text = '{"success": true}'
    return response

@pytest.fixture
def mock_bakta_client() -> Tuple[BaktaClient, Dict[str, Any]]:
    """Create a mocked BaktaClient with patched requests for testing."""
    with patch("amr_predictor.bakta.client.requests") as mock_requests:
        # Mock HTTP responses 
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = '{"success": true}'
        
        # Setup mock requests
        mock_requests.post.return_value = mock_response
        mock_requests.get.return_value = mock_response
        
        # Create client with mocked requests
        client = BaktaClient()
        return client, {"requests": mock_requests}

@pytest.fixture
def bakta_api_key(request):
    """Get the Bakta API key from the command line or environment variable."""
    api_key = request.config.getoption("--bakta-api-key")
    if api_key is None:
        api_key = os.environ.get("BAKTA_API_KEY")
    return api_key

@pytest.fixture
def bakta_environment(request):
    """Get the Bakta environment from the command line or environment variable."""
    env = request.config.getoption("--bakta-environment")
    if env is None:
        env = os.environ.get("BAKTA_ENVIRONMENT", "dev")
    return env

@pytest.fixture
def real_client(bakta_api_key, bakta_environment):
    """Create a real BaktaClient for integration tests."""
    if bakta_api_key is None:
        pytest.skip("No Bakta API key provided")
    return BaktaClient(environment=bakta_environment, api_key=bakta_api_key) 