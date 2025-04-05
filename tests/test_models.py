"""Tests for core models module."""

import pytest
import torch
import numpy as np
from typing import Dict, List

from amr_predictor.core.models import (
    AMRConfig,
    AMRModel,
    SequenceEncoder,
    PredictionHead
)

def test_amr_config_creation(test_model_config: AMRConfig):
    """Test AMRConfig creation and validation."""
    assert test_model_config.model_name == "test_model"
    assert test_model_config.model_type == "transformer"
    assert test_model_config.max_length == 512
    assert test_model_config.batch_size == 32
    assert test_model_config.num_classes == 3
    assert test_model_config.learning_rate == 1e-5
    assert test_model_config.num_epochs == 3

def test_amr_config_invalid():
    """Test AMRConfig validation with invalid parameters."""
    with pytest.raises(ValueError):
        AMRConfig(
            model_name="test",
            model_type="invalid_type",
            max_length=512,
            batch_size=32,
            num_classes=3,
            learning_rate=1e-5,
            num_epochs=3
        )

def test_sequence_encoder_initialization(test_model_config: AMRConfig):
    """Test SequenceEncoder initialization."""
    encoder = SequenceEncoder(test_model_config)
    assert encoder.max_length == test_model_config.max_length
    assert encoder.model_type == test_model_config.model_type

def test_sequence_encoder_forward(test_model_config: AMRConfig):
    """Test SequenceEncoder forward pass."""
    encoder = SequenceEncoder(test_model_config)
    batch_size = 2
    seq_length = 100
    
    # Create dummy input
    input_ids = torch.randint(0, 1000, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    
    # Forward pass
    outputs = encoder(input_ids, attention_mask)
    assert outputs.shape == (batch_size, test_model_config.max_length, encoder.hidden_size)

def test_prediction_head_initialization(test_model_config: AMRConfig):
    """Test PredictionHead initialization."""
    head = PredictionHead(test_model_config)
    assert head.num_classes == test_model_config.num_classes
    assert head.hidden_size == head.hidden_size

def test_prediction_head_forward(test_model_config: AMRConfig):
    """Test PredictionHead forward pass."""
    head = PredictionHead(test_model_config)
    batch_size = 2
    
    # Create dummy input
    hidden_states = torch.randn(batch_size, test_model_config.max_length, head.hidden_size)
    
    # Forward pass
    outputs = head(hidden_states)
    assert outputs.shape == (batch_size, test_model_config.num_classes)

def test_amr_model_initialization(test_model: AMRModel):
    """Test AMRModel initialization."""
    assert test_model.config.model_name == "test_model"
    assert test_model.config.model_type == "transformer"
    assert test_model.config.num_classes == 3

def test_amr_model_forward(test_model: AMRModel):
    """Test AMRModel forward pass."""
    batch_size = 2
    seq_length = 100
    
    # Create dummy input
    input_ids = torch.randint(0, 1000, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    
    # Forward pass
    outputs = test_model(input_ids, attention_mask)
    assert outputs.shape == (batch_size, test_model.config.num_classes)

def test_amr_model_predict(test_model: AMRModel):
    """Test AMRModel prediction method."""
    batch_size = 2
    seq_length = 100
    
    # Create dummy input
    input_ids = torch.randint(0, 1000, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    
    # Predict
    predictions = test_model.predict(input_ids, attention_mask)
    assert predictions.shape == (batch_size, test_model.config.num_classes)
    assert torch.all(predictions >= 0) and torch.all(predictions <= 1)

def test_amr_model_save_load(test_model: AMRModel, test_output_dir: Path):
    """Test AMRModel save and load functionality."""
    save_path = test_output_dir / "test_model.pt"
    
    # Save model
    test_model.save(save_path)
    assert save_path.exists()
    
    # Load model
    loaded_model = AMRModel.load(save_path)
    assert loaded_model.config.model_name == test_model.config.model_name
    assert loaded_model.config.model_type == test_model.config.model_type
    assert loaded_model.config.num_classes == test_model.config.num_classes

def test_amr_model_training(test_model: AMRModel):
    """Test AMRModel training loop."""
    batch_size = 2
    seq_length = 100
    
    # Create dummy data
    input_ids = torch.randint(0, 1000, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    labels = torch.randint(0, test_model.config.num_classes, (batch_size,))
    
    # Training step
    loss = test_model.training_step(input_ids, attention_mask, labels)
    assert isinstance(loss, torch.Tensor)
    assert loss.requires_grad

def test_amr_model_validation(test_model: AMRModel):
    """Test AMRModel validation loop."""
    batch_size = 2
    seq_length = 100
    
    # Create dummy data
    input_ids = torch.randint(0, 1000, (batch_size, seq_length))
    attention_mask = torch.ones(batch_size, seq_length)
    labels = torch.randint(0, test_model.config.num_classes, (batch_size,))
    
    # Validation step
    metrics = test_model.validation_step(input_ids, attention_mask, labels)
    assert isinstance(metrics, dict)
    assert "loss" in metrics
    assert "accuracy" in metrics 