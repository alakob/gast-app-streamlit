#!/usr/bin/env python3
"""
Validation module for Bakta input data.

This module provides functions for validating FASTA sequences and other inputs
for the Bakta API.
"""

import re
import json
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Union

from amr_predictor.bakta.exceptions import BaktaValidationError

def is_valid_fasta(sequence_or_file: Union[str, Path]) -> bool:
    """
    Check if a string or file contains a valid FASTA sequence
    
    Args:
        sequence_or_file: FASTA sequence as a string or path to a FASTA file
        
    Returns:
        True if the sequence is valid, False otherwise
    """
    # If it's a Path object or looks like a file path and exists, read the file
    if isinstance(sequence_or_file, Path) or (isinstance(sequence_or_file, str) and os.path.exists(sequence_or_file)):
        try:
            with open(sequence_or_file, 'r') as f:
                sequence = f.read()
        except Exception:
            return False
    else:
        # Assume it's a sequence string
        sequence = sequence_or_file
    
    # Simple check for valid FASTA format
    if not sequence or not isinstance(sequence, str):
        return False
        
    lines = [line.strip() for line in sequence.strip().split('\n') if line.strip()]
    
    # Must have at least header and one sequence line
    if len(lines) < 2:
        return False
        
    # First line must be a header
    if not lines[0].startswith('>'):
        return False
    
    # Validate structure (alternating headers and sequences)
    current_is_header = False
    for line in lines:
        if line.startswith('>'):
            if current_is_header:
                # Two headers in a row without sequence between them
                return False
            current_is_header = True
        else:
            current_is_header = False
            
    # Check for invalid characters in sequence lines
    for line in lines:
        if not line.startswith('>'):  # Skip header lines
            # Test for sequences with invalid nucleotide characters
            if re.search(r'[^ACGTNacgtn\s]', line):
                return False
    
    return True

def validate_fasta(sequence_or_file: Union[str, Path]) -> None:
    """
    Validate a FASTA sequence and raise an exception if invalid
    
    Args:
        sequence_or_file: FASTA sequence as a string or path to a FASTA file
        
    Raises:
        BaktaValidationError: If the FASTA sequence is invalid
    """
    # If it's a Path object or looks like a file path and not a FASTA string that starts with '>', check if it exists
    if isinstance(sequence_or_file, Path) or (isinstance(sequence_or_file, str) and not sequence_or_file.startswith('>')):
        # If it doesn't exist as a file, it might be a plain string content without FASTA header
        if not os.path.exists(sequence_or_file):
            # If it's not a file and doesn't start with ">", it's definitely invalid FASTA
            if isinstance(sequence_or_file, str):
                raise BaktaValidationError(f"Invalid FASTA: {sequence_or_file}")
            else:
                raise BaktaValidationError(f"FASTA file does not exist: {sequence_or_file}")
            
        try:
            with open(sequence_or_file, 'r') as f:
                sequence = f.read()
        except Exception as e:
            raise BaktaValidationError(f"Error reading FASTA file: {str(e)}")
    else:
        # Assume it's a sequence string
        sequence = sequence_or_file
    
    # Check if the sequence is empty or not a string
    if not sequence or not isinstance(sequence, str):
        raise BaktaValidationError("Invalid FASTA: sequence is empty or not a string")
        
    lines = [line.strip() for line in sequence.strip().split('\n') if line.strip()]
    
    # Must have at least header and one sequence line
    if len(lines) < 2:
        raise BaktaValidationError("Invalid FASTA: sequence must have at least a header and one sequence line")
        
    # First line must be a header
    if not lines[0].startswith('>'):
        raise BaktaValidationError("Invalid FASTA: header must start with '>'")
    
    # Validate structure (alternating headers and sequences)
    current_is_header = False
    for i, line in enumerate(lines):
        if line.startswith('>'):
            if current_is_header:
                # Two headers in a row without sequence between them
                raise BaktaValidationError(f"Invalid FASTA: missing sequence data between headers at line {i+1}")
            current_is_header = True
        else:
            current_is_header = False
            
    # Check for invalid characters in sequence lines
    for i, line in enumerate(lines):
        if not line.startswith('>'):  # Skip header lines
            # Test for sequences with invalid nucleotide characters
            if re.search(r'[^ACGTNacgtn\s]', line):
                raise BaktaValidationError(f"Invalid FASTA: line {i+1} contains invalid characters (only A, C, G, T, N are allowed)")
    
    return None

def validate_job_id(job_id: str) -> None:
    """
    Validate a job ID and raise an exception if invalid
    
    Args:
        job_id: Job ID to validate
        
    Raises:
        BaktaValidationError: If the job ID is invalid
    """
    if not job_id:
        raise BaktaValidationError("Job ID cannot be empty")
    
    if not isinstance(job_id, str):
        raise BaktaValidationError("Job ID must be a string")
    
    # Bakta job IDs typically follow a specific format (alphanumeric with hyphens)
    # Adjust the pattern as needed based on actual Bakta job ID format
    if not re.match(r'^[a-zA-Z0-9\-_]+$', job_id):
        raise BaktaValidationError(f"Invalid job ID format: {job_id}")
    
    return None

