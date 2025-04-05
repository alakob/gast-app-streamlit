"""
Sequence handling utilities for AMR Predictor.

This module provides functions for sequence manipulation, including:
- Loading sequences from FASTA files
- Splitting long sequences into manageable segments
- Utility functions for sequence analysis and manipulation
"""

import os
from typing import List, Tuple, Dict, Optional, Generator, Any
import logging
import re
from pathlib import Path

from .utils import logger

# Try to import BioPython for FASTA parsing
try:
    from Bio import SeqIO
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    logger.warning("BioPython not available. Some sequence handling functions will be limited.")


def load_fasta(file_path: str) -> List[Tuple[str, str]]:
    """
    Load sequences from a FASTA file.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        List of tuples containing (sequence_id, sequence)
    """
    sequences = []
    
    if not os.path.exists(file_path):
        logger.error(f"FASTA file not found: {file_path}")
        return sequences
    
    if BIOPYTHON_AVAILABLE:
        try:
            with open(file_path, "r") as handle:
                for record in SeqIO.parse(handle, "fasta"):
                    sequences.append((record.id, str(record.seq)))
            logger.info(f"Loaded {len(sequences)} sequences from {file_path}")
            return sequences
        except Exception as e:
            logger.error(f"Error loading FASTA file with BioPython: {str(e)}")
            # Fall back to manual parsing if BioPython fails
    
    # Manual FASTA parsing as fallback
    try:
        with open(file_path, "r") as file:
            current_id = None
            current_sequence = []
            
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith(">"):
                    # If we've been building a sequence, add it to the results
                    if current_id is not None:
                        sequences.append((current_id, "".join(current_sequence)))
                        current_sequence = []
                    
                    # Extract the new ID (remove the '>' and take everything up to the first whitespace)
                    current_id = line[1:].split()[0]
                else:
                    current_sequence.append(line)
            
            # Add the final sequence if there is one
            if current_id is not None:
                sequences.append((current_id, "".join(current_sequence)))
        
        logger.info(f"Loaded {len(sequences)} sequences from {file_path}")
        return sequences
    except Exception as e:
        logger.error(f"Error manually parsing FASTA file: {str(e)}")
        return []


