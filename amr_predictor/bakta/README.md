# Bakta API Client

A Python client for interacting with the Bakta API for bacterial genome annotation.

## Overview

This package provides a client for interacting with the Bakta API, which offers annotation services for bacterial genomes. The client handles:

- API interaction (submission, status checks, result retrieval)
- Input validation
- Configuration management
- Error handling

## Installation

```bash
# From the project root
pip install -e .
```

## Usage

### Basic Usage

```python
from amr_predictor.bakta import BaktaClient, create_config

# Create a client
client = BaktaClient()

# Create a job configuration
config = create_config(
    genus="Escherichia",
    species="coli",
    strain="K-12",
    locus="ECO",
    locus_tag="ECO"
)

# Submit a job
job_id = client.submit_job("path/to/sequence.fasta", config)

# Check job status
status = client.check_job_status(job_id)

# Retrieve results when done
if status == "COMPLETED":
    results = client.get_job_results(job_id)
```

## Configuration Management

The Bakta client provides extensive configuration management capabilities.

### Creating Configurations

Create a configuration with sensible defaults:

```python
from amr_predictor.bakta import create_config

# Basic configuration
config = create_config(
    genus="Escherichia",
    species="coli",
    strain="K-12"
)

# Configuration with more options
config = create_config(
    genus="Escherichia",
    species="coli",
    strain="K-12",
    locus="ECO",
    locus_tag="ECO",
    complete_genome=True,
    translation_table=11
)
```

### Using Configuration Presets

The package provides predefined presets for common bacterial species:

```python
from amr_predictor.bakta import get_available_presets, get_preset_config, create_config

# Get available presets
presets = get_available_presets()
print(presets)  # ['gram_positive', 'gram_negative', 'escherichia_coli', ...]

# Get a specific preset
ecoli_preset = get_preset_config("escherichia_coli")

# Create a configuration using a preset
config = create_config(
    preset="escherichia_coli",
    strain="K-12",
    locus="ECO",
    locus_tag="ECO"
)
```

### Environment-Based Configuration

Get environment-specific configurations:

```python
from amr_predictor.bakta import get_api_url, get_environment_config

# Get API URL for a specific environment
api_url = get_api_url("prod")  # or "staging", "dev", "local"

# Get environment-specific configuration
prod_config = get_environment_config("prod")
```

### File-Based Configuration

Save and load configurations from files:

```python
from amr_predictor.bakta import create_config, save_config_to_file, load_config_from_file

# Create a configuration
config = create_config(
    genus="Escherichia",
    species="coli",
    strain="K-12"
)

# Save to file
save_config_to_file(config, "ecoli_config.json", format="json")
# or
save_config_to_file(config, "ecoli_config.yaml", format="yaml")

# Load from file
loaded_config = load_config_from_file("ecoli_config.json")
# or
loaded_config = load_config_from_file("ecoli_config.yaml")
```

### Environment Variable Configuration

Create configurations from environment variables:

```python
import os
from amr_predictor.bakta import create_config_from_env

# Set environment variables
os.environ["BAKTA_GENUS"] = "Escherichia"
os.environ["BAKTA_SPECIES"] = "coli"
os.environ["BAKTA_STRAIN"] = "K-12"
os.environ["BAKTA_LOCUS"] = "ECO"
os.environ["BAKTA_LOCUS_TAG"] = "ECO"
os.environ["BAKTA_COMPLETE_GENOME"] = "true"

# Create configuration from environment variables
config = create_config_from_env()
```

### Custom API URLs

Set custom API URLs for different environments:

```python
import os
from amr_predictor.bakta import get_api_url

# Set a custom API URL
os.environ["BAKTA_API_URL_CUSTOM"] = "https://my-custom-bakta-api.example.com/api/v1"

# Get the custom API URL
custom_url = get_api_url("custom")
```

## Error Handling

The Bakta client provides comprehensive error handling:

```python
from amr_predictor.bakta import BaktaClient, BaktaException

client = BaktaClient()

try:
    # Submit a job
    job_id = client.submit_job("path/to/sequence.fasta", config)
except BaktaException as e:
    print(f"Error: {e}")
```

