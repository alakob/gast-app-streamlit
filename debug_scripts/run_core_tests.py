#!/usr/bin/env python
"""
Core component test runner for AMR Predictor.
This script executes the tests for essential core components including:
- Sequence processing pipeline
- Model registry
- Prediction engine
"""

import os
import subprocess
import sys

def main():
    """Run the tests for core AMR Predictor components."""
    print("Running command: python -m pytest -v tests/amr_predictor/test_core_minimal.py --no-header --log-cli-level=INFO")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/amr_predictor/test_core_minimal.py", "--no-header", "--log-cli-level=INFO"],
        capture_output=False
    )
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
