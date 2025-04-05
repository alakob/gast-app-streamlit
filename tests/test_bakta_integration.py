"""Integration tests for the Bakta API client.

These tests interact with the real Bakta API and require an internet connection.
They are marked with the 'integration' pytest marker and are skipped by default.
Run with --run-integration to include these tests.
"""

import os
import pytest
import tempfile
from pathlib import Path
import time

from amr_predictor.bakta import (
    BaktaClient,
    create_config,
    validate_fasta,
    BaktaException
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Skip all tests by default
pytest.importorskip("tests.bakta_conftest")

# Small E. coli test sequence for integration testing
ECOLI_TEST_SEQUENCE = """>contig1 Escherichia coli test sequence
ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA
CCCAGGCTTACCTGAACAACGGTTAATAGCCGCGCCGGTCGCGTCCCATCCCGGCCAGCGTTAACG
GCGGTTTGCAGCTGTTGCATGATGAACAAAGCAACAACAACGACAATCTGCGCGTTCGTTACGCAG
GTGTTTCGATACAGCCTGGCAAGTTCGCGCGAGAAACCGAATCCCGTCTTCACGCGGGTACCGAGA
TCCTGATGTCCGAACAATGGTTCCTGGCGGTTAGCCAGACCACCGATCTGCGTGACGGTCTGTACC
AGACCCGTCAGCAGTTCGAAGCACAGGCTCAAACGTCAGGCAGCAGCGTCTAACGTGAAAGCCGGG
GCTGAAAACGTCTACCTGACGGTAATGTCTGCTCCGAATAACAGCGCATTACCTTATGCGGACCAT
TTCTCCGGTTCCGGCCTGCAATCCGTGTTCGATAACGCGCTGATGCGTCGTATTGCCGGACAGGGT
GAAAACCCGGCAGACACCTGTGCGTCCGTTGTGCTGAATGAATCCGGTTCGTGGGTGAAAACCGTC
GAAAACGCAGAAGTGGCGGCGTTCAGCCATCCGGCACGTATCGCGGTGGAAAGCGACATTCCGGGT
ACGCTTACCCAGTTTGATACGGGTGAAAACCTGCTGGAAAGCGCGCTGCTGGCACCGGGTGGCCCG
CAGTCGGTGTTTATTCGTGAAGGTGAAGTGGCGGAAACCGCGTCAGCTGCGTCCGTCGCCACGTTC
CGCGTCGTCGTTAGCGGTAAAACCGGTCGTCCGGTACGTGAAGCGTCCTTTGAAACCGGTTCCGCC
TGTGCGAACTCCGGTGTTCTGCCACGTGAACGTCTGATTCAGGTTGAGTGGGATTCAACCGTTGAA
ATTGTGACCTGGTTTGATGAAGTTCATAACAGTATGGGCGTGGATAATCCGCTGTAA
"""

# Skip if no internet connection or API key
def has_internet_connection():
    """Check if there is an internet connection."""
    import socket
    try:
        # Try to connect to a reliable host
        socket.create_connection(("api.bakta.computational.bio", 443), timeout=5)
        return True
    except (socket.timeout, socket.error):
        return False

@pytest.fixture
def ecoli_fasta_file():
    """Create a temporary FASTA file with an E. coli test sequence."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(ECOLI_TEST_SEQUENCE)
        fasta_path = Path(f.name)
    yield fasta_path
    if fasta_path.exists():
        fasta_path.unlink()

@pytest.fixture
def bakta_client():
    """Create a BaktaClient for integration testing."""
    # Use the default API URL unless specified in environment
    api_url = os.environ.get("BAKTA_API_URL_TEST", None)
    api_key = os.environ.get("BAKTA_API_KEY_TEST", None)
    
    return BaktaClient(api_url=api_url, api_key=api_key)

@pytest.mark.skipif(not has_internet_connection(), reason="No internet connection")
def test_bakta_api_available():
    """Test that the Bakta API is available."""
    import requests
    
    # Try to access the API version endpoint
    url = "https://api.bakta.computational.bio/api/v1/version"
    try:
        response = requests.get(url, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "toolVersion" in data
        assert "dbVersion" in data
        assert "backendVersion" in data
    except requests.RequestException as e:
        pytest.skip(f"Bakta API is not available: {str(e)}")

@pytest.mark.skipif(not has_internet_connection(), reason="No internet connection")
def test_validate_real_fasta_file(ecoli_fasta_file):
    """Test validation of a real FASTA file."""
    # Should not raise any exception
    validate_fasta(str(ecoli_fasta_file))
    
    # Check with is_valid_fasta
    from amr_predictor.bakta import is_valid_fasta
    assert is_valid_fasta(str(ecoli_fasta_file)) is True

@pytest.mark.skipif(not has_internet_connection(), reason="No internet connection")
def test_initialize_job(bakta_client):
    """Test initializing a job with the real API."""
    try:
        job_result = bakta_client.initialize_job("integration_test_job")
        
        # Verify the response format
        assert "job_id" in job_result
        assert "secret" in job_result
        assert "upload_link" in job_result
        
        # Verify that the job ID is a UUID
        assert len(job_result["job_id"]) == 36
        assert "-" in job_result["job_id"]
    except BaktaException as e:
        if "rate limit" in str(e).lower():
            pytest.skip("API rate limit reached")
        else:
            raise

@pytest.mark.skipif(not has_internet_connection(), reason="No internet connection")
def test_job_workflow(bakta_client, ecoli_fasta_file):
    """Test the complete job workflow with the real API."""
    # Create a configuration
    config = create_config(
        genus="Escherichia",
        species="coli",
        strain="Test",
        locus="ECO",
        locus_tag="ECO",
        complete_genome=False,
        translation_table=11
    )
    
    try:
        # Submit a job
        job_result = bakta_client.initialize_job("integration_test_job")
        
        # Upload the FASTA file
        bakta_client.upload_fasta(job_result["upload_link"], str(ecoli_fasta_file))
        
        # Start the job
        bakta_client.start_job(job_result["job_id"], job_result["secret"], config)
        
        # Check the job status
        status = bakta_client.check_job_status(job_result["job_id"], job_result["secret"])
        
        # Verify that the job was started
        assert status in ["INIT", "RUNNING", "SUCCESSFUL"]
        
        # To avoid long-running tests, we won't wait for the job to complete
        # Instead, we'll just verify that we can poll the status
        
        # Poll the job status a few times (with a short timeout)
        try:
            for _ in range(3):
                status = bakta_client.check_job_status(job_result["job_id"], job_result["secret"])
                if status == "SUCCESSFUL":
                    break
                time.sleep(5)
        except BaktaException as e:
            # It's okay if the job fails or times out, we're just testing the API interaction
            pass
        
        # If the job completed successfully, try to get the results
        if status == "SUCCESSFUL":
            results = bakta_client.get_job_results(job_result["job_id"], job_result["secret"])
            assert "result_files" in results
            assert "job_id" in results
    except BaktaException as e:
        if "rate limit" in str(e).lower():
            pytest.skip("API rate limit reached")
        else:
            raise

# This test is disabled by default as it would download files
@pytest.mark.skip(reason="This test downloads files and is disabled by default")
def test_download_results(bakta_client, tmp_path):
    """Test downloading result files from a completed job."""
    # You would need a completed job ID and secret to run this test
    job_id = os.environ.get("BAKTA_TEST_JOB_ID", None)
    secret = os.environ.get("BAKTA_TEST_JOB_SECRET", None)
    
    if not job_id or not secret:
        pytest.skip("No test job ID and secret provided")
    
    try:
        # Get job results
        results = bakta_client.get_job_results(job_id, secret)
        
        # Check if there are any result files
        if not results.get("result_files"):
            pytest.skip("No result files available")
        
        # Download one of the result files
        result_file_url = next(iter(results["result_files"].values()))
        output_path = tmp_path / "result_file"
        
        bakta_client.download_result_file(result_file_url, str(output_path))
        
        # Verify that the file was downloaded
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    except BaktaException as e:
        if "rate limit" in str(e).lower():
            pytest.skip("API rate limit reached")
        else:
            raise 