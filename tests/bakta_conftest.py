"""Test fixtures for Bakta API client tests."""

import os
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Tuple

from amr_predictor.bakta import BaktaClient

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data" / "bakta"
os.makedirs(TEST_DATA_DIR, exist_ok=True)

# Sample FASTA data for testing
SAMPLE_FASTA = """>seq1
ATCGATCGATTCGATCGAGGCTAGCTAGCTAGCTAGCGGCGCGCTAGCTATCG
>seq2
GCTAGCTAGCTAGCTACGCGCTATAGCTAGCTAGCTAGCTATATATTTTTTTT
"""

# Sample job configuration
SAMPLE_CONFIG = {
    "genus": "Escherichia",
    "species": "coli",
    "strain": "K-12",
    "locus": "ECO",
    "locus_tag": "ECO",
    "completeGenome": True,
    "translationTable": 11
}

# Sample job response
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

# Sample result file content
SAMPLE_RESULT_FILE_CONTENT = b"Sample result file content"

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

@pytest.fixture
def bakta_data_dir() -> Path:
    """Provide test data directory for Bakta tests."""
    return TEST_DATA_DIR

@pytest.fixture
def sample_fasta() -> str:
    """Provide sample FASTA data."""
    return SAMPLE_FASTA

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide sample job configuration."""
    return SAMPLE_CONFIG.copy()

@pytest.fixture
def sample_job_response() -> Dict[str, Any]:
    """Provide sample job response."""
    return SAMPLE_JOB_RESPONSE.copy()

@pytest.fixture
def sample_status_responses() -> Dict[str, Dict[str, Any]]:
    """Provide sample job status responses."""
    return {k: v.copy() for k, v in SAMPLE_STATUS_RESPONSES.items()}

@pytest.fixture
def sample_results_response() -> Dict[str, Any]:
    """Provide sample job results response."""
    return SAMPLE_RESULTS_RESPONSE.copy()

@pytest.fixture
def sample_logs_response() -> str:
    """Provide sample job logs response."""
    return SAMPLE_LOGS_RESPONSE

@pytest.fixture
def sample_result_file_content() -> bytes:
    """Provide sample result file content."""
    return SAMPLE_RESULT_FILE_CONTENT

@pytest.fixture
def temp_fasta_file() -> Path:
    """Create a temporary FASTA file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(SAMPLE_FASTA)
        fasta_path = Path(f.name)
    yield fasta_path
    if fasta_path.exists():
        fasta_path.unlink()

@pytest.fixture
def mock_response():
    """Create a mock response with customizable status code and content."""
    class MockResponse:
        def __init__(self, status_code=200, content=None, json_data=None):
            self.status_code = status_code
            self.content = content or b""
            self._json_data = json_data
            
        def json(self):
            return self._json_data
            
        def raise_for_status(self):
            if self.status_code >= 400:
                from requests.exceptions import HTTPError
                raise HTTPError(f"HTTP Error: {self.status_code}")
    
    return MockResponse

@pytest.fixture
def mock_bakta_client() -> Tuple[BaktaClient, Dict[str, MagicMock]]:
    """Create a mock BaktaClient with patched requests module."""
    with patch('amr_predictor.bakta.client.requests') as mock_requests:
        client = BaktaClient()
        return client, {"requests": mock_requests} 