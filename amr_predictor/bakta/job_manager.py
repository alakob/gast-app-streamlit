#!/usr/bin/env python3
"""
Job manager for Bakta annotation jobs.

This module provides a job manager for submitting, monitoring, and
retrieving results from Bakta annotation jobs.
"""

import os
import json
import logging
import time
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import aiohttp
import aiofiles

# Import updated Bakta components
from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.repository_postgres import BaktaRepository
from amr_predictor.bakta.database_postgres import DatabaseManager
from amr_predictor.bakta.config import get_bakta_api_config
from amr_predictor.bakta.models import (
    BaktaJob,
    BaktaSequence,
    BaktaAnnotation,
    BaktaResultFile
)
from amr_predictor.bakta.exceptions import (
    BaktaException,
    BaktaJobError,
    BaktaApiError,
    BaktaDatabaseError,
    BaktaAuthError,
    BaktaTimeoutError
)

# Import environment configuration utilities
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("bakta-job-manager")

# Load environment variables
load_dotenv()

class BaktaJobManager:
    """
    Manager for Bakta annotation jobs.
    
    This class provides methods for submitting jobs to Bakta,
    checking job status, retrieving results, and storing results
    in a PostgreSQL database.
    """
    
    def __init__(
        self,
        client: Optional[BaktaClient] = None,
        repository: Optional[BaktaRepository] = None,
        results_dir: Optional[Union[str, Path]] = None,
        environment: str = 'prod',
        db_manager: Optional[DatabaseManager] = None
    ):
        """
        Initialize the job manager.
        
        Args:
            client: BaktaClient instance for API interaction (optional)
            repository: BaktaRepository instance for database storage (optional)
            results_dir: Directory to store downloaded results
            environment: Environment to use (dev, test, prod)
            db_manager: Database manager instance (optional)
        """
        self.environment = environment
        
        # Create client if not provided
        if client is None:
            # Get API configuration from environment
            api_config = get_bakta_api_config(environment)
            self.client = BaktaClient(
                api_url=api_config['url'],
                api_key=api_config['api_key']
            )
        else:
            self.client = client
            
        # Create database manager if not provided
        if db_manager is None:
            self.db_manager = DatabaseManager(environment=environment)
        else:
            self.db_manager = db_manager
            
        # Create repository if not provided
        if repository is None:
            self.repository = BaktaRepository(
                db_manager=self.db_manager,
                environment=environment
            )
        else:
            self.repository = repository
        
        # Set up results directory
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            # Use environment variable or default
            env_results_dir = os.getenv('BAKTA_RESULTS_DIR', '/app/results/bakta')
            self.results_dir = Path(env_results_dir)
        
        # Ensure the directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized Bakta job manager for environment: {environment}")
    
    async def submit_job(
        self,
        job_name: str,
        fasta_path: Union[str, Path],
        config: Dict[str, Any]
    ) -> BaktaJob:
        """
        Submit a new annotation job to Bakta.
        
        Args:
            job_name: Name for the job
            fasta_path: Path to the FASTA file
            config: Job configuration parameters
        
        Returns:
            BaktaJob instance with job details
        
        Raises:
            BaktaJobError: If job submission fails
            BaktaApiError: If there's an API error
            BaktaAuthError: If authentication fails
        """
        try:
            fasta_path = Path(fasta_path)
            if not fasta_path.exists():
                raise BaktaJobError(f"FASTA file not found: {fasta_path}")
            
            # Log environment and client configuration
            logger.info(f"Environment: {self.environment}")
            logger.info(f"Using Bakta client: {self.client.__class__.__name__}")
            logger.info(f"Bakta API URL: {self.client.base_url}")
            
            # Submit job to Bakta API
            logger.info(f"Submitting job '{job_name}' to Bakta API")
            logger.info(f"FASTA path: {fasta_path}")
            logger.info(f"Config: {json.dumps(config, indent=2)}")
            
            job_data = await self.client.submit_job(str(fasta_path), config)
            logger.info(f"Received job data: {json.dumps(job_data, indent=2)}")
            
            # Extract job details
            job_id = job_data.get('id')
            job_secret = job_data.get('secret')
            if not job_id or not job_secret:
                logger.error("Job data missing required fields: id or secret")
                raise BaktaJobError("Invalid job data returned from API")
            
            # We're always using real API mode now
            logger.info(f"Using real Bakta API with job ID: {job_id}")
            
            # Create job in database
            job = BaktaJob(
                id=job_id,
                name=job_name,
                status="CREATED",
                config=config,
                secret=job_secret,
                fasta_path=str(fasta_path),
                created_at=datetime.now().isoformat()
            )
            
            # Save job to database
            await self.repository.save_job(job)
            logger.info(f"Job saved to database: {job_id}")
            
            # Parse and save sequences from the FASTA file
            seq_count = await self._save_sequences_from_fasta(job_id, fasta_path)
            logger.info(f"Saved {seq_count} sequences from FASTA file")
            
            return job
            
        except (BaktaApiError, BaktaAuthError) as e:
            # API or authentication errors
            error_msg = f"API error while submitting job: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
        except Exception as e:
            # Other unexpected errors
            error_msg = f"Error submitting job: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def _save_sequences_from_fasta(self, job_id: str, fasta_path: Path) -> int:
        """
        Parse FASTA file and save sequences to database.
        
        Args:
            job_id: Job ID
            fasta_path: Path to FASTA file
            
        Returns:
            Number of sequences saved
        """
        try:
            sequences = []
            current_header = None
            current_sequence = []
            
            # Parse FASTA file
            async with aiofiles.open(fasta_path, 'r') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith('>'):
                        # Save previous sequence if any
                        if current_header and current_sequence:
                            sequences.append({
                                'header': current_header,
                                'sequence': ''.join(current_sequence)
                            })
                            
                        # Start new sequence
                        current_header = line[1:]  # Remove '>' prefix
                        current_sequence = []
                    else:
                        # Add to current sequence
                        current_sequence.append(line)
            
            # Save the last sequence
            if current_header and current_sequence:
                sequences.append({
                    'header': current_header,
                    'sequence': ''.join(current_sequence)
                })
                
            # Save sequences to database
            if sequences:
                await self.repository.save_sequences(job_id, sequences)
                logger.info(f"Saved {len(sequences)} sequences for job {job_id}")
                return len(sequences)
            else:
                logger.warning(f"No sequences found in FASTA file: {fasta_path}")
                return 0
                
        except Exception as e:
            error_msg = f"Error parsing FASTA file {fasta_path}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def get_job_status(self, job_id: str) -> str:
        """
        Get the status of a job from the Bakta API and update the database.
        
        Args:
            job_id: Job ID
        
        Returns:
            Job status string
            
        Raises:
            BaktaJobError: If the job status cannot be retrieved
        """
        try:
            # Get job from database to get the secret
            job = await self.repository.get_job(job_id)
            if not job:
                raise BaktaJobError(f"Job not found: {job_id}")
                
            # Check status with Bakta API
            status_data = await self.client.get_job_status(job_id, job.secret)
            
            # Extract status
            api_status = status_data.get('status', 'UNKNOWN')
            
            # Map API status to our status enum
            status_map = {
                'pending': 'QUEUED',
                'running': 'RUNNING',
                'finished': 'COMPLETED',
                'failed': 'FAILED',
                'canceled': 'FAILED',
                'expired': 'EXPIRED'
            }
            
            status = status_map.get(api_status.lower(), 'UNKNOWN')
            
            # Update database if status has changed
            if status != job.status:
                message = f"Status changed from {job.status} to {status}"
                await self.repository.update_job_status(job_id, status, message)
                logger.info(f"Updated job {job_id} status to {status}")
            
            return status
            
        except BaktaApiError as e:
            # Log error but don't raise, to allow polling to continue
            logger.warning(f"API error while checking job status: {str(e)}")
            return job.status if job else "UNKNOWN"
            
        except Exception as e:
            error_msg = f"Error checking job status: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def get_job(self, job_id: str) -> Optional[BaktaJob]:
        """
        Get job details from the database and update status if needed.
        
        Args:
            job_id: Job ID
        
        Returns:
            BaktaJob instance or None if not found
            
        Raises:
            BaktaJobError: If there's an error retrieving the job
        """
        try:
            # Get job from database
            job = await self.repository.get_job(job_id)
            if not job:
                logger.warning(f"Job not found: {job_id}")
                return None
                
            # Update status from API if job is not in a terminal state
            if job.status not in ["COMPLETED", "FAILED", "EXPIRED"]:
                # Don't await to avoid slowing down the response
                # The status will be updated in the background
                asyncio.create_task(self.get_job_status(job_id))
            
            return job
            
        except Exception as e:
            error_msg = f"Error retrieving job: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def download_results(
        self,
        job_id: str,
        output_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, str]:
        """
        Download results for a completed job from the Bakta API.
        
        Args:
            job_id: Job ID
            output_dir: Directory to save the downloaded files
        
        Returns:
            Dictionary mapping file types to file paths
            
        Raises:
            BaktaJobError: If job is not complete or results cannot be downloaded
            BaktaApiError: If there's an API error
        """
        try:
            # Get job from database to get the secret
            job = await self.repository.get_job(job_id)
            if not job:
                raise BaktaJobError(f"Job not found: {job_id}")
                
            # Check if job is completed
            if job.status != "COMPLETED":
                # Update status from API
                current_status = await self.get_job_status(job_id)
                if current_status != "COMPLETED":
                    raise BaktaJobError(
                        f"Cannot download results for job {job_id} with status {current_status}. "
                        f"Job must be COMPLETED."
                    )
            
            # Set up output directory
            output_dir = Path(output_dir) if output_dir else self.results_dir / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading results for job {job_id} to {output_dir}")
            
            # Get download URLs from Bakta API
            download_data = await self.client.get_job_results(job_id, job.secret)
            
            # Ensure the download data is valid
            if not download_data or not isinstance(download_data, dict):
                raise BaktaJobError(f"Invalid download data for job {job_id}")
                
            # Download each file
            result_files = {}
            for file_type, url in download_data.items():
                if not url or not isinstance(url, str):
                    logger.warning(f"Skipping invalid URL for {file_type}: {url}")
                    continue
                    
                # Determine file extension and name
                ext = "txt"  # Default extension
                if file_type == "gff3":
                    ext = "gff3"
                elif file_type == "json":
                    ext = "json"
                elif file_type == "gbff":
                    ext = "gbk"
                elif file_type == "faa":
                    ext = "faa"
                elif file_type == "ffn":
                    ext = "ffn"
                elif file_type == "fna":
                    ext = "fna"
                elif file_type == "tsv":
                    ext = "tsv"
                
                # Set output file path
                file_path = output_dir / f"{job_id}.{ext}"
                
                # Download the file
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            if response.status == 200:
                                content = await response.read()
                                async with aiofiles.open(file_path, 'wb') as f:
                                    await f.write(content)
                                    
                                # Save file reference to database
                                await self.repository.save_result_file(
                                    job_id=job_id,
                                    file_type=file_type,
                                    file_path=str(file_path),
                                    download_url=url
                                )
                                
                                result_files[file_type] = str(file_path)
                                logger.info(f"Downloaded {file_type} to {file_path}")
                            else:
                                error_msg = f"Failed to download {file_type}: HTTP {response.status}"
                                logger.error(error_msg)
                except Exception as e:
                    logger.error(f"Error downloading {file_type}: {str(e)}")
            
            if not result_files:
                raise BaktaJobError(f"No result files could be downloaded for job {job_id}")
                
            return result_files
            
        except BaktaApiError as e:
            error_msg = f"API error while downloading results: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error downloading results: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def import_annotations(
        self,
        job_id: str,
        gff_file: Union[str, Path],
        json_file: Union[str, Path]
    ) -> int:
        """
        Import annotations from GFF3 and JSON result files.
        
        Args:
            job_id: Job ID
            gff_file: Path to the GFF3 file
            json_file: Path to the JSON file
        
        Returns:
            Number of imported annotations
            
        Raises:
            BaktaJobError: If the annotations cannot be imported
        """
        try:
            gff_path = Path(gff_file)
            json_path = Path(json_file)
            
            # Check if files exist
            if not gff_path.exists():
                raise BaktaJobError(f"GFF3 file not found: {gff_path}")
                
            if not json_path.exists():
                raise BaktaJobError(f"JSON file not found: {json_path}")
                
            # Parse GFF3 file
            gff_annotations = []
            async with aiofiles.open(gff_path, 'r') as f:
                async for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Parse GFF3 line
                    fields = line.split('\t')
                    if len(fields) != 9:
                        logger.warning(f"Invalid GFF3 line: {line}")
                        continue
                        
                    # Extract basic fields
                    seqid, source, type, start, end, score, strand, phase, attributes_str = fields
                    
                    # Parse attributes
                    attributes = {}
                    for attr in attributes_str.split(';'):
                        if not attr:
                            continue
                        key_value = attr.split('=')
                        if len(key_value) == 2:
                            key, value = key_value
                            attributes[key] = value
                    
                    # Create annotation
                    annotation = {
                        'seqid': seqid,
                        'source': source,
                        'type': type,
                        'start': int(start),
                        'end': int(end),
                        'score': score if score != '.' else None,
                        'strand': strand,
                        'phase': phase if phase != '.' else None,
                        'attributes': attributes
                    }
                    
                    gff_annotations.append(annotation)
            
            # Parse JSON file
            async with aiofiles.open(json_path, 'r') as f:
                content = await f.read()
                json_data = json.loads(content)
            
            # Import annotations
            count = await self.repository.import_results(job_id, gff_annotations, json_data)
            logger.info(f"Imported {count} annotations for job {job_id}")
            
            return count
            
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON file: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error importing annotations: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def list_jobs(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[BaktaJob]:
        """
        List jobs from the database.
        
        Args:
            status: Filter by status
            limit: Maximum number of jobs to return
            offset: Offset for pagination
        
        Returns:
            List of jobs
            
        Raises:
            BaktaJobError: If there's an error retrieving jobs
        """
        try:
            return await self.repository.get_jobs(status=status, limit=limit, offset=offset)
            
        except Exception as e:
            error_msg = f"Error listing jobs: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the database and optionally the API.
        
        Args:
            job_id: Job ID
        
        Returns:
            True if successful, False if job was not found
            
        Raises:
            BaktaJobError: If there's an error deleting the job
        """
        try:
            # Get job from database to get the secret
            job = await self.repository.get_job(job_id)
            if not job:
                logger.warning(f"Job not found for deletion: {job_id}")
                return False
                
            # Try to delete from API (but don't fail if it doesn't work)
            try:
                await self.client.delete_job(job_id, job.secret)
                logger.info(f"Deleted job {job_id} from API")
            except BaktaApiError as e:
                # Log but continue - we still want to delete from database
                logger.warning(f"Failed to delete job {job_id} from API: {str(e)}")
            
            # Delete from database
            success = await self.repository.delete_job(job_id)
            if success:
                logger.info(f"Deleted job {job_id} from database")
            
            return success
            
        except Exception as e:
            error_msg = f"Error deleting job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
    async def get_job_result_files(self, job_id: str) -> List[BaktaResultFile]:
        """
        Get result files for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of result files
            
        Raises:
            BaktaJobError: If there's an error retrieving result files
        """
        try:
            return await self.repository.get_result_files(job_id)
            
        except Exception as e:
            error_msg = f"Error getting result files for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
    async def get_annotations(
        self, 
        job_id: str, 
        feature_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[BaktaAnnotation]:
        """
        Get annotations for a job.
        
        Args:
            job_id: Job ID
            feature_type: Optional feature type filter
            limit: Maximum number of annotations to return
            offset: Offset for pagination
            
        Returns:
            List of annotations
            
        Raises:
            BaktaJobError: If there's an error retrieving annotations
        """
        try:
            conditions = []
            if feature_type:
                conditions.append(["feature_type", "eq", feature_type])
                
            return await self.repository.query_annotations(
                job_id=job_id,
                conditions=conditions,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            error_msg = f"Error getting annotations for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
    async def get_annotation_count(
        self, 
        job_id: str, 
        feature_type: Optional[str] = None
    ) -> int:
        """
        Get annotation count for a job.
        
        Args:
            job_id: Job ID
            feature_type: Optional feature type filter
            
        Returns:
            Number of annotations
            
        Raises:
            BaktaJobError: If there's an error retrieving annotation count
        """
        try:
            conditions = []
            if feature_type:
                conditions.append(["feature_type", "eq", feature_type])
                
            return await self.repository.count_annotations(job_id, conditions)
            
        except Exception as e:
            error_msg = f"Error getting annotation count for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e
            
    async def get_feature_types(self, job_id: str) -> List[str]:
        """
        Get all feature types for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of feature types
            
        Raises:
            BaktaJobError: If there's an error retrieving feature types
        """
        try:
            return await self.repository.get_feature_types(job_id)
            
        except Exception as e:
            error_msg = f"Error getting feature types for job {job_id}: {str(e)}"
            logger.error(error_msg)
            raise BaktaJobError(error_msg) from e 