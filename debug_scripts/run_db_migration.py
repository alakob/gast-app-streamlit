#!/usr/bin/env python3
"""
Database migration runner script.

This script runs the database migration to ensure all databases are stored
in the project directory rather than in user home directories.
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-migration-runner")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Make sure the project directory is in the Python path
sys.path.insert(0, str(PROJECT_ROOT))

# Now import from our project
from amr_predictor.config.database_config import (
    get_database_path, migrate_legacy_database,
    DEFAULT_BAKTA_DB_PATH, DEFAULT_AMR_DB_PATH,
    LEGACY_BAKTA_DB_PATH, LEGACY_AMR_DB_PATH
)

def ensure_db_directories():
    """Ensure the database directories exist"""
    db_dirs = [
        DEFAULT_BAKTA_DB_PATH.parent,
        DEFAULT_AMR_DB_PATH.parent
    ]
    
    for dir_path in db_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database directory created or verified: {dir_path}")

def run_migration():
    """Run the database migration"""
    try:
        # Ensure database directories exist
        ensure_db_directories()
        
        # Check if we need to migrate Bakta database
        bakta_migrated = migrate_legacy_database("bakta")
        if bakta_migrated:
            logger.info(f"Migrated Bakta database from {LEGACY_BAKTA_DB_PATH} to {DEFAULT_BAKTA_DB_PATH}")
        else:
            if LEGACY_BAKTA_DB_PATH.exists():
                logger.info(f"Legacy Bakta database exists but migration not needed (already migrated)")
            else:
                logger.info("No legacy Bakta database found to migrate")
        
        # Check if we need to migrate AMR database
        amr_migrated = migrate_legacy_database("amr")
        if amr_migrated:
            logger.info(f"Migrated AMR database from {LEGACY_AMR_DB_PATH} to {DEFAULT_AMR_DB_PATH}")
        else:
            if LEGACY_AMR_DB_PATH.exists():
                logger.info(f"Legacy AMR database exists but migration not needed (already migrated)")
            else:
                logger.info("No legacy AMR database found to migrate")
        
        # Let's initialize the database to ensure the tables exist
        from amr_predictor.bakta.database import DatabaseManager
        from amr_predictor.bakta.database_extensions import extend_database_manager
        
        # Initialize database manager with default project path
        db_manager = DatabaseManager() 
        logger.info(f"Initialized database at {db_manager.database_path}")
        
        # Manually trigger the database initialization to ensure tables exist
        db_manager._initialize_database()
        
        # Extend with AMR functionality using a fresh connection
        amr_extensions = extend_database_manager(db_manager)
        logger.info("Extended database with AMR functionality")
        
        logger.info("Database migration completed successfully!")
        logger.info(f"Bakta database path: {DEFAULT_BAKTA_DB_PATH}")
        logger.info(f"AMR database path: {DEFAULT_AMR_DB_PATH}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    
    if success:
        print("\nMigration completed successfully!")
        print(f"Bakta database: {DEFAULT_BAKTA_DB_PATH}")
        print(f"AMR database: {DEFAULT_AMR_DB_PATH}")
        sys.exit(0)
    else:
        print("\nMigration failed, see logs for details.")
        sys.exit(1)
