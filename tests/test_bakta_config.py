"""Tests for the Bakta configuration module."""

import os
import pytest
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch

from amr_predictor.bakta import (
    create_config,
    get_api_url,
    load_config_from_file,
    save_config_to_file,
    get_available_presets,
    get_preset_config,
    get_environment_config,
    create_config_from_env,
    DEFAULT_CONFIG,
    CONFIGURATION_PRESETS,
    BaktaException
)

# Configuration creation tests
def test_create_config_default():
    """Test create_config with default values."""
    # Create a minimal configuration
    config = create_config(genus="Escherichia", species="coli")
    
    # Check required fields
    assert config["genus"] == "Escherichia"
    assert config["species"] == "coli"
    
    # Check default values
    assert "translationTable" in config
    assert "completeGenome" in config

def test_create_config_custom():
    """Test create_config with custom values."""
    # Create a configuration with custom values
    config = create_config(
        genus="Escherichia",
        species="coli",
        strain="K-12",
        locus="ECO",
        locus_tag="ECO",
        complete_genome=True,
        translation_table=11,
        min_contig_length=200
    )
    
    # Check custom values
    assert config["genus"] == "Escherichia"
    assert config["species"] == "coli"
    assert config["strain"] == "K-12"
    assert config["locus"] == "ECO"
    assert config["locusTag"] == "ECO"
    assert config["completeGenome"] is True
    assert config["translationTable"] == 11
    assert config["minContigLength"] == 200

def test_create_config_with_preset():
    """Test create_config with a preset."""
    # Get available presets
    presets = get_available_presets()
    assert len(presets) > 0
    
    # Use a preset
    preset_name = "escherichia_coli"
    if preset_name in presets:
        config = create_config(preset=preset_name, strain="K-12")
        
        # Check that preset values were applied
        preset_config = get_preset_config(preset_name)
        for key, value in preset_config.items():
            assert config[key] == value
        
        # Check that custom values override preset values
        assert config["strain"] == "K-12"

def test_create_config_invalid_preset():
    """Test create_config with an invalid preset."""
    with pytest.raises(BaktaException) as excinfo:
        create_config(preset="invalid_preset", genus="Escherichia", species="coli")
    
    assert "invalid preset" in str(excinfo.value).lower()

# API URL tests
def test_get_api_url_default():
    """Test get_api_url with default environment."""
    url = get_api_url()
    assert url is not None
    assert isinstance(url, str)
    assert url.startswith("http")

def test_get_api_url_environments():
    """Test get_api_url with different environments."""
    environments = ["prod", "staging", "dev", "local"]
    
    for env in environments:
        url = get_api_url(env)
        assert url is not None
        assert isinstance(url, str)
        assert url.startswith("http")

def test_get_api_url_custom():
    """Test get_api_url with a custom environment."""
    # Set a custom API URL
    os.environ["BAKTA_API_URL_CUSTOM"] = "https://custom-bakta-api.example.com/api/v1"
    
    try:
        url = get_api_url("custom")
        assert url == "https://custom-bakta-api.example.com/api/v1"
    finally:
        # Clean up the environment variable
        if "BAKTA_API_URL_CUSTOM" in os.environ:
            del os.environ["BAKTA_API_URL_CUSTOM"]

def test_get_api_url_invalid():
    """Test get_api_url with an invalid environment."""
    with pytest.raises(ValueError) as excinfo:
        get_api_url("invalid_environment")
    
    assert "invalid environment" in str(excinfo.value).lower()

# File-based configuration tests
def test_save_and_load_config_json(tmp_path):
    """Test saving and loading configuration in JSON format."""
    # Create a configuration
    config = create_config(
        genus="Escherichia",
        species="coli",
        strain="K-12",
        locus="ECO",
        locus_tag="ECO"
    )
    
    # Save the configuration to a JSON file
    json_path = tmp_path / "config.json"
    save_config_to_file(config, json_path)
    
    # Verify the file exists and contains valid JSON
    assert json_path.exists()
    with open(json_path, "r") as f:
        saved_data = json.load(f)
        assert saved_data == config
    
    # Load the configuration from the JSON file
    loaded_config = load_config_from_file(json_path)
    
    # Verify the loaded configuration matches the original
    assert loaded_config == config

def test_save_and_load_config_yaml(tmp_path):
    """Test saving and loading configuration in YAML format."""
    # Create a configuration
    config = create_config(
        genus="Escherichia",
        species="coli",
        strain="K-12",
        locus="ECO",
        locus_tag="ECO"
    )
    
    # Save the configuration to a YAML file
    yaml_path = tmp_path / "config.yaml"
    save_config_to_file(config, yaml_path, format="yaml")
    
    # Verify the file exists and contains valid YAML
    assert yaml_path.exists()
    with open(yaml_path, "r") as f:
        saved_data = yaml.safe_load(f)
        assert saved_data == config
    
    # Load the configuration from the YAML file
    loaded_config = load_config_from_file(yaml_path)
    
    # Verify the loaded configuration matches the original
    assert loaded_config == config

def test_save_config_invalid_format(tmp_path):
    """Test saving configuration with an invalid format."""
    config = create_config(genus="Escherichia", species="coli")
    file_path = tmp_path / "config.txt"
    
    with pytest.raises(BaktaException) as excinfo:
        save_config_to_file(config, file_path, format="invalid_format")
    
    assert "format" in str(excinfo.value).lower()
    assert "invalid" in str(excinfo.value).lower()

