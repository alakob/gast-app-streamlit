"""Tests for visualization module."""

import pytest
import numpy as np
from typing import Dict, List
from pathlib import Path

from amr_predictor.processing.visualization import (
    VisualizationEngine,
    VisualizationConfig,
    VisualizationResult,
    VisualizationFormat
)

def test_visualization_config_creation():
    """Test VisualizationConfig creation."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_heatmap=True,
        include_distribution=True,
        color_scheme="viridis",
        figure_size=(10, 8),
        dpi=300
    )
    assert config.format == VisualizationFormat.HTML
    assert config.include_heatmap is True
    assert config.include_distribution is True
    assert config.color_scheme == "viridis"
    assert config.figure_size == (10, 8)
    assert config.dpi == 300

def test_visualization_config_validation():
    """Test VisualizationConfig validation."""
    # Invalid format
    with pytest.raises(ValueError):
        VisualizationConfig(
            format="invalid_format",  # Not a valid enum value
            include_heatmap=True,
            include_distribution=True
        )
    
    # Invalid figure size
    with pytest.raises(ValueError):
        VisualizationConfig(
            format=VisualizationFormat.HTML,
            include_heatmap=True,
            include_distribution=True,
            figure_size=(0, 8)  # Invalid size
        )
    
    # Invalid DPI
    with pytest.raises(ValueError):
        VisualizationConfig(
            format=VisualizationFormat.HTML,
            include_heatmap=True,
            include_distribution=True,
            dpi=0  # Invalid DPI
        )

def test_visualization_engine_initialization():
    """Test VisualizationEngine initialization."""
    config = VisualizationConfig()
    engine = VisualizationEngine(config)
    assert engine.config == config
    assert engine.results is None

def test_visualization_engine_create_heatmap(test_predictions: Dict[str, Dict[str, float]]):
    """Test heatmap creation."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_heatmap=True
    )
    engine = VisualizationEngine(config)
    
    # Create heatmap
    heatmap = engine.create_heatmap(test_predictions)
    assert heatmap is not None
    assert isinstance(heatmap, str)  # HTML string
    assert "heatmap" in heatmap.lower()

def test_visualization_engine_create_distribution(test_predictions: Dict[str, Dict[str, float]]):
    """Test distribution plot creation."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_distribution=True
    )
    engine = VisualizationEngine(config)
    
    # Create distribution plot
    distribution = engine.create_distribution(test_predictions)
    assert distribution is not None
    assert isinstance(distribution, str)  # HTML string
    assert "distribution" in distribution.lower()

def test_visualization_engine_generate_visualization(test_predictions: Dict[str, Dict[str, float]]):
    """Test visualization generation."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_heatmap=True,
        include_distribution=True
    )
    engine = VisualizationEngine(config)
    
    # Generate visualization
    result = engine.generate_visualization(test_predictions)
    
    # Verify result
    assert isinstance(result, VisualizationResult)
    assert result.config == config
    assert result.visualization is not None
    assert isinstance(result.visualization, str)  # HTML string

def test_visualization_result_creation():
    """Test VisualizationResult creation."""
    config = VisualizationConfig()
    visualization = "<html><body>Test visualization</body></html>"
    
    result = VisualizationResult(config, visualization)
    assert result.config == config
    assert result.visualization == visualization
    assert result.timestamp is not None

def test_visualization_result_serialization():
    """Test VisualizationResult serialization."""
    config = VisualizationConfig()
    visualization = "<html><body>Test visualization</body></html>"
    
    result = VisualizationResult(config, visualization)
    serialized = result.to_dict()
    
    assert serialized["config"] == config.to_dict()
    assert serialized["visualization"] == visualization
    assert "timestamp" in serialized

def test_visualization_engine_save_visualization(test_predictions: Dict[str, Dict[str, float]], test_output_dir: Path):
    """Test saving visualization to file."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_heatmap=True,
        include_distribution=True
    )
    engine = VisualizationEngine(config)
    
    # Generate and save visualization
    output_file = test_output_dir / "test_visualization.html"
    engine.save_visualization(test_predictions, output_file)
    
    # Verify file was created
    assert output_file.exists()
    assert output_file.stat().st_size > 0

def test_visualization_engine_with_empty_predictions():
    """Test VisualizationEngine with empty predictions."""
    config = VisualizationConfig()
    engine = VisualizationEngine(config)
    empty_predictions = {}
    
    with pytest.raises(ValueError):
        engine.generate_visualization(empty_predictions)

def test_visualization_engine_with_invalid_predictions():
    """Test VisualizationEngine with invalid predictions."""
    config = VisualizationConfig()
    engine = VisualizationEngine(config)
    
    # Invalid prediction value
    invalid_predictions = {
        "seq1": {"amoxicillin": 1.5}  # > 1
    }
    
    with pytest.raises(ValueError):
        engine.generate_visualization(invalid_predictions)

def test_visualization_engine_with_missing_antibiotics(test_predictions: Dict[str, Dict[str, float]]):
    """Test VisualizationEngine with missing antibiotics."""
    config = VisualizationConfig()
    engine = VisualizationEngine(config)
    
    # Missing antibiotic
    incomplete_predictions = {
        "seq1": {"amoxicillin": 0.8}  # Missing ciprofloxacin
    }
    
    with pytest.raises(ValueError):
        engine.generate_visualization(incomplete_predictions)

def test_visualization_engine_different_formats(test_predictions: Dict[str, Dict[str, float]]):
    """Test visualization in different formats."""
    # Test HTML format
    html_config = VisualizationConfig(format=VisualizationFormat.HTML)
    html_engine = VisualizationEngine(html_config)
    html_result = html_engine.generate_visualization(test_predictions)
    assert isinstance(html_result.visualization, str)
    assert "<html" in html_result.visualization.lower()
    
    # Test JSON format
    json_config = VisualizationConfig(format=VisualizationFormat.JSON)
    json_engine = VisualizationEngine(json_config)
    json_result = json_engine.generate_visualization(test_predictions)
    assert isinstance(json_result.visualization, str)
    assert json_result.visualization.startswith("{")
    assert json_result.visualization.endswith("}")

def test_visualization_engine_custom_styling(test_predictions: Dict[str, Dict[str, float]]):
    """Test visualization with custom styling."""
    config = VisualizationConfig(
        format=VisualizationFormat.HTML,
        include_heatmap=True,
        include_distribution=True,
        color_scheme="plasma",
        figure_size=(12, 10),
        dpi=400
    )
    engine = VisualizationEngine(config)
    
    # Generate visualization with custom styling
    result = engine.generate_visualization(test_predictions)
    assert result is not None
    assert isinstance(result.visualization, str)
    assert "plasma" in result.visualization.lower() 