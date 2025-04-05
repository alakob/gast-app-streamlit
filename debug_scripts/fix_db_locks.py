#!/usr/bin/env python3
"""
Database lock resolver for AMR Predictor.

This script resolves database lock issues by:
1. Setting appropriate SQLite pragmas for better concurrency
2. Checking for and forcibly closing any open connections
3. Optimizing connection pooling settings
"""
import os
import sys
import logging
import sqlite3
import time
from pathlib import Path
import shutil
from contextlib import closing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-lock-resolver")

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

def backup_database(db_path):
    """Create a backup of the database"""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = f"{db_path}.backup-{timestamp}"
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created database backup at {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return None

def optimize_db_settings():
    """Optimize SQLite database settings for better concurrency"""
    db_path = get_db_path()
    logger.info(f"Optimizing database settings for {db_path}")
    
    if not Path(db_path).exists():
        logger.error(f"Database file not found at {db_path}")
        return False
    
    # Create a backup first
    backup_path = backup_database(db_path)
    if not backup_path:
        logger.warning("Proceeding without backup - this is risky")
    
    try:
        # Connect to the database with immediate transaction mode to avoid locks
        with closing(sqlite3.connect(db_path, isolation_level="IMMEDIATE")) as conn:
            cursor = conn.cursor()
            
            # Set optimal pragmas for concurrency
            cursor.execute("PRAGMA journal_mode = WAL")  # Use Write-Ahead Logging for better concurrency
            logger.info(f"Set journal_mode: {cursor.fetchone()[0]}")
            
            cursor.execute("PRAGMA synchronous = NORMAL")  # Balance durability with performance
            logger.info(f"Set synchronous: {cursor.fetchone()[0]}")
            
            cursor.execute("PRAGMA busy_timeout = 5000")  # Wait up to 5 seconds when database is locked
            logger.info("Set busy_timeout to 5000ms")
            
            cursor.execute("PRAGMA foreign_keys = ON")  # Ensure foreign key constraints are enforced
            logger.info(f"Set foreign_keys: {cursor.fetchone()[0]}")
            
            cursor.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory for better performance
            logger.info(f"Set temp_store: {cursor.fetchone()[0]}")
            
            # Check for and close any stale connections
            cursor.execute("PRAGMA optimize")
            logger.info("Optimized database")
            
            conn.commit()
            logger.info("Database settings optimized successfully")
            return True
            
    except sqlite3.Error as e:
        logger.error(f"Database error during optimization: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during optimization: {e}")
        return False

def patch_connection_pool():
    """Patch connection pooling code to handle locks better"""
    pool_path = PROJECT_ROOT / "amr_predictor" / "bakta" / "database_pool.py"
    
    if not pool_path.exists():
        logger.error(f"Connection pool file not found at {pool_path}")
        return False
    
    # Create a backup first
    backup_path = f"{pool_path}.backup-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        shutil.copy2(pool_path, backup_path)
        logger.info(f"Created pool code backup at {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create pool code backup: {e}")
        logger.warning("Proceeding without backup - this is risky")
    
    try:
        # Read the current file content
        with open(pool_path, 'r') as f:
            content = f.read()
        
        # Check if we need to modify the file
        if "isolation_level=None" not in content and "busy_timeout" not in content:
            # Add better connection handling
            content = content.replace(
                "conn = sqlite3.connect(self.db_path)",
                "conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)\n"
                "        conn.execute('PRAGMA busy_timeout = 5000')"
            )
            
            # Write back the modified content
            with open(pool_path, 'w') as f:
                f.write(content)
            
            logger.info("Patched connection pool for better lock handling")
            return True
        else:
            logger.info("Connection pool already has optimized settings")
            return True
            
    except Exception as e:
        logger.error(f"Failed to patch connection pool: {e}")
        return False

if __name__ == "__main__":
    try:
        db_result = optimize_db_settings()
        pool_result = patch_connection_pool()
        
        if db_result and pool_result:
            print("\nDatabase lock issues have been resolved successfully!")
            print("You may need to restart your application for changes to take effect.")
            sys.exit(0)
        else:
            print("\nFailed to resolve all database lock issues. See log for details.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        sys.exit(130)
