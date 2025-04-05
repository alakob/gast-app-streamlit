"""
Test package for AMR Predictor.

This package contains all test modules for the AMR Predictor functionality,
including tests for core components, processing modules, and interfaces.
"""

import os
import sys
import pytest
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Create test data directory if it doesn't exist
TEST_DATA_DIR = project_root / "tests" / "data"
TEST_DATA_DIR.mkdir(exist_ok=True)

# Create test output directory if it doesn't exist
TEST_OUTPUT_DIR = project_root / "tests" / "output"
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

# Clean up test output directory before each test session
@pytest.fixture(autouse=True)
def cleanup_test_output():
    """Clean up test output directory before each test session"""
    for file in TEST_OUTPUT_DIR.glob("*"):
        try:
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                import shutil
                shutil.rmtree(file)
        except Exception as e:
            print(f"Warning: Could not remove {file}: {e}") 