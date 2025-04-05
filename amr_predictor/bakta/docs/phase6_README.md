# Bakta Integration Phase 6: System Integration Testing

This document outlines the system integration testing phase of the Bakta module, which verifies that all components work together correctly.

## Overview

Phase 6 focuses on integration testing of the complete Bakta workflow:

1. Submitting annotation jobs to the Bakta API
2. Monitoring job status
3. Downloading results
4. Importing and storing annotations in the database
5. Querying annotations with various filtering and sorting options

The unified interface (`BaktaUnifiedInterface`) provides a single entry point to all functionality.

## Components Tested

The system integration tests verify the following components:

- **API Client**: Submitting jobs and retrieving results
- **Job Manager**: Tracking and monitoring job status
- **Parsers**: Processing GFF3 and JSON results
- **Database Manager**: Storing and retrieving annotations
- **Query Interface**: Filtering, sorting, and paginating annotations

## Running the Tests

### System Integration Tests

To run the system integration tests:

```bash
cd /path/to/project/root
./amr_predictor/bakta/tests/run_system_tests.sh
```

Add the `--verbose` flag for more detailed output:

```bash
./amr_predictor/bakta/tests/run_system_tests.sh --verbose
```

### Individual Test Files

You can also run specific test files directly:

```bash
pytest amr_predictor/bakta/tests/test_system_integration.py -v
```

## Test Structure

The system integration tests use mocks for external dependencies (Bakta API) but test the actual integration of all internal components. The tests follow a typical workflow:

1. Create a `BaktaUnifiedInterface` instance
2. Submit a job with a FASTA file
3. Check job status
4. Download job results
5. Import results into the database
6. Query annotations using various filter options and pagination
7. Verify the results match expectations

## Using the Unified Interface

The `BaktaUnifiedInterface` class provides a comprehensive API for all Bakta operations:

```python
from amr_predictor.bakta import create_bakta_interface

# Create interface using factory function
interface = create_bakta_interface(
    api_key="your-api-key",
    database_path="bakta.db",
    environment="dev"
)

# Alternatively, use as an async context manager
async with create_bakta_interface(api_key="your-api-key") as interface:
    # Use interface methods
    job_id = await interface.submit_job("genome.fasta", "My Job")
    # ...
```

See the example script at `amr_predictor/bakta/examples/unified_interface_example.py` for a complete usage example.

## Key Benefits of the Unified Interface

- **Simplicity**: Single entry point for all Bakta operations
- **Consistency**: Common patterns for synchronous and asynchronous operations
- **Error Handling**: Standardized error handling across all components
- **Flexibility**: Support for both simple and complex queries
- **Maintainability**: Reduces code duplication and improves organization

## Adding New Tests

When adding new system integration tests:

1. Add the test to `test_system_integration.py`
2. Mark it with `@pytest.mark.system` to include it in system test runs
3. Use mocks for external services but test real component integration
4. Follow the existing patterns for setup and assertions

## Next Steps

After completing Phase 6:

1. Document all APIs using standardized docstrings
2. Create additional examples for common use cases
3. Implement a CLI interface for common operations
4. Integrate with the broader AMR predictor system 