#!/usr/bin/env python3
"""
Database migration script for AMR predictor.

This script creates the necessary tables for the AMR predictor
while preserving existing Bakta database tables and data.
"""
import os
import sys
import argparse
import logging
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow importing modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, parent_dir)

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.bakta.database_extensions import extend_database_manager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob, AMRJobParams
from amr_predictor.auth.user_manager import UserManager, UserManagerError
from amr_predictor.config.database_config import (
    get_database_path, migrate_legacy_database,
    DEFAULT_BAKTA_DB_PATH, DEFAULT_AMR_DB_PATH,
    LEGACY_BAKTA_DB_PATH, LEGACY_AMR_DB_PATH
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db-migration")

def parse_args():
    parser = argparse.ArgumentParser(description="Database migration script for AMR predictor")
    parser.add_argument(
        "--db-path", 
        type=str, 
        help="Path to the SQLite database. If not provided, uses the default project directory path."
    )
    parser.add_argument(
        "--in-memory-jobs", 
        type=str, 
        help="Path to a JSON file with in-memory jobs to migrate to the database."
    )
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Create an admin user if it doesn't exist."
    )
    parser.add_argument(
        "--admin-username",
        type=str,
        default="admin",
        help="Admin username (default: admin)"
    )
    parser.add_argument(
        "--admin-password",
        type=str,
        help="Admin password. If not provided, will use 'admin' password."
    )
    parser.add_argument(
        "--admin-email",
        type=str,
        help="Admin email."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without committing changes."
    )
    
    return parser.parse_args()

def create_admin_user(user_manager, username, password, email=None):
    """Create an admin user if it doesn't exist"""
    try:
        # Check if user exists
        user = user_manager.get_user_by_username(username)
        if user:
            logger.info(f"Admin user '{username}' already exists.")
            return
        
        # Create user
        from amr_predictor.auth.models import UserCreate
        user_data = UserCreate(
            username=username,
            password=password,
            email=email
        )
        
        user = user_manager.create_user(user_data)
        logger.info(f"Created admin user '{username}'.")
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {str(e)}")
        raise

def migrate_in_memory_jobs(jobs_dict, job_dao):
    """Migrate in-memory jobs to the database"""
    migrated_count = 0
    skipped_count = 0
    
    for job_id, job_data in jobs_dict.items():
        # Check if job already exists in database
        existing_job = job_dao.get_by_id(job_id)
        if existing_job:
            logger.info(f"Job {job_id} already exists in database, skipping.")
            skipped_count += 1
            continue
        
        try:
            # Parse dates
            created_at = datetime.fromisoformat(job_data.get("start_time", datetime.now().isoformat()))
            completed_at = None
            if job_data.get("end_time"):
                completed_at = datetime.fromisoformat(job_data["end_time"])
            
            # Get additional info
            additional_info = job_data.get("additional_info", {})
            
            # Create job params
            params = None
            if additional_info:
                params = AMRJobParams(
                    model_name=additional_info.get("model_name", "alakob/DraGNOME-2.5b-v1"),
                    batch_size=additional_info.get("batch_size", 8),
                    segment_length=additional_info.get("segment_length", 6000),
                    segment_overlap=additional_info.get("segment_overlap", 0),
                    use_cpu=additional_info.get("use_cpu", False)
                )
            
            # Create job
            job = AMRJob(
                id=job_id,
                job_name=additional_info.get("input_file", f"Job {job_id}"),
                status=job_data.get("status", "Unknown"),
                progress=job_data.get("progress", 0.0),
                created_at=created_at,
                completed_at=completed_at,
                error=job_data.get("error"),
                result_file_path=job_data.get("result_file")
            )
            
            # Set params if available
            if params:
                job.params = params
            
            # Save to database
            job_dao.save(job)
            logger.info(f"Migrated job {job_id} to database.")
            migrated_count += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate job {job_id}: {str(e)}")
            skipped_count += 1
    
    return migrated_count, skipped_count

def main():
    args = parse_args()
    
    try:
        # Initialize database with project directory path by default
        db_manager = DatabaseManager(args.db_path)
        logger.info(f"Using database at {db_manager.db_path}")
        
        # Check for legacy databases and offer to migrate them
        if LEGACY_BAKTA_DB_PATH.exists() and DEFAULT_BAKTA_DB_PATH != LEGACY_BAKTA_DB_PATH:
            logger.info(f"Found legacy database at {LEGACY_BAKTA_DB_PATH}")
            if not args.dry_run and DEFAULT_BAKTA_DB_PATH.exists() is False:
                shutil.copy2(LEGACY_BAKTA_DB_PATH, DEFAULT_BAKTA_DB_PATH)
                logger.info(f"Migrated legacy database to {DEFAULT_BAKTA_DB_PATH}")
        
        # Initialize DAOs
        job_dao = AMRJobDAO(db_manager)
        
        # Create user manager
        user_manager = UserManager(db_path=db_manager.db_path)
        
        # Begin transaction if not dry run
        if not args.dry_run:
            conn = db_manager._get_connection()
            conn.execute("BEGIN TRANSACTION")
        
        # Create tables
        extend_database_manager(db_manager)
        logger.info("AMR tables created or verified.")
        
        # Create admin user if requested
        if args.create_admin:
            admin_password = args.admin_password or "admin"
            create_admin_user(user_manager, args.admin_username, admin_password, args.admin_email)
        
        # Migrate in-memory jobs if provided
        if args.in_memory_jobs:
            try:
                with open(args.in_memory_jobs, 'r') as f:
                    jobs_dict = json.load(f)
                
                logger.info(f"Found {len(jobs_dict)} jobs to migrate.")
                migrated, skipped = migrate_in_memory_jobs(jobs_dict, job_dao)
                logger.info(f"Migration complete. Migrated: {migrated}, Skipped: {skipped}")
                
            except FileNotFoundError:
                logger.error(f"Jobs file not found: {args.in_memory_jobs}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in jobs file: {args.in_memory_jobs}")
        
        # Commit changes if not dry run
        if not args.dry_run:
            conn.commit()
            logger.info("Changes committed to database.")
        else:
            logger.info("Dry run completed. No changes committed.")
        
        logger.info("Migration completed successfully.")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        
        # Rollback if not dry run
        if not args.dry_run:
            try:
                conn.rollback()
                logger.info("Changes rolled back.")
            except:
                pass
                
        sys.exit(1)

if __name__ == "__main__":
    main()
