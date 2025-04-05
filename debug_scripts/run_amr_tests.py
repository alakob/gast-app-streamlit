#!/usr/bin/env python3
"""
AMR API Integration Test Runner

This script specifically targets the AMR API integration tests,
running them in isolation from the rest of the test suite.
"""
import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path


def setup_test_env():
    """Set up necessary directories for testing."""
    # Create test data directories if they don't exist
    dirs = [
        "tests/fixtures",
        "testing",
        "results"
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    print("Test environment set up successfully")


def run_tests(test_modules=None, with_coverage=False):
    """Run the specified AMR API integration test modules."""
    # Set PYTHONPATH to include the project root
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(".")
    
    # Create a temporary pytest.ini file to override any existing configuration
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as temp_ini:
        temp_ini.write("[pytest]\n")
        temp_ini.write("testpaths = tests/amr_predictor\n")
        temp_ini.write("python_files = test_*.py\n")
        temp_ini.write("python_classes = Test*\n")
        temp_ini.write("python_functions = test_*\n")
        # Explicitly ignore the root conftest.py
        temp_ini.write("norecursedirs = tests/conftest.py\n")
        temp_ini_path = temp_ini.name
    
    try:
        # Base command
        cmd = [
            "python", "-m", "pytest", 
            "-v", 
            "--log-cli-level=INFO",
            f"--rootdir={os.path.abspath('.')}",
            f"-c={temp_ini_path}"
        ]
        
        # Add coverage if requested
        if with_coverage:
            cmd.extend([
                "--cov=amr_predictor", 
                "--cov-report=term", 
                "--cov-report=html:coverage_report"
            ])
        
        # Add specific modules or run all amr_predictor tests
        if test_modules:
            for module in test_modules:
                if "/" not in module and not module.startswith("test_"):
                    module = f"tests/amr_predictor/test_{module}.py"
                cmd.append(module)
        else:
            cmd.append("tests/amr_predictor/")
        
        print(f"Running command: {' '.join(cmd)}")
        return subprocess.call(cmd, env=env)
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_ini_path):
            os.unlink(temp_ini_path)


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="AMR API Integration Test Runner")
    
    parser.add_argument(
        "--setup", 
        action="store_true",
        help="Set up the test environment"
    )
    
    parser.add_argument(
        "--modules", 
        nargs="+",
        help="Specific test modules to run (without 'test_' prefix)"
    )
    
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run tests with coverage report"
    )
    
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Run all AMR API integration tests"
    )
    
    args = parser.parse_args()
    
    # Setup test environment if requested
    if args.setup:
        setup_test_env()
        return 0
    
    # Determine which tests to run
    test_modules = None
    if args.modules:
        test_modules = args.modules
    
    # Run the tests
    return run_tests(test_modules, args.coverage)


if __name__ == "__main__":
    sys.exit(main())
