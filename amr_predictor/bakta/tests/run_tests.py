#!/usr/bin/env python3
"""
Test runner script for the Bakta module.

This script allows running all Bakta tests or specific test modules.

Usage:
    python run_tests.py               # Run all tests
    python run_tests.py test_client   # Run only test_client.py
    python run_tests.py --verbose     # Run all tests with verbose output
"""

import os
import sys
import pytest
from pathlib import Path

def main():
    """Run Bakta tests based on command-line arguments."""
    # Get the directory of this script
    tests_dir = Path(__file__).parent
    
    # Default arguments
    args = [str(tests_dir)]
    
    # Process command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1].startswith("test_"):
            # Run a specific test file
            args = [str(tests_dir / f"{sys.argv[1]}.py")]
            print(f"Running tests in {args[0]}")
        elif sys.argv[1] == "--verbose" or sys.argv[1] == "-v":
            # Run all tests with verbose output
            args.append("-v")
        else:
            # Invalid argument
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage:")
            print("  python run_tests.py               # Run all tests")
            print("  python run_tests.py test_client   # Run only test_client.py")
            print("  python run_tests.py --verbose     # Run all tests with verbose output")
            return 1
    
    # Add any additional arguments from the command line (after the first one)
    if len(sys.argv) > 2:
        args.extend(sys.argv[2:])
    
    # Run the tests
    return pytest.main(args)

if __name__ == "__main__":
    sys.exit(main()) 