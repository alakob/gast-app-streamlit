"""Tests for core prediction module."""

import pytest
import torch
import numpy as np
from typing import Dict, List

from amr_predictor.core.prediction import (
    PredictionEngine,
    PredictionResult,
    PredictionBatch,
    PredictionMetrics
)

def test_prediction_engine_initialization(test_model: AMRModel):
    """Test PredictionEngine initialization."""
    engine = PredictionEngine(test_model)
    assert engine.model == test_model
    assert engine.device in ["cuda", "cpu"]
    assert engine.batch_size == test_model.config.batch_size

def test_prediction_engine_prepare_batch(test_sequence_set: SequenceSet):
    """Test PredictionEngine batch preparation."""
    engine = PredictionEngine(test_model)
    batch_size = 2
    
    # Prepare batch
    batch = engine.prepare_batch(test_sequence_set, batch_size)
    assert isinstance(batch, PredictionBatch)
    assert len(batch.sequences) <= batch_size
    assert batch.input_ids.shape[0] <= batch_size
    assert batch.attention_mask.shape[0] <= batch_size

def test_prediction_engine_predict_single(test_sequence_set: SequenceSet):
    """Test PredictionEngine single sequence prediction."""
    engine = PredictionEngine(test_model)
    seq = test_sequence_set.get("seq1")
    
    # Predict
    result = engine.predict_single(seq)
    assert isinstance(result, PredictionResult)
    assert result.sequence_name == seq.name
    assert result.predictions.shape == (test_model.config.num_classes,)
    assert torch.all(result.predictions >= 0) and torch.all(result.predictions <= 1)

def test_prediction_engine_predict_batch(test_sequence_set: SequenceSet):
    """Test PredictionEngine batch prediction."""
    engine = PredictionEngine(test_model)
    batch_size = 2
    
    # Predict batch
    results = engine.predict_batch(test_sequence_set, batch_size)
    assert len(results) == len(test_sequence_set)
    assert all(isinstance(r, PredictionResult) for r in results)
    assert all(r.predictions.shape == (test_model.config.num_classes,) for r in results)

def test_prediction_result_creation():
    """Test PredictionResult creation."""
    sequence_name = "test_seq"
    predictions = torch.tensor([0.8, 0.2, 0.5])
    
    result = PredictionResult(sequence_name, predictions)
    assert result.sequence_name == sequence_name
    assert torch.equal(result.predictions, predictions)
    assert result.timestamp is not None

def test_prediction_result_serialization():
    """Test PredictionResult serialization."""
    sequence_name = "test_seq"
    predictions = torch.tensor([0.8, 0.2, 0.5])
    
    result = PredictionResult(sequence_name, predictions)
    serialized = result.to_dict()
    
    assert serialized["sequence_name"] == sequence_name
    assert torch.equal(torch.tensor(serialized["predictions"]), predictions)
    assert "timestamp" in serialized

def test_prediction_batch_creation(test_sequence_set: SequenceSet):
    """Test PredictionBatch creation."""
    batch_size = 2
    sequences = list(test_sequence_set.values())[:batch_size]
    
    batch = PredictionBatch(sequences)
    assert len(batch.sequences) == len(sequences)
    assert batch.input_ids.shape[0] == len(sequences)
    assert batch.attention_mask.shape[0] == len(sequences)

def test_prediction_batch_to_device():
    """Test PredictionBatch device transfer."""
    batch = PredictionBatch(test_sequence_set.values())
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    batch.to_device(device)
    assert batch.input_ids.device.type == device
    assert batch.attention_mask.device.type == device

def test_prediction_metrics_initialization():
    """Test PredictionMetrics initialization."""
    metrics = PredictionMetrics()
    assert metrics.total_predictions == 0
    assert metrics.correct_predictions == 0
    assert metrics.total_loss == 0.0

def test_prediction_metrics_update():
    """Test PredictionMetrics update."""
    metrics = PredictionMetrics()
    
    # Update with correct prediction
    metrics.update(torch.tensor([0.8, 0.2]), torch.tensor([1, 0]), 0.5)
    assert metrics.total_predictions == 1
    assert metrics.correct_predictions == 1
    assert metrics.total_loss == 0.5
    
    # Update with incorrect prediction
    metrics.update(torch.tensor([0.3, 0.7]), torch.tensor([1, 0]), 0.8)
    assert metrics.total_predictions == 2
    assert metrics.correct_predictions == 1
    assert metrics.total_loss == 1.3

def test_prediction_metrics_computation():
    """Test PredictionMetrics computation."""
    metrics = PredictionMetrics()
    
    # Add some predictions
    metrics.update(torch.tensor([0.8, 0.2]), torch.tensor([1, 0]), 0.5)
    metrics.update(torch.tensor([0.3, 0.7]), torch.tensor([1, 0]), 0.8)
    
    # Compute metrics
    computed = metrics.compute()
    assert computed["accuracy"] == 0.5
    assert computed["average_loss"] == 0.65
    assert computed["total_predictions"] == 2

def test_prediction_metrics_reset():
    """Test PredictionMetrics reset."""
    metrics = PredictionMetrics()
    
    # Add predictions
    metrics.update(torch.tensor([0.8, 0.2]), torch.tensor([1, 0]), 0.5)
    
    # Reset
    metrics.reset()
    assert metrics.total_predictions == 0
    assert metrics.correct_predictions == 0
    assert metrics.total_loss == 0.0

def test_prediction_engine_with_invalid_input():
    """Test PredictionEngine with invalid input."""
    engine = PredictionEngine(test_model)
    
    # Invalid sequence
    invalid_seq = Sequence("invalid", "ATCGX")
    with pytest.raises(ValueError):
        engine.predict_single(invalid_seq)
    
    # Empty sequence set
    empty_set = SequenceSet({})
    with pytest.raises(ValueError):
        engine.predict_batch(empty_set)

def test_prediction_engine_with_large_batch(test_sequence_set: SequenceSet):
    """Test PredictionEngine with large batch size."""
    engine = PredictionEngine(test_model)
    large_batch_size = len(test_sequence_set) + 1
    
    # Should handle batch size larger than dataset
    results = engine.predict_batch(test_sequence_set, large_batch_size)
    assert len(results) == len(test_sequence_set) 