## Validation

The package provides validation functions for FASTA sequences and job configurations:

```python
from amr_predictor.bakta import validate_fasta, validate_job_configuration, is_valid_fasta

# Validate a FASTA file
validate_fasta("path/to/sequence.fasta")

# Check if a FASTA file is valid
if is_valid_fasta("path/to/sequence.fasta"):
    print("The FASTA file is valid")

# Validate a job configuration
validate_job_configuration(config)
```

## Example Scripts

The package includes several example scripts:

- `example.py`: Basic usage of the BaktaClient
- `error_handling_example.py`: Error handling examples
- `config_example.py`: Configuration management examples

Run these scripts to see the client in action:

```bash
python -m amr_predictor.bakta.example
python -m amr_predictor.bakta.error_handling_example
python -m amr_predictor.bakta.config_example
```

## API Reference

### BaktaClient Class

```python
from amr_predictor.bakta import BaktaClient

client = BaktaClient(api_url=None, api_key=None)
```

Methods:

- `submit_job(fasta_path, config)`: Submit a job for processing
- `check_job_status(job_id)`: Check the status of a job
- `get_job_results(job_id)`: Retrieve the results of a completed job

### Configuration Functions

```python
from amr_predictor.bakta import (
    create_config,
    get_api_url,
    load_config_from_file,
    save_config_to_file,
    get_available_presets,
    get_preset_config,
    get_environment_config,
    create_config_from_env,
    DEFAULT_CONFIG,
    CONFIGURATION_PRESETS
)
```

### Validation Functions

```python
from amr_predictor.bakta import (
    validate_fasta,
    validate_job_configuration,
    is_valid_fasta
)
```

## Examples

Several example scripts are provided to demonstrate how to use the Bakta API client:

1. **Simple Example** - A basic example demonstrating client initialization and job submission:
   ```python
   from amr_predictor.bakta import BaktaClient, create_config

   # Initialize the client
   client = BaktaClient()

   # Create a configuration
   config = create_config(
       genus="Escherichia",
       species="coli"
   )
   
   # Submit a job
   job_result = client.initialize_job("example_job")
   client.upload_fasta(job_result["upload_link"], "path/to/sequence.fasta")
   client.start_job(job_result["job_id"], job_result["secret"], config)
   ```

2. **Configuration Example** - An example demonstrating advanced configuration options:
   ```python
   from amr_predictor.bakta import create_config, load_config_from_file, save_config_to_file

   # Create configuration with preset
   config = create_config(
       genus="Staphylococcus",
       species="aureus",
       preset="gram_positive"
   )
   
   # Save configuration for later use
   save_config_to_file(config, "staph_config.json")
   
   # Load configuration from file
   loaded_config = load_config_from_file("staph_config.json")
   ```

3. **Complete Job Workflow** - A complete example script for running annotation jobs:
   ```bash
   # Run the workflow script with a FASTA file
   python -m amr_predictor.bakta.examples.run_bakta_job path/to/sequence.fasta output_directory
   
   # With additional options
   python -m amr_predictor.bakta.examples.run_bakta_job path/to/sequence.fasta output_directory \
       --genus "Staphylococcus" --species "aureus" \
       --complete --translation-table 11
   ```

See the `examples` directory for the complete source code of these examples.

## Integration Testing

The package includes integration tests that interact with the real Bakta API. These tests are marked with the `integration` pytest marker and are skipped by default.

To run the integration tests:

```bash
# Run unit tests only (default)
pytest amr_predictor/bakta/tests/

# Run integration tests
pytest amr_predictor/bakta/tests/ --run-integration
```

The integration tests verify:
- API availability
- FASTA validation
- Job initialization
- Job submission and status polling
- Result retrieval

**Note:** Integration tests require an internet connection and may be subject to API rate limits.

## Testing

To run the unit tests for the Bakta API client:

```bash
pytest amr_predictor/bakta/tests/
```

The tests cover:
- Client initialization and configuration
- API method calls and error handling
- FASTA validation
- Configuration management
- Example script functionality

## License

[MIT](LICENSE) 