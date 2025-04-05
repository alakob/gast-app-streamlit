"""Tests for aggregation module."""

import pytest
import numpy as np
from typing import Dict, List
from pathlib import Path

from amr_predictor.processing.aggregation import (
    PredictionAggregator,
    AggregationMethod,
    AggregationResult
)

def test_aggregation_method_enum():
    """Test AggregationMethod enum."""
    assert AggregationMethod.WEIGHTED_AVERAGE.value == "weighted_average"
    assert AggregationMethod.MAJORITY_VOTE.value == "majority_vote"
    assert AggregationMethod.CONFIDENCE_WEIGHTED.value == "confidence_weighted"

def test_prediction_aggregator_initialization():
    """Test PredictionAggregator initialization."""
    aggregator = PredictionAggregator()
    assert aggregator.method == AggregationMethod.WEIGHTED_AVERAGE
    assert aggregator.threshold == 0.5

def test_prediction_aggregator_weighted_average(test_predictions: Dict[str, Dict[str, float]]):
    """Test weighted average aggregation."""
    aggregator = PredictionAggregator(method=AggregationMethod.WEIGHTED_AVERAGE)
    
    # Create multiple prediction sets with weights
    predictions_list = [
        (test_predictions, 0.6),
        (test_predictions, 0.4)
    ]
    
    # Aggregate
    result = aggregator.aggregate(predictions_list)
    
    # Verify result
    assert isinstance(result, AggregationResult)
    assert result.method == AggregationMethod.WEIGHTED_AVERAGE
    assert len(result.aggregated_predictions) == len(test_predictions)
    
    # Check aggregated values
    for seq_name, preds in result.aggregated_predictions.items():
        assert len(preds) == len(test_predictions[seq_name])
        assert all(0 <= v <= 1 for v in preds.values())

def test_prediction_aggregator_majority_vote(test_predictions: Dict[str, Dict[str, float]]):
    """Test majority vote aggregation."""
    aggregator = PredictionAggregator(method=AggregationMethod.MAJORITY_VOTE)
    
    # Create multiple prediction sets
    predictions_list = [
        (test_predictions, 1.0),
        (test_predictions, 1.0)
    ]
    
    # Aggregate
    result = aggregator.aggregate(predictions_list)
    
    # Verify result
    assert isinstance(result, AggregationResult)
    assert result.method == AggregationMethod.MAJORITY_VOTE
    assert len(result.aggregated_predictions) == len(test_predictions)
    
    # Check aggregated values
    for seq_name, preds in result.aggregated_predictions.items():
        assert len(preds) == len(test_predictions[seq_name])
        assert all(v in [0, 1] for v in preds.values())

def test_prediction_aggregator_confidence_weighted(test_predictions: Dict[str, Dict[str, float]]):
    """Test confidence weighted aggregation."""
    aggregator = PredictionAggregator(method=AggregationMethod.CONFIDENCE_WEIGHTED)
    
    # Create multiple prediction sets with different confidences
    predictions_list = [
        (test_predictions, 0.8),
        (test_predictions, 0.6)
    ]
    
    # Aggregate
    result = aggregator.aggregate(predictions_list)
    
    # Verify result
    assert isinstance(result, AggregationResult)
    assert result.method == AggregationMethod.CONFIDENCE_WEIGHTED
    assert len(result.aggregated_predictions) == len(test_predictions)
    
    # Check aggregated values
    for seq_name, preds in result.aggregated_predictions.items():
        assert len(preds) == len(test_predictions[seq_name])
        assert all(0 <= v <= 1 for v in preds.values())

def test_aggregation_result_creation():
    """Test AggregationResult creation."""
    method = AggregationMethod.WEIGHTED_AVERAGE
    aggregated_predictions = {
        "seq1": {"amoxicillin": 0.7, "ciprofloxacin": 0.3},
        "seq2": {"amoxicillin": 0.4, "ciprofloxacin": 0.6}
    }
    
    result = AggregationResult(method, aggregated_predictions)
    assert result.method == method
    assert result.aggregated_predictions == aggregated_predictions
    assert result.timestamp is not None

def test_aggregation_result_serialization():
    """Test AggregationResult serialization."""
    method = AggregationMethod.WEIGHTED_AVERAGE
    aggregated_predictions = {
        "seq1": {"amoxicillin": 0.7, "ciprofloxacin": 0.3},
        "seq2": {"amoxicillin": 0.4, "ciprofloxacin": 0.6}
    }
    
    result = AggregationResult(method, aggregated_predictions)
    serialized = result.to_dict()
    
    assert serialized["method"] == method.value
    assert serialized["aggregated_predictions"] == aggregated_predictions
    assert "timestamp" in serialized

def test_prediction_aggregator_with_empty_predictions():
    """Test PredictionAggregator with empty predictions."""
    aggregator = PredictionAggregator()
    predictions_list = []
    
    with pytest.raises(ValueError):
        aggregator.aggregate(predictions_list)

def test_prediction_aggregator_with_invalid_weights(test_predictions: Dict[str, Dict[str, float]]):
    """Test PredictionAggregator with invalid weights."""
    aggregator = PredictionAggregator()
    
    # Invalid weight (negative)
    predictions_list = [(test_predictions, -0.5)]
    with pytest.raises(ValueError):
        aggregator.aggregate(predictions_list)
    
    # Invalid weight (sum not equal to 1)
    predictions_list = [(test_predictions, 0.6), (test_predictions, 0.5)]
    with pytest.raises(ValueError):
        aggregator.aggregate(predictions_list)

def test_prediction_aggregator_with_missing_sequences(test_predictions: Dict[str, Dict[str, float]]):
    """Test PredictionAggregator with missing sequences."""
    aggregator = PredictionAggregator()
    
    # Create predictions with missing sequences
    predictions1 = test_predictions.copy()
    predictions2 = {k: v for k, v in test_predictions.items() if k != "seq1"}
    
    predictions_list = [(predictions1, 0.5), (predictions2, 0.5)]
    
    with pytest.raises(ValueError):
        aggregator.aggregate(predictions_list)

def test_prediction_aggregator_with_missing_antibiotics(test_predictions: Dict[str, Dict[str, float]]):
    """Test PredictionAggregator with missing antibiotics."""
    aggregator = PredictionAggregator()
    
    # Create predictions with missing antibiotics
    predictions1 = test_predictions.copy()
    predictions2 = {
        "seq1": {"amoxicillin": 0.8},  # Missing ciprofloxacin
        "seq2": {"amoxicillin": 0.3, "ciprofloxacin": 0.7},
        "seq3": {"amoxicillin": 0.5, "ciprofloxacin": 0.5}
    }
    
    predictions_list = [(predictions1, 0.5), (predictions2, 0.5)]
    
    with pytest.raises(ValueError):
        aggregator.aggregate(predictions_list) 