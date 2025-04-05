"""Tests for AMR Predictor CLI."""

import pytest
from click.testing import CliRunner
import json
import asyncio
from pathlib import Path
import tempfile
import os

from amr_predictor.cli import cli

# Test data
TEST_SEQUENCES = {
    "seq1": "ATCGATCGATCG",
    "seq2": "GCTAGCTAGCTA"
}

TEST_PREDICTIONS = {
    "seq1": {"antibiotic1": 0.8, "antibiotic2": 0.3},
    "seq2": {"antibiotic1": 0.2, "antibiotic2": 0.7}
}

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def sequences_file():
    """Create a temporary file with test sequences."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(TEST_SEQUENCES, f)
        return f.name

@pytest.fixture
def predictions_file():
    """Create a temporary file with test predictions."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(TEST_PREDICTIONS, f)
        return f.name

def test_models_list(runner):
    """Test listing available models."""
    result = runner.invoke(cli, ['models', 'list'])
    assert result.exit_code == 0
    assert "Model:" in result.output
    assert "Version:" in result.output
    assert "Description:" in result.output

def test_models_info(runner):
    """Test getting model information."""
    result = runner.invoke(cli, ['models', 'info', 'default'])
    assert result.exit_code == 0
    assert "Model:" in result.output
    assert "Version:" in result.output
    assert "Description:" in result.output
    assert "Supported Antibiotics:" in result.output
    assert "Performance Metrics:" in result.output
    assert "Requirements:" in result.output

def test_predict_from_file(runner, sequences_file):
    """Test prediction from file."""
    result = runner.invoke(cli, ['predict', 'from-file', sequences_file])
    assert result.exit_code == 0
    assert "Created prediction job:" in result.output
    assert "Monitoring job progress..." in result.output

def test_batch_predict(runner, sequences_file):
    """Test batch prediction."""
    result = runner.invoke(cli, [
        'batch', 'predict',
        sequences_file,
        '--batch-size', '2',
        '--max-workers', '1'
    ])
    assert result.exit_code == 0
    assert "Created batch prediction job:" in result.output
    assert "Monitoring job progress..." in result.output

def test_analyze_predictions(runner, predictions_file):
    """Test prediction analysis."""
    result = runner.invoke(cli, [
        'analyze', 'predictions',
        predictions_file,
        '--metrics', 'accuracy',
        '--metrics', 'precision'
    ])
    assert result.exit_code == 0
    assert "Analysis Results:" in result.output
    assert "Metrics:" in result.output
    assert "Distributions:" in result.output
    assert "Correlations:" in result.output
    assert "Summary:" in result.output

def test_jobs_status(runner):
    """Test getting job status."""
    result = runner.invoke(cli, ['jobs', 'status', 'test_job_id'])
    assert result.exit_code == 0
    assert "Job:" in result.output
    assert "Type:" in result.output
    assert "Status:" in result.output
    assert "Progress:" in result.output

def test_jobs_list(runner):
    """Test listing jobs."""
    result = runner.invoke(cli, [
        'jobs', 'list',
        '--status', 'completed',
        '--type', 'prediction',
        '--limit', '5'
    ])
    assert result.exit_code == 0
    assert "Job:" in result.output
    assert "Type:" in result.output
    assert "Status:" in result.output
    assert "Progress:" in result.output

def test_jobs_cancel(runner):
    """Test cancelling a job."""
    result = runner.invoke(cli, ['jobs', 'cancel', 'test_job_id'])
    assert result.exit_code == 0
    assert "Job cancelled successfully" in result.output

def test_invalid_file(runner):
    """Test handling of invalid file."""
    result = runner.invoke(cli, ['predict', 'from-file', 'nonexistent.json'])
    assert result.exit_code != 0
    assert "Error" in result.output

def test_invalid_model(runner):
    """Test handling of invalid model ID."""
    result = runner.invoke(cli, ['models', 'info', 'nonexistent'])
    assert result.exit_code != 0
    assert "Error" in result.output

def test_invalid_job(runner):
    """Test handling of invalid job ID."""
    result = runner.invoke(cli, ['jobs', 'status', 'nonexistent'])
    assert result.exit_code != 0
    assert "Error" in result.output

def test_help(runner):
    """Test help messages."""
    # Test main help
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "AMR Predictor CLI" in result.output
    
    # Test subcommand help
    result = runner.invoke(cli, ['models', '--help'])
    assert result.exit_code == 0
    assert "Manage AMR prediction models" in result.output
    
    result = runner.invoke(cli, ['predict', '--help'])
    assert result.exit_code == 0
    assert "Predict AMR from sequences" in result.output
    
    result = runner.invoke(cli, ['batch', '--help'])
    assert result.exit_code == 0
    assert "Batch processing operations" in result.output
    
    result = runner.invoke(cli, ['analyze', '--help'])
    assert result.exit_code == 0
    assert "Analysis operations" in result.output
    
    result = runner.invoke(cli, ['jobs', '--help'])
    assert result.exit_code == 0
    assert "Job management operations" in result.output 