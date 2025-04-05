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


def format_column_names(df):
    """
    Convert DataFrame column names from snake_case to Title Case for better UI display.
    
    Args:
        df: Original DataFrame
        
    Returns:
        DataFrame with column names in Title Case
    """
    if df.empty:
        return df
    
    # Create a dictionary to map original column names to title case
    column_mapping = {}
    for col in df.columns:
        # Handle special case for columns with underscores
        if '_' in col:
            # Split the column name by underscore and capitalize each word
            words = col.split('_')
            title_col = ' '.join(word.capitalize() for word in words)
            column_mapping[col] = title_col
        else:
            # Handle camelCase columns (e.g., jobId)
            if re.match(r'[a-z]+[A-Z][a-z]*', col):  # camelCase pattern
                # Insert space before capital letters
                title_col = re.sub(r'([a-z])([A-Z])', r'\1 \2', col)
                # Capitalize first letters of all words
                title_col = ' '.join(word.capitalize() for word in title_col.split())
                column_mapping[col] = title_col
            else:
                # Simple capitalization for plain lowercase columns
                column_mapping[col] = col.capitalize()
    
    # Rename columns
    return df.rename(columns=column_mapping)


def filter_dataframe(df):
    """
    Auto-generates UI components to filter a dataframe.
    Based on: https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/
    
    Args:
        df: Pandas dataframe to filter
        
    Returns:
        Filtered dataframe
    """
    import streamlit as st
    import pandas as pd
    import numpy as np
    from datetime import datetime
    
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Try to convert object columns to datetime if possible
    for col in df.select_dtypes(include=['object']).columns:
        try:
            df[col] = pd.to_datetime(df[col])
        except Exception:
            pass
    
    # Create a filter section using an expander
    with st.expander("Filter Data"):
        # Add a "Select all" checkbox for each column type
        filter_container = st.container()
        
        # Split the filters into columns for better UI layout
        filter_columns = st.columns(3)
        column_index = 0
        
        # Categorize columns by type for different filter controls
        categorical_cols = list(df.select_dtypes(include=['object', 'category']).columns)
        numeric_cols = list(df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns)
        date_cols = list(df.select_dtypes(include=['datetime64', 'datetime64[ns, UTC]']).columns)
        bool_cols = list(df.select_dtypes(include=['bool']).columns)
        
        # Add a filter UI element for each column based on its type
        for column in df.columns:
            # Get the current column to add filter controls
            current_column = filter_columns[column_index % 3]
            column_index += 1
            
            # For categorical columns - use multiselect
            if column in categorical_cols:
                with current_column:
                    # Get all unique values in the column
                    unique_values = df[column].dropna().unique()
                    # Create a multiselect widget
                    selected_values = st.multiselect(
                        f"Filter by {column}",
                        options=sorted(unique_values),
                        default=None,
                        key=f"filter_{column}"
                    )
                    # Apply filter if values are selected
                    if selected_values:
                        df = df[df[column].isin(selected_values)]
            
            # For numeric columns - use range sliders
            elif column in numeric_cols:
                with current_column:
                    # Get min and max values
                    min_value = float(df[column].min())
                    max_value = float(df[column].max())
                    
                    # Handle case where min and max are identical (slider requires different values)
                    if min_value == max_value:
                        st.info(f"All values in '{column}' are identical: {min_value}")
                    else:
                        # Set step size based on range
                        range_size = max_value - min_value
                        step = 1.0
                        if range_size > 1000:
                            step = 10.0
                        elif range_size < 1:
                            step = 0.01
                        
                        # Create a slider for the range
                        value_range = st.slider(
                            f"Filter by {column}",
                            min_value=min_value,
                            max_value=max_value,
                            value=(min_value, max_value),
                            step=step,
                            key=f"filter_{column}"
                        )
                        # Apply filter based on range
                        df = df[(df[column] >= value_range[0]) & (df[column] <= value_range[1])]
            
            # For datetime columns - use date range pickers
            elif column in date_cols:
                with current_column:
                    try:
                        # Convert to datetime if not already
                        min_date = df[column].min().date()
                        max_date = df[column].max().date()
                        
                        # Create date inputs for range
                        start_date = st.date_input(f"Start date for {column}", min_date, key=f"start_{column}")
                        end_date = st.date_input(f"End date for {column}", max_date, key=f"end_{column}")
                        
                        # Convert date inputs to datetime for comparison
                        if start_date and end_date:
                            # Apply filter based on dates
                            # Convert dates to pandas datetime for consistent comparison
                            start_datetime = pd.to_datetime(start_date)
                            end_datetime = pd.to_datetime(end_date)
                            # Add a day to end date to make it inclusive
                            end_datetime = end_datetime + pd.Timedelta(days=1)
                            df = df[(df[column] >= start_datetime) & (df[column] <= end_datetime)]
                    except Exception as e:
                        st.warning(f"Error filtering date column {column}: {e}")
            
            # For boolean columns - use a simple toggle
            elif column in bool_cols:
                with current_column:
                    bool_value = st.checkbox(f"Show only where {column} is True", key=f"filter_{column}")
                    if bool_value:
                        df = df[df[column] == True]
    
    return df
