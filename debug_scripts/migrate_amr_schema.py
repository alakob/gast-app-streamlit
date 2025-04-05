#!/usr/bin/env python3
"""
Database schema migration script for AMR Predictor.

This script updates the AMR database schema to resolve column naming inconsistencies
between the codebase and the database structure after the SQLite migration.
"""
import os
import sys
import logging
import sqlite3
import uuid
from pathlib import Path
from contextlib import closing
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amr-schema-migration")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Make sure the project directory is in the Python path
sys.path.insert(0, str(PROJECT_ROOT))

# Import database configuration
from amr_predictor.config.database_config import get_database_path

def get_db_path():
    """Get the database path from configuration"""
    # Use the method from database_config to get the proper path
    return get_database_path()

def check_column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

def migrate_schema():
    """Migrate the AMR database schema to fix column naming inconsistencies"""
    db_path = get_db_path()
    logger.info(f"Starting schema migration for database at {db_path}")
    
    if not Path(db_path).exists():
        logger.error(f"Database file not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Step 1: Check if the required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            users_table_exists = cursor.fetchone() is not None
            
            # Create users table if it doesn't exist
            if not users_table_exists:
                logger.info("Creating missing users table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        full_name TEXT,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_login TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        is_admin INTEGER NOT NULL DEFAULT 0
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                
                # Add a default admin user to prevent foreign key issues
                admin_id = "admin-" + str(uuid.uuid4())
                now = datetime.now().isoformat()
                # Use a dummy password hash - change this in production!
                dummy_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" # "password"
                
                cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash, created_at, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (admin_id, "admin", "admin@example.com", dummy_hash, now, 1))
                
                logger.info("Created users table with default admin user")
                changes_made = True
            else:
                logger.info("Users table already exists")
                changes_made = False
            
            # Step 2: Check if amr_jobs table exists 
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='amr_jobs'")
            if not cursor.fetchone():
                logger.error("Table 'amr_jobs' does not exist in the database")
                conn.rollback()
                return False
            
            # Check for column naming inconsistencies
            columns_to_check = {
                "start_time": "started_at",  # Code uses start_time, but DB might have started_at
                "end_time": "completed_at"   # Code uses end_time, but DB might have completed_at
            }
            
            for code_column, db_column in columns_to_check.items():
                code_column_exists = check_column_exists(cursor, "amr_jobs", code_column)
                db_column_exists = check_column_exists(cursor, "amr_jobs", db_column)
                
                # Different scenarios:
                if code_column_exists and db_column_exists:
                    # Both columns exist - this is unusual, but we'll keep both for now
                    logger.warning(f"Both {code_column} and {db_column} exist in amr_jobs table")
                    
                elif code_column_exists and not db_column_exists:
                    # Only code column exists - rename to match DB convention
                    logger.info(f"Renaming column {code_column} to {db_column}")
                    # SQLite doesn't support direct column renaming, so we need to create a new table
                    # However, this approach is risky, so we'll add the new column instead
                    cursor.execute(f"ALTER TABLE amr_jobs ADD COLUMN {db_column} TEXT")
                    cursor.execute(f"UPDATE amr_jobs SET {db_column} = {code_column}")
                    changes_made = True
                    
                elif not code_column_exists and db_column_exists:
                    # Only DB column exists - we need to add the code column
                    logger.info(f"Adding missing column {code_column} that code expects")
                    cursor.execute(f"ALTER TABLE amr_jobs ADD COLUMN {code_column} TEXT")
                    cursor.execute(f"UPDATE amr_jobs SET {code_column} = {db_column}")
                    changes_made = True
                    
                else:
                    # Neither column exists - add the one the code expects
                    logger.info(f"Adding new column {code_column}")
                    cursor.execute(f"ALTER TABLE amr_jobs ADD COLUMN {code_column} TEXT")
                    changes_made = True
            
            # Step 3: Update schema version if we have one
            try:
                cursor.execute("UPDATE schema_info SET version = version + 1 WHERE id = 1")
                if cursor.rowcount == 0:
                    cursor.execute("INSERT INTO schema_info (id, version) VALUES (1, 1)")
            except sqlite3.OperationalError:
                # Schema versioning table doesn't exist
                cursor.execute("CREATE TABLE IF NOT EXISTS schema_info (id INTEGER PRIMARY KEY, version INTEGER)")
                cursor.execute("INSERT INTO schema_info (id, version) VALUES (1, 1)")
            
            # Commit changes if any were made
            if changes_made:
                conn.commit()
                logger.info("Schema migration completed successfully")
                return True
            else:
                logger.info("No schema changes were needed")
                conn.rollback()
                return True
                
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False

if __name__ == "__main__":
    try:
        if migrate_schema():
            print("\nSchema migration completed successfully.")
            sys.exit(0)
        else:
            print("\nSchema migration failed. See log for details.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nMigration interrupted by user.")
        sys.exit(130)
