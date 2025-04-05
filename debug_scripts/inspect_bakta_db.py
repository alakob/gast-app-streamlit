#!/usr/bin/env python3
"""
Script to inspect the bakta_jobs.db and other AMR-related SQLite databases.
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
logger = logging.getLogger("db-inspector")

# List of database files to examine
DB_PATHS = [
    # Main bakta.db found in .amr_predictor directory
    os.path.expanduser("~/.amr_predictor/bakta/bakta.db"),
    
    # Main bakta_jobs.db found in another project
    os.path.expanduser("~/projects/amr_UI/gast-predictor/streamlit_app/processing/bakta_jobs.db"),
    
    # Local database if it exists
    os.path.join(Path(__file__).parent, "bakta_jobs.db"),
    
    # Check for other common locations
    os.path.expanduser("~/projects/gast-app-streamlit/bakta_jobs.db"),
    os.path.expanduser("~/projects/gast-app-streamlit/streamlit/bakta_jobs.db"),
    os.path.expanduser("~/projects/gast-app-streamlit/amr_jobs.db")
]

def inspect_database(db_path):
    """Inspect the structure and content of a database file"""
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return None
    
    try:
        logger.info(f"Inspecting database: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        logger.info(f"Found {len(tables)} tables in {db_path}")
        
        db_info = {
            "path": db_path,
            "tables": {},
            "error_jobs": []
        }
        
        for table in tables:
            table_name = table[0]
            # Get columns for the table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Count rows in the table
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get statistics - how many jobs with each status
            status_stats = {}
            if 'status' in column_names:
                cursor.execute(f"SELECT status, COUNT(*) FROM {table_name} GROUP BY status")
                for status_row in cursor.fetchall():
                    status_stats[status_row[0]] = status_row[1]
            
            # Save table info
            db_info["tables"][table_name] = {
                "columns": column_names,
                "row_count": row_count,
                "status_stats": status_stats
            }
            
            # Check for jobs with error status
            if 'status' in column_names and row_count > 0:
                try:
                    cursor.execute(f"""
                        SELECT * FROM {table_name} 
                        WHERE status LIKE '%ERROR%' OR status LIKE '%FAILED%' OR status LIKE '%FAIL%'
                        LIMIT 100
                    """)
                    error_rows = cursor.fetchall()
                    
                    if error_rows:
                        logger.info(f"Found {len(error_rows)} jobs with error status in table {table_name}")
                        for row in error_rows:
                            row_dict = dict(row)
                            db_info["error_jobs"].append({
                                "table": table_name,
                                "data": row_dict
                            })
                except sqlite3.OperationalError as e:
                    logger.warning(f"Error querying {table_name}: {e}")
        
        conn.close()
        return db_info
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error inspecting {db_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error inspecting {db_path}: {e}")
        return None

def main():
    """Main entry point"""
    all_results = []
    
    for db_path in DB_PATHS:
        db_info = inspect_database(db_path)
        if db_info:
            all_results.append(db_info)
    
    print("\nDATABASE INSPECTION RESULTS:")
    print("============================")
    
    if not all_results:
        print("No valid database files found.")
        return
    
    # Print database structure and statistics
    for db_info in all_results:
        print(f"\nDatabase: {db_info['path']}")
        print("-" * 80)
        
        for table_name, table_info in db_info["tables"].items():
            print(f"  Table: {table_name}")
            print(f"    Columns: {', '.join(table_info['columns'])}")
            print(f"    Row Count: {table_info['row_count']}")
            
            if table_info["status_stats"]:
                print("    Status Statistics:")
                for status, count in table_info["status_stats"].items():
                    print(f"      {status}: {count}")
    
    # Print error jobs
    print("\nERROR JOBS:")
    print("===========")
    
    total_error_jobs = sum(len(db_info["error_jobs"]) for db_info in all_results)
    if total_error_jobs == 0:
        print("No jobs with error status found in any database.")
    else:
        print(f"Found {total_error_jobs} jobs with error status across all databases.")
        
        # Print a summary table
        print("\nSummary Table:")
        print("-" * 120)
        
        headers = ["Database", "Table", "ID", "Status", "Error"]
        print(f"{headers[0]:<30} | {headers[1]:<15} | {headers[2]:<36} | {headers[3]:<10} | {headers[4]:<20}")
        print("-" * 120)
        
        for db_info in all_results:
            db_name = os.path.basename(db_info["path"])
            
            for job in db_info["error_jobs"]:
                table = job["table"]
                data = job["data"]
                
                # Extract ID (might be named differently)
                job_id = data.get('id', data.get('job_id', str(data.get('rowid', 'Unknown'))))
                status = data.get('status', 'Unknown')
                error = data.get('error', data.get('message', 'Unknown error'))
                
                # Truncate error message
                if error and len(str(error)) > 20:
                    error = str(error)[:17] + '...'
                
                print(f"{db_name:<30} | {table:<15} | {job_id:<36} | {status:<10} | {error:<20}")

if __name__ == "__main__":
    main()
