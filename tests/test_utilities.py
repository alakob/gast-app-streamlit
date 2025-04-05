"""Tests for core utilities module."""

import pytest
from pathlib import Path
from typing import Dict

from amr_predictor.core.utilities import (
    load_fasta,
    save_fasta,
    load_predictions,
    save_predictions,
    validate_fasta,
    validate_predictions
)

def test_load_fasta(test_fasta_file: Path, test_sequences: Dict[str, str]):
    """Test loading FASTA file."""
    sequences = load_fasta(test_fasta_file)
    assert sequences == test_sequences

def test_save_fasta(test_output_dir: Path, test_sequences: Dict[str, str]):
    """Test saving FASTA file."""
    output_file = test_output_dir / "test_save.fasta"
    save_fasta(test_sequences, output_file)
    assert output_file.exists()
    
    # Verify saved content
    loaded_sequences = load_fasta(output_file)
    assert loaded_sequences == test_sequences

def test_load_predictions(test_prediction_file: Path, test_predictions: Dict[str, Dict[str, float]]):
    """Test loading prediction file."""
    predictions = load_predictions(test_prediction_file)
    assert predictions == test_predictions

def test_save_predictions(test_output_dir: Path, test_predictions: Dict[str, Dict[str, float]]):
    """Test saving prediction file."""
    output_file = test_output_dir / "test_save_predictions.json"
    save_predictions(test_predictions, output_file)
    assert output_file.exists()
    
    # Verify saved content
    loaded_predictions = load_predictions(output_file)
    assert loaded_predictions == test_predictions

def test_validate_fasta_valid(test_sequences: Dict[str, str]):
    """Test FASTA validation with valid data."""
    assert validate_fasta(test_sequences) is True

def test_validate_fasta_invalid():
    """Test FASTA validation with invalid data."""
    invalid_sequences = {
        "seq1": "ATCGX",  # Invalid character
        "seq2": "ATCG"    # Valid
    }
    assert validate_fasta(invalid_sequences) is False

def test_validate_predictions_valid(test_predictions: Dict[str, Dict[str, float]]):
    """Test prediction validation with valid data."""
    assert validate_predictions(test_predictions) is True

def test_validate_predictions_invalid():
    """Test prediction validation with invalid data."""
    invalid_predictions = {
        "seq1": {
            "amoxicillin": 1.5,  # Invalid probability
            "ciprofloxacin": 0.2
        }
    }
    assert validate_predictions(invalid_predictions) is False

def test_validate_predictions_missing_sequence(test_predictions: Dict[str, Dict[str, float]]):
    """Test prediction validation with missing sequence."""
    invalid_predictions = {
        "seq1": {
            "amoxicillin": 0.8,
            "ciprofloxacin": 0.2
        },
        "seq2": None  # Invalid value
    }
    assert validate_predictions(invalid_predictions) is False

def test_validate_predictions_missing_antibiotic(test_predictions: Dict[str, Dict[str, float]]):
    """Test prediction validation with missing antibiotic."""
    invalid_predictions = {
        "seq1": {
            "amoxicillin": 0.8
            # Missing ciprofloxacin
        }
    }
    assert validate_predictions(invalid_predictions) is False 