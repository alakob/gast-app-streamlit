# Bakta API Client Examples

This directory contains example scripts demonstrating how to use the Bakta API client.

## Available Examples

### `run_bakta_job.py`

A complete example script demonstrating the full Bakta annotation workflow:

1. Creating a Bakta client
2. Submitting a job with a FASTA file
3. Polling for job completion
4. Downloading and saving results

#### Usage

```bash
# Basic usage with default parameters
python run_bakta_job.py path/to/sequence.fasta output_directory

# With custom taxonomic information
python run_bakta_job.py path/to/sequence.fasta output_directory \
    --genus "Staphylococcus" --species "aureus"

# With additional options
python run_bakta_job.py path/to/sequence.fasta output_directory \
    --genus "Escherichia" --species "coli" \
    --strain "K-12" --locus "ECO" --locus-tag "ECO" \
    --complete --translation-table 11 \
    --environment prod --timeout 300 \
    --poll-interval 30 --max-poll-time 3600
```

#### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `fasta_file` | Path to the FASTA file to annotate | (required) |
| `output_dir` | Directory to save the results | (required) |
| `--genus` | Genus name | "Escherichia" |
| `--species` | Species name | "coli" |
| `--strain` | Strain name | "" |
| `--complete` | Flag if the genome is complete | False |
| `--translation-table` | Translation table to use | 11 |
| `--locus` | Locus prefix | "" |
| `--locus-tag` | Locus tag prefix | "" |
| `--environment` | API environment to use | "prod" |
| `--timeout` | API request timeout in seconds | 300 |
| `--poll-interval` | Interval in seconds to check job status | 30 |
| `--max-poll-time` | Maximum time in seconds to poll for job completion | 3600 |

#### Environment Variables

- `BAKTA_API_KEY`: API key for the Bakta API (optional)

## Running the Examples

To run the examples as modules:

```bash
# From the project root directory
python -m amr_predictor.bakta.examples.run_bakta_job path/to/sequence.fasta output_directory
```

## Testing

Unit tests for the examples are available in the `amr_predictor/bakta/tests/test_run_bakta_job.py` file.

To run the tests:

```bash
# From the project root directory
pytest amr_predictor/bakta/tests/test_run_bakta_job.py
``` 