#!/usr/bin/env python3
"""
Query interface for Bakta annotations.

This module provides a high-level interface for querying
Bakta annotations with support for filtering, sorting, and pagination.
"""

import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Union

from amr_predictor.bakta.models import BaktaAnnotation, QueryResult
from amr_predictor.bakta.repository import BaktaRepository
from amr_predictor.bakta.dao.query_builder import (
    QueryBuilder, 
    QueryCondition,
    FilterOperator,
    LogicalOperator
)
from amr_predictor.bakta.exceptions import BaktaException

# Configure logging
logger = logging.getLogger("bakta-query")

class SortOrder(str, Enum):
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"

class QueryOptions:
    """
    Options for querying annotations.
    
    This class encapsulates options for filtering, sorting, and paginating
    query results.
    """
    
    def __init__(
        self,
        filters: Optional[List[QueryCondition]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        limit: Optional[int] = None,
        offset: int = 0
    ):
        """
        Initialize query options.
        
        Args:
            filters: List of query conditions for filtering
            sort_by: Field to sort by
            sort_order: Sort order (ASC or DESC)
            limit: Maximum number of results to return
            offset: Number of results to skip
        """
        self.filters = filters or []
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.limit = limit
        self.offset = offset

class QueryInterface:
    """
    Interface for querying Bakta annotations.
    
    This class provides methods for querying annotations with filtering,
    sorting, and pagination.
    """
    
    def __init__(
        self,
        repository: BaktaRepository,
        cache_enabled: bool = True,
        cache_size: int = 100
    ):
        """
        Initialize the query interface.
        
        Args:
            repository: Bakta repository for retrieving annotations
            cache_enabled: Whether to enable result caching
            cache_size: Maximum number of queries to cache
        """
        self.repository = repository
        self.cache_enabled = cache_enabled
        self.cache_size = cache_size
        self._cache = {}
        
        logger.debug("Initialized Bakta query interface")
    
    def get_annotations(
        self,
        job_id: str,
        options: Optional[QueryOptions] = None
    ) -> QueryResult:
        """
        Query annotations with filtering, sorting, and pagination.
        
        Args:
            job_id: ID of the job to query
            options: Query options
        
        Returns:
            Query result with annotations and metadata
            
        Raises:
            BaktaException: If the query fails
        """
        try:
            # Use default options if none provided
            if options is None:
                options = QueryOptions()
            
            # Check cache if enabled
            cache_key = None
            if self.cache_enabled:
                cache_key = self._make_cache_key(job_id, options)
                if cache_key in self._cache:
                    logger.debug(f"Cache hit for query: {cache_key}")
                    return self._cache[cache_key]
            
            # Execute query
            annotations = self.repository.query_annotations(
                job_id=job_id,
                conditions=options.filters,
                sort_by=options.sort_by,
                sort_order=options.sort_order.value,
                limit=options.limit,
                offset=options.offset
            )
            
            # Get total count without pagination
            total = self.repository.count_annotations(
                job_id=job_id,
                conditions=options.filters
            )
            
            # Create result
            result = QueryResult(
                items=annotations,
                total=total,
                offset=options.offset,
                limit=options.limit
            )
            
            # Cache result if enabled
            if self.cache_enabled and cache_key:
                self._cache[cache_key] = result
                # Trim cache if needed
                if len(self._cache) > self.cache_size:
                    self._trim_cache()
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to query annotations: {e}")
            raise BaktaException(f"Failed to query annotations: {e}") from e
    
    def get_annotations_in_range(
        self,
        job_id: str,
        contig: str,
        start: int,
        end: int
    ) -> List[BaktaAnnotation]:
        """
        Get annotations within a genomic range.
        
        Args:
            job_id: ID of the job to query
            contig: Contig name
            start: Start position
            end: End position
        
        Returns:
            List of annotations in the range
            
        Raises:
            BaktaException: If the query fails
        """
        try:
            # Build range query
            builder = QueryBuilder(LogicalOperator.AND)
            builder.add_condition("contig", FilterOperator.EQUALS, contig)
            builder.add_condition("start", FilterOperator.LESS_THAN_OR_EQUAL, end)
            builder.add_condition("end", FilterOperator.GREATER_THAN_OR_EQUAL, start)
            
            # Create options
            options = QueryOptions(filters=builder.conditions)
            
            # Execute query
            result = self.get_annotations(job_id=job_id, options=options)
            return result.items
        
        except Exception as e:
            logger.error(f"Failed to query annotations in range: {e}")
            raise BaktaException(f"Failed to query annotations in range: {e}") from e
    
    def get_feature_types(self, job_id: str) -> List[str]:
        """
        Get all feature types for a job.
        
        Args:
            job_id: ID of the job to query
        
        Returns:
            List of feature types
            
        Raises:
            BaktaException: If the query fails
        """
        try:
            return self.repository.get_feature_types(job_id=job_id)
        
        except Exception as e:
            logger.error(f"Failed to get feature types: {e}")
            raise BaktaException(f"Failed to get feature types: {e}") from e
    
    def count_annotations(
        self,
        job_id: str,
        feature_type: Optional[str] = None
    ) -> int:
        """
        Count annotations for a job.
        
        Args:
            job_id: ID of the job to query
            feature_type: Optional feature type filter
        
        Returns:
            Number of annotations matching the criteria
            
        Raises:
            BaktaException: If the query fails
        """
        try:
            conditions = []
            if feature_type:
                builder = QueryBuilder(LogicalOperator.AND)
                builder.add_condition("feature_type", FilterOperator.EQUALS, feature_type)
                conditions = builder.conditions
            
            return self.repository.count_annotations(
                job_id=job_id,
                conditions=conditions
            )
        
        except Exception as e:
            logger.error(f"Failed to count annotations: {e}")
            raise BaktaException(f"Failed to count annotations: {e}") from e
    
    def _make_cache_key(self, job_id: str, options: QueryOptions) -> str:
        """
        Create a cache key for a query.
        
        Args:
            job_id: Job ID
            options: Query options
        
        Returns:
            Cache key string
        """
        # Create a string representation of filters
        filters_str = "[]"
        if options.filters:
            filters_str = "[" + ",".join(str(f) for f in options.filters) + "]"
        
        # Create cache key
        key = f"{job_id}:{filters_str}:{options.sort_by}:{options.sort_order}:{options.limit}:{options.offset}"
        return key
    
    def _trim_cache(self):
        """
        Trim cache to maximum size by removing oldest entries.
        """
        # Remove oldest entries (first added)
        excess = len(self._cache) - self.cache_size
        if excess > 0:
            keys_to_remove = list(self._cache.keys())[:excess]
            for key in keys_to_remove:
                del self._cache[key]
    
    def clear_cache(self):
        """
        Clear the query cache.
        """
        self._cache = {}
        logger.debug("Cleared query cache")
    
    def disable_cache(self):
        """
        Disable the query cache.
        """
        self.cache_enabled = False
        self.clear_cache()
        logger.debug("Disabled query cache")
    
    def enable_cache(self):
        """
        Enable the query cache.
        """
        self.cache_enabled = True
        logger.debug("Enabled query cache") 