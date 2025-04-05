#!/usr/bin/env python3
"""
PostgreSQL Migration Script (Part 2) - Data Migration

This script:
1. Migrates existing data from SQLite to PostgreSQL
2. Validates the migration to ensure data integrity
3. Creates a backup of the SQLite database before migration

Prerequisites:
- Part 1 of the migration has been completed successfully
- PostgreSQL databases and schema are set up
- Both SQLite and PostgreSQL databases are accessible

Usage:
    python migrate_to_postgresql_part2.py [--env dev|test|prod]
"""
import os
import sys
import sqlite3
import psycopg2
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pg-migration")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
SQLITE_DB_PATH = PROJECT_ROOT / "amr_predictor" / "core" / "amr_predictor.db"
ENV_FILE_PATH = PROJECT_ROOT / ".env"

def backup_sqlite_database():
    """Create a backup of the SQLite database before migration"""
    if not SQLITE_DB_PATH.exists():
        logger.warning(f"SQLite database not found at {SQLITE_DB_PATH}")
        return False
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{SQLITE_DB_PATH}.backup_{timestamp}"
    
    try:
        # Copy the database file
        shutil.copy2(SQLITE_DB_PATH, backup_path)
        logger.info(f"Created SQLite database backup at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating SQLite database backup: {str(e)}")
        return False

def get_postgresql_connection(env):
    """Get a connection to the PostgreSQL database for the specified environment"""
    # Load environment variables
    load_dotenv(ENV_FILE_PATH)
    
    # Get connection parameters
    pg_host = os.getenv('PG_HOST', 'localhost')
    pg_port = os.getenv('PG_PORT', '5432')
    pg_user = os.getenv('PG_USER', 'postgres')
    pg_password = os.getenv('PG_PASSWORD', '')
    
    # Get the appropriate database based on environment
    if env == 'dev':
        database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
    elif env == 'test':
        database = os.getenv('PG_DATABASE_TEST', 'amr_predictor_test')
    elif env == 'prod':
        database = os.getenv('PG_DATABASE_PROD', 'amr_predictor_prod')
    else:
        raise ValueError(f"Invalid environment: {env}")
    
    # Connect to the specified database
    return psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        database=database
    )

