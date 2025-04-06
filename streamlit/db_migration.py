#!/usr/bin/env python3
"""
Database migration script to add Bakta job association to AMR jobs table.
This is a lightweight migration that won't affect existing functionality.
"""

import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get a database connection based on environment variables"""
    # Get PostgreSQL connection parameters
    pg_host = os.getenv('PG_HOST', 'localhost')
    pg_port = os.getenv('PG_PORT', '5432')
    pg_user = os.getenv('PG_USER', 'postgres')
    pg_password = os.getenv('PG_PASSWORD', '')
    
    # Get environment (dev, test, or prod)
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    # Get database name based on environment
    if environment == 'dev':
        database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
    elif environment == 'test':
        database = os.getenv('PG_DATABASE_TEST', 'amr_predictor_test')
    elif environment == 'prod':
        database = os.getenv('PG_DATABASE_PROD', 'amr_predictor_prod')
    else:
        logger.warning(f"Unknown environment: {environment}, defaulting to dev")
        database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
    
    logger.info(f"Connecting to database for migration: {database} on {pg_host}:{pg_port}")
    
    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user=pg_user,
            password=pg_password,
            database=database
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def check_column_exists(conn, table, column):
    """Check if a column exists in a table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, (table, column))
        return cursor.fetchone() is not None
    finally:
        cursor.close()

def add_bakta_job_id_column():
    """Add bakta_job_id column to amr_jobs table if it doesn't exist"""
    conn = None
    try:
        conn = get_db_connection()
        
        # Check if the column already exists
        if check_column_exists(conn, 'amr_jobs', 'bakta_job_id'):
            logger.info("bakta_job_id column already exists in amr_jobs table")
            return
        
        # Add the column
        cursor = conn.cursor()
        try:
            logger.info("Adding bakta_job_id column to amr_jobs table")
            cursor.execute("""
                ALTER TABLE amr_jobs
                ADD COLUMN bakta_job_id VARCHAR(255) NULL
            """)
            conn.commit()
            logger.info("Successfully added bakta_job_id column to amr_jobs table")
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def run_migration():
    """Run all migration steps"""
    try:
        logger.info("Starting database migration")
        add_bakta_job_id_column()
        logger.info("Database migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False
    return True

if __name__ == "__main__":
    if run_migration():
        sys.exit(0)
    else:
        sys.exit(1)
