#!/bin/bash
# Script to run Phase 5 tests for the Bakta API
# This script allows running correctness and performance tests with configurable options

# Default values
DATASET_SIZE=5000
ITERATIONS=5
TEST_TYPE="all"
VERBOSE=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --correctness)
            TEST_TYPE="correctness"
            shift
            ;;
        --performance)
            TEST_TYPE="performance"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --dataset-size=*)
            DATASET_SIZE="${1#*=}"
            shift
            ;;
        --iterations=*)
            ITERATIONS="${1#*=}"
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --all               Run all tests (default)"
            echo "  --correctness       Run only correctness tests"
            echo "  --performance       Run only performance tests"
            echo "  --dataset-size=SIZE Set the dataset size (default: 5000)"
            echo "                      Valid sizes: 100, 1000, 5000, 10000"
            echo "  --iterations=NUM    Set the number of iterations for benchmarking (default: 5)"
            echo "  -v, --verbose       Enable verbose output"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Export environment variables for tests
export BAKTA_TEST_DATASET_SIZE=$DATASET_SIZE
export BAKTA_TEST_ITERATIONS=$ITERATIONS

# Print configuration
echo "====================== Bakta Phase 5 Tests ======================="
echo "Test type:       $TEST_TYPE"
echo "Dataset size:    $DATASET_SIZE"
echo "Iterations:      $ITERATIONS"
echo "Verbose:         $([ $VERBOSE -eq 1 ] && echo "Yes" || echo "No")"
echo "=================================================================="

# Run the tests
PYTEST_OPTS="-xvs"
if [ $VERBOSE -eq 0 ]; then
    PYTEST_OPTS="-x"
fi

EXIT_CODE=0

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "correctness" ]; then
    echo "Running correctness tests..."
    python -m pytest amr_predictor/bakta/tests/test_query_correctness.py $PYTEST_OPTS
    CORRECTNESS_EXIT=$?
    EXIT_CODE=$((EXIT_CODE + CORRECTNESS_EXIT))
fi

if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "performance" ]; then
    echo "Running performance tests..."
    python -m pytest amr_predictor/bakta/tests/test_query_performance.py $PYTEST_OPTS
    PERFORMANCE_EXIT=$?
    EXIT_CODE=$((EXIT_CODE + PERFORMANCE_EXIT))
fi

echo "=================================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "All tests passed successfully!"
else
    echo "Tests failed with exit code $EXIT_CODE"
fi
echo "=================================================================="

exit $EXIT_CODE 