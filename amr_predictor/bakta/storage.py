#!/usr/bin/env python3
"""
Storage service for Bakta result files.

This module provides a storage service for Bakta result files,
handling download, parsing, transformation, and storage.
"""

import os
import logging
import asyncio
import threading
import queue
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

from amr_predictor.bakta.models import (
    BaktaJob, 
    BaktaResultFile, 
    BaktaAnnotation,
    BaktaSequence
)
from amr_predictor.bakta.exceptions import (
    BaktaStorageError, 
    BaktaParserError,
    BaktaException
)
from amr_predictor.bakta.parsers import (
    GFF3Parser,
    TSVParser,
    JSONParser,
    EMBLParser,
    GenBankParser,
    FASTAParser,
    parse_file,
    get_parser_for_file
)
from amr_predictor.bakta.transformers import (
    get_transformer_for_format,
    BaseTransformer
)
from amr_predictor.bakta.repository import BaktaRepository
from amr_predictor.bakta.client import BaktaClient

logger = logging.getLogger("bakta-storage")

# Mapping of file types to file extensions
FILE_TYPE_TO_EXTENSION = {
    "GFF3": "gff3",
    "TSV": "tsv",
    "JSON": "json",
    "EMBL": "embl",
    "GBFF": "gbff",
    "FAA": "faa",
    "FFN": "ffn",
    "FNA": "fna"
}

