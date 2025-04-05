# PostgreSQL Migration Guide

This document provides detailed instructions for migrating your AMR Predictor from SQLite to PostgreSQL using the migration scripts provided.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Migration Scripts Explained](#migration-scripts-explained)
4. [Step-by-Step Migration Process](#step-by-step-migration-process)
5. [Docker Environment Migration](#docker-environment-migration)
6. [Troubleshooting](#troubleshooting)
7. [Post-Migration Verification](#post-migration-verification)

## Overview

The migration process from SQLite to PostgreSQL is divided into three main scripts:

1. `migrate_to_postgresql_part1.py` - Sets up PostgreSQL databases and schema
2. `migrate_to_postgresql_part2.py` - Migrates data from SQLite to PostgreSQL
3. `migrate_to_postgresql_part3.py` - Updates AMR Predictor code to use PostgreSQL

These scripts ensure a smooth transition with minimal downtime and risk.

## Prerequisites

Before starting the migration:

1. **Install Required Packages**:
   ```bash
   pip install psycopg2-binary python-dotenv
   ```

2. **Backup Your SQLite Database**:
   ```bash
   cp amr_predictor/core/amr_predictor.db amr_predictor/core/amr_predictor.db.backup
   ```

3. **PostgreSQL Installation**:
   - Ensure PostgreSQL is installed and running
   - For Docker setup, PostgreSQL is managed via containers

## Migration Scripts Explained

### Script 1: Database Setup (`migrate_to_postgresql_part1.py`)

This script:
- Creates PostgreSQL databases for development, testing, and production environments
- Sets up the required tables, indexes, and constraints
- Creates or updates the `.env` file with PostgreSQL configuration

**Usage:**
```bash
# Basic usage with defaults
python migrate_to_postgresql_part1.py

# With custom PostgreSQL connection parameters
python migrate_to_postgresql_part1.py --host localhost --port 5432 --user postgres --password yourpassword --env dev
```

**Parameters:**
- `--host`: PostgreSQL server hostname (default: localhost)
- `--port`: PostgreSQL server port (default: 5432)
- `--user`: PostgreSQL username (default: postgres)
- `--password`: PostgreSQL password (default: empty)
- `--env`: Target environment (default: dev, options: dev, test, prod)

**Output:**
- Creates databases: `amr_predictor_dev`, `amr_predictor_test`, `amr_predictor_prod`
- Sets up schema with tables: `amr_jobs`, `amr_job_parameters`, and others
- Creates required indexes for performance

### Script 2: Data Migration (`migrate_to_postgresql_part2.py`)

This script:
- Backs up the SQLite database before migration
- Exports data from SQLite tables to PostgreSQL
- Performs data validation to ensure integrity
- Maps SQLite data types to appropriate PostgreSQL types

**Usage:**
```bash
# Basic usage with defaults
python migrate_to_postgresql_part2.py

# With custom environment and batch size
python migrate_to_postgresql_part2.py --env dev --batch-size 50 --skip-backup
```

**Parameters:**
- `--env`: Target environment (default: dev, options: dev, test, prod)
- `--batch-size`: Number of records to process in each batch (default: 100)
- `--skip-backup`: Skip SQLite database backup (default: false)

**Output:**
- Migrates all job data, parameters, and related information
- Reports migration progress and statistics
- Validates data integrity after migration

### Script 3: Code Updates (`migrate_to_postgresql_part3.py`)

This script:
- Updates the database manager to use PostgreSQL
- Implements connection pooling for improved reliability
- Updates dependencies in requirements.txt
- Modifies error handling for PostgreSQL-specific errors

**Usage:**
```bash
# No parameters needed
python migrate_to_postgresql_part3.py
```

**Changes:**
- Replaces SQLite-specific code with PostgreSQL code
- Adds connection pooling for improved performance
- Updates error handling patterns
- Modifies import statements as needed

## Step-by-Step Migration Process

Follow these steps for a successful migration:

### 1. Preparation

```bash
# Ensure you have all dependencies
pip install psycopg2-binary python-dotenv

# Create a backup of your SQLite database
cp amr_predictor/core/amr_predictor.db amr_predictor/core/amr_predictor.db.backup

# Stop any running AMR Predictor instances
# (if using a service, stop it now)
```

### 2. Set Up PostgreSQL

```bash
# Run part 1 to create databases and schema
python migrate_to_postgresql_part1.py --host localhost --port 5432 --user postgres --password yourpassword --env dev
```

### 3. Migrate Data

```bash
# Run part 2 to migrate data from SQLite to PostgreSQL
python migrate_to_postgresql_part2.py --env dev
```

### 4. Update Code

```bash
# Run part 3 to update AMR Predictor code to use PostgreSQL
python migrate_to_postgresql_part3.py
```

### 5. Verify Migration

```bash
# Connect to PostgreSQL and check data
psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_jobs;"

# Start AMR Predictor and verify functionality
# (using your standard startup method)
```

## Docker Environment Migration

If you're using the Docker setup, the migration process is slightly different:

### 1. Start PostgreSQL Container

```bash
# Start just the PostgreSQL container
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U postgres -h localhost
```

### 2. Run Migration Scripts

```bash
# Run the migration scripts in sequence
docker-compose run --rm amr-api python migrate_to_postgresql_part1.py
docker-compose run --rm amr-api python migrate_to_postgresql_part2.py
docker-compose run --rm amr-api python migrate_to_postgresql_part3.py
```

### 3. Verify Migration

```bash
# Check data in PostgreSQL
docker-compose exec postgres psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_jobs;"

# Start the full stack
docker-compose up -d
```

## Troubleshooting

### Common Issues and Solutions

#### Database Connection Errors

**Problem**: Cannot connect to PostgreSQL
**Solution**:
```bash
# Check PostgreSQL is running
pg_isready -U postgres -h localhost

# Verify credentials in .env file
cat .env
```

#### Data Migration Failures

**Problem**: Data migration script fails
**Solution**:
```bash
# Try with a smaller batch size
python migrate_to_postgresql_part2.py --batch-size 20

# Check SQLite database integrity
sqlite3 amr_predictor/core/amr_predictor.db "PRAGMA integrity_check;"
```

#### Code Update Issues

**Problem**: Application fails to start after code update
**Solution**:
```bash
# Verify PostgreSQL connection in code
python -c "import psycopg2; conn = psycopg2.connect(dbname='amr_predictor_dev', user='postgres', host='localhost', password='yourpassword'); print('Connected!')"

# Check for missing dependencies
pip install -r requirements.txt
```

## Post-Migration Verification

After completing the migration, verify these key aspects:

### 1. Database Structure

```bash
# List tables in PostgreSQL
psql -U postgres -d amr_predictor_dev -c "\dt"

# Check table schema
psql -U postgres -d amr_predictor_dev -c "\d amr_jobs"
```

### 2. Data Integrity

```bash
# Count records in key tables
psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_jobs;"
psql -U postgres -d amr_predictor_dev -c "SELECT COUNT(*) FROM amr_job_parameters;"

# Compare with SQLite counts (should match)
sqlite3 amr_predictor/core/amr_predictor.db "SELECT COUNT(*) FROM amr_jobs;"
```

### 3. Application Functionality

- Submit a new job and verify it's stored in PostgreSQL
- Check that existing jobs are correctly displayed
- Verify that background tasks complete successfully

---

This migration approach eliminates the recurring "Cannot operate on a closed database" errors by leveraging PostgreSQL's robust connection handling and implementing proper connection pooling.

For further assistance or questions about the migration process, refer to the [PostgreSQL documentation](https://www.postgresql.org/docs/) or the [AMR Predictor documentation](./README.md).
