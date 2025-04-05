"""Tests for the Bakta API client."""

import os
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from amr_predictor.bakta import BaktaClient, BaktaException
from tests.bakta_conftest import (
    SAMPLE_FASTA,
    SAMPLE_CONFIG,
    SAMPLE_JOB_RESPONSE,
    SAMPLE_STATUS_RESPONSES,
    SAMPLE_RESULTS_RESPONSE,
    SAMPLE_LOGS_RESPONSE
)

# Import fixtures
pytest.importorskip("tests.bakta_conftest")

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
def test_initialize_job(mock_bakta_client, mock_response, sample_job_response):
    """Test initialize_job method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].post.return_value = mock_response(
        status_code=200, 
        json_data=sample_job_response
    )
    
    # Call the method
    job_result = client.initialize_job("test_job")
    
    # Verify the API call
    mocks["requests"].post.assert_called_once()
    url = mocks["requests"].post.call_args[0][0]
    assert "/job/init" in url
    
    # Verify the response processing
    assert job_result["job_id"] == sample_job_response["job"]["jobID"]
    assert job_result["secret"] == sample_job_response["job"]["secret"]
    assert job_result["upload_link"] == sample_job_response["uploadLinkFasta"]

def test_initialize_job_error(mock_bakta_client, mock_response):
    """Test initialize_job method with error response."""
    client, mocks = mock_bakta_client
    
    # Mock error response
    mocks["requests"].post.return_value = mock_response(status_code=500)
    
    # Call the method and check for exception
    with pytest.raises(BaktaException):
        client.initialize_job("test_job")

def test_upload_fasta(mock_bakta_client, mock_response, temp_fasta_file):
    """Test upload_fasta method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].put.return_value = mock_response(status_code=200)
    
    # Call the method
    client.upload_fasta("https://example.com/upload", str(temp_fasta_file))
    
    # Verify the API call
    mocks["requests"].put.assert_called_once()
    url = mocks["requests"].put.call_args[0][0]
    assert url == "https://example.com/upload"
    
    # Verify file data was sent
    assert mocks["requests"].put.call_args[1]["data"] is not None

def test_start_job(mock_bakta_client, mock_response, sample_config):
    """Test start_job method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].post.return_value = mock_response(status_code=200)
    
    # Call the method
    client.start_job("test-job-id", "test-secret", sample_config)
    
    # Verify the API call
    mocks["requests"].post.assert_called_once()
    url = mocks["requests"].post.call_args[0][0]
    assert "/job/start" in url
    
    # Verify request data
    request_data = json.loads(mocks["requests"].post.call_args[1]["data"])
    assert request_data["job"]["jobID"] == "test-job-id"
    assert request_data["job"]["secret"] == "test-secret"
    assert request_data["config"] == sample_config

def test_check_job_status(mock_bakta_client, mock_response, sample_status_responses):
    """Test check_job_status method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].post.return_value = mock_response(
        status_code=200, 
        json_data=sample_status_responses["RUNNING"]
    )
    
    # Call the method
    status = client.check_job_status("test-job-id", "test-secret")
    
    # Verify the API call
    mocks["requests"].post.assert_called_once()
    url = mocks["requests"].post.call_args[0][0]
    assert "/job/list" in url
    
    # Verify request data
    request_data = json.loads(mocks["requests"].post.call_args[1]["data"])
    assert len(request_data["jobs"]) == 1
    assert request_data["jobs"][0]["jobID"] == "test-job-id"
    assert request_data["jobs"][0]["secret"] == "test-secret"
    
    # Verify the response processing
    assert status == "RUNNING"

def test_check_job_status_not_found(mock_bakta_client, mock_response):
    """Test check_job_status method with job not found."""
    client, mocks = mock_bakta_client
    
    # Mock response with failed job
    response_data = {
        "jobs": [],
        "failedJobs": [
            {"jobID": "test-job-id", "reason": "NOT_FOUND"}
        ]
    }
    mocks["requests"].post.return_value = mock_response(
        status_code=200, 
        json_data=response_data
    )
    
    # Call the method and check for exception
    with pytest.raises(BaktaException) as excinfo:
        client.check_job_status("test-job-id", "test-secret")
    
    assert "not found" in str(excinfo.value).lower()

def test_get_job_logs(mock_bakta_client, mock_response, sample_logs_response):
    """Test get_job_logs method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].get.return_value = mock_response(
        status_code=200, 
        content=sample_logs_response.encode()
    )
    
    # Call the method
    logs = client.get_job_logs("test-job-id", "test-secret")
    
    # Verify the API call
    mocks["requests"].get.assert_called_once()
    url = mocks["requests"].get.call_args[0][0]
    assert "/job/logs" in url
    
    # Verify the query parameters
    params = mocks["requests"].get.call_args[1]["params"]
    assert params["jobID"] == "test-job-id"
    assert params["secret"] == "test-secret"
    
    # Verify the response processing
    assert logs == sample_logs_response

def test_get_job_results(mock_bakta_client, mock_response, sample_results_response):
    """Test get_job_results method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].post.return_value = mock_response(
        status_code=200, 
        json_data=sample_results_response
    )
    
    # Call the method
    results = client.get_job_results("test-job-id", "test-secret")
    
    # Verify the API call
    mocks["requests"].post.assert_called_once()
    url = mocks["requests"].post.call_args[0][0]
    assert "/job/result" in url
    
    # Verify request data
    request_data = json.loads(mocks["requests"].post.call_args[1]["data"])
    assert request_data["jobID"] == "test-job-id"
    assert request_data["secret"] == "test-secret"
    
    # Verify the response processing
    assert "result_files" in results
    assert len(results["result_files"]) == len(sample_results_response["ResultFiles"])
    assert results["job_id"] == sample_results_response["jobID"]

