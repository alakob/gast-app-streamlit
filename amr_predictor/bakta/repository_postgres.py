#!/usr/bin/env python3
"""
PostgreSQL repository for Bakta annotations.

This module provides a repository for storing and querying
Bakta annotations in a PostgreSQL database.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

from amr_predictor.bakta.models import (
    BaktaJob,
    BaktaSequence,
    BaktaAnnotation,
    BaktaResultFile,
    QueryResult
)
from amr_predictor.bakta.exceptions import BaktaException, BaktaDatabaseError
from amr_predictor.bakta.database_postgres import DatabaseManager

logger = logging.getLogger("bakta-repository-postgres")

class BaktaRepository:
    """
    Repository for Bakta annotations using PostgreSQL.
    
    This class provides methods for storing and querying
    Bakta annotations in a PostgreSQL database.
    """
    
    def __init__(
        self, 
        db_manager: Optional[DatabaseManager] = None,
        environment: str = 'prod'
    ):
        """
        Initialize the repository.
        
        Args:
            db_manager: DatabaseManager instance for database operations
            environment: Environment name ('dev', 'test', or 'prod')
        """
        self.environment = environment
        
        # Use provided database manager or create a new one
        if db_manager is None:
            self.db_manager = DatabaseManager(environment=environment)
        else:
            self.db_manager = db_manager
            
        logger.info(f"Initialized Bakta repository with {environment} database")
    
    async def query_annotations(
        self,
        job_id: str,
        conditions: Optional[List] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[BaktaAnnotation]:
        """
        Query annotations with filtering, sorting, and pagination.
        
        Args:
            job_id: Job ID to query
            conditions: Query conditions for filtering
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of annotations matching the query
        """
        try:
            # Start building the query
            query = "SELECT * FROM bakta_annotations WHERE job_id = %s"
            params = [job_id]
            
            # Add conditions if provided
            if conditions:
                for condition in conditions:
                    if len(condition) == 3:
                        field, operator, value = condition
                        
                        # Map operator to SQL
                        op_map = {
                            "eq": "=",
                            "ne": "!=",
                            "gt": ">",
                            "lt": "<",
                            "gte": ">=",
                            "lte": "<=",
                            "like": "ILIKE",
                            "in": "IN"
                        }
                        
                        sql_op = op_map.get(operator, "=")
                        
                        if operator == "in" and isinstance(value, list):
                            placeholders = ', '.join(['%s'] * len(value))
                            query += f" AND {field} IN ({placeholders})"
                            params.extend(value)
                        elif operator == "like":
                            query += f" AND {field} {sql_op} %s"
                            params.append(f"%{value}%")
                        else:
                            query += f" AND {field} {sql_op} %s"
                            params.append(value)
            
            # Add sorting
            if sort_by:
                if sort_order.lower() not in ["asc", "desc"]:
                    sort_order = "asc"
                query += f" ORDER BY {sort_by} {sort_order.upper()}"
            else:
                # Default sorting by position
                query += " ORDER BY contig, start ASC"
            
            # Add pagination
            if limit is not None:
                query += " LIMIT %s OFFSET %s"
                params.append(limit)
                params.append(offset)
            
            # Execute the query
            with self.db_manager._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to BaktaAnnotation objects
                    annotations = []
                    for row in rows:
                        # Parse the attributes JSON
                        attributes = json.loads(row['attributes']) if isinstance(row['attributes'], str) else row['attributes']
                        
                        annotation = BaktaAnnotation(
                            id=row['id'],
                            job_id=row['job_id'],
                            feature_id=row['feature_id'],
                            feature_type=row['feature_type'],
                            contig=row['contig'],
                            start=row['start'],
                            end=row['end'],
                            strand=row['strand'],
                            attributes=attributes
                        )
                        annotations.append(annotation)
                    
                    return annotations
                    
        except psycopg2.Error as e:
            error_msg = f"Database error while querying annotations: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    async def count_annotations(
        self,
        job_id: str,
        conditions: Optional[List] = None
    ) -> int:
        """
        Count annotations matching a query.
        
        Args:
            job_id: Job ID to query
            conditions: Query conditions for filtering
        
        Returns:
            Number of annotations matching the query
        """
        try:
            # Start building the query
            query = "SELECT COUNT(*) FROM bakta_annotations WHERE job_id = %s"
            params = [job_id]
            
            # Add conditions if provided
            if conditions:
                for condition in conditions:
                    if len(condition) == 3:
                        field, operator, value = condition
                        
                        # Map operator to SQL
                        op_map = {
                            "eq": "=",
                            "ne": "!=",
                            "gt": ">",
                            "lt": "<",
                            "gte": ">=",
                            "lte": "<=",
                            "like": "ILIKE",
                            "in": "IN"
                        }
                        
                        sql_op = op_map.get(operator, "=")
                        
                        if operator == "in" and isinstance(value, list):
                            placeholders = ', '.join(['%s'] * len(value))
                            query += f" AND {field} IN ({placeholders})"
                            params.extend(value)
                        elif operator == "like":
                            query += f" AND {field} {sql_op} %s"
                            params.append(f"%{value}%")
                        else:
                            query += f" AND {field} {sql_op} %s"
                            params.append(value)
            
            # Execute the query
            with self.db_manager._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    count = cursor.fetchone()[0]
                    return count
                    
        except psycopg2.Error as e:
            error_msg = f"Database error while counting annotations: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    async def get_feature_types(self, job_id: str) -> List[str]:
        """
        Get all feature types for a job.
        
        Args:
            job_id: Job ID to query
        
        Returns:
            List of feature types with counts
        """
        try:
            with self.db_manager._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT feature_type, COUNT(*) as count 
                        FROM bakta_annotations 
                        WHERE job_id = %s 
                        GROUP BY feature_type 
                        ORDER BY count DESC
                        """,
                        (job_id,)
                    )
                    
                    return [row[0] for row in cursor.fetchall()]
                    
        except psycopg2.Error as e:
            error_msg = f"Database error while getting feature types: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    async def get_feature_type_counts(self, job_id: str) -> Dict[str, int]:
        """
        Get counts of each feature type for a job.
        
        Args:
            job_id: Job ID to query
        
        Returns:
            Dictionary mapping feature types to counts
        """
        try:
            with self.db_manager._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT feature_type, COUNT(*) as count 
                        FROM bakta_annotations 
                        WHERE job_id = %s 
                        GROUP BY feature_type 
                        ORDER BY count DESC
                        """,
                        (job_id,)
                    )
                    
                    return {row[0]: row[1] for row in cursor.fetchall()}
                    
        except psycopg2.Error as e:
            error_msg = f"Database error while getting feature type counts: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    async def import_results(
        self,
        job_id: str,
        gff_annotations: List[Dict[str, Any]],
        json_data: Dict[str, Any]
    ) -> int:
        """
        Import annotations from GFF3 and JSON data.
        
        Args:
            job_id: Job ID for the annotations
            gff_annotations: GFF3 annotations
            json_data: JSON data
        
        Returns:
            Number of imported annotations
        """
        try:
            # Transform GFF annotations into database format
            annotations = []
            for gff in gff_annotations:
                # Extract feature ID from attributes
                feature_id = gff.get('attributes', {}).get('ID', f"feature_{len(annotations)+1}")
                
                annotation = {
                    'feature_id': feature_id,
                    'feature_type': gff.get('type', 'unknown'),
                    'contig': gff.get('seqid', 'unknown'),
                    'start': gff.get('start', 0),
                    'end': gff.get('end', 0),
                    'strand': gff.get('strand', '.'),
                    'attributes': gff.get('attributes', {})
                }
                
                annotations.append(annotation)
            
            # Save annotations to database
            if annotations:
                # Save in batches to avoid memory issues
                batch_size = 1000
                saved_count = 0
                
                for i in range(0, len(annotations), batch_size):
                    batch = annotations[i:i+batch_size]
                    self.db_manager.save_annotations(job_id, batch)
                    saved_count += len(batch)
                
                logger.info(f"Imported {saved_count} annotations for job {job_id}")
                return saved_count
            else:
                logger.warning(f"No annotations to import for job {job_id}")
                return 0
                
        except Exception as e:
            error_msg = f"Error importing annotations for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def get_jobs(
        self, 
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[BaktaJob]:
        """
        Get jobs from the database.
        
        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return
            offset: Offset for pagination
        
        Returns:
            List of jobs
        """
        try:
            # Get jobs from the database
            db_jobs = self.db_manager.get_jobs(status=status, limit=limit, offset=offset)
            
            # Convert to BaktaJob objects
            jobs = []
            for job_data in db_jobs:
                job = BaktaJob(
                    id=job_data['id'],
                    name=job_data['name'],
                    status=job_data['status'],
                    config=job_data['config'],
                    secret=job_data['secret'],
                    fasta_path=job_data['fasta_path'],
                    created_at=job_data['created_at'],
                    updated_at=job_data['updated_at'],
                    started_at=job_data['started_at'],
                    completed_at=job_data['completed_at']
                )
                jobs.append(job)
            
            return jobs
            
        except Exception as e:
            error_msg = f"Error getting jobs: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def save_job(self, job: BaktaJob) -> None:
        """
        Save a job to the database.
        
        Args:
            job: BaktaJob object to save
        """
        try:
            # Save job to database
            self.db_manager.save_job(
                job_id=job.id,
                job_name=job.name,
                job_secret=job.secret,
                config=job.config,
                fasta_path=job.fasta_path
            )
            
            # Update status if provided
            if job.status:
                self.db_manager.update_job_status(job.id, job.status)
                
        except Exception as e:
            error_msg = f"Error saving job {job.id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def get_job(self, job_id: str) -> Optional[BaktaJob]:
        """
        Get a job from the database.
        
        Args:
            job_id: Job ID
            
        Returns:
            BaktaJob object or None if not found
        """
        try:
            # Get job from database
            job_data = self.db_manager.get_job(job_id)
            
            if job_data:
                # Convert to BaktaJob object
                job = BaktaJob(
                    id=job_data['id'],
                    name=job_data['name'],
                    status=job_data['status'],
                    config=job_data['config'],
                    secret=job_data['secret'],
                    fasta_path=job_data['fasta_path'],
                    created_at=job_data['created_at'],
                    updated_at=job_data['updated_at'],
                    started_at=job_data['started_at'],
                    completed_at=job_data['completed_at']
                )
                return job
            else:
                return None
                
        except Exception as e:
            error_msg = f"Error getting job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the database.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was deleted, False if not found
        """
        try:
            return self.db_manager.delete_job(job_id)
        except Exception as e:
            error_msg = f"Error deleting job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def get_sequences(self, job_id: str) -> List[BaktaSequence]:
        """
        Get sequences for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaSequence objects
        """
        try:
            with self.db_manager._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM bakta_sequences 
                        WHERE job_id = %s 
                        ORDER BY id
                        """,
                        (job_id,)
                    )
                    
                    rows = cursor.fetchall()
                    
                    # Convert to BaktaSequence objects
                    sequences = []
                    for row in rows:
                        sequence = BaktaSequence(
                            id=row['id'],
                            job_id=row['job_id'],
                            header=row['header'],
                            sequence=row['sequence'],
                            length=row['length']
                        )
                        sequences.append(sequence)
                    
                    return sequences
                    
        except psycopg2.Error as e:
            error_msg = f"Database error while getting sequences: {str(e)}"
            logger.error(error_msg)
            raise BaktaDatabaseError(error_msg)
    
    async def save_sequences(self, job_id: str, sequences: List[Dict[str, str]]) -> int:
        """
        Save sequences for a job.
        
        Args:
            job_id: Job ID
            sequences: List of sequence dictionaries with 'header' and 'sequence' keys
            
        Returns:
            Number of sequences saved
        """
        try:
            self.db_manager.save_sequences(job_id, sequences)
            return len(sequences)
        except Exception as e:
            error_msg = f"Error saving sequences for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def get_result_files(self, job_id: str) -> List[BaktaResultFile]:
        """
        Get result files for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaResultFile objects
        """
        try:
            # Get result files from database
            files_data = self.db_manager.get_result_files(job_id)
            
            # Convert to BaktaResultFile objects
            result_files = []
            for file_data in files_data:
                result_file = BaktaResultFile(
                    id=file_data['id'],
                    job_id=file_data['job_id'],
                    file_type=file_data['file_type'],
                    file_path=file_data['file_path'],
                    download_url=file_data['download_url'],
                    downloaded_at=file_data['downloaded_at']
                )
                result_files.append(result_file)
            
            return result_files
            
        except Exception as e:
            error_msg = f"Error getting result files for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def save_result_file(
        self, 
        job_id: str, 
        file_type: str, 
        file_path: str, 
        download_url: Optional[str] = None
    ) -> BaktaResultFile:
        """
        Save a result file for a job.
        
        Args:
            job_id: Job ID
            file_type: Type of file (GFF3, JSON, TSV, etc.)
            file_path: Path to the downloaded file
            download_url: Original download URL
            
        Returns:
            BaktaResultFile object
        """
        try:
            # Save result file to database
            self.db_manager.save_result_file(
                job_id=job_id,
                file_type=file_type,
                file_path=file_path,
                download_url=download_url
            )
            
            # Create and return a BaktaResultFile object
            now = datetime.now().isoformat()
            return BaktaResultFile(
                id=None,  # ID will be assigned by database
                job_id=job_id,
                file_type=file_type,
                file_path=file_path,
                download_url=download_url,
                downloaded_at=now
            )
            
        except Exception as e:
            error_msg = f"Error saving result file for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def update_job_status(
        self, 
        job_id: str, 
        status: str, 
        message: Optional[str] = None
    ) -> None:
        """
        Update the status of a job.
        
        Args:
            job_id: Job ID
            status: New status
            message: Optional message about status change
        """
        try:
            self.db_manager.update_job_status(job_id, status, message)
        except Exception as e:
            error_msg = f"Error updating status for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
    
    async def get_job_status_history(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get status history for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of status history dictionaries
        """
        try:
            return self.db_manager.get_job_status_history(job_id)
        except Exception as e:
            error_msg = f"Error getting status history for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaException(error_msg)
