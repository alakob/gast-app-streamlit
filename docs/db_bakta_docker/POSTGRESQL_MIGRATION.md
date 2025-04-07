# PostgreSQL Migration for AMR Predictor

This guide outlines the migration process from SQLite to PostgreSQL for the AMR Predictor API. This migration addresses the connection handling issues we've been experiencing with SQLite, particularly the "Cannot operate on a closed database" errors.

## Why PostgreSQL?

PostgreSQL offers several advantages over SQLite for our application:

1. **Robust Concurrent Connection Handling**: Unlike SQLite (which is file-based), PostgreSQL is designed as a client-server database that properly handles multiple concurrent connections.

2. **Connection Pooling**: PostgreSQL supports robust connection pooling, allowing us to maintain a persistent set of database connections that can be reused across requests.

3. **Transaction Management**: PostgreSQL has superior transaction isolation and management, ensuring that database operations for background tasks remain atomic and reliable.

4. **Performance with Scale**: As the job queue grows, PostgreSQL will handle the load much better than SQLite, which degrades with concurrent writes.

## Migration Process

The migration is divided into three scripts to ensure a smooth transition:

### Part 1: Database Setup (`migrate_to_postgresql_part1.py`)

- Creates PostgreSQL databases for dev, test, and prod environments
- Sets up the required schema (tables, indexes, etc.)
- Creates or updates the `.env` file with PostgreSQL configuration

```bash
python migrate_to_postgresql_part1.py --host localhost --port 5432 --user postgres --password yourpassword --env dev
```

### Part 2: Data Migration (`migrate_to_postgresql_part2.py`)

- Backs up the existing SQLite database
- Migrates all existing jobs and job parameters to PostgreSQL
- Validates the migration to ensure data integrity

```bash
python migrate_to_postgresql_part2.py --env dev
```

### Part 3: Code Updates (`migrate_to_postgresql_part3.py`)

- Updates the `AMRDatabaseManager` class to use PostgreSQL with connection pooling
- Modifies error handling in the repository and API layers
- Updates dependencies in `requirements.txt`

```bash
python migrate_to_postgresql_part3.py
```

## Prerequisites

Before starting the migration, ensure you have:

1. **PostgreSQL installed and running** on your system or accessible server
2. **Python dependencies** installed: 
   ```bash
   pip install psycopg2-binary python-dotenv
   ```
3. **Database credentials** with permissions to create databases and tables

## Configuration

The migration creates a `.env` file with the following structure:

```
# PostgreSQL Database Configuration
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=yourpassword

# Database names for different environments
PG_DATABASE_DEV=amr_predictor_dev
PG_DATABASE_TEST=amr_predictor_test
PG_DATABASE_PROD=amr_predictor_prod

# Current environment (dev, test, or prod)
ENVIRONMENT=dev

# Other settings
HF_TOKEN=  # Optional: Add your Hugging Face token if needed
```

You can modify these values to match your PostgreSQL setup.

## After Migration

After completing all three parts of the migration:

1. **Restart the API server**:
   ```bash
   python -m uvicorn amr_predictor.web.api:app --log-level debug
   ```

2. **Verify the migration** by checking that:
   - The API starts without errors
   - Existing jobs can be retrieved
   - New jobs can be created and processed
   - The "Cannot operate on a closed database" errors no longer occur

## Troubleshooting

If you encounter issues during migration:

1. **Database Connection Errors**: 
   - Verify PostgreSQL is running
   - Check that the credentials in `.env` are correct
   - Ensure the specified user has the necessary permissions

2. **Schema Issues**:
   - Run `migrate_to_postgresql_part1.py` again to verify/recreate the schema

3. **Data Migration Failures**:
   - Check the SQLite backup is intact
   - Verify PostgreSQL has enough disk space
   - Run `migrate_to_postgresql_part2.py` with `--batch-size` decreased to handle smaller batches

4. **API Startup Issues**:
   - Check for missing dependencies: `pip install -r requirements.txt`
   - Verify the `.env` file has the correct settings for your environment

## Benefits of This Migration

This migration addresses the specific issues we've been experiencing with the AMR Predictor API:

1. **Elimination of "Cannot operate on a closed database" errors** through proper connection pooling
2. **Improved reliability for concurrent job processing** through PostgreSQL's robust transaction management
3. **Better performance for background tasks** by maintaining persistent database connections
4. **Scalable database layer** that can handle increased load as the application grows

The updated architecture follows the industry best practice of separating database connections for different environments (dev, test, prod), in line with your project preferences.
