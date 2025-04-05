#!/usr/bin/env python3
"""
Sequence DAO module for Bakta entities.

This module provides a DAO implementation for BaktaSequence entities.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from amr_predictor.bakta.dao.base_dao import BaseDAO, DAOError
from amr_predictor.bakta.models import BaktaSequence
from amr_predictor.bakta.database import BaktaDatabaseError
from amr_predictor.bakta.validation import validate_fasta

logger = logging.getLogger("bakta-sequence-dao")

class SequenceDAO(BaseDAO[BaktaSequence]):
    """
    Data Access Object for BaktaSequence entities.
    
    This class provides methods for accessing BaktaSequence data in the database.
    """
    
    def get_by_id(self, id: int) -> Optional[BaktaSequence]:
        """
        Get a sequence by its ID.
        
        Args:
            id: Sequence ID
            
        Returns:
            BaktaSequence instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the sequence
        """
        try:
            sequences = self.db_manager.get_sequences(None)
            for seq_dict in sequences:
                if seq_dict.get('id') == id:
                    return BaktaSequence.from_dict(seq_dict)
            return None
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_id for sequence {id}", e)
    
    def get_all(self) -> List[BaktaSequence]:
        """
        Get all sequences.
        
        Returns:
            List of BaktaSequence instances
            
        Raises:
            DAOError: If there is an error retrieving sequences
        """
        try:
            sequence_dicts = self.db_manager.get_sequences(None)
            return [BaktaSequence.from_dict(seq_dict) for seq_dict in sequence_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error("get_all sequences", e)
    
    def save(self, sequence: BaktaSequence) -> BaktaSequence:
        """
        Save a sequence.
        
        Args:
            sequence: BaktaSequence to save
            
        Returns:
            Saved BaktaSequence
            
        Raises:
            DAOError: If there is an error saving the sequence
        """
        try:
            self.db_manager.save_sequences(
                job_id=sequence.job_id,
                sequences=[{
                    'header': sequence.header,
                    'sequence': sequence.sequence,
                    'length': sequence.length or len(sequence.sequence)
                }]
            )
            return sequence
        except BaktaDatabaseError as e:
            self._handle_db_error(f"save sequence {sequence.header}", e)
    
    def save_batch(self, sequences: List[BaktaSequence]) -> List[BaktaSequence]:
        """
        Save multiple sequences in a batch.
        
        Args:
            sequences: List of BaktaSequence instances to save
            
        Returns:
            List of saved BaktaSequence instances
            
        Raises:
            DAOError: If there is an error saving the sequences
        """
        if not sequences:
            return []
        
        try:
            job_id = sequences[0].job_id
            sequence_dicts = [
                {
                    'header': seq.header,
                    'sequence': seq.sequence,
                    'length': seq.length or len(seq.sequence)
                }
                for seq in sequences
            ]
            self.db_manager.save_sequences(job_id, sequence_dicts)
            return sequences
        except (BaktaDatabaseError, IndexError) as e:
            self._handle_db_error(f"save_batch sequences", e)
    
    def update(self, sequence: BaktaSequence) -> BaktaSequence:
        """
        Update a sequence.
        
        Note: This implementation removes the existing sequence and adds
        a new one with the updated data, as SQLite does not support direct updates
        to the sequences table.
        
        Args:
            sequence: BaktaSequence to update
            
        Returns:
            Updated BaktaSequence
            
        Raises:
            DAOError: If there is an error updating the sequence
        """
        # For simplicity, we're just saving the sequence again
        # In a more sophisticated implementation, we would use a transaction
        # to delete the old one and insert the new one
        return self.save(sequence)
    
    def delete(self, id: int) -> bool:
        """
        Delete a sequence by its ID.
        
        Note: Not implemented in the current database schema.
        
        Args:
            id: Sequence ID
            
        Returns:
            True if sequence was deleted, False if sequence was not found
            
        Raises:
            DAOError: Always raised since deletion is not supported
        """
        # Not implemented in the current database schema
        raise DAOError("Deleting individual sequences is not supported")
    
    def get_by_job_id(self, job_id: str) -> List[BaktaSequence]:
        """
        Get sequences for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of BaktaSequence instances
            
        Raises:
            DAOError: If there is an error retrieving the sequences
        """
        try:
            sequence_dicts = self.db_manager.get_sequences(job_id)
            return [BaktaSequence.from_dict(seq_dict) for seq_dict in sequence_dicts]
        except BaktaDatabaseError as e:
            self._handle_db_error(f"get_by_job_id for job {job_id}", e)
    
    def get_by_header(self, job_id: str, header: str) -> Optional[BaktaSequence]:
        """
        Get a sequence by its header.
        
        Args:
            job_id: Job ID
            header: Sequence header
            
        Returns:
            BaktaSequence instance or None if not found
            
        Raises:
            DAOError: If there is an error retrieving the sequence
        """
        try:
            sequences = self.get_by_job_id(job_id)
            for sequence in sequences:
                if sequence.header == header:
                    return sequence
            return None
        except DAOError as e:
            self._handle_db_error(f"get_by_header for header {header}", e)
    
    def save_from_fasta(self, job_id: str, fasta_content: str) -> List[BaktaSequence]:
        """
        Save sequences from FASTA content.
        
        Args:
            job_id: Job ID
            fasta_content: FASTA content
            
        Returns:
            List of saved BaktaSequence instances
            
        Raises:
            DAOError: If there is an error saving the sequences
        """
        try:
            # Validate FASTA content
            sequences = validate_fasta(fasta_content)
            
            # Map to BaktaSequence instances
            bakta_sequences = [
                BaktaSequence(
                    job_id=job_id,
                    header=seq['header'],
                    sequence=seq['sequence'],
                    length=len(seq['sequence'])
                )
                for seq in sequences
            ]
            
            # Save to database
            sequence_dicts = [
                {
                    'header': seq.header,
                    'sequence': seq.sequence,
                    'length': seq.length
                }
                for seq in bakta_sequences
            ]
            self.db_manager.save_sequences(job_id, sequence_dicts)
            
            return bakta_sequences
        except Exception as e:
            self._handle_db_error(f"save_from_fasta for job {job_id}", e)
    
    def save_from_file(self, job_id: str, fasta_path: Union[str, Path]) -> List[BaktaSequence]:
        """
        Save sequences from a FASTA file.
        
        Args:
            job_id: Job ID
            fasta_path: Path to FASTA file
            
        Returns:
            List of saved BaktaSequence instances
            
        Raises:
            DAOError: If there is an error saving the sequences
        """
        try:
            with open(fasta_path, 'r') as f:
                fasta_content = f.read()
            
            return self.save_from_fasta(job_id, fasta_content)
        except (IOError, OSError) as e:
            self._handle_db_error(f"save_from_file for file {fasta_path}", e) 