def validate_multi_fasta(sequence: str) -> Tuple[bool, Optional[str], Optional[List[Dict[str, str]]]]:
    """
    Validate a multi-FASTA sequence and extract individual sequences
    
    Args:
        sequence: FASTA sequence as a string
        
    Returns:
        Tuple of (is_valid, error_message, extracted_sequences)
        If is_valid is False, error_message contains the reason
        extracted_sequences is a list of dictionaries with 'header' and 'sequence' keys
    """
    try:
        validate_fasta(sequence)
        is_valid = True
        error_msg = None
    except BaktaValidationError as e:
        return False, str(e), None
    
    # Extract individual sequences
    lines = [line.strip() for line in sequence.strip().split('\n') if line.strip()]
    
    extracted_sequences = []
    current_header = None
    current_sequence = []
    
    for line in lines:
        if line.startswith('>'):
            # Save previous sequence if exists
            if current_header is not None:
                extracted_sequences.append({
                    'header': current_header,
                    'sequence': ''.join(current_sequence)
                })
            
            # Start new sequence
            current_header = line[1:].strip()
            current_sequence = []
        else:
            if current_header is not None:
                current_sequence.append(line)
    
    # Add the last sequence
    if current_header is not None and current_sequence:
        extracted_sequences.append({
            'header': current_header,
            'sequence': ''.join(current_sequence)
        })
    
    return True, None, extracted_sequences

def validate_config(config: dict) -> None:
    """
    Validate Bakta job configuration and raise an exception if invalid
    
    Args:
        config: Job configuration dictionary
        
    Raises:
        BaktaValidationError: If the configuration is invalid
    """
    # Check for required fields
    required_fields = ["genus", "species"]
    for field in required_fields:
        if field not in config:
            raise BaktaValidationError(f"Missing required field: {field}")
    
    # If translation table is specified, check it's valid
    if "translationTable" in config:
        valid_translation_tables = [1, 4, 11]
        if not isinstance(config.get("translationTable"), int):
            raise BaktaValidationError(f"translationTable must be an integer")
        if config.get("translationTable") not in valid_translation_tables:
            raise BaktaValidationError(f"Invalid translation table: {config.get('translationTable')}. Must be one of: {', '.join(map(str, valid_translation_tables))}")
    
    # If completeGenome is specified, check it's a boolean
    if "completeGenome" in config and not isinstance(config.get("completeGenome"), bool):
        raise BaktaValidationError(f"completeGenome must be a boolean")
    
    # Validate genus, species, strain
    for field in ["genus", "species"]:
        value = config.get(field, "")
        if not isinstance(value, str):
            raise BaktaValidationError(f"{field} must be a string")
    
    return None

# Keep backward compatibility
validate_job_config = validate_config

def validate_api_response(response_data: Union[Dict[str, Any], str], expected_fields: List[str] = None) -> None:
    """
    Validate an API response to ensure it contains expected fields
    
    Args:
        response_data: Response data from API (dict or string that can be parsed as JSON)
        expected_fields: List of top-level fields expected in the response
        
    Raises:
        BaktaValidationError: If the response is invalid
    """
    # If the response is a string, try to parse it as JSON
    if isinstance(response_data, str):
        try:
            response_data = json.loads(response_data)
        except json.JSONDecodeError:
            raise BaktaValidationError("Invalid JSON response")
    
    # Check if the response is a dictionary
    if not isinstance(response_data, dict):
        raise BaktaValidationError("Response is not a dictionary")
    
    # If expected fields are specified, check that they exist
    if expected_fields:
        for field in expected_fields:
            if field not in response_data:
                raise BaktaValidationError(f"Missing expected field in response: {field}")
    
    return None

def validate_init_response(response_data: Dict[str, Any]) -> None:
    """
    Validate an initialization response
    
    Args:
        response_data: Response data from initialization API
        
    Raises:
        BaktaValidationError: If the response is invalid
    """
    # Check for required fields
    required_fields = ["job", "uploadLinkFasta"]
    validate_api_response(response_data, required_fields)
    
    # Check job object
    job_fields = ["jobID", "secret"]
    for field in job_fields:
        if field not in response_data.get("job", {}):
            raise BaktaValidationError(f"Missing field in job object: {field}")

def validate_job_status_response(response_data: Dict[str, Any]) -> None:
    """
    Validate a job status response
    
    Args:
        response_data: Response data from status API
        
    Raises:
        BaktaValidationError: If the response is invalid
    """
    # Check for required fields
    required_fields = ["jobs"]
    validate_api_response(response_data, required_fields)
    
    # If there are jobs, check they have required fields
    jobs = response_data.get("jobs", [])
    if jobs:
        job_fields = ["jobID", "jobStatus"]
        for job in jobs:
            for field in job_fields:
                if field not in job:
                    raise BaktaValidationError(f"Missing field in job object: {field}")

def validate_job_results_response(response_data: Dict[str, Any]) -> None:
    """
    Validate a job results response
    
    Args:
        response_data: Response data from results API
        
    Raises:
        BaktaValidationError: If the response is invalid
    """
    # Check for required fields
    required_fields = ["ResultFiles", "jobID"]
    validate_api_response(response_data, required_fields)
    
    # Check ResultFiles object
    if not isinstance(response_data.get("ResultFiles", {}), dict):
        raise BaktaValidationError("ResultFiles is not a dictionary")
    
    # Check if there are result files
    if len(response_data.get("ResultFiles", {})) == 0:
        raise BaktaValidationError("No result files found") 