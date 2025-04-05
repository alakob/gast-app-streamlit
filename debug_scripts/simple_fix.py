#!/usr/bin/env python3
"""
Simple fix to ensure the database schema is correct and optimize SQLite settings.

This script:
1. Checks and ensures the job_name column exists in the amr_jobs table
2. Sets the appropriate SQLite PRAGMA settings for better concurrency
3. Creates a test job to verify database operations work correctly
"""
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = PROJECT_ROOT / "data" / "db" / "predictor.db"

def ensure_directory_exists(path):
    """Ensure directory exists"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def optimize_db_settings(conn):
    """Optimize SQLite settings for better concurrency"""
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Use WAL journal mode for better concurrency
    cursor.execute("PRAGMA journal_mode = WAL")
    
    # Set a busy timeout
    cursor.execute("PRAGMA busy_timeout = 5000")  # 5 seconds
    
    conn.commit()
    print("SQLite settings optimized for better concurrency")

def ensure_users_table(conn):
    """Ensure the users table exists"""
    cursor = conn.cursor()
    
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        # Create users table
        cursor.execute('''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Add a default admin user
        now = datetime.now().isoformat()
        admin_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, "admin", "admin@example.com", now)
        )
        
        conn.commit()
        print("Created users table with default admin user")
    else:
        print("Users table already exists")

def ensure_job_name_column(conn):
    """Ensure job_name column exists in amr_jobs table"""
    cursor = conn.cursor()
    
    # Check if amr_jobs table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='amr_jobs'")
    if not cursor.fetchone():
        # Create amr_jobs table with job_name column
        cursor.execute('''
        CREATE TABLE amr_jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            progress REAL NOT NULL DEFAULT 0.0,
            start_time TEXT NOT NULL,
            end_time TEXT,
            result_file TEXT,
            aggregated_result_file TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            job_name TEXT NOT NULL DEFAULT 'AMR Analysis Job'
        )
        ''')
        
        conn.commit()
        print("Created amr_jobs table with job_name column")
    else:
        # Check if job_name column exists
        cursor.execute("PRAGMA table_info(amr_jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "job_name" not in columns:
            # Add job_name column
            cursor.execute("ALTER TABLE amr_jobs ADD COLUMN job_name TEXT NOT NULL DEFAULT 'AMR Analysis Job'")
            conn.commit()
            print("Added job_name column to amr_jobs table")
        else:
            print("job_name column already exists in amr_jobs table")

def test_job_creation(conn):
    """Test creating a job to verify database operations"""
    cursor = conn.cursor()
    
    # Create a test job
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    job_name = "Test Job"
    
    cursor.execute(
        """
        INSERT INTO amr_jobs (
            id, status, progress, start_time, created_at, job_name
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (job_id, "Test", 0.0, now, now, job_name)
    )
    
    # Verify the job was created
    cursor.execute("SELECT id, job_name FROM amr_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    
    if row and row[0] == job_id and row[1] == job_name:
        print(f"Successfully created and retrieved test job: {job_id}")
        
        # Clean up the test job
        cursor.execute("DELETE FROM amr_jobs WHERE id = ?", (job_id,))
        conn.commit()
        print("Test job cleaned up")
        return True
    else:
        print("Failed to create or retrieve test job")
        return False

if __name__ == "__main__":
    # Ensure database directory exists
    ensure_directory_exists(DB_PATH)
    
    print(f"Working with database at: {DB_PATH}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        
        # Optimize database settings
        optimize_db_settings(conn)
        
        # Ensure users table exists
        ensure_users_table(conn)
        
        # Ensure job_name column exists
        ensure_job_name_column(conn)
        
        # Test job creation
        if test_job_creation(conn):
            print("\nDatabase is now properly configured and working correctly!")
            print("You can now start the API server with:")
            print("python -m uvicorn amr_predictor.web.api:app --log-level debug")
        else:
            print("\nDatabase configuration complete, but job creation test failed.")
            print("Please check the database or application code for other issues.")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sys.exit(1)
    finally:
        # Close the connection
        if 'conn' in locals():
            conn.close()
