#!/usr/bin/env python3
"""
Periodic status checking service for Bakta jobs.

This module provides a background service that periodically checks the status
of Bakta annotation jobs and updates the database accordingly.
"""

import os
import asyncio
import logging
import time
import signal
import sys
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta

from dotenv import load_dotenv

from amr_predictor.bakta.job_manager import BaktaJobManager
from amr_predictor.bakta.exceptions import BaktaException, BaktaJobError
from amr_predictor.bakta.models import BaktaJob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bakta-status-service")

# Load environment variables
load_dotenv()

class BaktaStatusService:
    """
    Service for periodically checking the status of Bakta jobs.
    
    This service runs in the background and polls the Bakta API for job status
    updates, storing the results in the database.
    """
    
    def __init__(
        self,
        job_manager: Optional[BaktaJobManager] = None,
        check_interval: int = 60,
        environment: str = 'prod'
    ):
        """
        Initialize the status service.
        
        Args:
            job_manager: BaktaJobManager instance (optional)
            check_interval: Interval in seconds between status checks
            environment: Environment to use (dev, test, prod)
        """
        self.environment = environment
        self.check_interval = check_interval
        
        # Create job manager if not provided
        if job_manager is None:
            self.job_manager = BaktaJobManager(environment=environment)
        else:
            self.job_manager = job_manager
            
        # Flag to control the service loop
        self.running = False
        self.loop = None
        
        # Set to keep track of jobs being processed to avoid duplicates
        self.processing_jobs: Set[str] = set()
        
        logger.info(f"Initialized Bakta status service with {check_interval}s interval")
    
    async def start(self):
        """
        Start the status checking service.
        
        This method will run indefinitely until stop() is called.
        """
        if self.running:
            logger.warning("Service already running")
            return
            
        self.running = True
        self.loop = asyncio.get_event_loop()
        
        # Set up signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self.stop(s))
            )
        
        logger.info("Starting Bakta status service")
        
        try:
            while self.running:
                try:
                    # Check for jobs that need status updates
                    await self.check_job_statuses()
                    
                    # Wait for the next interval
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in status check loop: {str(e)}")
                    # Wait a bit before retrying to avoid rapid error loops
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            logger.info("Status service cancelled")
        finally:
            self.running = False
            logger.info("Bakta status service stopped")
    
    async def stop(self, signal=None):
        """
        Stop the status checking service.
        
        Args:
            signal: Optional signal that triggered the stop
        """
        if signal:
            logger.info(f"Received signal {signal.name}, shutting down")
            
        self.running = False
        
        # Give any pending tasks a chance to complete
        pending = asyncio.all_tasks(self.loop)
        current_task = asyncio.current_task(self.loop)
        
        if current_task:
            pending.discard(current_task)
            
        if pending:
            logger.info(f"Waiting for {len(pending)} pending tasks to complete")
            await asyncio.gather(*pending, return_exceptions=True)
            
        logger.info("Shutdown complete")
    
    async def check_job_statuses(self):
        """
        Check the status of all non-terminal jobs.
        
        This method will query for all jobs that are not in a terminal state
        (COMPLETED, FAILED, EXPIRED) and check their status.
        """
        try:
            # Get all non-terminal jobs
            pending_jobs = await self.get_pending_jobs()
            if not pending_jobs:
                logger.debug("No pending jobs to check")
                return
                
            logger.info(f"Checking status of {len(pending_jobs)} pending jobs")
            
            # Check each job's status
            for job in pending_jobs:
                # Skip if already being processed
                if job.id in self.processing_jobs:
                    logger.debug(f"Job {job.id} is already being processed, skipping")
                    continue
                    
                # Add to processing set
                self.processing_jobs.add(job.id)
                
                try:
                    # Check status
                    logger.debug(f"Checking status of job {job.id} (current: {job.status})")
                    status = await self.job_manager.get_job_status(job.id)
                    
                    # If job is now completed, try to download results
                    if status == "COMPLETED":
                        logger.info(f"Job {job.id} is now complete, downloading results")
                        asyncio.create_task(self.download_job_results(job.id))
                        
                except Exception as e:
                    logger.error(f"Error checking status for job {job.id}: {str(e)}")
                finally:
                    # Remove from processing set
                    self.processing_jobs.discard(job.id)
                    
        except Exception as e:
            logger.error(f"Error checking job statuses: {str(e)}")
    
    async def get_pending_jobs(self) -> List[BaktaJob]:
        """
        Get all jobs that are not in a terminal state.
        
        Returns:
            List of pending jobs
        """
        # Get running jobs
        running_jobs = await self.job_manager.list_jobs(status="RUNNING")
        
        # Get queued jobs
        queued_jobs = await self.job_manager.list_jobs(status="QUEUED")
        
        # Get created jobs
        created_jobs = await self.job_manager.list_jobs(status="CREATED")
        
        # Combine all pending jobs
        pending_jobs = running_jobs + queued_jobs + created_jobs
        
        return pending_jobs
    
    async def download_job_results(self, job_id: str):
        """
        Download results for a completed job.
        
        Args:
            job_id: ID of the completed job
        """
        try:
            logger.info(f"Downloading results for job {job_id}")
            
            # Download results
            result_files = await self.job_manager.download_results(job_id)
            
            if not result_files:
                logger.warning(f"No result files downloaded for job {job_id}")
                return
                
            logger.info(f"Downloaded {len(result_files)} result files for job {job_id}")
            
            # Import annotations if GFF3 and JSON files are available
            gff_file = result_files.get("gff3")
            json_file = result_files.get("json")
            
            if gff_file and json_file:
                logger.info(f"Importing annotations for job {job_id}")
                annotation_count = await self.job_manager.import_annotations(
                    job_id=job_id,
                    gff_file=gff_file,
                    json_file=json_file
                )
                logger.info(f"Imported {annotation_count} annotations for job {job_id}")
            else:
                logger.warning(f"Missing required files for annotation import: GFF3={bool(gff_file)}, JSON={bool(json_file)}")
                
        except Exception as e:
            logger.error(f"Error downloading results for job {job_id}: {str(e)}")

async def run_service():
    """
    Run the status service.
    
    This function is the main entry point for running the service from the command line.
    """
    # Get environment from command line or environment variable
    environment = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ENVIRONMENT", "prod")
    
    # Get check interval from environment or use default
    check_interval = int(os.getenv("BAKTA_STATUS_CHECK_INTERVAL", "60"))
    
    # Create and start the service
    service = BaktaStatusService(
        check_interval=check_interval,
        environment=environment
    )
    
    await service.start()

if __name__ == "__main__":
    asyncio.run(run_service())
