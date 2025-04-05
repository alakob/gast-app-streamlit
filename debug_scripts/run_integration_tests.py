#!/usr/bin/env python
"""
Integration test runner for AMR API components.
This script executes the integration tests that verify interactions
between multiple components of the AMR API.
"""

import os
import subprocess
import sys

def main():
    """Run the integration tests for AMR API components."""
    print("Running command: python -m pytest -v tests/amr_predictor/test_api_integration_minimal.py --no-header --log-cli-level=INFO")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/amr_predictor/test_api_integration_minimal.py", "--no-header", "--log-cli-level=INFO"],
        capture_output=False
    )
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
