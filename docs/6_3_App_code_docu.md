# AMR Predictor - Technical Documentation

## 1. Overview

The AMR Predictor is a Python-based application designed to predict antimicrobial properties of genetic sequences and provide comprehensive annotations. The system utilizes a transformer model for predictions and integrates with the Bakta API service for sequence annotation. Results are stored in a SQLite database for efficient retrieval.

This application consists of several key components:
- A transformer-based prediction model
- Sequence processing pipeline
- Bakta API integration for annotation
- SQLite database for persistent storage
- RESTful API and WebSocket interfaces

Originally developed as a CLI tool, the application now provides a comprehensive API suitable for integration with web-based frontends supporting multiple concurrent users.

## 2. Setup and Installation

### Dependencies

```bash
# Install Python dependencies
pip install fastapi uvicorn pydantic sqlalchemy aiohttp websockets elasticsearch transformers torch numpy pandas matplotlib

# Additional dependencies
pip install python-multipart python-dotenv
```

### Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Create a `.env` file with the following configuration:
   ```
   BAKTA_API_KEY=your_bakta_api_key
   BAKTA_API_URL=https://api.bakta.example.com/v1
   MODEL_PATH=./models/amr_transformer
   DATABASE_URL=sqlite:///amr_predictor.db
   ```

### Database Initialization

```bash
# Initialize the database (run once)
python -m app.db.init_db
```

### Starting the Service

```bash
# Start the backend service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup, the application will:
1. Load the transformer model into memory
2. Initialize database connections
3. Establish connections to external services

## 3. API Endpoints

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Process a sequence for prediction and annotation |
| `/api/jobs` | POST | Create a new analysis job |
| `/api/jobs/{job_id}` | GET | Retrieve job status and results |
| `/api/batch` | POST | Submit multiple sequences for batch processing |
| `/api/batch/{batch_id}` | GET | Retrieve batch processing results |
| `/api/models` | GET | List available prediction models |
| `/ws/jobs/{job_id}` | WebSocket | Real-time updates for job progress |

### Detailed Endpoint Specifications

#### POST /api/analyze

**Purpose**: Process a single sequence to predict antimicrobial properties and fetch annotations.

**Request**:
```json
{
  "sequence": "ACGTACGT...",
  "model_id": "amr_default"  // Optional, defaults to the primary model
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": {
    "prediction": {
      "is_antimicrobial": true,
      "confidence": 0.92,
      "class_probabilities": {
        "antimicrobial": 0.92,
        "non_antimicrobial": 0.08
      }
    },
    "annotations": {
      "gene_id": "AMR123",
      "description": "Beta-lactamase enzyme",
      "functions": ["antibiotic resistance", "hydrolase"],
      "organism": "Escherichia coli",
      "additional_properties": { ... }
    }
  }
}
```

**Validation Rules**:
- Sequence must contain only valid characters: A, C, G, T
- Sequence length must be between 10 and 10,000 characters

#### POST /api/jobs

**Purpose**: Create an asynchronous job for sequence analysis.

**Request**:
```json
{
  "sequence": "ACGTACGT...",
  "model_id": "amr_default",
  "include_annotations": true  // Optional, defaults to true
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2023-08-15T14:30:00Z"
}
```

#### GET /api/jobs/{job_id}

**Purpose**: Retrieve the status and results of a job.

**Parameters**:
- `job_id`: UUID of the job

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",  // One of: pending, processing, completed, failed
  "created_at": "2023-08-15T14:30:00Z",
  "completed_at": "2023-08-15T14:30:05Z",
  "results": { ... }  // Same format as /api/analyze response
}
```

#### POST /api/batch

**Purpose**: Submit multiple sequences for batch processing.

**Request**:
```json
{
  "sequences": [
    "ACGTACGT...",
    "GCTAGCTA..."
  ],
  "model_id": "amr_default",
  "include_annotations": true
}
```

**Response**:
```json
{
  "batch_id": "7f9c5d3a-e29b-41d4-a716-446655440000",
  "status": "pending",
  "job_count": 2,
  "created_at": "2023-08-15T14:35:00Z"
}
```

#### WebSocket: /ws/jobs/{job_id}

**Purpose**: Establish a WebSocket connection for real-time job updates.

**Messages Received**:
```json
{
  "type": "status_update",
  "data": {
    "status": "processing",
    "progress": 0.5,
    "message": "Processing sequence"
  }
}
```

```json
{
  "type": "completed",
  "data": {
    "results": { ... }  // Complete results object
  }
}
```

## 4. Data Formats

### Prediction Results

```json
{
  "is_antimicrobial": true,
  "confidence": 0.92,
  "class_probabilities": {
    "antimicrobial": 0.92,
    "non_antimicrobial": 0.08
  }
}
```

### Annotation Results

