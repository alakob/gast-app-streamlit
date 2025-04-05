#!/usr/bin/env python3
"""
Manager for Bakta annotation functionality.

This module provides a manager for interacting with the Bakta
annotation service API and local database storage.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.repository import BaktaRepository
from amr_predictor.bakta.models import BaktaJob
from amr_predictor.bakta.exceptions import (
    BaktaException,
    BaktaManagerError,
    BaktaApiError,
    BaktaDatabaseError
)

logger = logging.getLogger("bakta-manager")

class BaktaManager:
    """
    Manager for Bakta annotation service interactions.
    
    This class provides a unified interface for interacting with
    the Bakta API and local database storage.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: str = "dev",
        database_path: Optional[str] = None,
        results_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the Bakta manager.
        
        Args:
            api_key: API key for authentication
            environment: Environment to use (dev, staging, prod)
            database_path: Path to the SQLite database
            results_dir: Directory to store downloaded results
        """
        # Initialize client
        self.api_key = api_key or os.environ.get("BAKTA_API_KEY", "")
        self.client = BaktaClient(
            api_key=self.api_key,
            environment=environment
        )
        
        # Initialize repository
        self.database_path = database_path or os.environ.get("BAKTA_DB_PATH", "bakta.db")
        self.repository = BaktaRepository(
            database_path=self.database_path,
            create_tables=True
        )
        
        # Initialize results directory
        self.results_dir = Path(results_dir) if results_dir else Path("bakta_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def create_job(
        self,
        name: str,
        fasta_path: Union[str, Path],
        config: Dict[str, Any]
    ) -> BaktaJob:
        """
        Create a new Bakta job.
        
        Args:
            name: Job name
            fasta_path: Path to the FASTA file
            config: Job configuration
        
        Returns:
            BaktaJob instance
        """
        # This is a mock implementation for testing
        job_id = "mock-job-id"
        secret = "mock-secret"
        
        return BaktaJob(
            id=job_id,
            name=name,
            status="CREATED",
            config=config,
            secret=secret,
            fasta_path=str(fasta_path)
        )
    
    def start_job(self, job_id: str) -> BaktaJob:
        """
        Start a job that has been created.
        
        Args:
            job_id: Job ID
        
        Returns:
            Updated BaktaJob instance
        """
        # This is a mock implementation for testing
        return BaktaJob(
            id=job_id,
            name=f"Mock Job {job_id}",
            status="RUNNING",
            config={},
            secret="mock-secret"
        )
    
    def check_job_status(self, job_id: str) -> BaktaJob:
        """
        Check the status of a job.
        
        Args:
            job_id: Job ID
        
        Returns:
            Updated BaktaJob instance
        """
        # This is a mock implementation for testing
        return BaktaJob(
            id=job_id,
            name=f"Mock Job {job_id}",
            status="COMPLETED",
            config={},
            secret="mock-secret"
        )
    
    def get_jobs(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[BaktaJob]:
        """
        Get jobs.
        
        Args:
            status: Filter by status
            limit: Maximum number of jobs to return
            offset: Offset for pagination
        
        Returns:
            List of BaktaJob instances
        """
        # This is a mock implementation for testing
        return []
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job ID
        
        Returns:
            True if successful
        """
        # This is a mock implementation for testing
        return True 