# AMR Predictor Containerization Guide

This guide provides comprehensive instructions for containerizing the AMR Predictor application with Docker, integrating the Bakta client, PostgreSQL database, and Streamlit frontend.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Docker Components](#docker-components)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Bakta Integration Details](#bakta-integration-details)
7. [PostgreSQL Migration Guide](#postgresql-migration-guide)
8. [Testing & Validation](#testing--validation)
9. [Troubleshooting](#troubleshooting)

## Architecture Overview

The containerized AMR Predictor consists of four main components:

1. **PostgreSQL Database**: Persistent storage for job data, parameters, and results
2. **pgAdmin**: Web-based PostgreSQL administration tool for database management
3. **AMR Predictor API**: Backend service with the Bakta client for bacterial genome annotation
4. **Streamlit Frontend**: User interface for interacting with the AMR Predictor

```
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Streamlit Frontend │<────>│  AMR Predictor API  │
│     (Container)     │      │     (Container)     │
│                     │      │                     │
└─────────────────────┘      └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │                     │
                             │    PostgreSQL DB    │
                             │     (Container)     │
                             │                     │
                             └─────────────────────┘
                                ▲              ▲
                                │              │
                                │     ┌─────────────────────┐
                                │     │                     │
                                └────>│      pgAdmin       │
                                      │     (Container)     │
                                      │                     │
                                      └─────────────────────┘
                                                │
                                                ▼
                                      [External Bakta API]
```

The containers communicate over a dedicated Docker network, with the API container connecting to the external Bakta API service for genome annotation as needed.

## Prerequisites

Before starting, ensure you have:

- Docker Engine (19.03.0+)
- Docker Compose (1.27.0+)
- Python 3.10+
- Free ports: 5432 (PostgreSQL), 8000 (API), 8501 (Streamlit)

## Environment Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd gast-app-streamlit
   ```

2. **Create environment file**:
   ```bash
   cp .env.template .env
   ```

3. **Edit the `.env` file** with your specific configurations:
   - Set a secure PostgreSQL password
   - Add your Bakta API key
   - Configure any other environment-specific settings

## Docker Components

### Docker Compose (`docker-compose.yml`)

The main orchestration file that defines all services, networks, and volumes:

- **PostgreSQL**: Database service with persistent storage
- **AMR API**: Backend API with Bakta client integration
- **Streamlit**: Frontend service for the user interface

### API Dockerfile (`Dockerfile.api`)

Builds the AMR Predictor API container:
- Based on Python 3.10
- Installs all dependencies
- Sets up the PostgreSQL client
- Configures environment for the Bakta client

### Streamlit Dockerfile (`Dockerfile.streamlit`)

Builds the Streamlit frontend container:
- Based on Python 3.10
- Installs Streamlit and all dependencies
- Configures environment for connecting to the API

### PostgreSQL Configuration

Located in `docker/postgres/`:
- **Dockerfile**: Extends the official PostgreSQL image
- **init/create-multiple-databases.sh**: Creates separate dev/test/prod databases
- **init/init-amr-schema.sql**: Sets up the required database schema
- **init/import-sql-schema.sh**: Imports the schema into all databases

## Step-by-Step Deployment

Follow these steps to deploy the containerized AMR Predictor:

### 1. Configure Environment

```bash
# Copy the template
cp .env.template .env

# Edit the .env file with your specific settings
nano .env  # or use any text editor
```

### 2. Build the Docker Images

```bash
# Build all images
docker-compose build
```

### 3. Start the Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 4. Verify Deployment

- **PostgreSQL**: `docker logs amr_postgres`
- **pgAdmin**: Access http://localhost:5050 in your browser
  - Login using credentials from `.env` (default: admin@amrpredictor.org / your_pgadmin_password_here)
  - Add server connection: Right-click Servers → Create → Server
    - Name: AMR Predictor DB
    - Connection tab: Host: postgres, Port: 5432, Username: postgres, Password: (from .env)
- **API**: Access http://localhost:8000/docs in your browser
- **Streamlit**: Access http://localhost:8501 in your browser

### 5. Migrate Existing Data (Optional)

If you have existing data in SQLite, follow the [PostgreSQL Migration Guide](#postgresql-migration-guide) for detailed migration steps.

## Bakta Integration Details

The AMR Predictor API container includes the Bakta client library from `amr_predictor/bakta/` which communicates with the external Bakta API for bacterial genome annotation.

### Data Flow

1. **User uploads sequence via Streamlit UI**
2. **Streamlit sends request to AMR Predictor API**
3. **API creates job in PostgreSQL database**
4. **Background task processes the job**:
   - Calls `BaktaClient` to submit the sequence to the external Bakta API
   - Polls for job completion
   - Downloads and processes the results
5. **Results are stored in PostgreSQL database**
6. **Streamlit retrieves and displays results**

### Configuration

The Bakta client is configured through environment variables in the Docker Compose file:

```yaml
environment:
  - BAKTA_API_URL=${BAKTA_API_URL:-https://bakta.computational.bio/api/v1}
  - BAKTA_API_KEY=${BAKTA_API_KEY:-}
```

These values are passed from your `.env` file. Ensure your Bakta API key is valid.

## PostgreSQL Migration Guide

When transitioning from SQLite to PostgreSQL, follow these steps:

### 1. Export SQLite Data

If you have existing data in SQLite that you want to preserve:

```bash
# Start just the PostgreSQL container
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U postgres -h localhost
```

### 2. Run the Migration Script

```bash
# Run the migration script (parts 1-3)
docker-compose run --rm amr-api python migrate_to_postgresql_part1.py
docker-compose run --rm amr-api python migrate_to_postgresql_part2.py
docker-compose run --rm amr-api python migrate_to_postgresql_part3.py
```

### 3. Verify Migration

```bash
# Connect to PostgreSQL and check data
docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_jobs;"
```

See the full [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md) document for detailed migration instructions.

## Testing & Validation

After deployment, verify that all components are working correctly:

### 1. Verify Database Connection

```bash
# Test API database connection
curl http://localhost:8000/health
```

### 2. Test Job Submission

Upload a test FASTA file through the Streamlit interface and verify that:
- The job is created in the database
- Bakta processing starts
- Results are stored and can be retrieved

### 3. Verify Error Handling

Intentionally submit an invalid FASTA file to ensure proper error handling throughout the system.

## Troubleshooting

### Common Issues & Solutions

#### PostgreSQL Connection Issues

**Problem**: The API cannot connect to PostgreSQL
**Solution**: 
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Verify environment variables in .env
cat .env
```

#### Bakta API Connection Issues

**Problem**: Cannot connect to external Bakta API
**Solution**:
```bash
# Check Bakta API key in .env
# Verify Bakta API endpoint is accessible
docker-compose exec amr-api curl -I ${BAKTA_API_URL}
```

#### Streamlit UI Issues

**Problem**: Streamlit cannot connect to the API
**Solution**:
```bash
# Check if API is running
docker-compose ps amr-api

# Verify API is accessible
curl http://localhost:8000/health

# Check Streamlit logs
docker-compose logs streamlit
```

### Getting Help

If you encounter persistent issues:

1. Check all container logs: `docker-compose logs`
2. Verify all environment variables are properly set
3. Ensure external services (e.g., Bakta API) are accessible
4. Check for port conflicts with other services on your host

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Bakta API Documentation](reference to your Bakta API docs)
- [Streamlit Documentation](https://docs.streamlit.io/)
