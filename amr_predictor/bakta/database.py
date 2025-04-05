#!/usr/bin/env python3
"""
Database module for Bakta API client.

This module provides a database manager class for storing and retrieving
Bakta annotation data using SQLite.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
from datetime import datetime

from amr_predictor.bakta.exceptions import BaktaException
from amr_predictor.config.database_config import get_database_path

logger = logging.getLogger("bakta-database")

# SQL to create the database schema
SCHEMA_SQL = """
-- Table to store Bakta job metadata and configuration
CREATE TABLE IF NOT EXISTS bakta_jobs (
    id TEXT PRIMARY KEY,                -- Job ID from Bakta API (UUID)
    name TEXT NOT NULL,                 -- User-defined job name
    secret TEXT NOT NULL,               -- Job secret for API authentication
    status TEXT NOT NULL,               -- Job status (INIT, RUNNING, SUCCESSFUL, ERROR)
    fasta_path TEXT,                    -- Path to the FASTA file used for the job
    config TEXT NOT NULL,               -- JSON string of job configuration
    created_at TEXT NOT NULL,           -- Timestamp when job was created
    updated_at TEXT NOT NULL,           -- Timestamp when job was last updated
    started_at TEXT,                    -- Timestamp when job was started on the API
    completed_at TEXT                   -- Timestamp when job was completed
);

-- Table to store the sequences submitted to Bakta
CREATE TABLE IF NOT EXISTS bakta_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,               -- Foreign key to bakta_jobs.id
    header TEXT NOT NULL,               -- Sequence header (from FASTA)
    sequence TEXT NOT NULL,             -- The actual sequence
    length INTEGER NOT NULL,            -- Length of the sequence
    FOREIGN KEY (job_id) REFERENCES bakta_jobs(id) ON DELETE CASCADE
);

-- Table to store paths to downloaded result files
CREATE TABLE IF NOT EXISTS bakta_result_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,               -- Foreign key to bakta_jobs.id
    file_type TEXT NOT NULL,            -- Type of file (GFF3, JSON, TSV, etc.)
    file_path TEXT NOT NULL,            -- Path to the downloaded file
    download_url TEXT,                  -- Original download URL
    downloaded_at TEXT NOT NULL,        -- Timestamp when file was downloaded
    FOREIGN KEY (job_id) REFERENCES bakta_jobs(id) ON DELETE CASCADE
);

-- Table to store annotation data extracted from result files
CREATE TABLE IF NOT EXISTS bakta_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,               -- Foreign key to bakta_jobs.id
    feature_id TEXT NOT NULL,           -- Feature ID (from annotation)
    feature_type TEXT NOT NULL,         -- Feature type (CDS, rRNA, tRNA, etc.)
    contig TEXT NOT NULL,               -- Contig/chromosome name
    start INTEGER NOT NULL,             -- Start position (1-based)
    end INTEGER NOT NULL,               -- End position
    strand TEXT NOT NULL,               -- Strand (+, -, or .)
    attributes TEXT NOT NULL,           -- JSON string of feature attributes 
    FOREIGN KEY (job_id) REFERENCES bakta_jobs(id) ON DELETE CASCADE
);

