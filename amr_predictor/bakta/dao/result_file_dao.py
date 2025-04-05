#!/usr/bin/env python3
"""
Result File DAO module for Bakta entities.

This module provides a DAO implementation for BaktaResultFile entities.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from amr_predictor.bakta.dao.base_dao import BaseDAO, DAOError
from amr_predictor.bakta.models import BaktaResultFile
from amr_predictor.bakta.database import BaktaDatabaseError

logger = logging.getLogger("bakta-result-file-dao")

class ResultFileDAO(BaseDAO[BaktaResultFile]):
    """
    Data Access Object for BaktaResultFile entities.
    
    This class provides methods for accessing BaktaResultFile data in the database.
    """
    
    def get_by_id(self, id: int) -> Optional[BaktaResultFile]:
        """
        Get a result file by its ID.
        
        Args:
            id: Result file ID
            
        Returns:
            BaktaResultFile instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the result file
        """
        try:
            result_files = self.db_manager.get_result_files(None)
            for rf_dict in result_files:
                if rf_dict.get('id') == id:
                    return BaktaResultFile.from_dict(rf_dict)
            return None
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_id for result file {id}", e)
    
    def get_all(self) -> List[BaktaResultFile]:
        """
        Get all result files.
        
        Returns:
            List of BaktaResultFile instances
            
        Raises:
            DAOError: If there is an error retrieving result files
        """
        try:
            rf_dicts = self.db_manager.get_result_files(None)
            return [BaktaResultFile.from_dict(rf_dict) for rf_dict in rf_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error("get_all result files", e)
    
    def save(self, result_file: BaktaResultFile) -> BaktaResultFile:
        """
        Save a result file.
        
        Args:
            result_file: BaktaResultFile to save
            
        Returns:
            Saved BaktaResultFile
            
        Raises:
            DAOError: If there is an error saving the result file
        """
        try:
            self.db_manager.save_result_file(
                job_id=result_file.job_id,
                file_type=result_file.file_type,
                file_path=result_file.file_path,
                download_url=result_file.download_url
            )
            
            # Set downloaded_at if not already set
            if not result_file.downloaded_at:
                result_file.downloaded_at = datetime.now().isoformat()
            
            return result_file
        except BaktaDatabaseError as e:
            self._handle_db_error(f"save result file {result_file.file_type}", e)
    
    def update(self, result_file: BaktaResultFile) -> BaktaResultFile:
        """
        Update a result file.
        
        Note: This implementation removes the existing result file and adds
        a new one with the updated data, as SQLite does not support direct updates
        to the result_files table.
        
        Args:
            result_file: BaktaResultFile to update
            
        Returns:
            Updated BaktaResultFile
            
        Raises:
            DAOError: If there is an error updating the result file
        """
        # For simplicity, we're just saving the result file again
        # In a more sophisticated implementation, we would use a transaction
        # to delete the old one and insert the new one
        return self.save(result_file)
    
    def delete(self, id: int) -> bool:
        """
        Delete a result file by its ID.
        
        Note: Not implemented in the current database schema.
        
        Args:
            id: Result file ID
            
        Returns:
            True if result file was deleted, False if result file was not found
            
        Raises:
            DAOError: Always raised since deletion is not supported
        """
        # Not implemented in the current database schema
        raise DAOError("Deleting individual result files is not supported")
    
    def get_by_job_id(self, job_id: str) -> List[BaktaResultFile]:
        """
        Get result files for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaResultFile instances
            
        Raises:
            DAOError: If there is an error retrieving the result files
        """
        try:
            rf_dicts = self.db_manager.get_result_files(job_id)
            return [BaktaResultFile.from_dict(rf_dict) for rf_dict in rf_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_job_id for job {job_id}", e)
    
    def get_by_file_type(self, job_id: str, file_type: str) -> Optional[BaktaResultFile]:
        """
        Get a result file by its type.
        
        Args:
            job_id: Job ID
            file_type: File type
            
        Returns:
            BaktaResultFile instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the result file
        """
        try:
            rf_dicts = self.db_manager.get_result_files(job_id, file_type)
            if not rf_dicts:
                return None
            return BaktaResultFile.from_dict(rf_dicts[0])
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_file_type for type {file_type}", e)
    
    def get_file_path(self, job_id: str, file_type: str) -> Optional[str]:
        """
        Get the file path for a result file.
        
        Args:
            job_id: Job ID
            file_type: File type
            
        Returns:
            File path or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the file path
        """
        result_file = self.get_by_file_type(job_id, file_type)
        if result_file is None:
            return None
        return result_file.file_path 