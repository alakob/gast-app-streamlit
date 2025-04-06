#!/usr/bin/env python3
"""
Migration utilities for transitioning Bakta data from SQLite to PostgreSQL.

This module provides functionality to migrate existing Bakta annotation data
from the old SQLite database to the new PostgreSQL database.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from contextlib import contextmanager

from amr_predictor.bakta.exceptions import BaktaDatabaseError
from amr_predictor.bakta.database_postgres import DatabaseManager as PostgresDatabaseManager
from amr_predictor.config.database_config import get_database_path

logger = logging.getLogger("bakta-migration")

class BaktaMigrationManager:
    """
    Migration manager for transitioning Bakta data from SQLite to PostgreSQL.
    """
    
    def __init__(
        self, 
        sqlite_path: Optional[Union[str, Path]] = None,
        pg_manager: Optional[PostgresDatabaseManager] = None,
        environment: str = 'dev'
    ):
        """
        Initialize the migration manager.
        
        Args:
            sqlite_path: Path to the SQLite database file
            pg_manager: PostgreSQL database manager instance
            environment: Environment to use for PostgreSQL ('dev', 'test', 'prod')
        """
        # Get SQLite database path if not provided
        if sqlite_path is None:
            sqlite_path = get_database_path()
        
        self.sqlite_path = Path(sqlite_path)
        self.environment = environment
        
        # Create PostgreSQL database manager if not provided
        if pg_manager is None:
            self.pg_manager = PostgresDatabaseManager(environment=environment)
        else:
            self.pg_manager = pg_manager
            
        logger.info(f"Initialized migration manager with SQLite path: {self.sqlite_path}")
        
    @contextmanager
    def _get_sqlite_connection(self):
        """
        Context manager for SQLite database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        if not self.sqlite_path.exists():
            raise BaktaDatabaseError(f"SQLite database file not found: {self.sqlite_path}")
            
        # Connect to SQLite database with row factory for dictionary-like rows
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            conn.close()
    
    def migrate_all(self) -> Dict[str, int]:
        """
        Migrate all data from SQLite to PostgreSQL.
        
        Returns:
            Dictionary with counts of migrated records by type
        """
        counts = {
            "jobs": 0,
            "sequences": 0,
            "result_files": 0,
            "annotations": 0,
            "status_history": 0
        }
        
        # Get all jobs from SQLite
        try:
            with self._get_sqlite_connection() as conn:
                # Get jobs
                cur = conn.execute("SELECT * FROM bakta_jobs")
                jobs = [dict(row) for row in cur.fetchall()]
                
                for job in jobs:
                    # Migrate each job and its related data
                    job_id = job['id']
                    
                    try:
                        self._migrate_job(conn, job)
                        counts["jobs"] += 1
                        
                        # Migrate sequences
                        seq_count = self._migrate_sequences(conn, job_id)
                        counts["sequences"] += seq_count
                        
                        # Migrate result files
                        file_count = self._migrate_result_files(conn, job_id)
                        counts["result_files"] += file_count
                        
                        # Migrate annotations
                        ann_count = self._migrate_annotations(conn, job_id)
                        counts["annotations"] += ann_count
                        
                        # Migrate status history
                        hist_count = self._migrate_status_history(conn, job_id)
                        counts["status_history"] += hist_count
                        
                        logger.info(f"Successfully migrated job {job_id}")
                    except Exception as e:
                        logger.error(f"Error migrating job {job_id}: {str(e)}")
                
                logger.info(f"Migration completed: {counts}")
                return counts
                
        except sqlite3.Error as e:
            error_msg = f"SQLite error during migration: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def _migrate_job(self, sqlite_conn, job: Dict[str, Any]) -> None:
        """
        Migrate a single job from SQLite to PostgreSQL.
        
        Args:
            sqlite_conn: SQLite connection
            job: Job dictionary from SQLite
        """
        # Convert status to PostgreSQL enum format
        sqlite_status = job['status']
        pg_status_map = {
            'INIT': 'CREATED',
            'RUNNING': 'RUNNING',
            'SUCCESSFUL': 'COMPLETED',
            'ERROR': 'FAILED',
            'QUEUED': 'QUEUED',
            'EXPIRED': 'EXPIRED',
            'UNKNOWN': 'UNKNOWN'
        }
        pg_status = pg_status_map.get(sqlite_status, 'UNKNOWN')
        
        # Save job to PostgreSQL
        self.pg_manager.save_job(
            job_id=job['id'],
            job_name=job['name'],
            job_secret=job['secret'],
            config=json.loads(job['config']),
            fasta_path=job['fasta_path']
        )
        
        # Update job status and timestamps
        self.pg_manager.update_job_status(job['id'], pg_status)
        
        # Use direct connection to update timestamps
        with self.pg_manager._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE bakta_jobs SET 
                        started_at = %s,
                        completed_at = %s
                    WHERE id = %s
                    """,
                    (job['started_at'], job['completed_at'], job['id'])
                )
                conn.commit()
    
    def _migrate_sequences(self, sqlite_conn, job_id: str) -> int:
        """
        Migrate sequences for a job from SQLite to PostgreSQL.
        
        Args:
            sqlite_conn: SQLite connection
            job_id: Job ID
            
        Returns:
            Number of sequences migrated
        """
        cur = sqlite_conn.execute(
            "SELECT * FROM bakta_sequences WHERE job_id = ?",
            (job_id,)
        )
        sequences = [dict(row) for row in cur.fetchall()]
        
        if not sequences:
            return 0
        
        # Transform sequences for PostgreSQL manager
        pg_sequences = [
            {
                'header': seq['header'],
                'sequence': seq['sequence']
            }
            for seq in sequences
        ]
        
        # Save sequences to PostgreSQL
        self.pg_manager.save_sequences(job_id, pg_sequences)
        
        return len(sequences)
    
    def _migrate_result_files(self, sqlite_conn, job_id: str) -> int:
        """
        Migrate result files for a job from SQLite to PostgreSQL.
        
        Args:
            sqlite_conn: SQLite connection
            job_id: Job ID
            
        Returns:
            Number of result files migrated
        """
        cur = sqlite_conn.execute(
            "SELECT * FROM bakta_result_files WHERE job_id = ?",
            (job_id,)
        )
        files = [dict(row) for row in cur.fetchall()]
        
        if not files:
            return 0
        
        # Save each file reference to PostgreSQL
        for file in files:
            self.pg_manager.save_result_file(
                job_id=job_id,
                file_type=file['file_type'],
                file_path=file['file_path'],
                download_url=file['download_url']
            )
        
        return len(files)
    
    def _migrate_annotations(self, sqlite_conn, job_id: str) -> int:
        """
        Migrate annotations for a job from SQLite to PostgreSQL.
        
        Args:
            sqlite_conn: SQLite connection
            job_id: Job ID
            
        Returns:
            Number of annotations migrated
        """
        cur = sqlite_conn.execute(
            "SELECT * FROM bakta_annotations WHERE job_id = ?",
            (job_id,)
        )
        annotations = [dict(row) for row in cur.fetchall()]
        
        if not annotations:
            return 0
        
        # Transform annotations for PostgreSQL manager
        pg_annotations = [
            {
                'feature_id': ann['feature_id'],
                'feature_type': ann['feature_type'],
                'contig': ann['contig'],
                'start': ann['start'],
                'end': ann['end'],
                'strand': ann['strand'],
                'attributes': json.loads(ann['attributes'])
            }
            for ann in annotations
        ]
        
        # Save annotations to PostgreSQL in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, len(pg_annotations), batch_size):
            batch = pg_annotations[i:i+batch_size]
            self.pg_manager.save_annotations(job_id, batch)
        
        return len(annotations)
    
    def _migrate_status_history(self, sqlite_conn, job_id: str) -> int:
        """
        Migrate status history for a job from SQLite to PostgreSQL.
        
        Args:
            sqlite_conn: SQLite connection
            job_id: Job ID
            
        Returns:
            Number of status history records migrated
        """
        cur = sqlite_conn.execute(
            "SELECT * FROM bakta_job_status_history WHERE job_id = ?",
            (job_id,)
        )
        history = [dict(row) for row in cur.fetchall()]
        
        if not history:
            return 0
        
        # Map SQLite status to PostgreSQL enum values
        status_map = {
            'INIT': 'CREATED',
            'RUNNING': 'RUNNING',
            'SUCCESSFUL': 'COMPLETED',
            'ERROR': 'FAILED',
            'QUEUED': 'QUEUED',
            'EXPIRED': 'EXPIRED',
            'UNKNOWN': 'UNKNOWN'
        }
        
        # Save each history record to PostgreSQL
        with self.pg_manager._get_connection() as conn:
            with conn.cursor() as cursor:
                for entry in history:
                    pg_status = status_map.get(entry['status'], 'UNKNOWN')
                    cursor.execute(
                        """
                        INSERT INTO bakta_job_status_history (
                            job_id, status, timestamp, message
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (job_id, pg_status, entry['timestamp'], entry['message'])
                    )
                conn.commit()
        
        return len(history)

def migrate_to_postgres(
    sqlite_path: Optional[Union[str, Path]] = None,
    environment: str = 'dev'
) -> Dict[str, int]:
    """
    Migrate all Bakta data from SQLite to PostgreSQL.
    
    Args:
        sqlite_path: Path to the SQLite database file
        environment: PostgreSQL environment to migrate to
        
    Returns:
        Dictionary with counts of migrated records by type
    """
    logger.info(f"Starting migration from SQLite to PostgreSQL ({environment})")
    
    manager = BaktaMigrationManager(
        sqlite_path=sqlite_path,
        environment=environment
    )
    
    return manager.migrate_all()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration from command line
    try:
        results = migrate_to_postgres()
        print(f"Migration completed successfully: {results}")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        print(f"Migration failed: {str(e)}")
