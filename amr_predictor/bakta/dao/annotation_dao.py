#!/usr/bin/env python3
"""
Annotation DAO module for Bakta entities.

This module provides a DAO implementation for BaktaAnnotation entities.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Set
from pathlib import Path

from amr_predictor.bakta.dao.base_dao import BaseDAO, DAOError
from amr_predictor.bakta.models import BaktaAnnotation
from amr_predictor.bakta.database import BaktaDatabaseError
from amr_predictor.bakta.dao.cache_manager import cached
from amr_predictor.bakta.dao.batch_processor import BatchProcessor, process_in_batches

logger = logging.getLogger("bakta-annotation-dao")

class AnnotationDAO(BaseDAO[BaktaAnnotation]):
    """
    Data Access Object for BaktaAnnotation entities.
    
    This class provides methods for accessing BaktaAnnotation data in the database.
    """
    
    def __init__(self, db_path=None, batch_size: int = 100):
        """
        Initialize the DAO with a database manager.
        
        Args:
            db_path: Path to the SQLite database file. If None, a default
                   path will be used in the user's home directory.
            batch_size: Default batch size for batch operations
        """
        super().__init__(db_path)
        self.batch_processor = BatchProcessor[BaktaAnnotation, List[BaktaAnnotation]](batch_size=batch_size)
        self.batch_size = batch_size
    
    def get_by_id(self, id: int) -> Optional[BaktaAnnotation]:
        """
        Get an annotation by its ID.
        
        Args:
            id: Annotation ID
            
        Returns:
            BaktaAnnotation instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the annotation
        """
        try:
            annotations = self.db_manager.get_annotations(None)
            for ann_dict in annotations:
                if ann_dict.get('id') == id:
                    return BaktaAnnotation.from_dict(ann_dict)
            return None
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_id for annotation {id}", e)
    
    def get_all(self) -> List[BaktaAnnotation]:
        """
        Get all annotations.
        
        Returns:
            List of BaktaAnnotation instances
            
        Raises:
            DAOError: If there is an error retrieving annotations
        """
        try:
            annotation_dicts = self.db_manager.get_annotations(None)
            return [BaktaAnnotation.from_dict(ann_dict) for ann_dict in annotation_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error("get_all annotations", e)
    
    def save(self, annotation: BaktaAnnotation) -> BaktaAnnotation:
        """
        Save an annotation.
        
        Args:
            annotation: BaktaAnnotation to save
            
        Returns:
            Saved BaktaAnnotation
            
        Raises:
            DAOError: If there is an error saving the annotation
        """
        try:
            self.db_manager.save_annotations(annotation.job_id, [annotation.to_dict()])
            return annotation
        except BaktaDatabaseError as e:
            self._handle_db_error(f"save annotation {annotation.feature_id}", e)
    
    def save_batch(self, annotations: List[BaktaAnnotation]) -> List[BaktaAnnotation]:
        """
        Save multiple annotations in a batch.
        
        Args:
            annotations: List of BaktaAnnotation instances to save
            
        Returns:
            List of saved BaktaAnnotation instances
            
        Raises:
            DAOError: If there is an error saving the annotations
        """
        if not annotations:
            return []
        
        try:
            # Process in optimized batches
            if len(annotations) > self.batch_size:
                job_id = annotations[0].job_id
                
                # Define a batch processor function
                def process_batch(batch: List[BaktaAnnotation]) -> None:
                    batch_dicts = [ann.to_dict() for ann in batch]
                    self.db_manager.save_annotations(job_id, batch_dicts)
                
                # Process using batch processor
                result = process_in_batches(
                    annotations, 
                    process_batch, 
                    batch_size=self.batch_size
                )
                
                if not result["success"]:
                    logger.warning(f"Some batches failed during annotation save: {result['errors']}")
                
                return annotations
            else:
                # For smaller batches, use the regular approach
                job_id = annotations[0].job_id
                annotation_dicts = [ann.to_dict() for ann in annotations]
                self.db_manager.save_annotations(job_id, annotation_dicts)
                return annotations
        except (BaktaDatabaseError, IndexError) as e:
            self._handle_db_error(f"save_batch annotations", e)
    
    def update(self, annotation: BaktaAnnotation) -> BaktaAnnotation:
        """
        Update an annotation.
        
        Note: This implementation removes the existing annotation and adds
        a new one with the updated data, as SQLite does not support direct updates
        to the annotations table.
        
        Args:
            annotation: BaktaAnnotation to update
            
        Returns:
            Updated BaktaAnnotation
            
        Raises:
            DAOError: If there is an error updating the annotation
        """
        # For simplicity, we're just saving the annotation again
        # In a more sophisticated implementation, we would use a transaction
        # to delete the old one and insert the new one
        return self.save(annotation)
    
    def delete(self, id: int) -> bool:
        """
        Delete an annotation by its ID.
        
        Note: Not implemented in the current database schema.
        
        Args:
            id: Annotation ID
            
        Returns:
            True if annotation was deleted, False if annotation was not found
            
        Raises:
            DAOError: Always raised since deletion is not supported
        """
        # Not implemented in the current database schema
        raise DAOError("Deleting individual annotations is not supported")
    
    @cached(ttl_seconds=300, key_prefix="annotations")
    def get_by_job_id(self, job_id: str) -> List[BaktaAnnotation]:
        """
        Get annotations for a job.
        
        This method is cached for 5 minutes to improve performance.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaAnnotation instances
            
        Raises:
            DAOError: If there is an error retrieving the annotations
        """
        try:
            annotation_dicts = self.db_manager.get_annotations(job_id)
            return [BaktaAnnotation.from_dict(ann_dict) for ann_dict in annotation_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_job_id for job {job_id}", e)
    
    @cached(ttl_seconds=300, key_prefix="annotations_by_feature_type")
    def get_by_feature_type(self, job_id: str, feature_type: str) -> List[BaktaAnnotation]:
        """
        Get annotations by feature type.
        
        This method is cached for 5 minutes to improve performance.
        
        Args:
            job_id: Job ID
            feature_type: Feature type
            
        Returns:
            List of BaktaAnnotation instances
            
        Raises:
            DAOError: If there is an error retrieving the annotations
        """
        try:
            annotation_dicts = self.db_manager.get_annotations(job_id, feature_type)
            return [BaktaAnnotation.from_dict(ann_dict) for ann_dict in annotation_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_feature_type for job {job_id}", e)
    
    @cached(ttl_seconds=300, key_prefix="annotation_by_feature_id")
    def get_by_feature_id(self, job_id: str, feature_id: str) -> Optional[BaktaAnnotation]:
        """
        Get an annotation by its feature ID.
        
        This method is cached for 5 minutes to improve performance.
        
        Args:
            job_id: Job ID
            feature_id: Feature ID
            
        Returns:
            BaktaAnnotation instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the annotation
        """
        try:
            annotations = self.get_by_job_id(job_id)
            for annotation in annotations:
                if annotation.feature_id == feature_id:
                    return annotation
            return None
        except DAOError as e:
            self._handle_db_error(f"get_by_feature_id for feature {feature_id}", e)
    
    @cached(ttl_seconds=600, key_prefix="feature_types")
    def get_feature_types(self, job_id: str) -> List[str]:
        """
        Get all feature types for a job.
        
        This method is cached for 10 minutes to improve performance.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of feature types
            
        Raises:
            DAOError: If there is an error retrieving the feature types
        """
        try:
            annotations = self.get_by_job_id(job_id)
            types: Set[str] = set()
            for annotation in annotations:
                types.add(annotation.feature_type)
            return sorted(list(types))
        except DAOError as e:
            self._handle_db_error(f"get_feature_types for job {job_id}", e)
    
    @cached(ttl_seconds=600, key_prefix="contigs")
    def get_contigs(self, job_id: str) -> List[str]:
        """
        Get all contigs for a job.
        
        This method is cached for 10 minutes to improve performance.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of contigs
            
        Raises:
            DAOError: If there is an error retrieving the contigs
        """
        try:
            annotations = self.get_by_job_id(job_id)
            contigs: Set[str] = set()
            for annotation in annotations:
                contigs.add(annotation.contig)
            return sorted(list(contigs))
        except DAOError as e:
            self._handle_db_error(f"get_contigs for job {job_id}", e)
    
    @cached(ttl_seconds=120, key_prefix="annotations_in_range")
    def get_in_range(
        self, 
        job_id: str, 
        contig: str, 
        start: int, 
        end: int
    ) -> List[BaktaAnnotation]:
        """
        Get annotations in a genomic range.
        
        This retrieves all annotations that overlap with the specified range.
        This method is cached for 2 minutes to improve performance.
        
        Args:
            job_id: Job ID
            contig: Contig name
            start: Start position
            end: End position
            
        Returns:
            List of BaktaAnnotation instances
            
        Raises:
            DAOError: If there is an error retrieving the annotations
        """
        try:
            # Use the more optimized query with the contig-specific database index
            annotation_dicts = self.db_manager.get_annotations_in_range(job_id, contig, start, end)
            if annotation_dicts is not None:
                return [BaktaAnnotation.from_dict(ann_dict) for ann_dict in annotation_dicts]
            
            # Fallback to in-memory filtering if the database doesn't support range queries
            all_annotations = self.get_by_job_id(job_id)
            in_range = []
            
            for annotation in all_annotations:
                if (annotation.contig == contig and 
                    not (annotation.end < start or annotation.start > end)):
                    in_range.append(annotation)
            
            return in_range
        except (DAOError, BaktaDatabaseError) as e:
            self._handle_db_error(f"get_in_range for job {job_id}", e) 