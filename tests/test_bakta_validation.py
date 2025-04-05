"""Tests for the Bakta validation module."""

import os
import pytest
import tempfile
from pathlib import Path

from amr_predictor.bakta import (
    validate_fasta,
    validate_job_configuration,
    is_valid_fasta,
    BaktaException
)
from tests.bakta_conftest import SAMPLE_FASTA, SAMPLE_CONFIG

# Import fixtures
pytest.importorskip("tests.bakta_conftest")

# FASTA validation tests
def test_is_valid_fasta_with_valid_string():
    """Test is_valid_fasta with a valid FASTA string."""
    assert is_valid_fasta(SAMPLE_FASTA) is True

def test_is_valid_fasta_with_invalid_string():
    """Test is_valid_fasta with an invalid FASTA string."""
    invalid_fasta = "This is not a FASTA format"
    assert is_valid_fasta(invalid_fasta) is False
    
    # No header
    invalid_fasta = "ATCGATCGATCGATCG"
    assert is_valid_fasta(invalid_fasta) is False
    
    # Invalid characters in sequence
    invalid_fasta = ">seq1\nATCGZXYATCG"
    assert is_valid_fasta(invalid_fasta) is False

def test_is_valid_fasta_with_file(temp_fasta_file):
    """Test is_valid_fasta with a valid FASTA file."""
    assert is_valid_fasta(str(temp_fasta_file)) is True

def test_is_valid_fasta_with_invalid_file(tmp_path):
    """Test is_valid_fasta with an invalid FASTA file."""
    # Create an invalid FASTA file
    invalid_file = tmp_path / "invalid.fasta"
    with open(invalid_file, "w") as f:
        f.write("This is not a FASTA format")
    
    assert is_valid_fasta(str(invalid_file)) is False

def test_validate_fasta_with_valid_string():
    """Test validate_fasta with a valid FASTA string."""
    # Should not raise any exception
    validate_fasta(SAMPLE_FASTA)

def test_validate_fasta_with_invalid_string():
    """Test validate_fasta with an invalid FASTA string."""
    invalid_fasta = "This is not a FASTA format"
    
    with pytest.raises(BaktaException) as excinfo:
        validate_fasta(invalid_fasta)
    
    assert "invalid fasta" in str(excinfo.value).lower()

def test_validate_fasta_with_valid_file(temp_fasta_file):
    """Test validate_fasta with a valid FASTA file."""
    # Should not raise any exception
    validate_fasta(str(temp_fasta_file))

def test_validate_fasta_with_invalid_file(tmp_path):
    """Test validate_fasta with an invalid FASTA file."""
    # Create an invalid FASTA file
    invalid_file = tmp_path / "invalid.fasta"
    with open(invalid_file, "w") as f:
        f.write("This is not a FASTA format")
    
    with pytest.raises(BaktaException) as excinfo:
        validate_fasta(str(invalid_file))
    
    assert "invalid fasta" in str(excinfo.value).lower()

def test_validate_fasta_with_nonexistent_file():
    """Test validate_fasta with a nonexistent file."""
    with pytest.raises(BaktaException) as excinfo:
        validate_fasta("/path/to/nonexistent/file.fasta")
    
    assert "does not exist" in str(excinfo.value).lower()

# Job configuration validation tests
def test_validate_job_configuration_with_valid_config():
    """Test validate_job_configuration with a valid configuration."""
    # Should not raise any exception
    validate_job_configuration(SAMPLE_CONFIG)

def test_validate_job_configuration_with_missing_required_fields():
    """Test validate_job_configuration with missing required fields."""
    # Missing genus
    config = SAMPLE_CONFIG.copy()
    del config["genus"]
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "required" in str(excinfo.value).lower()
    assert "genus" in str(excinfo.value).lower()
    
    # Missing species
    config = SAMPLE_CONFIG.copy()
    del config["species"]
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "required" in str(excinfo.value).lower()
    assert "species" in str(excinfo.value).lower()

def test_validate_job_configuration_with_invalid_types():
    """Test validate_job_configuration with invalid field types."""
    # Non-string genus
    config = SAMPLE_CONFIG.copy()
    config["genus"] = 123
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "genus" in str(excinfo.value).lower()
    
    # Non-string species
    config = SAMPLE_CONFIG.copy()
    config["species"] = 123
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "species" in str(excinfo.value).lower()
    
    # Non-boolean completeGenome
    config = SAMPLE_CONFIG.copy()
    config["completeGenome"] = "yes"
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "completeGenome" in str(excinfo.value).lower()
    
    # Non-integer translationTable
    config = SAMPLE_CONFIG.copy()
    config["translationTable"] = "11"
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "translationTable" in str(excinfo.value).lower()

def test_validate_job_configuration_with_invalid_translation_table():
    """Test validate_job_configuration with invalid translation table value."""
    # Invalid translation table value
    config = SAMPLE_CONFIG.copy()
    config["translationTable"] = 99
    
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(config)
    
    assert "valid value" in str(excinfo.value).lower()
    assert "translationTable" in str(excinfo.value).lower()

def test_validate_job_configuration_with_extra_fields():
    """Test validate_job_configuration with extra unknown fields."""
    # Extra field
    config = SAMPLE_CONFIG.copy()
    config["unknown_field"] = "value"
    
    # Should not raise an exception, extra fields are allowed
    validate_job_configuration(config)

def test_validate_job_configuration_with_empty_config():
    """Test validate_job_configuration with an empty configuration."""
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration({})
    
    assert "required" in str(excinfo.value).lower()

def test_validate_job_configuration_with_none():
    """Test validate_job_configuration with None."""
    with pytest.raises(BaktaException) as excinfo:
        validate_job_configuration(None)
    
    assert "configuration" in str(excinfo.value).lower()
    assert "none" in str(excinfo.value).lower()

def test_validate_job_configuration_with_minimal_config():
    """Test validate_job_configuration with a minimal valid configuration."""
    minimal_config = {
        "genus": "Escherichia",
        "species": "coli"
    }
    
    # Should not raise any exception
    validate_job_configuration(minimal_config) 