# Docker Development Guide for AMR Predictor

This guide provides comprehensive step-by-step instructions for developing the AMR Predictor application within the Docker environment. Follow these instructions sequentially to ensure a successful setup and development experience.

**Quick Reference:**
- Start AMR API locally: `python -m uvicorn amr_predictor.web.api:app --log-level debug`
- Start Streamlit locally: `streamlit run streamlit/app.py`

## Table of Contents

1. [Understanding the Environment Structure](#understanding-the-environment-structure)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Starting and Managing Services](#starting-and-managing-services)
5. [Development Workflow](#development-workflow)
6. [Bakta API Integration](#bakta-api-integration)
7. [Database Management](#database-management)
8. [SQLite to PostgreSQL Migration](#sqlite-to-postgresql-migration)
9. [Testing in Docker](#testing-in-docker)
10. [Debugging](#debugging)
11. [Common Development Tasks](#common-development-tasks)
12. [Best Practices](#best-practices)

## Understanding the Environment Structure

The AMR Predictor uses three separate environments for different stages of development:

1. **Development (dev)**
   - Database: `amr_predictor_dev`
   - Purpose: Active development and feature implementation
   - Used for: Daily development tasks and local testing

2. **Testing (test)**
   - Database: `amr_predictor_test`
   - Purpose: Running automated tests and validation
   - Used for: CI/CD pipelines and structured testing

3. **Production (prod)**
   - Database: `amr_predictor_prod`
   - Purpose: Live application serving end users
   - Used for: Production deployment

Each environment uses a separate PostgreSQL database to maintain proper isolation of data and configurations.

### Architecture Overview

The containerized AMR Predictor consists of four main components with the following data flow:

```
┌─────────────────────┐      ┌─────────────────────┐        ┌─────────────────┐
│                     │      │                     │        │                 │
│  Streamlit Frontend │<────>│  AMR Predictor API  │───────>│ External Bakta  │
│     (Container)     │      │     (Container)     │        │      API        │
│                     │      │    uses bakta/      │<───────│                 │
└─────────────────────┘      └──────────┬──────────┘        └─────────────────┘
                                        │
                                        │ Stores results
                                        │ from both Bakta 
                                        │ and AMR predictions
                                        ▼
                             ┌─────────────────────┐
                             │                     │
                             │    PostgreSQL DB    │
                             │     (Container)     │
                             │                     │
                             └─────────────────────┘
                                        ▲
                                        │ Management 
                                        │ Interface
                             ┌─────────────────────┐
                             │                     │
                             │      pgAdmin       │
                             │    (Container)     │
                             │                     │
                             └─────────────────────┘
```

## Prerequisites

Before beginning, ensure you have installed:

1. **Docker Engine** (19.03.0+)
2. **Docker Compose** (1.27.0+)
3. **Git** for version control
4. **Free ports** on your machine:
   - 5432 (PostgreSQL)
   - 5050 (pgAdmin)
   - 8000 (API)
   - 8501 (Streamlit)

## Initial Setup

Follow these steps in order to set up your development environment:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd gast-app-streamlit
```

### 2. Configure Environment

Create and configure your environment file:

```bash
# Create environment file from template
cp .env.template .env

# Edit .env with your development settings
nano .env  # or use any text editor
```

Required settings for the development environment:
```
# PostgreSQL Configuration
PG_HOST=postgres
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=dev_password
PG_DATABASE_DEV=amr_predictor_dev
PG_DATABASE_TEST=amr_predictor_test
PG_DATABASE_PROD=amr_predictor_prod
ENVIRONMENT=dev

# pgAdmin Configuration
PGADMIN_EMAIL=admin@amrpredictor.org
PGADMIN_PASSWORD=admin

# Bakta API Configuration
BAKTA_API_URL=https://bakta.computational.bio/api/v1
BAKTA_API_KEY=your_bakta_api_key_here
```

**Important**: Replace `your_bakta_api_key_here` with your actual Bakta API key.

### 3. Verify Docker Configuration Files

Check that your Docker configuration files are correctly set up for development:

#### docker-compose.yml

Ensure your `docker-compose.yml` includes proper volume bindings for development:

```yaml
# In the amr-api service section:
volumes:
  - ./amr_predictor:/app/amr_predictor
  - result_data:/app/results

# In the streamlit service section:
volumes:
  - ./streamlit:/app/streamlit
  - ./amr_predictor:/app/amr_predictor
```

#### Dockerfile.api

Check that the API Dockerfile is properly configured for PostgreSQL support:

```dockerfile
# Ensure it includes PostgreSQL dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary python-dotenv
```

#### Dockerfile.streamlit

Verify the Streamlit Dockerfile has the correct path to run the application:

```dockerfile
# Command to run Streamlit (should point to the streamlit directory)
CMD ["streamlit", "run", "streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Starting and Managing Services

### 1. Start the Development Environment

```bash
# Build and start all services in detached mode
docker-compose up -d --build

# Check if all services are running properly
docker-compose ps
```

### 2. Verify Service Health

```bash
# Check container logs for any startup issues
docker-compose logs

# Verify PostgreSQL is up and responding
docker-compose exec postgres pg_isready -U postgres

# Test the API health endpoint
curl http://localhost:8000/health

# Verify Streamlit is accessible
open http://localhost:8501
```

### 3. Access pgAdmin (Database Management UI)

Open your browser and navigate to http://localhost:5050

Login with the credentials defined in your `.env` file:
- Username: `admin@amrpredictor.org` (or your configured PGADMIN_EMAIL)
- Password: `admin` (or your configured PGADMIN_PASSWORD)

Add a new server connection in pgAdmin:
1. Right-click on "Servers" and select "Create" > "Server..."
2. Name: `AMR Predictor`
3. Connection tab:
   - Host: `postgres` 
   - Port: `5432`
   - Username: `postgres`
   - Password: `dev_password` (or your configured PG_PASSWORD)

## Development Workflow

### Making Code Changes

1. **Edit Code on Host Machine**:
   - Make changes to Python files in the `amr_predictor` directory
   - Changes will be immediately available in the containers

2. **Apply Changes**:
   - For API changes: The server will need to be restarted (unless hot reload is configured)
   - For Streamlit changes: Many changes will be automatically reflected

3. **Restart Services When Needed**:
   ```bash
   # Restart only the API service
   docker-compose restart amr-api
   
   # Restart only the Streamlit service
   docker-compose restart streamlit
   ```

### Checking Logs

Continuously monitor logs during development to catch errors:

```bash
# Follow all logs
docker-compose logs -f

# Follow logs for a specific service
docker-compose logs -f amr-api

# View recent logs with specific line count
docker-compose logs --tail=100 amr-api
```

## Bakta API Integration

The AMR Predictor uses a custom Bakta client to interact with the external Bakta API service for bacterial genome annotation.

### Understanding the Bakta Client

The Bakta client library (`amr_predictor/bakta/`) handles:
- API communication with the Bakta service
- Job submission and status checking
- Result retrieval and processing

### Data Flow for Genome Annotation

1. **User uploads sequence** via Streamlit frontend
2. **AMR Predictor API** creates a job in PostgreSQL 
3. **Background task** processes the job:
   - Uses `BaktaClient` to submit the sequence
   - Client sends HTTP requests to the external Bakta API
   - Client polls API for job completion
   - Client downloads results when ready
4. **Results are stored** in PostgreSQL
5. **User accesses results** via Streamlit frontend

### Troubleshooting Bakta Integration

If you experience issues with the Bakta client:

1. **Verify API key and URL**:
   ```bash
   # Check environment variables in the API container
   docker-compose exec amr-api env | grep BAKTA
   ```

2. **Test API connectivity**:
   ```bash
   docker-compose exec amr-api curl -I ${BAKTA_API_URL}
   ```

3. **Check logs for Bakta client errors**:
   ```bash
   docker-compose logs amr-api | grep -i bakta
   ```

4. **Test a direct API client call**:
   ```bash
   docker-compose exec amr-api python -c "from amr_predictor.bakta import BaktaClient; client = BaktaClient(); print(client.test_connection())"
   ```

## Database Management

### Working with PostgreSQL in Docker

The AMR Predictor uses PostgreSQL for data storage. Here's how to work with the database in the Docker environment:

#### Connecting to the Database

```bash
# Connect to PostgreSQL using psql
docker-compose exec postgres psql -U postgres -d amr_predictor_dev

# Run a specific SQL query
docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "SELECT * FROM amr_jobs LIMIT 5;"
```

#### Managing Database Data

```bash
# Backup a database
docker-compose exec postgres pg_dump -U postgres amr_predictor_dev > backup.sql

# Restore a database
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d amr_predictor_dev

# Create test data
docker-compose exec amr-api python -c "from amr_predictor.tools import create_test_data; create_test_data(10)"
```

### Routine Schema Migrations

When making routine schema changes to PostgreSQL:

1. **Create Migration Script**:
   ```bash
   # Create a migration file
   docker-compose exec amr-api python -c "from amr_predictor.core.database_manager import AMRDatabaseManager; db = AMRDatabaseManager(); db.create_migration('add_new_column')"
   ```

2. **Apply Migration**:
   ```bash
   # Apply pending migrations
   docker-compose exec amr-api python -c "from amr_predictor.core.database_manager import AMRDatabaseManager; db = AMRDatabaseManager(); db.apply_migrations()"
   ```

3. **View Schema**:
   Use pgAdmin at http://localhost:5050 to inspect database schema.

## SQLite to PostgreSQL Migration

If you're migrating from SQLite to PostgreSQL, follow this step-by-step approach. The migration is divided into three phases for safety and verification at each step.

### Overview of the Migration Process

The migration consists of three sequential scripts:

1. **Part 1**: Creates PostgreSQL databases and schema structure
2. **Part 2**: Transfers data from SQLite to PostgreSQL
3. **Part 3**: Updates application code to use PostgreSQL

### Step 1: Database Setup

```bash
# Make sure PostgreSQL is running
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U postgres -h localhost

# Run Part 1: Create PostgreSQL databases and schema
docker-compose exec amr-api python migrate_to_postgresql_part1.py
```

This step:
1. Creates the required PostgreSQL databases (dev, test, prod)
2. Sets up the schema structure (tables, indexes, constraints)
3. Prepares the environment but doesn't transfer any data yet

**Verification after Step 1:**
```bash
# Check if the database structure was created properly
docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "\dt"
```

### Step 2: Data Migration

```bash
# Run Part 2: Transfer data from SQLite to PostgreSQL
docker-compose exec amr-api python migrate_to_postgresql_part2.py
```

This step:
1. Reads records from the SQLite database
2. Converts data types as needed (SQLite has different types than PostgreSQL)
3. Writes records to the PostgreSQL database
4. Maintains data integrity during transfer

**Verification after Step 2:**
```bash
# Check if data was migrated successfully
docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_jobs;"

# Compare with SQLite count (if you still have access to the SQLite DB)
docker-compose exec amr-api python -c "import sqlite3; conn = sqlite3.connect('sqlite.db'); print(conn.execute('SELECT COUNT(*) FROM amr_jobs').fetchone()[0])"
```

### Step 3: Code Updates

```bash
# Run Part 3: Update application code to use PostgreSQL
docker-compose exec amr-api python migrate_to_postgresql_part3.py
```

This step:
1. Updates database connection code to use PostgreSQL instead of SQLite
2. Implements connection pooling for better performance
3. Updates error handling for PostgreSQL-specific errors
4. Makes any necessary adjustments to queries for PostgreSQL compatibility

**Verification after Step 3:**
```bash
# Restart the API service to apply code changes
docker-compose restart amr-api

# Check API logs for any errors
docker-compose logs -f amr-api
```

### Complete Migration Verification

After completing all three parts, verify the entire system works:

```bash
# Test a complete workflow
docker-compose exec amr-api python -c "from amr_predictor.core.database_manager import AMRDatabaseManager; db = AMRDatabaseManager(); print('Connection successful' if db.test_connection() else 'Connection failed')"
```

**Important:** Keep a backup of your SQLite database until you've verified the migration is complete and successful.

## Development Workflow Optimization

### Hot Reload Configuration

Configure hot reloading to automatically restart services when code changes:

#### For API Service

Create a new Dockerfile for development:

```dockerfile
# Dockerfile.api.dev
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary python-dotenv uvicorn[standard] watchfiles

# Copy application code
COPY . .

# Create results directory
RUN mkdir -p /app/results

# Set environment variables
ENV PYTHONPATH=/app
ENV RESULTS_DIR=/app/results

# Expose the API port
EXPOSE 8000

# Command with hot reload
CMD ["uvicorn", "amr_predictor.web.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/amr_predictor"]
```

Update your docker-compose.yml to use this Dockerfile for development:

```yaml
amr-api:
  build:
    context: .
    dockerfile: Dockerfile.api.dev
  # Rest of the configuration remains the same
```

#### For Streamlit Service

Streamlit includes hot reloading by default for most changes.

## Testing in Docker

### Run Unit Tests

```bash
# Run unit tests in the API container
docker-compose exec amr-api python -m pytest amr_predictor/tests/

# Run tests with coverage
docker-compose exec amr-api python -m pytest --cov=amr_predictor amr_predictor/tests/
```

### Create Test Database

For testing with a separate database:

1. Ensure your PostgreSQL container has the test database created:
   ```bash
   docker-compose exec postgres psql -U postgres -c "CREATE DATABASE amr_predictor_test;"
   ```

2. Run tests with the test database:
   ```bash
   docker-compose exec -e ENVIRONMENT=test amr-api python -m pytest amr_predictor/tests/
   ```



## Debugging

### Debugging API

1. **Enable Debug Logs**:
   ```bash
   # Set log level to debug
   docker-compose exec amr-api python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
   ```

2. **Attach Debugger**:
   - Use VS Code's "Attach to Running Container" feature
   - Configure remote debugging in PyCharm

3. **Interactive Debugging Session**:
   ```bash
   # Start an interactive Python session
   docker-compose exec amr-api python
   
   # Import modules and debug
   >>> from amr_predictor.core.database_manager import AMRDatabaseManager
   >>> db = AMRDatabaseManager()
   >>> db.get_job("some-job-id")  # Test specific functions
   ```

### Debugging Streamlit

1. **Enable Debug Mode**:
   ```bash
   # Edit docker-compose.yml to add this environment variable to streamlit service
   environment:
     - STREAMLIT_DEBUG=true
   ```

2. **Check Browser Console**:
   - Open developer tools in your browser
   - Check the console for JavaScript errors

## Common Development Tasks

### Add New Dependencies

1. **Add to requirements.txt**:
   - Update requirements.txt with new dependencies

2. **Rebuild Containers**:
   ```bash
   docker-compose build --no-cache amr-api
   docker-compose up -d
   ```

### Work with the Database

1. **Connect via psql**:
   ```bash
   docker-compose exec postgres psql -U postgres -d amr_predictor_dev
   ```

2. **Run SQL Queries**:
   ```bash
   docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "SELECT * FROM amr_jobs LIMIT 5;"
   ```

3. **Backup Dev Database**:
   ```bash
   docker-compose exec postgres pg_dump -U postgres amr_predictor_dev > backup.sql
   ```

### Create Test Data

```bash
# Run a script to create test data
docker-compose exec amr-api python -c "from amr_predictor.tools import create_test_data; create_test_data(10)"
```

## Best Practices

### Docker Development Best Practices

1. **Use Volume Bindings**: Always map your code directories as volumes for a smooth development experience.

2. **Environment Variables**: Use `.env` files for configuration and never hardcode secrets.

3. **Optimize Builds**: Use multi-stage builds and `.dockerignore` to keep images small.

4. **Clean Up Regularly**:
   ```bash
   # Remove unused images
   docker image prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

5. **Use Container Networks**: Isolate development and production networks.

### Code Development Best Practices

1. **Environment Separation**: Maintain clear separation between development, testing, and production environments.
   ```bash
   # Use environment-specific variables
   docker-compose exec amr-api python -c "import os; print(f'Current environment: {os.environ.get("ENVIRONMENT", "dev")}')"   
   ```

2. **Database Transactions**: Always use transactions for database operations to ensure atomicity.
   ```python
   # Example transaction pattern in Python
   with db.transaction():
       # Database operations here
       pass
   ```

3. **Clean Code Organization**: Keep modules small and focused on a single responsibility.
   ```bash
   # Check file length
   docker-compose exec amr-api find amr_predictor -name "*.py" | xargs wc -l | sort -nr | head
   ```

4. **Proper Error Handling**: Implement consistent error handling using try/except blocks with early returns.
   ```python
   # Recommended error handling pattern
   try:
       # Operation that might fail
   except SpecificException as e:
       # Log and handle the specific error
       logger.error(f"Specific error occurred: {e}")
       # Take appropriate action
   ```

5. **Logging Strategy**: Use appropriate log levels for different environments.
   ```bash
   # Set appropriate log level based on environment
   docker-compose exec amr-api python -c "import logging; logging.basicConfig(level=logging.DEBUG if os.environ.get('ENVIRONMENT') == 'dev' else logging.INFO)" 
   ```

6. **Code Formatting**: Maintain consistent code style with automated tools:
   ```bash
   # Format code with Black
   docker-compose exec amr-api black amr_predictor/
   ```

## Conclusion

By following this guide, you'll have a productive development environment for the AMR Predictor application using Docker. This containerized approach provides several benefits:

- **Consistency**: Ensures the same environment across development, testing, and production
- **Isolation**: Properly separates databases and services for different environments
- **Reproducibility**: Makes it easy for new team members to get started
- **Scalability**: Provides a foundation for expanding the application

The combination of Docker, PostgreSQL, and the proper separation of environments will help you maintain a stable, scalable, and maintainable AMR Predictor application.

---

**Additional Resources:**
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