def migrate_amr_jobs(sqlite_conn, pg_conn, batch_size=100):
    """Migrate data from amr_jobs table"""
    logger.info("Migrating AMR jobs data...")
    
    # Get SQLite cursor
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get PostgreSQL cursor
    pg_cursor = pg_conn.cursor()
    
    # Count total jobs to migrate
    sqlite_cursor.execute("SELECT COUNT(*) FROM amr_jobs")
    total_jobs = sqlite_cursor.fetchone()[0]
    logger.info(f"Found {total_jobs} jobs to migrate")
    
    # Clear existing data if any (optional, comment out if you want to preserve data)
    pg_cursor.execute("DELETE FROM amr_job_parameters")
    pg_cursor.execute("DELETE FROM amr_jobs")
    logger.info("Cleared existing data in PostgreSQL tables")
    
    # Fetch all jobs from SQLite
    sqlite_cursor.execute("SELECT * FROM amr_jobs")
    
    # Get column names
    column_names = [description[0] for description in sqlite_cursor.description]
    
    # Process in batches
    batch_count = 0
    migrated_count = 0
    batch_data = []
    
    for row in sqlite_cursor:
        # Create a dictionary of the row data
        job_data = dict(zip(column_names, row))
        
        # Convert SQLite NULL to Python None
        for key, value in job_data.items():
            if value == "NULL" or value == "":
                job_data[key] = None
        
        # Handle additional_info JSON
        if job_data.get('additional_info'):
            try:
                # If it's stored as a string, parse it
                if isinstance(job_data['additional_info'], str):
                    job_data['additional_info'] = json.loads(job_data['additional_info'])
            except:
                # If parsing fails, set to empty object
                job_data['additional_info'] = {}
        else:
            job_data['additional_info'] = {}
            
        # Prepare SQL for insertion
        insert_sql = """
        INSERT INTO amr_jobs (id, status, progress, start_time, end_time, 
                             result_file, aggregated_result_file, error, additional_info)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Prepare parameters
        params = (
            job_data.get('id'),
            job_data.get('status'),
            job_data.get('progress', 0),
            job_data.get('start_time'),
            job_data.get('end_time'),
            job_data.get('result_file'),
            job_data.get('aggregated_result_file'),
            job_data.get('error'),
            json.dumps(job_data.get('additional_info', {}))
        )
        
        batch_data.append(params)
        
        # Execute in batches
        if len(batch_data) >= batch_size:
            try:
                pg_cursor.executemany(insert_sql, batch_data)
                pg_conn.commit()
                migrated_count += len(batch_data)
                logger.info(f"Migrated {migrated_count}/{total_jobs} jobs")
                batch_data = []
            except Exception as e:
                pg_conn.rollback()
                logger.error(f"Error migrating batch: {str(e)}")
                return False
    
    # Insert any remaining jobs
    if batch_data:
        try:
            pg_cursor.executemany(insert_sql, batch_data)
            pg_conn.commit()
            migrated_count += len(batch_data)
            logger.info(f"Migrated {migrated_count}/{total_jobs} jobs")
        except Exception as e:
            pg_conn.rollback()
            logger.error(f"Error migrating final batch: {str(e)}")
            return False
    
    logger.info(f"Successfully migrated all {migrated_count} jobs")
    return True

def migrate_job_parameters(sqlite_conn, pg_conn, batch_size=100):
    """Migrate data from amr_job_parameters table"""
    logger.info("Migrating job parameters data...")
    
    # Get SQLite cursor
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get PostgreSQL cursor
    pg_cursor = pg_conn.cursor()
    
    # Count total parameters to migrate
    sqlite_cursor.execute("SELECT COUNT(*) FROM amr_job_parameters")
    total_params = sqlite_cursor.fetchone()[0]
    logger.info(f"Found {total_params} job parameters to migrate")
    
    # Fetch all parameters from SQLite
    sqlite_cursor.execute("SELECT job_id, param_name, param_value FROM amr_job_parameters")
    
    # Process in batches
    batch_count = 0
    migrated_count = 0
    batch_data = []
    
    for row in sqlite_cursor:
        job_id, param_name, param_value = row
        
        # Convert SQLite NULL to Python None
        if param_value == "NULL" or param_value == "":
            param_value = None
        
        # Prepare parameters
        params = (job_id, param_name, param_value)
        batch_data.append(params)
        
        # Execute in batches
        if len(batch_data) >= batch_size:
            try:
                pg_cursor.executemany(
                    "INSERT INTO amr_job_parameters (job_id, param_name, param_value) VALUES (%s, %s, %s)",
                    batch_data
                )
                pg_conn.commit()
                migrated_count += len(batch_data)
                logger.info(f"Migrated {migrated_count}/{total_params} parameters")
                batch_data = []
            except Exception as e:
                pg_conn.rollback()
                logger.error(f"Error migrating parameter batch: {str(e)}")
                return False
    
    # Insert any remaining parameters
    if batch_data:
        try:
            pg_cursor.executemany(
                "INSERT INTO amr_job_parameters (job_id, param_name, param_value) VALUES (%s, %s, %s)",
                batch_data
            )
            pg_conn.commit()
            migrated_count += len(batch_data)
            logger.info(f"Migrated {migrated_count}/{total_params} parameters")
        except Exception as e:
            pg_conn.rollback()
            logger.error(f"Error migrating final parameter batch: {str(e)}")
            return False
    
    logger.info(f"Successfully migrated all {migrated_count} job parameters")
    return True

def validate_migration(sqlite_conn, pg_conn):
    """Validate that all data was migrated correctly"""
    logger.info("Validating migration...")
    
    # Get cursors
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Validate job count
    sqlite_cursor.execute("SELECT COUNT(*) FROM amr_jobs")
    sqlite_job_count = sqlite_cursor.fetchone()[0]
    
    pg_cursor.execute("SELECT COUNT(*) FROM amr_jobs")
    pg_job_count = pg_cursor.fetchone()[0]
    
    if sqlite_job_count != pg_job_count:
        logger.error(f"Job count mismatch: SQLite ({sqlite_job_count}) vs PostgreSQL ({pg_job_count})")
        return False
    
    # Validate parameter count
    sqlite_cursor.execute("SELECT COUNT(*) FROM amr_job_parameters")
    sqlite_param_count = sqlite_cursor.fetchone()[0]
    
    pg_cursor.execute("SELECT COUNT(*) FROM amr_job_parameters")
    pg_param_count = pg_cursor.fetchone()[0]
    
    if sqlite_param_count != pg_param_count:
        logger.error(f"Parameter count mismatch: SQLite ({sqlite_param_count}) vs PostgreSQL ({pg_param_count})")
        return False
    
    # Validate specific job IDs (sample a few)
    sqlite_cursor.execute("SELECT id FROM amr_jobs LIMIT 5")
    sample_job_ids = [row[0] for row in sqlite_cursor.fetchall()]
    
    for job_id in sample_job_ids:
        # Get job from SQLite
        sqlite_cursor.execute("SELECT * FROM amr_jobs WHERE id = ?", (job_id,))
        sqlite_job = dict(zip([d[0] for d in sqlite_cursor.description], sqlite_cursor.fetchone()))
        
        # Get job from PostgreSQL
        pg_cursor.execute("SELECT * FROM amr_jobs WHERE id = %s", (job_id,))
        columns = [desc[0] for desc in pg_cursor.description]
        pg_job = dict(zip(columns, pg_cursor.fetchone()))
        
        # Check key fields
        for field in ['status', 'progress', 'result_file', 'error']:
            if field in sqlite_job and field in pg_job:
                if sqlite_job[field] != pg_job[field]:
                    logger.error(f"Data mismatch for job {job_id}, field {field}")
                    logger.error(f"  SQLite: {sqlite_job[field]}")
                    logger.error(f"  PostgreSQL: {pg_job[field]}")
                    return False
    
    logger.info("Migration validation successful!")
    return True

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="PostgreSQL Migration Script - Part 2 (Data Migration)")
    parser.add_argument("--env", default="dev", choices=["dev", "test", "prod"], 
                        help="Environment to migrate data to")
    parser.add_argument("--batch-size", type=int, default=100, 
                        help="Batch size for database operations")
    parser.add_argument("--skip-backup", action="store_true", 
                        help="Skip SQLite database backup")
    args = parser.parse_args()
    
    logger.info(f"Starting PostgreSQL migration - Part 2 (Data Migration) to {args.env} environment")
    
    # Step 1: Backup SQLite database
    if not args.skip_backup:
        logger.info("Step 1: Creating SQLite database backup")
        if not backup_sqlite_database():
            logger.error("Failed to create SQLite database backup. Exiting.")
            return 1
    else:
        logger.info("Skipping SQLite database backup as requested")
    
    # Step 2: Connect to databases
    try:
        logger.info("Step 2: Connecting to databases")
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        
        pg_conn = get_postgresql_connection(args.env)
        
        logger.info("Successfully connected to both databases")
    except Exception as e:
        logger.error(f"Error connecting to databases: {str(e)}")
        return 1
    
    try:
        # Step 3: Migrate AMR jobs
        logger.info("Step 3: Migrating AMR jobs")
        if not migrate_amr_jobs(sqlite_conn, pg_conn, args.batch_size):
            logger.error("Failed to migrate AMR jobs. Exiting.")
            return 1
        
        # Step 4: Migrate job parameters
        logger.info("Step 4: Migrating job parameters")
        if not migrate_job_parameters(sqlite_conn, pg_conn, args.batch_size):
            logger.error("Failed to migrate job parameters. Exiting.")
            return 1
        
        # Step 5: Validate migration
        logger.info("Step 5: Validating migration")
        if not validate_migration(sqlite_conn, pg_conn):
            logger.error("Migration validation failed. Please check the data manually.")
            return 1
        
        logger.info("Data migration completed successfully!")
        logger.info("Please run migrate_to_postgresql_part3.py to update the database manager")
        
        return 0
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return 1
    finally:
        # Close database connections
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()

if __name__ == "__main__":
    sys.exit(main())