def test_download_result_file(mock_bakta_client, mock_response, sample_result_file_content, tmp_path):
    """Test download_result_file method."""
    client, mocks = mock_bakta_client
    
    # Mock successful response
    mocks["requests"].get.return_value = mock_response(
        status_code=200, 
        content=sample_result_file_content
    )
    
    # Output path
    output_path = tmp_path / "result.txt"
    
    # Call the method
    client.download_result_file("https://example.com/results/output.txt", str(output_path))
    
    # Verify the API call
    mocks["requests"].get.assert_called_once()
    url = mocks["requests"].get.call_args[0][0]
    assert url == "https://example.com/results/output.txt"
    
    # Verify the file was written
    assert output_path.exists()
    assert output_path.read_bytes() == sample_result_file_content

def test_poll_job_status(mock_bakta_client, mock_response, sample_status_responses):
    """Test poll_job_status method."""
    client, mocks = mock_bakta_client
    
    # Mock responses for each call
    mocks["requests"].post.side_effect = [
        mock_response(status_code=200, json_data=sample_status_responses["INIT"]),
        mock_response(status_code=200, json_data=sample_status_responses["RUNNING"]),
        mock_response(status_code=200, json_data=sample_status_responses["SUCCESSFUL"])
    ]
    
    # Call the method with shorter polling to speed up test
    status = client.poll_job_status("test-job-id", "test-secret", poll_interval=0.1)
    
    # Verify the API calls
    assert mocks["requests"].post.call_count == 3
    
    # Verify the final status
    assert status == "SUCCESSFUL"

def test_poll_job_status_error(mock_bakta_client, mock_response, sample_status_responses):
    """Test poll_job_status method with error status."""
    client, mocks = mock_bakta_client
    
    # Mock responses for each call
    mocks["requests"].post.side_effect = [
        mock_response(status_code=200, json_data=sample_status_responses["INIT"]),
        mock_response(status_code=200, json_data=sample_status_responses["RUNNING"]),
        mock_response(status_code=200, json_data=sample_status_responses["ERROR"])
    ]
    
    # Call the method and check for exception
    with pytest.raises(BaktaException) as excinfo:
        client.poll_job_status("test-job-id", "test-secret", poll_interval=0.1)
    
    assert "error" in str(excinfo.value).lower()

def test_submit_job(mock_bakta_client, mock_response, temp_fasta_file, sample_config, sample_job_response, sample_status_responses):
    """Test the complete submit_job method."""
    client, mocks = mock_bakta_client
    
    # Mock responses for each call in the submit_job flow
    mocks["requests"].post.side_effect = [
        # initialize_job response
        mock_response(status_code=200, json_data=sample_job_response),
        # start_job response
        mock_response(status_code=200),
        # check_job_status (in poll_job_status) responses
        mock_response(status_code=200, json_data=sample_status_responses["INIT"]),
        mock_response(status_code=200, json_data=sample_status_responses["RUNNING"]),
        mock_response(status_code=200, json_data=sample_status_responses["SUCCESSFUL"])
    ]
    
    # Mock upload_fasta response
    mocks["requests"].put.return_value = mock_response(status_code=200)
    
    # Call the submit_job method
    job_id = client.submit_job(str(temp_fasta_file), sample_config, poll_interval=0.1)
    
    # Verify the job_id
    assert job_id == sample_job_response["job"]["jobID"]
    
    # Verify the correct sequence of API calls
    assert mocks["requests"].post.call_count >= 3  # initialize_job, start_job, at least one check_job_status
    assert mocks["requests"].put.call_count == 1  # upload_fasta

# Custom configuration tests
def test_custom_config_submission(mock_bakta_client, mock_response, temp_fasta_file, sample_job_response):
    """Test submitting a job with custom configuration."""
    client, mocks = mock_bakta_client
    
    # Create a custom configuration
    custom_config = {
        "genus": "Pseudomonas",
        "species": "aeruginosa",
        "strain": "PAO1",
        "completeGenome": False,
        "translationTable": 11,
        "minContigLength": 200
    }
    
    # Mock responses
    mocks["requests"].post.side_effect = [
        mock_response(status_code=200, json_data=sample_job_response),
        mock_response(status_code=200)
    ]
    mocks["requests"].put.return_value = mock_response(status_code=200)
    
    # Call initialize_job and start_job (not using submit_job to avoid polling)
    job_result = client.initialize_job("test_job")
    client.upload_fasta(job_result["upload_link"], str(temp_fasta_file))
    client.start_job(job_result["job_id"], job_result["secret"], custom_config)
    
    # Verify the config in the start_job call
    start_job_call = mocks["requests"].post.call_args_list[1]
    request_data = json.loads(start_job_call[1]["data"])
    
    # Check each config parameter
    assert request_data["config"]["genus"] == custom_config["genus"]
    assert request_data["config"]["species"] == custom_config["species"]
    assert request_data["config"]["strain"] == custom_config["strain"]
    assert request_data["config"]["completeGenome"] == custom_config["completeGenome"]
    assert request_data["config"]["translationTable"] == custom_config["translationTable"]
    assert request_data["config"]["minContigLength"] == custom_config["minContigLength"] 