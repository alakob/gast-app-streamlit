# Bakta Integration in AMR Predictor

This document explains how the AMR Predictor integrates with Bakta API for bacterial genome annotation using our custom client implementation.

## Architecture Overview

The AMR Predictor uses a custom Bakta client library (`amr_predictor/bakta/`) to interact with the external Bakta API service. This client handles all API communication, job submission, status checking, and result retrieval.

```
┌─────────────────────┐
│                     │
│  AMR Predictor API  │
│     (Container)     │
│                     │
└──────────┬──────────┘
           │
           │ Uses
           ▼
┌─────────────────────┐       ┌─────────────────────┐
│                     │       │                     │
│   Bakta Client      │──────>│  External Bakta API │
│  (amr_predictor/bakta)      │     Service         │
│                     │       │                     │
└─────────────────────┘       └─────────────────────┘
```

## Bakta Client Configuration

The Bakta client is configured through environment variables:

```yaml
environment:
  - BAKTA_API_URL=${BAKTA_API_URL:-https://bakta.computational.bio/api/v1}
  - BAKTA_API_KEY=${BAKTA_API_KEY:-}
```

These variables are defined in your `.env` file (or use defaults if not specified) and are used by the Bakta client library to connect to the appropriate API endpoint with the correct credentials.

## Data Flow for Genome Annotation

1. **User uploads sequence** via Streamlit frontend
2. **AMR Predictor API** creates a job in PostgreSQL 
3. **Background task** processes the job:
   - Uses `BaktaClient` from `amr_predictor/bakta/` to submit the sequence
   - Client sends HTTP requests to the external Bakta API
   - Client polls API for job completion
   - Client downloads results when ready
4. **Results are stored** in PostgreSQL
5. **User accesses results** via Streamlit frontend

## Benefits of This Approach

- **Code Reuse**: Leverages your existing Bakta client implementation
- **Simplified Architecture**: No need to run the full Bakta engine locally
- **Reduced Resource Requirements**: External API handles compute-intensive genome annotation

## Configuration Requirements

To use this integration, you must have:

1. **Bakta API URL**: The URL of the Bakta API service (default: https://bakta.computational.bio/api/v1)
2. **Bakta API Key**: Your authentication key for the Bakta API service

These should be defined in your `.env` file as:

```
BAKTA_API_URL=https://bakta.computational.bio/api/v1
BAKTA_API_KEY=your_bakta_api_key_here
```

Replace `your_bakta_api_key_here` with your actual API key.

## Troubleshooting

If you encounter issues with Bakta integration:

1. **Check API key validity** - Ensure your Bakta API key is valid and has not expired
2. **Verify API endpoint** - Confirm the API URL is correct and accessible
3. **Check logs** - View the AMR API container logs for detailed error information:
   ```bash
   docker-compose logs amr-api
   ```
4. **Test API connectivity** - Test a direct connection to the Bakta API:
   ```bash
   docker-compose exec amr-api curl -I ${BAKTA_API_URL}
   ```
