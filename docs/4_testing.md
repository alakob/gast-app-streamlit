# AMR Predictor Testing Framework

## Overview

The AMR Predictor application includes a comprehensive testing framework designed to ensure reliability, maintainability, and correctness of all components. This document outlines the testing approach, available test suites, and instructions for running tests.

## Testing Architecture

The testing framework uses pytest and is structured to cover multiple layers of the application:

1. **Unit Tests**: Target individual functions and classes to verify they work in isolation
2. **Integration Tests**: Verify that components interact correctly with each other
3. **API Tests**: Ensure that the API endpoints behave as expected
4. **End-to-End Tests**: Test the complete workflow from input to output

## Test Directory Structure

```
tests/
├── amr_predictor/
│   ├── conftest.py                    # Common fixtures for all tests
│   ├── test_amr_api_integration.py    # Tests for the AMR API integration
│   ├── test_database_pool.py          # Tests for database connection pooling
│   ├── test_job_archiver.py           # Tests for job archiving functionality
│   ├── test_monitoring.py             # Tests for the monitoring system
│   ├── test_monitoring_api.py         # Tests for the monitoring API
│   ├── test_optimized_database.py     # Tests for the optimized database manager
│   └── test_user_manager.py           # Tests for user authentication and management
└── fixtures/                          # Test data and fixtures
    └── test.fasta                     # Sample FASTA file for testing
```

## Running Tests

### Running All Tests

```bash
python -m pytest tests/
```

### Running Specific Test Modules

```bash
python -m pytest tests/amr_predictor/test_amr_api_integration.py
python -m pytest tests/amr_predictor/test_monitoring.py
```

### Running Tests with Coverage

```bash
python -m pytest --cov=amr_predictor tests/
```

### Debug Logging During Tests

```bash
python -m pytest tests/ -v --log-cli-level=DEBUG
```

## Test Components

### Database Integration Tests

Tests verify the database operations including:
- Connection pooling functionality
- Job storage and retrieval
- Optimized database access patterns
- Transaction handling

### API Integration Tests

Tests ensure the API endpoints work correctly including:
- Job creation, retrieval, and updating
- User authentication and authorization
- Error handling and status codes
- File uploads and downloads

### Monitoring System Tests

Tests validate the monitoring system including:
- Metrics collection and reporting
- Performance tracking
- Error rate monitoring
- System status reporting

### User Management Tests

Tests verify user functionality including:
- User registration and authentication
- Password hashing and verification
- Token generation and validation
- User role permissions

## Sample Test Flow

The following commands demonstrate a complete flow of using the AMR predictor for testing purposes:

```bash
# Predict AMR using a test file
python -m amr_predictor predict \
    --fasta datasets/test.fasta \
    --model 'alakob/DraGNOME-2.5b-v1' \
    --segment-length 300 \
    --segment-overlap 10 \
    --cpu \
    --output testing/ \
    --verbose

# Aggregate the results
python -m amr_predictor aggregate \
    --input-files testing/test_DraGNOME-2.5b-v1_amr_predictions_20250402_173325.csv \
    --output testing/ \
    --model-suffix "_amr_predictions" \
    --verbose

# Process the sequences
python -m amr_predictor sequence \
    --input testing/test_DraGNOME-2.5b-v1_amr_predictions_20250402_173325.csv \
    --output testing/ \
    --threshold 0.5 \
    --verbose

# Visualize the results
python -m amr_predictor visualize \
    --input testing/test_DraGNOME-2.5b-v1_amr_predictions_20250402_173325.csv \
    --processed testing/ \
    --step-size 10 \
    --verbose
```

# Run AMR API SERVER
python -m uvicorn amr_predictor.web.api:app --log-level debug


## Adding New Tests

When adding new functionality to the AMR Predictor, follow these guidelines:

1. Create test cases before or alongside new code (TDD approach when possible)
2. Use fixtures from conftest.py for common test dependencies
3. Aim for high test coverage (>80%) for all new code
4. Include both positive and negative test cases
5. Mock external dependencies when appropriate

## Continuous Integration

All tests run automatically in the CI/CD pipeline when code is pushed to the repository. Tests must pass before code can be merged into the main branch.
# AMR API CALLS
cd /Users/alakob/projects/gast-app-streamlit && python -m uvicorn amr_predictor.web.api:app --reload

python -m uvicorn amr_predictor.web.api:app --reload

# BAKTA API CALLS