class BaktaStorageService:
    """
    Storage service for Bakta results.
    
    This class coordinates the download, parsing, transformation,
    and storage of Bakta result files.
    """
    
    def __init__(self, repository: BaktaRepository, client: BaktaClient, 
                 results_dir: Union[str, Path] = None,
                 max_queue_size: int = 100,
                 num_workers: int = 2):
        """
        Initialize the storage service.
        
        Args:
            repository: BaktaRepository instance for database operations
            client: BaktaClient instance for API operations
            results_dir: Directory to store result files
            max_queue_size: Maximum size of the processing queue
            num_workers: Number of worker threads to process the queue
            
        Raises:
            BaktaStorageError: If initialization fails
        """
        self.repository = repository
        self.client = client
        
        if results_dir is None:
            # Default to a directory in user's home
            home_dir = Path.home()
            self.results_dir = home_dir / ".amr_predictor" / "bakta" / "results"
        else:
            self.results_dir = Path(results_dir)
        
        # Create the results directory if it doesn't exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Processing queue
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.num_workers = num_workers
        self.workers = []
        self.running = False
        
        logger.info(f"Initialized BaktaStorageService with results dir: {self.results_dir}")
    
    def start_workers(self):
        """
        Start worker threads for processing the queue.
        
        Raises:
            BaktaStorageError: If workers are already running
        """
        if self.running:
            raise BaktaStorageError("Workers are already running")
        
        self.running = True
        self.workers = []
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._process_queue,
                name=f"BaktaStorage-Worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.num_workers} worker threads")
    
    def stop_workers(self):
        """
        Stop worker threads.
        """
        self.running = False
        
        # Add shutdown markers to the queue
        for _ in range(self.num_workers):
            self.queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)
        
        logger.info("Stopped worker threads")
    
    def _process_queue(self):
        """
        Process items from the queue.
        
        This is the worker thread function.
        """
        while self.running:
            try:
                # Get an item from the queue
                item = self.queue.get(timeout=1.0)
                
                # Check for shutdown marker
                if item is None:
                    break
                
                # Process the item
                try:
                    job_id, file_path, file_type = item
                    self._process_file(job_id, file_path, file_type)
                except Exception as e:
                    logger.error(f"Error processing {item}: {str(e)}")
                
                # Mark the item as done
                self.queue.task_done()
                
            except queue.Empty:
                # Queue is empty, just continue
                continue
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
    
    def download_result_files(self, job_id: str, file_types: List[str] = None) -> Dict[str, str]:
        """
        Download result files for a job.
        
        Args:
            job_id: Job ID
            file_types: List of file types to download, or None for all
            
        Returns:
            Dictionary mapping file types to local file paths
            
        Raises:
            BaktaStorageError: If download fails
        """
        try:
            # Get job from repository
            job = self.repository.get_job(job_id)
            if not job:
                raise BaktaStorageError(f"Job not found: {job_id}")
            
            # Create job results directory
            job_results_dir = self.results_dir / job_id
            job_results_dir.mkdir(parents=True, exist_ok=True)
            
            # Get result files for the job
            result_files_response = self.client.get_job_results(
                job_id=job_id,
                job_secret=job.secret
            )
            
            # Get result files
            result_files = result_files_response.get("ResultFiles", {})
            
            # Filter file types if specified
            if file_types:
                result_files = {k: v for k, v in result_files.items() if k in file_types}
            
            # Download files
            downloaded_files = {}
            
            for file_type, url in result_files.items():
                try:
                    # Determine file extension
                    extension = FILE_TYPE_TO_EXTENSION.get(file_type, file_type.lower())
                    
                    # Create output path
                    output_path = str(job_results_dir / f"{job_id}.{extension}")
                    
                    # Download the file
                    self.client.download_result_file(
                        url=url,
                        output_path=output_path,
                        show_progress=True
                    )
                    
                    # Save result file in repository
                    result_file = self.repository.save_result_file({
                        "job_id": job_id,
                        "file_type": file_type,
                        "file_path": output_path,
                        "download_url": url
                    })
                    
                    downloaded_files[file_type] = output_path
                    logger.info(f"Downloaded {file_type} result to: {output_path}")
                    
                    # Queue file for processing
                    self.queue_file_for_processing(job_id, output_path, file_type)
                    
                except Exception as e:
                    logger.warning(f"Failed to download {file_type} file: {str(e)}")
            
            # Update job status
            if downloaded_files:
                self.repository.update_job_status(job_id, "PROCESSING")
            
            return downloaded_files
            
        except Exception as e:
            msg = f"Failed to download result files for job {job_id}: {str(e)}"
            logger.error(msg)
            raise BaktaStorageError(msg) from e
    
    def queue_file_for_processing(self, job_id: str, file_path: str, file_type: str) -> None:
        """
        Queue a file for processing.
        
        Args:
            job_id: Job ID
            file_path: Path to the file
            file_type: Type of the file
            
        Raises:
            BaktaStorageError: If queueing fails
        """
        try:
            # Start workers if not already running
            if not self.running:
                self.start_workers()
            
            # Add to queue
            self.queue.put((job_id, file_path, file_type))
            logger.info(f"Queued {file_type} file for processing: {file_path}")
            
        except Exception as e:
            msg = f"Failed to queue file for processing: {str(e)}"
            logger.error(msg)
            raise BaktaStorageError(msg) from e
    
    def _process_file(self, job_id: str, file_path: str, file_type: str) -> None:
        """
        Process a single result file.
        
        Args:
            job_id: Job ID
            file_path: Path to the file
            file_type: Type of the file
        """
        logger.info(f"Processing {file_type} file: {file_path}")
        
        try:
            # Parse the file
            parser = get_parser_for_file(file_path)
            parsed_data = parser.parse()
            
            # Get format from parsed data
            format_type = parsed_data.get("format")
            if not format_type:
                # Try to determine format from file_type
                format_type = file_type.lower()
            
            # Transform the data
            transformer = get_transformer_for_format(format_type, job_id)
            transformed_data = transformer.transform(parsed_data)
            
            # Store the data based on type
            if isinstance(transformed_data[0], BaktaAnnotation) if transformed_data else False:
                self.repository.save_annotations(transformed_data)
                logger.info(f"Stored {len(transformed_data)} annotations from {file_path}")
            elif isinstance(transformed_data[0], BaktaSequence) if transformed_data else False:
                self.repository.save_sequences(transformed_data)
                logger.info(f"Stored {len(transformed_data)} sequences from {file_path}")
            else:
                logger.warning(f"Unknown data type from {file_path}: {type(transformed_data[0]) if transformed_data else None}")
            
        except Exception as e:
            logger.error(f"Error processing {file_type} file {file_path}: {str(e)}")
            # Don't propagate the error - we want to continue processing other files
    
    async def async_process_all_files(self, job_id: str) -> Dict[str, int]:
        """
        Process all result files for a job asynchronously.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with counts of processed items by type
            
        Raises:
            BaktaStorageError: If processing fails
        """
        try:
            # Get all result files for the job
            result_files = self.repository.get_result_files(job_id)
            
            # Create tasks for processing each file
            tasks = []
            for result_file in result_files:
                tasks.append(asyncio.create_task(
                    self._async_process_file(
                        job_id=job_id,
                        file_path=result_file.file_path,
                        file_type=result_file.file_type
                    )
                ))
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            counts = {
                "annotations": 0,
                "sequences": 0,
                "errors": 0
            }
            
            for result in results:
                if isinstance(result, Exception):
                    counts["errors"] += 1
                elif isinstance(result, dict):
                    for key, value in result.items():
                        counts[key] = counts.get(key, 0) + value
            
            # Update job status
            if counts["errors"] == 0:
                self.repository.update_job_status(job_id, "PROCESSED")
                logger.info(f"Completed processing all files for job {job_id}")
            else:
                self.repository.update_job_status(
                    job_id, 
                    "PROCESSING_ERROR",
                    f"Encountered {counts['errors']} errors during processing"
                )
                logger.warning(f"Completed processing for job {job_id} with {counts['errors']} errors")
            
            return counts
            
        except Exception as e:
            msg = f"Failed to process all files for job {job_id}: {str(e)}"
            logger.error(msg)
            raise BaktaStorageError(msg) from e
    
    async def _async_process_file(self, job_id: str, file_path: str, file_type: str) -> Dict[str, int]:
        """
        Process a single result file asynchronously.
        
        Args:
            job_id: Job ID
            file_path: Path to the file
            file_type: Type of the file
            
        Returns:
            Dictionary with counts of processed items by type
            
        Raises:
            BaktaStorageError: If processing fails
        """
        logger.info(f"Processing {file_type} file: {file_path}")
        
        try:
            # Parse the file
            parser = get_parser_for_file(file_path)
            parsed_data = parser.parse()
            
            # Get format from parsed data
            format_type = parsed_data.get("format")
            if not format_type:
                # Try to determine format from file_type
                format_type = file_type.lower()
            
            # Transform the data
            transformer = get_transformer_for_format(format_type, job_id)
            transformed_data = transformer.transform(parsed_data)
            
            # Store the data based on type
            counts = {}
            if isinstance(transformed_data[0], BaktaAnnotation) if transformed_data else False:
                await asyncio.to_thread(self.repository.save_annotations, transformed_data)
                counts["annotations"] = len(transformed_data)
                logger.info(f"Stored {counts['annotations']} annotations from {file_path}")
            elif isinstance(transformed_data[0], BaktaSequence) if transformed_data else False:
                await asyncio.to_thread(self.repository.save_sequences, transformed_data)
                counts["sequences"] = len(transformed_data)
                logger.info(f"Stored {counts['sequences']} sequences from {file_path}")
            else:
                logger.warning(f"Unknown data type from {file_path}: {type(transformed_data[0]) if transformed_data else None}")
            
            return counts
            
        except Exception as e:
            msg = f"Error processing {file_type} file {file_path}: {str(e)}"
            logger.error(msg)
            raise BaktaStorageError(msg) from e 