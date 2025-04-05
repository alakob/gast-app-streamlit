#!/usr/bin/env python3
"""
Explore the database structure and query for jobs with error status.
"""
import os
import sys
import json
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-explorer")

def find_db_paths():
    """Find all potential database file paths"""
    db_paths = []
    
    # Check default location
    default_path = os.path.expanduser("~/.amr_predictor/bakta/bakta.db")
    if os.path.exists(default_path):
        logger.info(f"Found database at: {default_path}")
        db_paths.append(default_path)
    
    # Check project directory for sqlite files
    project_root = Path(__file__).parent
    for path in project_root.glob("**/*.db"):
        if path.is_file():
            logger.info(f"Found potential database: {path}")
            db_paths.append(str(path))
    
    # Look for database paths in environment files
    env_files = list(project_root.glob("**/.env*"))
    for env_path in env_files:
        logger.info(f"Checking {env_path} for database location...")
        try:
            with open(env_path, "r") as f:
                for line in f:
                    if "DATABASE" in line.upper() or "DB_PATH" in line.upper() or "SQLITE" in line.upper():
                        parts = line.strip().split("=", 1)
                        if len(parts) == 2:
                            path = parts[1].strip().strip("'").strip('"')
                            path = os.path.expanduser(path)
                            if os.path.exists(path) and path not in db_paths:
                                logger.info(f"Found database path in {env_path}: {path}")
                                db_paths.append(path)
        except Exception as e:
            logger.warning(f"Error reading {env_path}: {e}")

    return db_paths

def explore_database(db_path):
    """Explore the structure of a database file"""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        logger.info(f"Found {len(tables)} tables in {db_path}")
        
        table_info = {}
        for table in tables:
            table_name = table[0]
            # Get columns for each table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Sample some data
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample_row = cursor.fetchone()
            except:
                sample_row = None
            
            # Check for status or error columns
            has_status = any(col[1].lower() == 'status' for col in columns)
            has_error = any(col[1].lower() == 'error' for col in columns)
            
            table_info[table_name] = {
                "columns": [col[1] for col in columns],
                "has_status_column": has_status,
                "has_error_column": has_error,
                "has_data": sample_row is not None
            }
        
        conn.close()
        return table_info
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error exploring {db_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error exploring {db_path}: {e}")
        return {}

def query_error_jobs(db_path, table_info):
    """Query the database for jobs with error status based on table structure"""
    error_jobs = []
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to query each table that has status and error columns
        for table_name, info in table_info.items():
            if info["has_status_column"] and info["has_data"]:
                logger.info(f"Checking table {table_name} for error status jobs...")
                
                # Check if this looks like a jobs table
                is_job_table = ('id' in info["columns"] or 'job_id' in info["columns"]) and 'status' in info["columns"]
                
                if is_job_table:
                    # Prepare the query based on available columns
                    select_columns = ['*']
                    if 'id' in info["columns"]: 
                        id_col = 'id'
                    elif 'job_id' in info["columns"]:
                        id_col = 'job_id'
                    else:
                        id_col = info["columns"][0]  # Use first column as ID
                    
                    # Build the query
                    query = f"""
                        SELECT * FROM {table_name}
                        WHERE (status LIKE '%ERROR%' OR status LIKE '%FAIL%')
                        ORDER BY 
                    """
                    
                    # Order by created_at if it exists, otherwise just use ID
                    if 'created_at' in info["columns"]:
                        query += "created_at DESC"
                    else:
                        query += f"{id_col}"
                    
                    logger.info(f"Executing query: {query}")
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    if rows:
                        logger.info(f"Found {len(rows)} error jobs in table {table_name}")
                        for row in rows:
                            job_dict = dict(row)
                            error_jobs.append({
                                "table": table_name,
                                "data": job_dict
                            })
        
        conn.close()
        return error_jobs
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error querying error jobs: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying error jobs: {e}")
        return []

def main():
    """Main entry point"""
    try:
        # Find all potential database paths
        db_paths = find_db_paths()
        
        if not db_paths:
            logger.warning("No database files found!")
            print("\nNo database files found. Check that the application is correctly installed.")
            return
        
        print("\nEXPLORING DATABASE STRUCTURE:")
        print("=============================")
        
        all_error_jobs = []
        
        # Explore each database
        for db_path in db_paths:
            print(f"\nDatabase: {db_path}")
            print("-" * 80)
            
            # Explore database structure
            table_info = explore_database(db_path)
            
            if not table_info:
                print(f"  No tables found or could not read database structure")
                continue
                
            # Print database structure
            for table_name, info in table_info.items():
                status_col = "✓" if info["has_status_column"] else "✗"
                error_col = "✓" if info["has_error_column"] else "✗"
                data = "✓" if info["has_data"] else "✗"
                
                print(f"  Table: {table_name}")
                print(f"    Columns: {', '.join(info['columns'])}")
                print(f"    Has Status: {status_col} | Has Error: {error_col} | Has Data: {data}")
            
            # Query for error jobs
            error_jobs = query_error_jobs(db_path, table_info)
            if error_jobs:
                all_error_jobs.extend(error_jobs)
        
        # Display error jobs
        print("\nERROR JOBS:")
        print("===========")
        
        if not all_error_jobs:
            print("No jobs with ERROR status found in any database.")
        else:
            print(f"Found {len(all_error_jobs)} jobs with ERROR status")
            print(json.dumps(all_error_jobs, indent=2))
            
            # Print a summary table
            print("\nSummary Table:")
            print("-" * 120)
            
            headers = ["Table", "ID/Job ID", "Status", "Error"]
            print(f"{headers[0]:<20} | {headers[1]:<36} | {headers[2]:<15} | {headers[3]:<40}")
            print("-" * 120)
            
            for job in all_error_jobs:
                table = job["table"]
                data = job["data"]
                
                # Extract ID (might be named differently)
                job_id = data.get('id', data.get('job_id', 'Unknown'))
                status = data.get('status', 'Unknown')
                error = data.get('error', 'Unknown error')
                
                # Truncate error message
                if error and len(str(error)) > 40:
                    error = str(error)[:37] + '...'
                
                print(f"{table:<20} | {job_id:<36} | {status:<15} | {error:<40}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
