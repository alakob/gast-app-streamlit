"""Tests for the Bakta validation module."""

import os
import pytest
import tempfile
from pathlib import Path

from amr_predictor.bakta import (
    validate_fasta,
    validate_job_config,
    is_valid_fasta,
    BaktaValidationError
)
from amr_predictor.bakta.tests.conftest import SAMPLE_FASTA, SAMPLE_CONFIG

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
    
    # Clean up
    if invalid_file.exists():
        invalid_file.unlink()

def test_validate_fasta_with_valid_string():
    """Test validate_fasta with a valid FASTA string."""
    # Should not raise any exception
    validate_fasta(SAMPLE_FASTA)

def test_validate_fasta_with_invalid_string():
    """Test validate_fasta with an invalid FASTA string."""
    invalid_fasta = "This is not a FASTA format"
    
    with pytest.raises(BaktaValidationError) as excinfo:
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
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_fasta(str(invalid_file))
    
    assert "invalid fasta" in str(excinfo.value).lower()
    
    # Clean up
    if invalid_file.exists():
        invalid_file.unlink()

def test_validate_fasta_with_nonexistent_file():
    """Test validate_fasta with a nonexistent file."""
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_fasta("/path/to/nonexistent/file.fasta")
    
    assert "invalid fasta" in str(excinfo.value).lower()

# Job configuration validation tests
def test_validate_job_configuration_with_valid_config():
    """Test validate_job_configuration with a valid configuration."""
    # Should not raise any exception
    validate_job_config(SAMPLE_CONFIG)

def test_validate_job_configuration_with_missing_required_fields():
    """Test validate_job_configuration with missing required fields."""
    # Missing genus
    config = SAMPLE_CONFIG.copy()
    del config["genus"]
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "required" in str(excinfo.value).lower()
    assert "genus" in str(excinfo.value).lower()
    
    # Missing species
    config = SAMPLE_CONFIG.copy()
    del config["species"]
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "required" in str(excinfo.value).lower()
    assert "species" in str(excinfo.value).lower()

def test_validate_job_configuration_with_invalid_types():
    """Test validate_job_configuration with invalid field types."""
    # Non-string genus
    config = SAMPLE_CONFIG.copy()
    config["genus"] = 123
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "genus" in str(excinfo.value).lower()
    
    # Non-string species
    config = SAMPLE_CONFIG.copy()
    config["species"] = 123
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "species" in str(excinfo.value).lower()
    
    # Non-boolean completeGenome
    config = SAMPLE_CONFIG.copy()
    config["completeGenome"] = "yes"
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "completegenome" in str(excinfo.value).lower()
    
    # Non-integer translationTable
    config = SAMPLE_CONFIG.copy()
    config["translationTable"] = "11"
    
    with pytest.raises(BaktaValidationError) as excinfo:
        validate_job_config(config)
    
    assert "must be" in str(excinfo.value).lower()
    assert "translationtable" in str(excinfo.value).lower()

def test_validate_multi_fasta():
    """Test validate_multi_fasta function."""
    from amr_predictor.bakta.validation import validate_multi_fasta
    
    # Valid multi-FASTA
    is_valid, error_msg, sequences = validate_multi_fasta(SAMPLE_FASTA)
    assert is_valid is True
    assert error_msg is None
    assert len(sequences) == 2
    assert sequences[0]["header"] == "contig1"
    assert sequences[1]["header"] == "contig2"
    
    # Invalid multi-FASTA
    is_valid, error_msg, sequences = validate_multi_fasta("Not a FASTA")
    assert is_valid is False
    assert error_msg is not None
    assert sequences is None 