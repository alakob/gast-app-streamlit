#!/usr/bin/env python3
"""
Test runner for the AMR Predictor application.

This script provides commands for running different test suites and 
configuring the test environment.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path


def setup_test_environment():
    """Set up the test environment by creating necessary directories."""
    # Create test directories if they don't exist
    test_dirs = [
        "tests/fixtures",
        "testing"
    ]
    
    for test_dir in test_dirs:
        os.makedirs(test_dir, exist_ok=True)
    
    print("Test environment setup complete")


def run_tests(modules=None, coverage=False, verbose=False, skip_setup=False):
    """Run the specified test modules with optional coverage reporting."""
    if not skip_setup:
        setup_test_environment()
    
    cmd = ["python", "-m", "pytest"]
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=amr_predictor", "--cov-report=term", "--cov-report=html:coverage_report"])
    
    # Add verbosity
    if verbose:
        cmd.extend(["-v", "--log-cli-level=INFO"])
    
    # Add modules if specified, otherwise run all tests
    if modules:
        for module in modules:
            if os.path.isfile(module):
                cmd.append(module)
            else:
                cmd.append(f"tests/amr_predictor/test_{module}.py")
    else:
        cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd)


def run_api_tests():
    """Run the API integration tests."""
    return run_tests(modules=["amr_api_integration"], verbose=True)


def run_monitoring_tests():
    """Run the monitoring system tests."""
    return run_tests(modules=["monitoring", "monitoring_api"], verbose=True)


def run_database_tests():
    """Run the database integration tests."""
    return run_tests(
        modules=[
            "database_pool", 
            "optimized_database", 
            "job_archiver"
        ], 
        verbose=True
    )


def run_auth_tests():
    """Run the authentication and user management tests."""
    return run_tests(modules=["user_manager"], verbose=True)


def run_all_tests_with_coverage():
    """Run all tests with coverage reporting."""
    return run_tests(coverage=True, verbose=True)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="AMR Predictor Test Runner")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup test environment
    setup_parser = subparsers.add_parser("setup", help="Set up the test environment")
    
    # Run specific test modules
    run_parser = subparsers.add_parser("run", help="Run specific test modules")
    run_parser.add_argument(
        "modules", 
        nargs="*", 
        help="Test modules to run (without 'test_' prefix)"
    )
    run_parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Run with coverage reporting"
    )
    run_parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Run tests with verbose output"
    )
    
    # Pre-configured test suites
    subparsers.add_parser("api", help="Run API integration tests")
    subparsers.add_parser("monitoring", help="Run monitoring system tests")
    subparsers.add_parser("database", help="Run database integration tests")
    subparsers.add_parser("auth", help="Run authentication tests")
    subparsers.add_parser("all", help="Run all tests with coverage reporting")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "setup":
        setup_test_environment()
        return 0
    elif args.command == "run":
        return run_tests(
            modules=args.modules, 
            coverage=args.coverage, 
            verbose=args.verbose
        )
    elif args.command == "api":
        return run_api_tests()
    elif args.command == "monitoring":
        return run_monitoring_tests()
    elif args.command == "database":
        return run_database_tests()
    elif args.command == "auth":
        return run_auth_tests()
    elif args.command == "all":
        return run_all_tests_with_coverage()
    else:
        # No command or invalid command, show help
        print("Please specify a command")
        print("Run 'python run_tests.py --help' for usage information")
        return 1


if __name__ == "__main__":
    sys.exit(main())
