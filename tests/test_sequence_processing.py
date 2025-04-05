"""Tests for sequence processing module."""

import pytest
import numpy as np
from typing import Dict, List
from pathlib import Path

from amr_predictor.processing.sequence_processing import (
    SequenceProcessor,
    ProcessingConfig,
    ProcessingResult
)

def test_processing_config_creation():
    """Test ProcessingConfig creation."""
    config = ProcessingConfig(
        threshold=0.7,
        min_confidence=0.8,
        max_sequences=1000,
        batch_size=32
    )
    assert config.threshold == 0.7
    assert config.min_confidence == 0.8
    assert config.max_sequences == 1000
    assert config.batch_size == 32

def test_processing_config_validation():
    """Test ProcessingConfig validation."""
    # Invalid threshold
    with pytest.raises(ValueError):
        ProcessingConfig(
            threshold=1.5,  # > 1
            min_confidence=0.8,
            max_sequences=1000,
            batch_size=32
        )
    
    # Invalid min_confidence
    with pytest.raises(ValueError):
        ProcessingConfig(
            threshold=0.7,
            min_confidence=1.5,  # > 1
            max_sequences=1000,
            batch_size=32
        )
    
    # Invalid max_sequences
    with pytest.raises(ValueError):
        ProcessingConfig(
            threshold=0.7,
            min_confidence=0.8,
            max_sequences=0,  # <= 0
            batch_size=32
        )
    
    # Invalid batch_size
    with pytest.raises(ValueError):
        ProcessingConfig(
            threshold=0.7,
            min_confidence=0.8,
            max_sequences=1000,
            batch_size=0  # <= 0
        )

def test_sequence_processor_initialization():
    """Test SequenceProcessor initialization."""
    config = ProcessingConfig()
    processor = SequenceProcessor(config)
    assert processor.config == config
    assert processor.results is None

def test_sequence_processor_process_predictions(test_predictions: Dict[str, Dict[str, float]]):
    """Test processing predictions."""
    config = ProcessingConfig(
        threshold=0.5,
        min_confidence=0.6
    )
    processor = SequenceProcessor(config)
    
    # Process predictions
    result = processor.process_predictions(test_predictions)
    
    # Verify result
    assert isinstance(result, ProcessingResult)
    assert result.config == config
    assert len(result.processed_predictions) <= len(test_predictions)
    
    # Check processed values
    for seq_name, preds in result.processed_predictions.items():
        assert len(preds) == len(test_predictions[seq_name])
        assert all(0 <= v <= 1 for v in preds.values())
        assert all(v >= config.min_confidence for v in preds.values())

def test_sequence_processor_filter_by_confidence(test_predictions: Dict[str, Dict[str, float]]):
    """Test filtering by confidence."""
    config = ProcessingConfig(min_confidence=0.7)
    processor = SequenceProcessor(config)
    
    # Process predictions
    result = processor.process_predictions(test_predictions)
    
    # Check filtered predictions
    for seq_name, preds in result.processed_predictions.items():
        assert all(v >= config.min_confidence for v in preds.values())

def test_sequence_processor_apply_threshold(test_predictions: Dict[str, Dict[str, float]]):
    """Test applying threshold."""
    config = ProcessingConfig(threshold=0.5)
    processor = SequenceProcessor(config)
    
    # Process predictions
    result = processor.process_predictions(test_predictions)
    
    # Check thresholded predictions
    for seq_name, preds in result.processed_predictions.items():
        assert all(v >= config.threshold for v in preds.values())

def test_sequence_processor_limit_sequences(test_predictions: Dict[str, Dict[str, float]]):
    """Test limiting number of sequences."""
    config = ProcessingConfig(max_sequences=2)
    processor = SequenceProcessor(config)
    
    # Process predictions
    result = processor.process_predictions(test_predictions)
    
    # Check sequence limit
    assert len(result.processed_predictions) <= config.max_sequences

def test_processing_result_creation():
    """Test ProcessingResult creation."""
    config = ProcessingConfig()
    processed_predictions = {
        "seq1": {"amoxicillin": 0.8, "ciprofloxacin": 0.2},
        "seq2": {"amoxicillin": 0.4, "ciprofloxacin": 0.6}
    }
    
    result = ProcessingResult(config, processed_predictions)
    assert result.config == config
    assert result.processed_predictions == processed_predictions
    assert result.timestamp is not None

def test_processing_result_serialization():
    """Test ProcessingResult serialization."""
    config = ProcessingConfig()
    processed_predictions = {
        "seq1": {"amoxicillin": 0.8, "ciprofloxacin": 0.2},
        "seq2": {"amoxicillin": 0.4, "ciprofloxacin": 0.6}
    }
    
    result = ProcessingResult(config, processed_predictions)
    serialized = result.to_dict()
    
    assert serialized["config"] == config.to_dict()
    assert serialized["processed_predictions"] == processed_predictions
    assert "timestamp" in serialized

def test_sequence_processor_with_empty_predictions():
    """Test SequenceProcessor with empty predictions."""
    config = ProcessingConfig()
    processor = SequenceProcessor(config)
    empty_predictions = {}
    
    with pytest.raises(ValueError):
        processor.process_predictions(empty_predictions)

def test_sequence_processor_with_invalid_predictions():
    """Test SequenceProcessor with invalid predictions."""
    config = ProcessingConfig()
    processor = SequenceProcessor(config)
    
    # Invalid prediction value
    invalid_predictions = {
        "seq1": {"amoxicillin": 1.5}  # > 1
    }
    
    with pytest.raises(ValueError):
        processor.process_predictions(invalid_predictions)

def test_sequence_processor_with_missing_antibiotics(test_predictions: Dict[str, Dict[str, float]]):
    """Test SequenceProcessor with missing antibiotics."""
    config = ProcessingConfig()
    processor = SequenceProcessor(config)
    
    # Missing antibiotic
    incomplete_predictions = {
        "seq1": {"amoxicillin": 0.8}  # Missing ciprofloxacin
    }
    
    with pytest.raises(ValueError):
        processor.process_predictions(incomplete_predictions)

def test_sequence_processor_batch_processing(test_predictions: Dict[str, Dict[str, float]]):
    """Test batch processing of predictions."""
    config = ProcessingConfig(batch_size=2)
    processor = SequenceProcessor(config)
    
    # Process in batches
    result = processor.process_predictions(test_predictions)
    
    # Verify batch processing
    assert len(result.processed_predictions) == len(test_predictions)
    assert all(seq_name in result.processed_predictions for seq_name in test_predictions) 