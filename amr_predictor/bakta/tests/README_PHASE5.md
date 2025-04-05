# Bakta Integration - Phase 5 Testing

This directory contains tests for Phase 5 of the Bakta integration, focusing on testing the query interface and data access layer. These tests verify both the correctness of query results and the performance of query operations with large datasets.

## Overview

The Phase 5 testing consists of:

1. **Correctness Testing** - Verifies that queries return accurate results
2. **Performance Testing** - Benchmarks query performance with different data set sizes
3. **Comprehensive Test Runner** - Executes tests and generates detailed reports

## Test Components

### 1. Query Correctness Tests (`test_query_correctness.py`)

These tests verify the correctness of:
- Basic filtering operations
- Complex filtering with multiple conditions
- Attribute-based filtering
- Logical operators (AND/OR)
- Sorting (ascending/descending)
- Pagination
- Edge cases

### 2. Query Performance Tests (`test_query_performance.py`)

These tests benchmark:
- Filtering performance with small, medium, and large datasets
- Complex query performance with multiple conditions
- Sorting performance
- Caching efficiency
- Range query performance
- Batch processing efficiency

### 3. Phase 5 Test Runner (`test_phase5.py`)

The test runner:
- Executes all Phase 5 tests
- Collects test results and metrics
- Generates detailed reports
- Verifies success criteria
- Saves results for later analysis

## Running the Tests

To run the Phase 5 tests:

```bash
# Run all Phase 5 tests
python -m amr_predictor.bakta.tests.test_phase5

# Run only correctness tests
python -m pytest amr_predictor.bakta.tests.test_query_correctness

# Run only performance tests
python -m pytest amr_predictor.bakta.tests.test_query_performance
```

## Test Results

Test results are saved in the `amr_predictor/bakta/tests/results` directory with timestamped filenames. These results include:

- Overall test execution time
- Correctness test results
- Performance test results
- Detailed performance metrics

## Success Criteria

The Phase 5 testing criteria are met when:

1. At least 95% of correctness tests pass
2. At least 90% of performance tests pass
3. Performance metrics meet expected thresholds:
   - Queries execute efficiently even with large datasets
   - Complex queries complete in reasonable time
   - Caching provides significant performance improvement
   - Batch processing enhances throughput

## Performance Optimization Features

These tests validate the implementation of several performance optimization features:

1. **Database Indexes** - Testing efficiency of queries using optimized indexes
2. **Caching** - Measuring performance improvements from the caching system
3. **Batch Processing** - Evaluating efficiency of large dataset handling

## Troubleshooting

If tests fail, check the following:

1. Database configuration and indexes
2. Cache manager implementation
3. Query builder logic
4. Filter and sort implementation

For performance issues, examine:
1. Query execution plans
2. Cache hit rates
3. Batch processing configuration

## Notes for Developers

When modifying the query interface or data access layer:

1. Run these tests to ensure correctness and performance
2. Compare benchmark results with previous runs to detect regressions
3. Add new tests for new features or edge cases 