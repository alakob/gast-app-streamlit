"""
Utility functions for the AMR Streamlit app.
"""
import re
import os
import json
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
import io

def is_valid_dna_sequence(sequence: str) -> bool:
    """
    Validate if the input string is a valid DNA sequence.
    
    Args:
        sequence: Input string to validate
    
    Returns:
        True if valid DNA sequence, False otherwise
    """
    # Clean the sequence by removing whitespace, numbers and FASTA header lines
    clean_seq = '\n'.join(
        line.strip() for line in sequence.split('\n') 
        if line.strip() and not line.startswith('>')
    )
    clean_seq = re.sub(r'\s+', '', clean_seq)
    
    # Check if the sequence contains only valid DNA nucleotides (ATCGN)
    if not clean_seq:
        return False
    
    dna_pattern = re.compile(r'^[ATCGN]+$', re.IGNORECASE)
    return bool(dna_pattern.match(clean_seq))

def get_sequence_statistics(sequence: str) -> Dict[str, Any]:
    """
    Calculate statistics for a DNA sequence.
    
    Args:
        sequence: DNA sequence string
    
    Returns:
        Dictionary with sequence statistics
    """
    # Clean the sequence by removing whitespace and FASTA header lines
    clean_seq = '\n'.join(
        line.strip() for line in sequence.split('\n') 
        if line.strip() and not line.startswith('>')
    )
    clean_seq = re.sub(r'\s+', '', clean_seq)
    clean_seq = clean_seq.upper()
    
    if not clean_seq:
        return {
            "length": 0,
            "gc_content": 0,
            "a_count": 0,
            "t_count": 0,
            "c_count": 0,
            "g_count": 0,
            "n_count": 0
        }
    
    # Calculate base counts
    a_count = clean_seq.count('A')
    t_count = clean_seq.count('T')
    c_count = clean_seq.count('C')
    g_count = clean_seq.count('G')
    n_count = clean_seq.count('N')
    
    # Calculate GC content
    gc_count = g_count + c_count
    gc_content = (gc_count / len(clean_seq)) * 100 if len(clean_seq) > 0 else 0
    
    return {
        "length": len(clean_seq),
        "gc_content": round(gc_content, 2),
        "a_count": a_count,
        "t_count": t_count,
        "c_count": c_count,
        "g_count": g_count,
        "n_count": n_count
    }

def parse_fasta_file(file_data: bytes) -> Tuple[str, List[str]]:
    """
    Parse a FASTA format file.
    
    Args:
        file_data: Raw bytes from uploaded file
    
    Returns:
        Tuple containing:
        - The complete sequence as a string
        - List of sequence headers
    """
    content = file_data.decode('utf-8')
    lines = content.strip().split('\n')
    
    headers = []
    sequence_parts = []
    current_sequence = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('>'):
            # If we already have sequence data, add it to parts
            if current_sequence:
                sequence_parts.append(''.join(current_sequence))
                current_sequence = []
            
            headers.append(line)
        else:
            current_sequence.append(line)
    
    # Add the last sequence if there is one
    if current_sequence:
        sequence_parts.append(''.join(current_sequence))
    
    full_sequence = ''.join(sequence_parts)
    return full_sequence, headers

def read_sample_sequence() -> Optional[str]:
    """
    Read the sample sequence from the configured file path.
    
    Returns:
        Sample sequence as string, or None if file not found
    """
    import config
    
    sample_path = config.SAMPLE_SEQUENCE_PATH
    
    if not os.path.exists(sample_path):
        return None
    
    try:
        with open(sample_path, 'r') as f:
            return f.read()
    except Exception:
        return None

def format_job_status(status: str) -> Tuple[str, str]:
    """
    Format a job status for display.
    
    Args:
        status: Raw status string
    
    Returns:
        Tuple of (formatted status, status color)
    """
    status_map = {
        "PENDING": ("Pending", "blue"),
        "RUNNING": ("Running", "orange"),
        "SUCCESSFUL": ("Complete", "green"),
        "FAILED": ("Failed", "red"),
        "CANCELLED": ("Cancelled", "gray")
    }
    
    default = ("Unknown", "gray")
    return status_map.get(status, default)

def format_results_for_display(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format API results for display in the UI.
    
    Args:
        results: Raw results dictionary
    
    Returns:
        Formatted results for display
    """
    # Make a copy to avoid modifying the original
    formatted = results.copy()
    
    # Format specific fields as needed
    # This can be customized based on the actual result structure
    
    return formatted

def convert_to_csv(data: Dict[str, Any]) -> str:
    """
    Convert results dictionary to CSV format.
    
    Args:
        data: Results dictionary
    
    Returns:
        CSV formatted string
    """
    # Implementation depends on the specific structure of the results
    # This is a placeholder
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    if data:
        writer.writerow(data.keys())
        
        # Write values
        writer.writerow(data.values())
    
    return output.getvalue()

def create_unique_job_name(prefix: str = "streamlit_job") -> str:
    """
    Create a unique job name with timestamp.
    
    Args:
        prefix: Prefix for the job name
    
    Returns:
        Unique job name
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}"