-- Table to store job status history for tracking progress
CREATE TABLE IF NOT EXISTS bakta_job_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,               -- Foreign key to bakta_jobs.id
    status TEXT NOT NULL,               -- Job status
    timestamp TEXT NOT NULL,            -- Timestamp when status was recorded
    message TEXT,                       -- Optional message about status change
    FOREIGN KEY (job_id) REFERENCES bakta_jobs(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_status ON bakta_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_job_id ON bakta_sequences(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_job_id ON bakta_result_files(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_id ON bakta_annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_feature_type ON bakta_annotations(feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_job_status_history_job_id ON bakta_job_status_history(job_id);

-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_feature_id ON bakta_annotations(feature_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_contig ON bakta_annotations(contig);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_position ON bakta_annotations(start, end);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_contig ON bakta_annotations(job_id, contig);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_feature_type ON bakta_annotations(job_id, feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_header ON bakta_sequences(header);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_file_type ON bakta_result_files(file_type);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_job_file_type ON bakta_result_files(job_id, file_type);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_created_at ON bakta_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_updated_at ON bakta_jobs(updated_at);
"""

class BaktaDatabaseError(BaktaException):
    """Exception raised for database-related errors."""
    pass

class DatabaseManager:
    """
    Database manager for Bakta API client.
    
    This class provides methods for storing and retrieving data
    from a SQLite database for Bakta annotation jobs.
    """
    
    def __init__(self, database_path: Union[str, Path] = None):
        """
        Initialize the database manager.
        
        Args:
            database_path: Path to the SQLite database file. If None, a default
                          path will be used in the project directory.
        """
        # Get the database path from the configuration
        self.database_path = get_database_path(database_path)
        logger.info(f"Using database at {self.database_path}")
        
        # Initialize the database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """
        Initialize the database by creating tables if they don't exist.
        """
        try:
            with self._get_connection() as conn:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
                logger.info(f"Initialized database at {self.database_path}")
        except sqlite3.Error as e:
            error_msg = f"Failed to initialize database: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.
        
        This ensures connections are properly closed after use.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        try:
            # Enable foreign key constraints
            conn = sqlite3.connect(str(self.database_path))
            conn.execute("PRAGMA foreign_keys = ON")
            # Return dictionary-like rows
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise BaktaDatabaseError(f"Database connection error: {str(e)}")
        finally:
            conn.close()
    
    def save_job(self, job_id: str, job_name: str, job_secret: str, 
                 config: Dict[str, Any], fasta_path: Optional[str] = None) -> None:
        """
        Save a new Bakta job to the database.
        
        Args:
            job_id: Job ID from the Bakta API
            job_name: User-defined job name
            job_secret: Job secret from the Bakta API
            config: Job configuration dictionary
            fasta_path: Path to the FASTA file used for the job
            
        Raises:
            BaktaDatabaseError: If the job could not be saved
        """
        now = datetime.now().isoformat()
        
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO bakta_jobs (
                        id, name, secret, status, fasta_path, config, 
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id, job_name, job_secret, "INIT", fasta_path, 
                        json.dumps(config), now, now
                    )
                )
                
                # Add initial status to history
                conn.execute(
                    """
                    INSERT INTO bakta_job_status_history (
                        job_id, status, timestamp, message
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (job_id, "INIT", now, "Job initialized")
                )
                
                conn.commit()
                logger.info(f"Saved job {job_id} to database")
        except sqlite3.Error as e:
            error_msg = f"Failed to save job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def update_job_status(self, job_id: str, status: str, message: Optional[str] = None) -> None:
        """
        Update the status of a Bakta job.
        
        Args:
            job_id: Job ID from the Bakta API
            status: New job status (INIT, RUNNING, SUCCESSFUL, ERROR)
            message: Optional message about the status change
            
        Raises:
            BaktaDatabaseError: If the job status could not be updated
        """
        now = datetime.now().isoformat()
        
        try:
            with self._get_connection() as conn:
                # Update job status
                conn.execute(
                    """
                    UPDATE bakta_jobs SET status = ?, updated_at = ? WHERE id = ?
                    """,
                    (status, now, job_id)
                )
                
                # Add status to history
                conn.execute(
                    """
                    INSERT INTO bakta_job_status_history (
                        job_id, status, timestamp, message
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (job_id, status, now, message)
                )
                
                # Update timestamps based on status
                if status == "RUNNING":
                    conn.execute(
                        """
                        UPDATE bakta_jobs SET started_at = ? WHERE id = ? AND started_at IS NULL
                        """,
                        (now, job_id)
                    )
                elif status in ["SUCCESSFUL", "ERROR"]:
                    conn.execute(
                        """
                        UPDATE bakta_jobs SET completed_at = ? WHERE id = ? AND completed_at IS NULL
                        """,
                        (now, job_id)
                    )
                
                conn.commit()
                logger.info(f"Updated job {job_id} status to {status}")
        except sqlite3.Error as e:
            error_msg = f"Failed to update job {job_id} status: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a Bakta job by ID.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            Dict with job information or None if job not found
            
        Raises:
            BaktaDatabaseError: If the job could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM bakta_jobs WHERE id = ?
                    """,
                    (job_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    job_dict = dict(row)
                    # Parse JSON config
                    job_dict["config"] = json.loads(job_dict["config"])
                    return job_dict
                return None
        except sqlite3.Error as e:
            error_msg = f"Failed to get job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all Bakta jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter (INIT, RUNNING, SUCCESSFUL, ERROR)
            
        Returns:
            List of job dictionaries
            
        Raises:
            BaktaDatabaseError: If the jobs could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                if status:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_jobs WHERE status = ? ORDER BY created_at DESC
                        """,
                        (status,)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_jobs ORDER BY created_at DESC
                        """
                    )
                
                jobs = []
                for row in cursor.fetchall():
                    job_dict = dict(row)
                    # Parse JSON config
                    job_dict["config"] = json.loads(job_dict["config"])
                    jobs.append(job_dict)
                return jobs
        except sqlite3.Error as e:
            error_msg = f"Failed to get jobs: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_sequences(self, job_id: str, sequences: List[Dict[str, str]]) -> None:
        """
        Save FASTA sequences for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            sequences: List of dictionaries with 'header' and 'sequence' keys
            
        Raises:
            BaktaDatabaseError: If the sequences could not be saved
        """
        try:
            with self._get_connection() as conn:
                for seq in sequences:
                    conn.execute(
                        """
                        INSERT INTO bakta_sequences (
                            job_id, header, sequence, length
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            job_id, seq["header"], seq["sequence"], 
                            len(seq["sequence"])
                        )
                    )
                conn.commit()
                logger.info(f"Saved {len(sequences)} sequences for job {job_id}")
        except sqlite3.Error as e:
            error_msg = f"Failed to save sequences for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_sequences(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get FASTA sequences for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            List of sequence dictionaries
            
        Raises:
            BaktaDatabaseError: If the sequences could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM bakta_sequences WHERE job_id = ?
                    """,
                    (job_id,)
                )
                
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            error_msg = f"Failed to get sequences for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_result_file(self, job_id: str, file_type: str, file_path: str, 
                         download_url: Optional[str] = None) -> None:
        """
        Save a result file for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            file_type: Type of file (GFF3, JSON, TSV, etc.)
            file_path: Path to the downloaded file
            download_url: Original download URL
            
        Raises:
            BaktaDatabaseError: If the result file could not be saved
        """
        now = datetime.now().isoformat()
        
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO bakta_result_files (
                        job_id, file_type, file_path, download_url, downloaded_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (job_id, file_type, file_path, download_url, now)
                )
                conn.commit()
                logger.info(f"Saved {file_type} result file for job {job_id}")
        except sqlite3.Error as e:
            error_msg = f"Failed to save result file for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_result_files(self, job_id: str, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get result files for a job, optionally filtered by file type.
        
        Args:
            job_id: Job ID from the Bakta API
            file_type: Optional file type filter (GFF3, JSON, TSV, etc.)
            
        Returns:
            List of result file dictionaries
            
        Raises:
            BaktaDatabaseError: If the result files could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                if file_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_result_files 
                        WHERE job_id = ? AND file_type = ?
                        """,
                        (job_id, file_type)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_result_files WHERE job_id = ?
                        """,
                        (job_id,)
                    )
                
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            error_msg = f"Failed to get result files for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_annotations(self, job_id: str, annotations: List[Dict[str, Any]]) -> None:
        """
        Save annotations for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            annotations: List of annotation dictionaries
            
        Raises:
            BaktaDatabaseError: If the annotations could not be saved
        """
        try:
            with self._get_connection() as conn:
                for annotation in annotations:
                    # Convert attributes to JSON string
                    attributes = json.dumps(annotation.get("attributes", {}))
                    
                    conn.execute(
                        """
                        INSERT INTO bakta_annotations (
                            job_id, feature_id, feature_type, contig, 
                            start, end, strand, attributes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id, 
                            annotation["feature_id"], 
                            annotation["feature_type"], 
                            annotation["contig"],
                            annotation["start"], 
                            annotation["end"], 
                            annotation["strand"], 
                            attributes
                        )
                    )
                conn.commit()
                logger.info(f"Saved {len(annotations)} annotations for job {job_id}")
        except sqlite3.Error as e:
            error_msg = f"Failed to save annotations for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_annotations(self, job_id: str, feature_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get annotations for a job, optionally filtered by feature type.
        
        Args:
            job_id: Job ID from the Bakta API
            feature_type: Optional feature type filter (CDS, rRNA, tRNA, etc.)
            
        Returns:
            List of annotation dictionaries
            
        Raises:
            BaktaDatabaseError: If the annotations could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                if feature_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_annotations 
                        WHERE job_id = ? AND feature_type = ?
                        """,
                        (job_id, feature_type)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM bakta_annotations WHERE job_id = ?
                        """,
                        (job_id,)
                    )
                
                annotations = []
                for row in cursor.fetchall():
                    annotation = dict(row)
                    # Parse JSON attributes
                    annotation["attributes"] = json.loads(annotation["attributes"])
                    annotations.append(annotation)
                return annotations
        except sqlite3.Error as e:
            error_msg = f"Failed to get annotations for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_job_status_history(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get status history for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            List of status history dictionaries
            
        Raises:
            BaktaDatabaseError: If the status history could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM bakta_job_status_history 
                    WHERE job_id = ? ORDER BY timestamp ASC
                    """,
                    (job_id,)
                )
                
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            error_msg = f"Failed to get status history for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and all associated data.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            True if job was deleted, False if job was not found
            
        Raises:
            BaktaDatabaseError: If the job could not be deleted
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM bakta_jobs WHERE id = ?
                    """,
                    (job_id,)
                )
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted job {job_id} from database")
                else:
                    logger.warning(f"Job {job_id} not found for deletion")
                
                return deleted
        except sqlite3.Error as e:
            error_msg = f"Failed to delete job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_job_status_history(self, job_id: str, status: str, 
                       timestamp: str, message: Optional[str] = None) -> None:
        """
        Save a job status history record.
        
        Args:
            job_id: Job ID
            status: Job status
            timestamp: Timestamp when the status was recorded
            message: Optional message about the status change
            
        Raises:
            BaktaDatabaseError: If the history record could not be saved
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO bakta_job_status_history (
                        job_id, status, timestamp, message
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (job_id, status, timestamp, message)
                )
                conn.commit()
                logger.debug(f"Saved status history for job {job_id}: {status}")
        except sqlite3.Error as e:
            error_msg = f"Failed to save job status history: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_annotations_in_range(
            self, 
            job_id: str, 
            contig: str, 
            start: int, 
            end: int
        ) -> List[Dict[str, Any]]:
            """
            Get annotations in a genomic range.
            
            This is an optimized query that uses database indexes for better performance.
            
            Args:
                job_id: Job ID
                contig: Contig name
                start: Start position
                end: End position
                
            Returns:
                List of annotation dictionaries
                
            Raises:
                BaktaDatabaseError: If there is an error retrieving the annotations
            """
            try:
                with self._get_connection() as conn:
                    # Use a parameterized query to avoid SQL injection
                    # The query gets all annotations that overlap with the specified range
                    cur = conn.execute(
                        """
                        SELECT * FROM bakta_annotations 
                        WHERE job_id = ? AND contig = ? AND 
                        NOT (end < ? OR start > ?)
                        """,
                        (job_id, contig, start, end)
                    )
                    
                    # Convert rows to dictionaries
                    return [dict(row) for row in cur.fetchall()]
            except sqlite3.Error as e:
                error_msg = f"Failed to get annotations in range for job {job_id}: {str(e)}"
                logger.error(error_msg)
                raise BaktaDatabaseError(error_msg) 