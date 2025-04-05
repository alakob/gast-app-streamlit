#!/usr/bin/env python3
"""
Bakta genome annotation service integration module.

This module provides an interface for the Bakta bacterial genome
annotation service, allowing for automated annotation submission,
result retrieval, and database storage.
"""

import logging
import os
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.environ.get("BAKTA_DEBUG") else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Import the unified interface for easy access
from amr_predictor.bakta.unified_interface import (
    BaktaUnifiedInterface,
    create_bakta_interface
)

# Import query related classes for convenience
from amr_predictor.bakta.query_interface import (
    QueryOptions,
    QueryResult,
    SortOrder
)

from amr_predictor.bakta.dao.query_builder import (
    FilterOperator,
    LogicalOperator,
    QueryBuilder,
    QueryCondition
)

# Import main model classes
from amr_predictor.bakta.models import (
    BaktaAnnotation,
    BaktaJob,
    BaktaSequence,
    BaktaResultFile,
    BaktaJobStatusHistory,
    BaktaResult,
    QueryResult,
    QueryOptions,
    QueryBuilder,
    Filter,
    FilterOperator
)

# Import exceptions
from amr_predictor.bakta.exceptions import (
    BaktaException,
    BaktaApiError,
    BaktaDatabaseError,
    BaktaParseError
)

# Import BaktaClient and BaktaRepository
from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.repository import BaktaRepository

# Define package version
__version__ = "0.5.0"

# Define what's available when importing the package
__all__ = [
    # Main interfaces
    "BaktaUnifiedInterface",
    "create_bakta_interface",
    
    # Query related
    "QueryOptions",
    "QueryResult",
    "SortOrder",
    "FilterOperator",
    "LogicalOperator",
    "QueryBuilder",
    "QueryCondition",
    
    # Models
    "BaktaAnnotation",
    "BaktaJob",
    "BaktaSequence",
    "BaktaResultFile",
    "BaktaJobStatusHistory",
    "BaktaResult",
    
    # Exceptions
    "BaktaException",
    "BaktaApiError",
    "BaktaDatabaseError",
    "BaktaParseError",
    
    # BaktaClient and BaktaRepository
    "BaktaClient",
    "BaktaRepository",
    
    # Version
    "__version__"
]

# Convenience function to get the interface
def get_interface(**kwargs) -> BaktaUnifiedInterface:
    """
    Get a configured Bakta interface.
    
    A convenience function that looks for configuration in environment
    variables and creates a properly configured interface.
    
    Args:
        **kwargs: Override any configuration parameters
        
    Returns:
        Configured BaktaUnifiedInterface instance
    """
    # Get API key from environment variable if not provided
    api_key = kwargs.get("api_key")
    if api_key is None:
        api_key = os.environ.get("BAKTA_API_KEY")
    
    # Get database path from environment variable if not provided
    database_path = kwargs.get("database_path")
    if database_path is None:
        database_path = os.environ.get("BAKTA_DATABASE_PATH")
    
    # Get environment from environment variable if not provided
    environment = kwargs.get("environment")
    if environment is None:
        environment = os.environ.get("BAKTA_ENVIRONMENT", "prod")
    
    # Create and return the interface
    return create_bakta_interface(
        api_key=api_key,
        database_path=database_path,
        environment=environment,
        cache_enabled=kwargs.get("cache_enabled", True)
    ) 