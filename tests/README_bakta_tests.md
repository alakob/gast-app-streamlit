# Bakta API Client Tests

This directory contains tests for the Bakta API client. The tests are divided into unit tests and integration tests.

## Test Files

- `test_bakta_client.py`: Unit tests for the `BaktaClient` class
- `test_bakta_validation.py`: Unit tests for the validation functions
- `test_bakta_config.py`: Unit tests for the configuration management system
- `test_bakta_integration.py`: Integration tests for the Bakta API client
- `bakta_conftest.py`: Test fixtures for Bakta API client tests

## Running the Tests

### Unit Tests

To run the unit tests, use the following command:

```bash
pytest tests/test_bakta_client.py tests/test_bakta_validation.py tests/test_bakta_config.py -v
```

### Integration Tests

The integration tests require an internet connection and interact with the real Bakta API. They are skipped by default to avoid making unnecessary API calls during regular testing.

To run the integration tests, use the `--run-integration` flag:

```bash
pytest tests/test_bakta_integration.py --run-integration -v
```

Alternatively, you can run specific integration tests:

```bash
pytest tests/test_bakta_integration.py::test_initialize_job --run-integration -v
```

## Test Configuration

### Integration Test Environment Variables

The integration tests use the following environment variables:

- `BAKTA_API_URL_TEST`: Custom API URL for integration tests (optional)
- `BAKTA_API_KEY_TEST`: API key for integration tests (optional)
- `BAKTA_TEST_JOB_ID`: Job ID for testing result retrieval (optional)
- `BAKTA_TEST_JOB_SECRET`: Job secret for testing result retrieval (optional)

Example:

```bash
export BAKTA_API_URL_TEST="https://api.bakta.computational.bio/api/v1"
export BAKTA_API_KEY_TEST="your-api-key"
pytest tests/test_bakta_integration.py --run-integration -v
```

## Test Coverage

The tests cover the following aspects of the Bakta API client:

### BaktaClient Tests

- Initialization with different parameters
- API method calls (initialize_job, upload_fasta, start_job, etc.)
- Error handling for API errors
- Job workflow (submit, poll, get results)
- Custom configuration usage

### Validation Tests

- FASTA format validation
- Job configuration validation
- Error handling for invalid inputs

### Configuration Tests

- Creating configurations with default and custom values
- Using configuration presets
- Environment-specific configurations
- File-based configuration management
- Environment variable-based configuration

### Integration Tests

- Validating real FASTA sequences
- Initializing jobs with the real API
- Complete job workflow with the real API
- Downloading result files from completed jobs

## Test Data

The tests use the following test data:

- Sample FASTA sequences
- Sample job configurations
- Mock API responses
- Environment-specific configurations

## Adding New Tests

To add new tests, follow these guidelines:

1. Create a new test function in the appropriate test file
2. Use the fixtures from `bakta_conftest.py` for test data
3. Use pytest's assertion methods to verify functionality
4. For integration tests, mark the test with `@pytest.mark.integration`
5. For tests that require internet connection, use `@pytest.mark.skipif(not has_internet_connection(), reason="No internet connection")`

## Test Maintenance

To keep the tests up to date:

1. Update the test data when the API or client changes
2. Add tests for new functionality
3. Update integration tests if the API behavior changes
4. Keep test fixtures in sync with the client's implementation 