```json
{
  "gene_id": "AMR123",
  "description": "Beta-lactamase enzyme",
  "functions": ["antibiotic resistance", "hydrolase"],
  "organism": "Escherichia coli",
  "sequence_properties": {
    "length": 280,
    "gc_content": 0.52,
    "molecular_weight": 31240
  },
  "domains": [
    {
      "name": "Beta-lactamase",
      "start": 24,
      "end": 285,
      "score": 180.5
    }
  ]
}
```

## 5. Database Schema

The application uses a SQLite database with the following structure:

### Jobs Table

| Column | Type | Description |
|--------|------|-------------|
| job_id | TEXT | Primary key, UUID |
| status | TEXT | Job status (pending, processing, completed, failed) |
| sequence_hash | TEXT | SHA-256 hash of the sequence |
| sequence | TEXT | The actual sequence |
| model_id | TEXT | ID of the model used for prediction |
| created_at | DATETIME | Job creation timestamp |
| completed_at | DATETIME | Job completion timestamp |
| results | TEXT | JSON string with prediction results |

### Annotations Table

| Column | Type | Description |
|--------|------|-------------|
| sequence_hash | TEXT | Primary key, SHA-256 hash of the sequence |
| sequence | TEXT | The actual sequence |
| annotations | TEXT | JSON string with annotation data |
| fetched_at | DATETIME | When annotations were retrieved |
| last_accessed | DATETIME | Last access timestamp |

### Batch Jobs Table

| Column | Type | Description |
|--------|------|-------------|
| batch_id | TEXT | Primary key, UUID |
| status | TEXT | Batch status |
| job_ids | TEXT | JSON array of individual job IDs |
| created_at | DATETIME | Batch creation timestamp |
| completed_at | DATETIME | Batch completion timestamp |

## 6. External API Integration

### Bakta API Integration

The application integrates with the Bakta API service for sequence annotation:

- **Endpoint**: `https://api.bakta.example.com/v1/annotate`
- **Authentication**: API key in Authorization header
- **Request Method**: POST
- **Request Format**:
  ```json
  {
    "sequence": "ACGTACGT...",
    "options": {
      "format": "json",
      "detailed": true
    }
  }
  ```

**Considerations**:
- The API has a rate limit of 10 requests per minute
- Maximum sequence length: 10 MB
- The backend implements retries with exponential backoff for failed requests
- Annotations are cached in the local database to minimize API calls

## 7. Concurrency and Performance

### Concurrency Model

The application uses FastAPI's asynchronous framework to handle multiple concurrent users:

- **Request Handling**: Async endpoints using FastAPI
- **Database Access**: Connection pooling with SQLAlchemy
- **Model Inference**: Shared transformer model loaded at startup
- **External API Calls**: Asynchronous with aiohttp

### Performance Optimizations

- **Model Loading**: The transformer model is loaded once at application startup
- **Caching**: Annotations are cached in the database to prevent redundant API calls
- **Database Transactions**: Short-lived transactions to minimize locking
- **Background Processing**: Long-running predictions are processed in background tasks
- **Batch Processing**: Multiple sequences can be processed efficiently in batches
- **WebSockets**: Real-time updates reduce polling overhead

### SQLite Concurrency Limitations

SQLite has a single-writer, multiple-reader concurrency model. The application addresses this with:

- Connection pooling
- Short-lived transactions
- Retry logic for write conflicts
- Read preference when possible

## 8. Error Handling

### Common Error Responses

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | Bad Request | Invalid input parameters |
| 404 | Not Found | Resource (job, batch) not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | External service (Bakta API) unavailable |

### Sample Error Response

```json
{
  "error": {
    "code": "invalid_sequence",
    "message": "Invalid sequence format",
    "details": "Sequence contains invalid characters. Only A, C, G, T allowed."
  }
}
```

### Error Handling Strategy

- Input validation via Pydantic models
- Structured error responses with consistent format
- Detailed error logging on the server
- Graceful degradation (e.g., returning predictions without annotations when Bakta API is unavailable)

## 9. Security Considerations

### Input Validation

- All input is validated using Pydantic models
- Sequence strings are sanitized to prevent injection attacks
- Request size limits are enforced

### API Security

- API endpoints can be secured with JWT authentication (configurable)
- Role-based access control for admin operations
- Rate limiting to prevent abuse

### Data Security

- Sensitive configuration (API keys) stored in environment variables
- Database connections use parameterized queries to prevent SQL injection
- Result data is associated with job IDs that can be secured per user

## 10. Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_prediction.py
pytest tests/test_annotation.py

# Run with coverage report
pytest --cov=app tests/
```

### Test Endpoints

The API includes testing endpoints (disabled in production):

- `/api/test/predict`: Test prediction without saving results
- `/api/test/annotate`: Test annotation without calling the external API

### Mocking External Services

For development and testing, mock responses for the Bakta API are available:

```bash
# Start with mocked external services
MOCK_EXTERNAL_SERVICES=1 uvicorn app.main:app
```

## Additional Resources

- API Documentation: `/docs` or `/redoc` (Swagger UI and ReDoc)
- Model Information: `/api/models/info`
- Health Check: `/health` 