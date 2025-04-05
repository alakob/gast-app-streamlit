#!/bin/bash
# Script to run Bakta system integration tests
# 
# This script runs all system integration tests for the Bakta module
# Usage: ./run_system_tests.sh [--verbose]

set -e

# Default values
VERBOSE=0
COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_RESET="\033[0m"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose|-v)
      VERBOSE=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./run_system_tests.sh [--verbose]"
      exit 1
      ;;
  esac
done

# Set Python path to include project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Configure pytest options
PYTEST_OPTS=""
if [ $VERBOSE -eq 1 ]; then
  PYTEST_OPTS="-v"
fi

echo "==================================================="
echo "Running Bakta System Integration Tests"
echo "==================================================="
echo

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Run the system integration tests
echo "Running system integration tests..."
python -m pytest test_system_integration.py $PYTEST_OPTS -m system

# Check the test result
if [ $? -eq 0 ]; then
  echo -e "${COLOR_GREEN}✓ All system integration tests passed!${COLOR_RESET}"
  echo
  echo "System Integration Testing completed successfully."
  exit 0
else
  echo -e "${COLOR_RED}✗ System integration tests failed.${COLOR_RESET}"
  echo
  echo "Please review the test output above for details."
  exit 1
fi 