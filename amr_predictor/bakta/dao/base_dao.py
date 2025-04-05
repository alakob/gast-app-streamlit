#!/usr/bin/env python3
"""
Base DAO module for Bakta entities.

This module defines the base DAO interface for all Bakta entities.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generic, TypeVar, Union
from pathlib import Path

from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError
from amr_predictor.bakta.exceptions import BaktaException

logger = logging.getLogger("bakta-dao")

# Generic type for entity models
T = TypeVar('T')

class DAOError(BaktaException):
    """Exception raised for DAO errors."""
    pass

class BaseDAO(Generic[T], ABC):
    """
    Base Data Access Object interface for Bakta entities.
    
    This abstract class defines the common interface for all DAOs.
    """
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the DAO with a database manager.
        
        Args:
            db_path: Path to the SQLite database file. If None, a default
                   path will be used in the user's home directory.
        """
        self.db_manager = DatabaseManager(db_path)
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the entity
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """
        Get all entities.
        
        Returns:
            List of entity instances
            
        Raises:
            DAOError: If there is an error retrieving the entities
        """
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Save an entity.
        
        Args:
            entity: Entity to save
            
        Returns:
            Saved entity with any database-generated values
            
        Raises:
            DAOError: If there is an error saving the entity
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Entity to update
            
        Returns:
            Updated entity
            
        Raises:
            DAOError: If there is an error updating the entity
        """
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        """
        Delete an entity by its ID.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity was deleted, False if entity was not found
            
        Raises:
            DAOError: If there is an error deleting the entity
        """
        pass
    
    def _handle_db_error(self, operation: str, error: Exception) -> None:
        """
        Handle database errors by logging and raising a DAOError.
        
        Args:
            operation: Description of the operation being performed
            error: The original error
            
        Raises:
            DAOError: Always raised with the original error as the cause
        """
        error_msg = f"DAO error during {operation}: {str(error)}"
        logger.error(error_msg)
        raise DAOError(error_msg) from error 