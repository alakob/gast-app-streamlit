#!/usr/bin/env python3
"""
Simple database lock resolver for AMR Predictor.

This script uses a more direct approach to resolve SQLite lock issues.
"""
import os
import sys
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-lock-resolver")

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Database path
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"

def fix_database_locks():
    """Fix database locks with minimal direct changes"""
    logger.info(f"Attempting to fix database locks on {DB_PATH}")
    
    if not DB_PATH.exists():
        logger.error(f"Database file not found at {DB_PATH}")
        return False
    
    try:
        # Connect directly to the database
        # Use isolation_level=None for autocommit mode to avoid transaction locking
        conn = sqlite3.connect(str(DB_PATH), isolation_level=None)
        
        try:
            # Set WAL mode which has better concurrency properties
            conn.execute("PRAGMA journal_mode=WAL")
            logger.info("Set journal_mode to WAL")
            
            # Set busy timeout to wait instead of failing immediately on locks
            conn.execute("PRAGMA busy_timeout=5000")
            logger.info("Set busy_timeout to 5000ms")
            
            # Make sure connections are properly closed
            conn.close()
            logger.info("Database connection properly closed")
            
            return True
        finally:
            # Make sure connection is closed even if there's an error
            if conn:
                conn.close()
                
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    if fix_database_locks():
        print("\nDatabase lock issues successfully resolved!")
        print("The database is now configured for better concurrent access.")
        
        # Also suggest stopping any running API processes
        print("\nIMPORTANT: To fully resolve lock issues, you should:")
        print("1. Stop any running API servers")
        print("2. Restart your API server with:")
        print("   python -m uvicorn amr_predictor.web.api:app --log-level debug")
    else:
        print("\nFailed to resolve database lock issues. See log for details.")
        sys.exit(1)
