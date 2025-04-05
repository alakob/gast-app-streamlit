#!/usr/bin/env python3
"""
Database initialization script for AMR predictor.

This script creates a unified SQLite database in the project directory
for storing both AMR and Bakta job data.
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
logger = logging.getLogger("db-initializer")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Make sure the project directory is in the Python path
sys.path.insert(0, str(PROJECT_ROOT))

# Now import from our project
from amr_predictor.config.database_config import get_database_path, DB_DIR, DB_FILE

def ensure_db_directory():
    """Ensure the database directory exists"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Database directory created or verified: {DB_DIR}")

def initialize_database():
    """Initialize the shared database for both Bakta and AMR"""
    try:
        # Ensure database directory exists
        ensure_db_directory()
        
        # Initialize database using the DatabaseManager which will create all required tables
        from amr_predictor.bakta.database import DatabaseManager
        from amr_predictor.bakta.database_extensions import extend_database_manager
        
        # Initialize database manager with the project path
        db_manager = DatabaseManager()
        logger.info(f"Initialized database at {db_manager.database_path}")
        
        # Extend with AMR functionality
        extend_database_manager(db_manager)
        logger.info("Extended database with AMR functionality")
        
        logger.info("Database initialization completed successfully!")
        logger.info(f"Shared database path: {DB_FILE}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    
    if success:
        print("\nDatabase initialization completed successfully!")
        print(f"Shared database path: {DB_FILE}")
        sys.exit(0)
    else:
        print("\nDatabase initialization failed, see logs for details.")
        sys.exit(1)
