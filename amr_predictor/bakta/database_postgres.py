#!/usr/bin/env python3
"""
PostgreSQL database module for Bakta API client.

This module provides a database manager class for storing and retrieving
Bakta annotation data using PostgreSQL.
"""

import os
import json
import logging
import psycopg2
import psycopg2.extras
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
from datetime import datetime

from amr_predictor.bakta.exceptions import BaktaDatabaseError
from amr_predictor.bakta.database_pool import get_connection
from amr_predictor.config.database_config import get_database_path

logger = logging.getLogger("bakta-postgres")

class DatabaseManager:
    """
    Database manager for Bakta API client using PostgreSQL.
    
    This class provides methods for storing and retrieving data
    from a PostgreSQL database for Bakta annotation jobs.
    """
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        environment: str = 'prod',
        min_connections: int = 2,
        max_connections: int = 10,
        results_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the database manager.
        
        Args:
            db_url: PostgreSQL connection URL. If None, uses environment variables.
            environment: Environment to use (dev, test, prod)
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections in the pool
            results_dir: Directory to store downloaded results
        """
        # Get database URL from environment if not provided
        self.db_url = db_url
        self.environment = environment
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        # Set up results directory
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            # Default to Docker volume path for results
            self.results_dir = Path(os.getenv('BAKTA_RESULTS_DIR', '/app/results/bakta'))
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized PostgreSQL database manager for environment: {environment}")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.
        
        This ensures connections are properly closed after use.
        
        Yields:
            psycopg2.connection: Database connection
        """
        with get_connection(self.db_url, environment=self.environment) as conn:
            # Set transaction level for consistency
            with conn.cursor() as cursor:
                cursor.execute("SET search_path TO public")
            yield conn
    
    def save_job(
        self, 
        job_id: str, 
        job_name: str, 
        job_secret: str, 
        config: Dict[str, Any], 
        fasta_path: Optional[str] = None
    ) -> None:
        """
        Save a new Bakta job to the database.
        
        Args:
            job_id: Job ID from the Bakta API
            job_name: User-defined job name
            job_secret: Job secret from the Bakta API
            config: Job configuration dictionary
            fasta_path: Optional path to the FASTA file
            
        Raises:
            BaktaDatabaseError: If the job could not be saved
        """
        try:
            now = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Convert config to JSON string
                    config_json = json.dumps(config)
                    
                    cursor.execute(
                        """
                        INSERT INTO bakta_jobs (
                            id, name, secret, status, fasta_path, config, 
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (job_id, job_name, job_secret, "CREATED", fasta_path, 
                         config_json, now, now)
                    )
                    
                    # Also add a status history record
                    cursor.execute(
                        """
                        INSERT INTO bakta_job_status_history (
                            job_id, status, timestamp, message
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (job_id, "CREATED", now, "Job created")
                    )
                    
                    conn.commit()
                    logger.info(f"Saved job {job_id} to database")
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to save job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def update_job_status(
        self, 
        job_id: str, 
        status: str, 
        message: Optional[str] = None
    ) -> None:
        """
        Update the status of a Bakta job.
        
        Args:
            job_id: Job ID from the Bakta API
            status: New job status (CREATED, QUEUED, RUNNING, COMPLETED, FAILED)
            message: Optional message about the status change
            
        Raises:
            BaktaDatabaseError: If the job status could not be updated
        """
        try:
            now = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update the job record
                    cursor.execute(
                        """
                        UPDATE bakta_jobs SET 
                            status = %s, 
                            updated_at = %s
                        WHERE id = %s
                        """,
                        (status, now, job_id)
                    )
                    
                    # Add timestamp fields based on status
                    if status == "RUNNING":
                        cursor.execute(
                            """
                            UPDATE bakta_jobs SET 
                                started_at = %s
                            WHERE id = %s AND started_at IS NULL
                            """,
                            (now, job_id)
                        )
                    elif status in ("COMPLETED", "FAILED"):
                        cursor.execute(
                            """
                            UPDATE bakta_jobs SET 
                                completed_at = %s
                            WHERE id = %s AND completed_at IS NULL
                            """,
                            (now, job_id)
                        )
                    
                    # Add a status history record
                    cursor.execute(
                        """
                        INSERT INTO bakta_job_status_history (
                            job_id, status, timestamp, message
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (job_id, status, now, message)
                    )
                    
                    conn.commit()
                    logger.info(f"Updated job {job_id} status to {status}")
                    
        except psycopg2.Error as e:
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
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM bakta_jobs WHERE id = %s
                        """,
                        (job_id,)
                    )
                    
                    job = cursor.fetchone()
                    
                    if job:
                        # Parse the config JSON
                        job['config'] = json.loads(job['config'])
                        return dict(job)
                    else:
                        return None
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to get job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_jobs(
        self, 
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all Bakta jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter (CREATED, QUEUED, RUNNING, COMPLETED, FAILED)
            limit: Maximum number of jobs to return
            offset: Offset for pagination
            
        Returns:
            List of job dictionaries
            
        Raises:
            BaktaDatabaseError: If the jobs could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    if status:
                        query = """
                            SELECT * FROM bakta_jobs 
                            WHERE status = %s 
                            ORDER BY created_at DESC
                        """
                        params = (status,)
                    else:
                        query = """
                            SELECT * FROM bakta_jobs 
                            ORDER BY created_at DESC
                        """
                        params = ()
                    
                    # Add pagination if requested
                    if limit is not None:
                        query += " LIMIT %s OFFSET %s"
                        params = params + (limit, offset)
                        
                    cursor.execute(query, params)
                    
                    jobs = cursor.fetchall()
                    
                    # Parse the config JSON for each job
                    for job in jobs:
                        job['config'] = json.loads(job['config'])
                    
                    return [dict(job) for job in jobs]
                    
        except psycopg2.Error as e:
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
                with conn.cursor() as cursor:
                    # Use executemany for better performance with multiple sequences
                    values = [
                        (job_id, seq['header'], seq['sequence'], len(seq['sequence']))
                        for seq in sequences
                    ]
                    
                    cursor.executemany(
                        """
                        INSERT INTO bakta_sequences (
                            job_id, header, sequence, length
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        values
                    )
                    
                    conn.commit()
                    logger.info(f"Saved {len(sequences)} sequences for job {job_id}")
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to save sequences for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def save_result_file(
        self, 
        job_id: str, 
        file_type: str, 
        file_path: str, 
        download_url: Optional[str] = None
    ) -> None:
        """
        Save a result file reference for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            file_type: Type of file (GFF3, JSON, TSV, etc.)
            file_path: Path to the downloaded file
            download_url: Original download URL
            
        Raises:
            BaktaDatabaseError: If the result file could not be saved
        """
        try:
            now = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO bakta_result_files (
                            job_id, file_type, file_path, download_url, downloaded_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (job_id, file_type, file_path, download_url, now)
                    )
                    
                    conn.commit()
                    logger.info(f"Saved result file {file_type} for job {job_id}")
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to save result file for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_result_files(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get result files for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            List of result file dictionaries
            
        Raises:
            BaktaDatabaseError: If the result files could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM bakta_result_files 
                        WHERE job_id = %s 
                        ORDER BY file_type
                        """,
                        (job_id,)
                    )
                    
                    files = cursor.fetchall()
                    return [dict(file) for file in files]
                    
        except psycopg2.Error as e:
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
                with conn.cursor() as cursor:
                    # Use executemany for better performance with multiple annotations
                    values = [
                        (
                            job_id, 
                            ann['feature_id'], 
                            ann['feature_type'], 
                            ann['contig'], 
                            ann['start'], 
                            ann['end'], 
                            ann['strand'], 
                            json.dumps(ann['attributes'])
                        )
                        for ann in annotations
                    ]
                    
                    cursor.executemany(
                        """
                        INSERT INTO bakta_annotations (
                            job_id, feature_id, feature_type, contig, 
                            start, end, strand, attributes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        values
                    )
                    
                    conn.commit()
                    logger.info(f"Saved {len(annotations)} annotations for job {job_id}")
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to save annotations for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_annotations(
        self, 
        job_id: str, 
        feature_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get annotations for a job, optionally filtered by feature type.
        
        Args:
            job_id: Job ID from the Bakta API
            feature_type: Optional feature type filter (CDS, rRNA, tRNA, etc.)
            limit: Maximum number of annotations to return
            offset: Offset for pagination
            
        Returns:
            List of annotation dictionaries
            
        Raises:
            BaktaDatabaseError: If the annotations could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    if feature_type:
                        query = """
                            SELECT * FROM bakta_annotations 
                            WHERE job_id = %s AND feature_type = %s 
                            ORDER BY contig, start
                        """
                        params = (job_id, feature_type)
                    else:
                        query = """
                            SELECT * FROM bakta_annotations 
                            WHERE job_id = %s 
                            ORDER BY contig, start
                        """
                        params = (job_id,)
                    
                    # Add pagination if requested
                    if limit is not None:
                        query += " LIMIT %s OFFSET %s"
                        params = params + (limit, offset)
                        
                    cursor.execute(query, params)
                    
                    annotations = cursor.fetchall()
                    
                    # Parse the attributes JSON for each annotation
                    for ann in annotations:
                        ann['attributes'] = json.loads(ann['attributes'])
                    
                    return [dict(ann) for ann in annotations]
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to get annotations for job {job_id}: {str(e)}"
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
            job_id: Job ID from the Bakta API
            contig: Contig name
            start: Start position
            end: End position
            
        Returns:
            List of annotation dictionaries
            
        Raises:
            BaktaDatabaseError: If the annotations could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Use a parameterized query to avoid SQL injection
                    # The query gets all annotations that overlap with the specified range
                    cursor.execute(
                        """
                        SELECT * FROM bakta_annotations 
                        WHERE job_id = %s AND contig = %s AND 
                        NOT (end < %s OR start > %s)
                        ORDER BY start
                        """,
                        (job_id, contig, start, end)
                    )
                    
                    annotations = cursor.fetchall()
                    
                    # Parse the attributes JSON for each annotation
                    for ann in annotations:
                        ann['attributes'] = json.loads(ann['attributes'])
                    
                    return [dict(ann) for ann in annotations]
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to get annotations in range for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_job_status_history(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get the status history for a job.
        
        Args:
            job_id: Job ID from the Bakta API
            
        Returns:
            List of status history dictionaries
            
        Raises:
            BaktaDatabaseError: If the status history could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM bakta_job_status_history 
                        WHERE job_id = %s 
                        ORDER BY timestamp
                        """,
                        (job_id,)
                    )
                    
                    history = cursor.fetchall()
                    return [dict(entry) for entry in history]
                    
        except psycopg2.Error as e:
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
                with conn.cursor() as cursor:
                    # Due to foreign key constraints, deleting the job will
                    # automatically delete all associated data
                    cursor.execute(
                        """
                        DELETE FROM bakta_jobs WHERE id = %s
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
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to delete job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    def get_job_count_by_status(self) -> Dict[str, int]:
        """
        Get a count of jobs by status.
        
        Returns:
            Dictionary mapping status to count
            
        Raises:
            BaktaDatabaseError: If the job count could not be retrieved
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT status, COUNT(*) as count 
                        FROM bakta_jobs 
                        GROUP BY status
                        """
                    )
                    
                    counts = cursor.fetchall()
                    
                    # Convert to a simpler dictionary
                    return {entry['status']: entry['count'] for entry in counts}
                    
        except psycopg2.Error as e:
            error_msg = f"Failed to get job count by status: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
