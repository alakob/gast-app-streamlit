#!/usr/bin/env python3
"""
Minimal Test Runner for AMR API Tests

This script runs focused tests that have minimal dependencies
to avoid issues with complex test fixtures.
"""
import os
import sys
import subprocess


def run_minimal_tests():
    """Run minimal test modules that don't have complex dependencies."""
    # Set PYTHONPATH to include the project root
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(".")
    
    # Base command with minimal pytest setup
    cmd = [
        "python", "-m", "pytest", 
        "-v",
        "tests/amr_predictor/test_monitoring_minimal.py",
        "--no-header", 
        "--log-cli-level=INFO"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(run_minimal_tests())
