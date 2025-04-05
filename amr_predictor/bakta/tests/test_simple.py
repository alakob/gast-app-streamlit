"""Simple tests for Bakta API client."""

import pytest
from amr_predictor.bakta import BaktaClient, BaktaException

def test_client_initialization():
    """Test client initialization."""
    # Default parameters
    client = BaktaClient()
    assert client.api_url == "https://api.bakta.computational.bio/api/v1"
    assert client.timeout == 30
    assert client.api_key is None
    
    # Custom parameters
    custom_client = BaktaClient(
        api_url="https://custom.api.url",
        timeout=60,
        api_key="test-key"
    )
    assert custom_client.api_url == "https://custom.api.url"
    assert custom_client.timeout == 60
    assert custom_client.api_key == "test-key"

def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    # All specialized exceptions should inherit from BaktaException
    from amr_predictor.bakta.client import (
        BaktaApiError,
        BaktaNetworkError,
        BaktaResponseError,
        BaktaValidationError,
        BaktaResourceNotFoundError,
        BaktaAuthenticationError,
        BaktaJobError
    )
    
    # Check inheritance
    assert issubclass(BaktaApiError, BaktaException)
    assert issubclass(BaktaNetworkError, BaktaApiError)
    assert issubclass(BaktaResponseError, BaktaApiError)
    assert issubclass(BaktaValidationError, BaktaApiError)
    assert issubclass(BaktaResourceNotFoundError, BaktaApiError)
    assert issubclass(BaktaAuthenticationError, BaktaApiError)
    assert issubclass(BaktaJobError, BaktaApiError)
    
    # Check instantiation
    e = BaktaException("Test exception")
    assert str(e) == "Test exception"
    
    e = BaktaApiError("API error")
    assert str(e) == "API error"
    assert isinstance(e, BaktaException)

def test_validation_functions():
    """Test validation functions."""
    from amr_predictor.bakta import (
        is_valid_fasta, 
        validate_fasta, 
        validate_job_config, 
        BaktaValidationError
    )
    
    # Test FASTA validation
    assert is_valid_fasta(">header\nATGC") is True
    assert is_valid_fasta("not a fasta") is False
    
    # Test validate_fasta with valid input
    try:
        validate_fasta(">header\nATGCATGC")
        valid_fasta = True
    except BaktaValidationError:
        valid_fasta = False
    assert valid_fasta is True
    
    # Test validate_fasta with invalid input
    try:
        validate_fasta("invalid")
        valid_fasta = True
    except BaktaValidationError:
        valid_fasta = False
    assert valid_fasta is False
    
    # Test job config validation
    valid_config = {
        "genus": "Escherichia",
        "species": "coli"
    }
    
    # Test validate_job_config with valid input
    try:
        validate_job_config(valid_config)
        valid_config_result = True
    except BaktaValidationError:
        valid_config_result = False
    assert valid_config_result is True
    
    # Test validate_job_config with invalid input
    invalid_config = {
        "genus": "Escherichia"
        # Missing species
    }
    
    try:
        validate_job_config(invalid_config)
        valid_config_result = True
    except BaktaValidationError as e:
        valid_config_result = False
        error_message = str(e)
    assert valid_config_result is False
    assert "Missing required field: species" in error_message

def test_configuration_functions():
    """Test configuration functions."""
    from amr_predictor.bakta import (
        create_config,
        get_api_url,
        DEFAULT_CONFIG
    )
    
    # Test create_config
    config = create_config(genus="Escherichia", species="coli")
    assert config.get("genus") == "Escherichia"
    assert config.get("species") == "coli"
    
    # Test inherited defaults
    assert "translationTable" in config
    
    # Test get_api_url
    api_url = get_api_url()
    assert api_url.startswith("http")
    assert "api" in api_url
    
    # Test DEFAULT_CONFIG
    assert isinstance(DEFAULT_CONFIG, dict)
    assert "translationTable" in DEFAULT_CONFIG 