def split_sequence(seq_id: str, sequence: str, max_length: int = 6000, 
                 min_length: int = 6, overlap: int = 0, id_prefix: str = "segment") -> List[Tuple[str, str]]:
    """
    Split a long sequence into smaller segments with optional overlap.
    
    Args:
        seq_id: Identifier for the sequence
        sequence: The nucleotide sequence string
        max_length: Maximum length for each segment
        min_length: Minimum length required for a segment to be included
        overlap: Number of nucleotides to overlap between segments
        id_prefix: Prefix for segment IDs (default: "segment")
        
    Returns:
        List of tuples containing (segment_id, segment_sequence)
    """
    if max_length <= 0:  # No splitting needed
        return [(seq_id, sequence)]
    
    sequence_length = len(sequence)
    
    # If sequence is shorter than max_length, return as is
    if sequence_length <= max_length:
        return [(seq_id, sequence)]
    
    # If sequence is shorter than minimum length, skip it
    if sequence_length < min_length:
        logger.warning(f"Sequence {seq_id} length ({sequence_length}) is below minimum ({min_length})")
        return []
    
    segments = []
    
    # Calculate effective step size (considering overlap)
    step_size = max_length - overlap
    if step_size <= 0:
        logger.warning(f"Invalid segment parameters: max_length ({max_length}) must be greater than overlap ({overlap})")
        step_size = max(1, max_length // 2)  # Use a safe default
    
    # Split the sequence into segments
    segment_count = ((sequence_length - overlap) + step_size - 1) // step_size
    
    for i in range(segment_count):
        start = i * step_size
        end = min(start + max_length, sequence_length)
        
        # Skip segments smaller than minimum length
        if end - start < min_length:
            continue
        
        segment = sequence[start:end]
        # Use the same format as segment_sequences.py
        segment_id = f"{seq_id}_{id_prefix}_{start+1}_{end}"
        
        segments.append((segment_id, segment))
    
    logger.debug(f"Split sequence {seq_id} ({sequence_length} bp) into {len(segments)} segments")
    return segments


def calculate_sequence_complexity(sequence: str) -> Dict[str, float]:
    """
    Calculate complexity metrics for a DNA sequence.
    
    Args:
        sequence: The nucleotide sequence string
        
    Returns:
        Dictionary containing complexity metrics
    """
    if not sequence:
        return {
            "gc_content": 0.0,
            "sequence_length": 0,
            "complexity_score": 0.0
        }
    
    # Calculate GC content
    gc_count = sum(1 for base in sequence.upper() if base in "GC")
    gc_content = gc_count / len(sequence) if sequence else 0
    
    # Count nucleotide frequencies
    base_counts = {}
    for base in sequence.upper():
        if base in "ACGTN":
            base_counts[base] = base_counts.get(base, 0) + 1
    
    # Calculate a simple complexity score (higher is more complex)
    # This is based on the distribution of nucleotides
    total = sum(base_counts.values())
    frequencies = [count / total for count in base_counts.values()]
    entropy = -sum(f * (f and (f > 0) and (f > 0) and (f > 0)) for f in frequencies)
    complexity_score = min(1.0, max(0.0, entropy / 2.0))  # Normalize to 0-1 range
    
    return {
        "gc_content": gc_content,
        "sequence_length": len(sequence),
        "complexity_score": complexity_score,
        "base_counts": base_counts
    }


def is_valid_sequence(sequence: str, valid_chars: str = "ACGTN-") -> bool:
    """
    Check if a sequence contains only valid nucleotide characters.
    
    Args:
        sequence: The sequence to check
        valid_chars: String of valid characters
        
    Returns:
        True if sequence contains only valid characters
    """
    if not sequence:
        return False
    
    return all(char.upper() in valid_chars for char in sequence)


def clean_sequence(sequence: str, keep_chars: str = "ACGTN-") -> str:
    """
    Clean a sequence by removing invalid characters.
    
    Args:
        sequence: The sequence to clean
        keep_chars: Characters to keep
        
    Returns:
        Cleaned sequence string
    """
    return "".join(char for char in sequence.upper() if char in keep_chars)


def get_fasta_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a FASTA file without loading all sequences.
    
    Args:
        file_path: Path to the FASTA file
        
    Returns:
        Dictionary with file information
    """
    if not os.path.exists(file_path):
        return {
            "exists": False,
            "file_size": 0,
            "sequence_count": 0
        }
    
    file_size = os.path.getsize(file_path)
    
    # Count sequences by counting '>' characters at the start of lines
    sequence_count = 0
    max_seq_length = 0
    min_seq_length = float('inf')
    current_length = 0
    
    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith(">"):
                    sequence_count += 1
                    if current_length > 0:
                        max_seq_length = max(max_seq_length, current_length)
                        min_seq_length = min(min_seq_length, current_length)
                    current_length = 0
                else:
                    current_length += len(line)
            
            # Account for the last sequence
            if current_length > 0:
                max_seq_length = max(max_seq_length, current_length)
                min_seq_length = min(min_seq_length, current_length)
    
    except Exception as e:
        logger.error(f"Error analyzing FASTA file: {str(e)}")
        return {
            "exists": True,
            "file_size": file_size,
            "sequence_count": 0,
            "error": str(e)
        }
    
    # Adjust min_seq_length if no sequences were found
    if min_seq_length == float('inf'):
        min_seq_length = 0
    
    return {
        "exists": True,
        "file_size": file_size,
        "sequence_count": sequence_count,
        "max_sequence_length": max_seq_length,
        "min_sequence_length": min_seq_length,
        "file_path": file_path,
        "file_name": os.path.basename(file_path)
    }
