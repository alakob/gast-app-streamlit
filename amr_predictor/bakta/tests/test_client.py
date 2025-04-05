#!/usr/bin/env python3
"""
Tests for the Bakta API client.
"""

import pytest
import json
import os
import requests
from unittest.mock import patch, MagicMock, mock_open, Mock
from amr_predictor.bakta import BaktaClient
from amr_predictor.bakta.exceptions import (
    BaktaException, BaktaValidationError, BaktaResponseError,
    BaktaNetworkError, BaktaAuthenticationError, BaktaResourceNotFoundError
)
from amr_predictor.bakta.tests.conftest import SAMPLE_CONFIG, SAMPLE_JOB_RESPONSE

@pytest.fixture
def sample_job_response():
    """Return a sample job response for testing."""
    return SAMPLE_JOB_RESPONSE

@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return SAMPLE_CONFIG

# Client initialization tests
def test_client_initialization():
    """Test BaktaClient initialization with different parameters."""
    # Default initialization
    client = BaktaClient()
    assert client.api_url is not None
    assert client.timeout > 0
    
    # Custom API URL
    custom_url = "https://custom-bakta-api.example.com/api/v1"
    client = BaktaClient(api_url=custom_url)
    assert client.api_url == custom_url
    
    # Custom timeout
    client = BaktaClient(timeout=60)
    assert client.timeout == 60
    
    # Custom API key
    api_key = "test-api-key"
    client = BaktaClient(api_key=api_key)
    assert client.api_key == api_key

# API method tests
@patch('requests.post')
@patch('amr_predictor.bakta.client.validate_init_response')
def test_initialize_job(mock_validate, mock_post, sample_job_response):
    """Test initialize_job method."""
    # Setup the mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_job_response
    mock_post.return_value = mock_response
    
    # Create client and call the method
    client = BaktaClient(api_url="https://api.example.com")
    job_result = client.initialize_job("test_job")
    
    # Verify the API call
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert "https://api.example.com/job/init" in call_args[0]
    
    # Check the payload
    assert call_kwargs["json"]["name"] == "test_job"
    
    # Verify the response processing
    assert job_result["job_id"] == sample_job_response["job"]["jobID"]
    assert job_result["secret"] == sample_job_response["job"]["secret"]
    assert job_result["upload_link"] == sample_job_response["uploadLinkFasta"]

@patch('requests.post')
def test_initialize_job_error(mock_post):
    """Test initialize_job method with error response."""
    # Setup the mock error response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "{}", 0)
    mock_response.text = "Server error"
    mock_post.return_value = mock_response
    
    # Create client and check for error
    client = BaktaClient(api_url="https://api.example.com")
    
    with pytest.raises(BaktaResponseError):
        client.initialize_job("test_job")

@patch('requests.put')
@patch('amr_predictor.bakta.validation.validate_fasta')
def test_upload_fasta(mock_validate, mock_put):
    """Test upload_fasta method with a direct string."""
    # Setup the mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_put.return_value = mock_response
    
    # Create client and call the method with a string
    client = BaktaClient()
    result = client.upload_fasta("https://example.com/upload", ">test\nATGC")
    
    # Verify the API call
    mock_put.assert_called_once()
    call_args = mock_put.call_args[0]
    assert call_args[0] == "https://example.com/upload"
    
    # Verify the result
    assert result is True

@patch('requests.put')
@patch('amr_predictor.bakta.validation.validate_fasta')
def test_upload_fasta_from_file(mock_validate, mock_put):
    """Test upload_fasta method with a file path."""
    # Setup the mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_put.return_value = mock_response
    
    # Mock file operations
    with patch('builtins.open', mock_open(read_data=">test\nATGC")):
        with patch('os.path.exists', return_value=True):
            # Create client and call the method with a file path
            client = BaktaClient()
            result = client.upload_fasta("https://example.com/upload", "/mock/path/file.fasta")
    
    # Verify the API call
    mock_put.assert_called_once()
    call_args = mock_put.call_args[0]
    assert call_args[0] == "https://example.com/upload"
    
    # Verify the result
    assert result is True

@patch('requests.post')
@patch('amr_predictor.bakta.client.validate_job_config')
def test_start_job(mock_validate, mock_post, sample_config):
    """Test start_job method."""
    # Setup the mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    # Create client and call the method
    client = BaktaClient(api_url="https://api.example.com")
    result = client.start_job("test-job-id", "test-secret", sample_config)
    
    # Verify the API call
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert "https://api.example.com/job/start" in call_args[0]
    
    # Verify the payload
    assert call_kwargs["json"]["job"]["jobID"] == "test-job-id"
    assert call_kwargs["json"]["job"]["secret"] == "test-secret"
    assert "config" in call_kwargs["json"]
    
    # Verify the result
    assert result is True 