def test_load_config_nonexistent_file():
    """Test loading configuration from a nonexistent file."""
    with pytest.raises(BaktaException) as excinfo:
        load_config_from_file("/path/to/nonexistent/config.json")
    
    assert "file" in str(excinfo.value).lower()
    assert "not found" in str(excinfo.value).lower()

def test_load_config_invalid_format(tmp_path):
    """Test loading configuration from a file with invalid format."""
    # Create a file with invalid format
    invalid_file = tmp_path / "invalid.txt"
    with open(invalid_file, "w") as f:
        f.write("This is not a valid JSON or YAML file")
    
    with pytest.raises(BaktaException) as excinfo:
        load_config_from_file(invalid_file)
    
    assert "format" in str(excinfo.value).lower()
    assert "invalid" in str(excinfo.value).lower()

# Preset configuration tests
def test_get_available_presets():
    """Test get_available_presets function."""
    presets = get_available_presets()
    
    # Verify that presets are returned
    assert isinstance(presets, list)
    assert len(presets) > 0
    
    # Verify that each preset exists in CONFIGURATION_PRESETS
    for preset in presets:
        assert preset in CONFIGURATION_PRESETS

def test_get_preset_config():
    """Test get_preset_config function."""
    # Get available presets
    presets = get_available_presets()
    assert len(presets) > 0
    
    # Get configuration for each preset
    for preset in presets:
        preset_config = get_preset_config(preset)
        
        # Verify that the configuration is a dictionary
        assert isinstance(preset_config, dict)
        
        # Verify that the configuration contains required fields
        assert "genus" in preset_config
        assert "species" in preset_config

def test_get_preset_config_invalid():
    """Test get_preset_config with an invalid preset."""
    with pytest.raises(ValueError) as excinfo:
        get_preset_config("invalid_preset")
    
    assert "preset" in str(excinfo.value).lower()
    assert "not found" in str(excinfo.value).lower()

# Environment-based configuration tests
def test_get_environment_config():
    """Test get_environment_config function."""
    environments = ["prod", "staging", "dev", "local"]
    
    for env in environments:
        env_config = get_environment_config(env)
        
        # Verify that the configuration is a dictionary
        assert isinstance(env_config, dict)
        
        # Verify that the configuration contains the API URL
        assert "api_url" in env_config

def test_get_environment_config_invalid():
    """Test get_environment_config with an invalid environment."""
    with pytest.raises(ValueError) as excinfo:
        get_environment_config("invalid_environment")
    
    assert "environment" in str(excinfo.value).lower()
    assert "invalid" in str(excinfo.value).lower()

# Environment variable configuration tests
def test_create_config_from_env():
    """Test create_config_from_env function."""
    # Set environment variables
    env_vars = {
        "BAKTA_GENUS": "Escherichia",
        "BAKTA_SPECIES": "coli",
        "BAKTA_STRAIN": "K-12",
        "BAKTA_LOCUS": "ECO",
        "BAKTA_LOCUS_TAG": "ECO",
        "BAKTA_COMPLETE_GENOME": "true",
        "BAKTA_TRANSLATION_TABLE": "11"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Create configuration from environment variables
        config = create_config_from_env()
        
        # Verify that the configuration contains the environment variables
        assert config["genus"] == "Escherichia"
        assert config["species"] == "coli"
        assert config["strain"] == "K-12"
        assert config["locus"] == "ECO"
        assert config["locusTag"] == "ECO"
        assert config["completeGenome"] is True
        assert config["translationTable"] == 11
    finally:
        # Clean up the environment variables
        for key in env_vars:
            if key in os.environ:
                del os.environ[key]

def test_create_config_from_env_boolean_conversion():
    """Test create_config_from_env with boolean environment variables."""
    # Set environment variables with different boolean representations
    os.environ["BAKTA_GENUS"] = "Escherichia"
    os.environ["BAKTA_SPECIES"] = "coli"
    os.environ["BAKTA_COMPLETE_GENOME"] = "true"
    os.environ["BAKTA_COMPLIANT"] = "yes"
    os.environ["BAKTA_KEEP_CONTIG_HEADERS"] = "1"
    
    try:
        # Create configuration from environment variables
        config = create_config_from_env()
        
        # Verify boolean conversions
        assert config["completeGenome"] is True
        assert config["compliant"] is True
        assert config["keepContigHeaders"] is True
    finally:
        # Clean up the environment variables
        for key in ["BAKTA_GENUS", "BAKTA_SPECIES", "BAKTA_COMPLETE_GENOME", "BAKTA_COMPLIANT", "BAKTA_KEEP_CONTIG_HEADERS"]:
            if key in os.environ:
                del os.environ[key]

def test_create_config_from_env_numeric_conversion():
    """Test create_config_from_env with numeric environment variables."""
    # Set environment variables with numeric values
    os.environ["BAKTA_GENUS"] = "Escherichia"
    os.environ["BAKTA_SPECIES"] = "coli"
    os.environ["BAKTA_TRANSLATION_TABLE"] = "11"
    os.environ["BAKTA_MIN_CONTIG_LENGTH"] = "200"
    
    try:
        # Create configuration from environment variables
        config = create_config_from_env()
        
        # Verify numeric conversions
        assert config["translationTable"] == 11
        assert config["minContigLength"] == 200
    finally:
        # Clean up the environment variables
        for key in ["BAKTA_GENUS", "BAKTA_SPECIES", "BAKTA_TRANSLATION_TABLE", "BAKTA_MIN_CONTIG_LENGTH"]:
            if key in os.environ:
                del os.environ[key] 