#!/usr/bin/env python3
"""
Command-line runner for Bakta Phase 5 tests.

This script provides a convenient way to run Phase 5 tests for the Bakta
query interface with various options.
"""

import argparse
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bakta-phase5-runner")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Bakta Phase 5 tests with various options."
    )
    
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Run all tests (correctness and performance)"
    )
    
    parser.add_argument(
        "--correctness", 
        action="store_true",
        help="Run only correctness tests"
    )
    
    parser.add_argument(
        "--performance", 
        action="store_true",
        help="Run only performance tests"
    )
    
    parser.add_argument(
        "--dataset-size", 
        type=int,
        choices=[100, 1000, 5000, 10000],
        default=5000,
        help="Size of the test dataset (default: 5000)"
    )
    
    parser.add_argument(
        "--iterations", 
        type=int,
        default=5,
        help="Number of iterations for benchmarking (default: 5)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

def run_tests(args):
    """
    Run the specified tests.
    
    Args:
        args: Command-line arguments
    """
    import pytest
    
    # Set environment variables for test configuration
    import os
    os.environ["BAKTA_TEST_DATASET_SIZE"] = str(args.dataset_size)
    os.environ["BAKTA_TEST_ITERATIONS"] = str(args.iterations)
    
    # Define test modules
    tests_to_run = []
    
    if args.all or (not args.correctness and not args.performance):
        # Run all tests if --all is specified or no specific tests are selected
        from amr_predictor.bakta.tests.test_phase5 import main
        return main()
    
    if args.correctness:
        tests_to_run.append("amr_predictor.bakta.tests.test_query_correctness")
    
    if args.performance:
        tests_to_run.append("amr_predictor.bakta.tests.test_query_performance")
    
    # Build pytest arguments
    pytest_args = tests_to_run.copy()
    
    if args.verbose:
        pytest_args.append("-v")
    
    # Run tests
    return pytest.main(pytest_args)

def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        result = run_tests(args)
        return result
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 