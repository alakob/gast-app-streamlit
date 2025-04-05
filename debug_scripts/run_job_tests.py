#!/usr/bin/env python
"""
Minimal test runner for AMR API job management tests.
This script executes the focused job management tests without
requiring the full AMR application context.
"""

import os
import subprocess
import sys

def main():
    """Run the minimal tests for AMR API job management functionality."""
    print("Running command: python -m pytest -v tests/amr_predictor/test_jobs_minimal.py --no-header --log-cli-level=INFO")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/amr_predictor/test_jobs_minimal.py", "--no-header", "--log-cli-level=INFO"],
        capture_output=False
    )
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
