# AMR API Database Integration

This document details the database integration implementation for the AMR API, transitioning from an in-memory job tracking system to a robust SQLite database infrastructure.

## Overview

The AMR API previously used an in-memory dictionary to track job information, which was not persistent and couldn't handle server restarts. This implementation adds a proper database layer for job management while maintaining backward compatibility with existing code.

## Architecture

The database integration follows a layered architecture:

1. **Data Models Layer** - Contains the models representing AMR jobs and parameters
2. **Data Access Layer** - Contains DAOs (Data Access Objects) for database operations
3. **Service Layer** - Contains services for job lifecycle management
4. **API Layer** - Contains FastAPI endpoints that use the services

### Key Components

#### Database Management

- **DatabaseManager**: Extended from Bakta to manage AMR job data
- **OptimizedDatabaseManager**: Enhanced version with connection pooling
- **ConnectionPool**: Provides connection pooling for better performance

#### Job Management

- **AMRJobDAO**: Data Access Object for AMR jobs
- **JobArchiver**: Manages job archiving and cleanup
- **ProgressTracker**: Updates job progress in the database

#### User Authentication

- **UserManager**: Handles user registration, authentication, and session management
- **AuthMiddleware**: Provides authentication middleware for FastAPI

## Database Schema

### AMR Jobs Table

```sql
CREATE TABLE amr_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error TEXT,
    result_file_path TEXT,
    input_file_path TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
)
```

### AMR Job Parameters Table

```sql
CREATE TABLE amr_job_params (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    param_name TEXT NOT NULL,
    param_value TEXT,
    FOREIGN KEY (job_id) REFERENCES amr_jobs(id) ON DELETE CASCADE
)
```

### Users Table

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
)
```

## Configuration

### Job Lifecycle Configuration

The job lifecycle is configurable through the `JobLifecycleConfig` class. Default configuration:

```yaml
retention_periods:
  Completed: 30  # Days to keep completed jobs
  Error: 14      # Days to keep failed jobs
  Archived: 90   # Days to keep archived jobs
  Submitted: 2   # Days to keep stalled jobs
  Running: 7     # Days to keep stalled jobs

archiving:
  enabled: true
  min_age_days: 7
  compress_results: true

cleanup:
  enabled: true
  run_frequency_hours: 24
  max_jobs_per_run: 100
```

## User Authentication

The API uses JWT (JSON Web Token) based authentication. Users need to:

1. Register with a username and password
2. Login to receive an access token
3. Use the access token in subsequent requests

### API Endpoints

#### Authentication Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user information

## Job Management

### Job Lifecycle

AMR jobs follow this lifecycle:

1. **Submitted** - Initial state when job is created
2. **Running** - Job is being processed
3. **Completed** - Job has finished successfully
4. **Error** - Job has failed with an error
5. **Archived** - Job has been archived (after a configurable period)

### Job Maintenance

Jobs are automatically:

1. **Archived** - Older completed jobs are archived for storage efficiency
2. **Cleaned up** - Jobs older than their retention period are deleted

## Migration

A migration script (`migrate_database.py`) is provided to:

1. Create the necessary database tables
2. Migrate in-memory jobs to the database
3. Create admin users if needed

## Integration with Existing Code

The database integration maintains backward compatibility through:

1. **LegacyCompatibleProgressTracker** - Updates both in-memory and database
2. **Dual-storage approach** - During transition, jobs are stored in both systems

## Performance Optimization

Performance is optimized through:

1. **Connection pooling** - Reuse database connections
2. **Indexing** - Key fields are indexed for faster queries
3. **Transaction management** - Batch operations use transactions
4. **Query optimization** - Queries are designed for efficiency

## Monitoring

Monitoring is implemented through:

1. **Logging** - Comprehensive logging of database operations
2. **Performance metrics** - Track database operation times
3. **Error tracking** - Detailed error logs for troubleshooting

## Testing

Comprehensive test coverage is provided for:

1. **Unit tests** - Test individual components in isolation
2. **Integration tests** - Test components working together
3. **End-to-end tests** - Test the entire system

## Deployment Considerations

When deploying the system:

1. **Database location** - Ensure the database file is in a backed-up location
2. **Scheduled tasks** - Set up the maintenance scheduler to run regularly
3. **Backup strategy** - Implement regular database backups
4. **Monitoring** - Set up monitoring for database size and performance
