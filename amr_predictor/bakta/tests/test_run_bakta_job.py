"""Tests for the run_bakta_job.py example script."""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the examples directory to sys.path so we can import the script
sys.path.append(str(Path(__file__).parent.parent / "examples"))

# Import the script functions
from run_bakta_job import run_bakta_job, parse_arguments

# Sample FASTA content for testing
SAMPLE_FASTA = """>contig1 Escherichia coli test sequence
ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA
CCCAGGCTTACCTGAACAACGGTTAATAGCCGCGCCGGTCGCGTCCCATCCCGGCCAGCGTTAACG"""

@pytest.fixture
def sample_fasta_file():
    """Create a temporary FASTA file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(SAMPLE_FASTA)
        fasta_path = Path(f.name)
    
    yield fasta_path
    
    if fasta_path.exists():
        fasta_path.unlink()

@pytest.fixture
def mock_args():
    """Create a mock args object for testing."""
    args = MagicMock()
    args.fasta_file = "/path/to/test.fasta"
    args.output_dir = "/path/to/output"
    args.genus = "Escherichia"
    args.species = "coli"
    args.strain = "test"
    args.complete = False
    args.translation_table = 11
    args.locus = "TEST"
    args.locus_tag = "TEST"
    args.environment = "prod"
    args.timeout = 300
    args.poll_interval = 5
    args.max_poll_time = 20
    return args

def test_parse_arguments():
    """Test argument parsing with default values."""
    # Mock sys.argv
    with patch('sys.argv', ['run_bakta_job.py', 'test.fasta', 'output_dir']):
        args = parse_arguments()
        
        # Check that required arguments are parsed
        assert args.fasta_file == 'test.fasta'
        assert args.output_dir == 'output_dir'
        
        # Check default values
        assert args.genus == 'Escherichia'
        assert args.species == 'coli'
        assert args.complete is False
        assert args.translation_table == 11
        assert args.environment == 'prod'
        assert args.timeout == 300
        assert args.poll_interval == 30
        assert args.max_poll_time == 3600

def test_run_bakta_job_with_validation_error(mock_args):
    """Test run_bakta_job when FASTA validation fails."""
    # Mock validation to raise an error
    with patch('run_bakta_job.validate_fasta') as mock_validate:
        # Simulate validation error
        from amr_predictor.bakta import BaktaValidationError
        mock_validate.side_effect = BaktaValidationError("Invalid FASTA file")
        
        # Run the function
        result = run_bakta_job(mock_args)
        
        # Check that the function returns error code
        assert result == 1
        
        # Verify validate_fasta was called with the correct arguments
        mock_validate.assert_called_once_with(mock_args.fasta_file)

@patch('os.environ.get')
@patch('run_bakta_job.BaktaClient')
@patch('run_bakta_job.validate_fasta')
@patch('run_bakta_job.create_config')
@patch('run_bakta_job.get_api_url')
@patch('pathlib.Path.mkdir')
def test_run_bakta_job_success(mock_mkdir, mock_get_api_url, mock_create_config, 
                               mock_validate, mock_client_class, mock_environ_get,
                               mock_args, sample_fasta_file):
    """Test run_bakta_job with a successful job run."""
    # Update the fasta_file path to use our real temp file
    mock_args.fasta_file = str(sample_fasta_file)
    
    # Set up mocks
    mock_environ_get.return_value = "test_api_key"
    mock_get_api_url.return_value = "https://api.bakta.test"
    mock_create_config.return_value = {"genus": "Escherichia", "species": "coli"}
    
    # Mock client methods
    mock_client = mock_client_class.return_value
    mock_client.initialize_job.return_value = {
        "job_id": "test-job-id",
        "secret": "test-secret",
        "upload_link": "https://upload.test"
    }
    
    # First call to check_job_status returns "RUNNING", second call returns "SUCCESSFUL"
    mock_client.check_job_status.side_effect = ["RUNNING", "SUCCESSFUL"]
    
    # Mock job results
    mock_client.get_job_results.return_value = {
        "job_id": "test-job-id",
        "result_files": {
            "test.gff": "https://download.test/test.gff",
            "test.gbff": "https://download.test/test.gbff"
        }
    }
    
    # Run the function
    result = run_bakta_job(mock_args)
    
    # Check that the function returns success code
    assert result == 0
    
    # Verify method calls
    mock_validate.assert_called_once_with(str(sample_fasta_file))
    mock_mkdir.assert_called_once()
    mock_create_config.assert_called_once()
    mock_client_class.assert_called_once_with(
        api_url=mock_get_api_url.return_value,
        api_key="test_api_key",
        timeout=mock_args.timeout
    )
    
    # Verify client method calls
    mock_client.initialize_job.assert_called_once()
    mock_client.upload_fasta.assert_called_once_with("https://upload.test", str(sample_fasta_file))
    mock_client.start_job.assert_called_once()
    assert mock_client.check_job_status.call_count == 2
    mock_client.get_job_results.assert_called_once()
    assert mock_client.download_result_file.call_count == 2

@patch('os.environ.get')
@patch('run_bakta_job.BaktaClient')
@patch('run_bakta_job.validate_fasta')
@patch('run_bakta_job.create_config')
@patch('run_bakta_job.get_api_url')
@patch('pathlib.Path.mkdir')
def test_run_bakta_job_api_error(mock_mkdir, mock_get_api_url, mock_create_config, 
                                mock_validate, mock_client_class, mock_environ_get,
                                mock_args):
    """Test run_bakta_job when an API error occurs."""
    # Set up mocks
    mock_environ_get.return_value = "test_api_key"
    mock_get_api_url.return_value = "https://api.bakta.test"
    mock_create_config.return_value = {"genus": "Escherichia", "species": "coli"}
    
    # Mock client to raise an API error
    mock_client = mock_client_class.return_value
    from amr_predictor.bakta import BaktaApiError
    mock_client.initialize_job.side_effect = BaktaApiError("API error")
    
    # Run the function
    result = run_bakta_job(mock_args)
    
    # Check that the function returns error code
    assert result == 1
    
    # Verify method calls
    mock_validate.assert_called_once()
    mock_mkdir.assert_called_once()
    mock_create_config.assert_called_once()
    mock_client_class.assert_called_once()
    mock_client.initialize_job.assert_called_once()

@patch('os.environ.get')
@patch('run_bakta_job.BaktaClient')
@patch('run_bakta_job.validate_fasta')
@patch('run_bakta_job.create_config')
@patch('run_bakta_job.get_api_url')
@patch('pathlib.Path.mkdir')
def test_run_bakta_job_timeout(mock_mkdir, mock_get_api_url, mock_create_config, 
                              mock_validate, mock_client_class, mock_environ_get,
                              mock_args):
    """Test run_bakta_job when job times out."""
    # Set up mocks
    mock_environ_get.return_value = "test_api_key"
    mock_get_api_url.return_value = "https://api.bakta.test"
    mock_create_config.return_value = {"genus": "Escherichia", "species": "coli"}
    
    # Mock client methods
    mock_client = mock_client_class.return_value
    mock_client.initialize_job.return_value = {
        "job_id": "test-job-id",
        "secret": "test-secret",
        "upload_link": "https://upload.test"
    }
    
    # Always return "RUNNING" for check_job_status
    mock_client.check_job_status.return_value = "RUNNING"
    
    # Run the function - it should time out
    result = run_bakta_job(mock_args)
    
    # Check that the function returns error code
    assert result == 1
    
    # Verify method calls
    mock_validate.assert_called_once()
    mock_client.initialize_job.assert_called_once()
    mock_client.upload_fasta.assert_called_once()
    mock_client.start_job.assert_called_once()
    
    # Should call check_job_status multiple times but not get_job_results
    assert mock_client.check_job_status.call_count > 1
    mock_client.get_job_results.assert_not_called()