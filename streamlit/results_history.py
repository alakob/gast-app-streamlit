"""
Results history component for the AMR predictor Streamlit application.

This module provides consolidated views of historical AMR prediction results,
displaying data from multiple completed jobs.
"""

import os
import json
import pandas as pd
import streamlit as st
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Import the column formatting utilities
from utils import format_column_names, filter_dataframe

# Configure logging
logger = logging.getLogger(__name__)

# Try to import matplotlib, but provide graceful fallback
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    logger.warning("Matplotlib is not installed. Visualizations will be disabled.")
    HAS_MATPLOTLIB = False

# Initialize pagination state
def init_pagination_state():
    """Initialize pagination state variables if they don't exist"""
    if "prediction_page" not in st.session_state:
        st.session_state.prediction_page = 0
    if "aggregated_page" not in st.session_state:
        st.session_state.aggregated_page = 0
    if "rows_per_page" not in st.session_state:
        st.session_state.rows_per_page = 10

def collect_completed_job_files(db_manager=None) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Collect job data, prediction files, and aggregated result files from the AMR API.
    
    Returns:
        Tuple containing:
        - List of job data dictionaries
        - List of prediction file paths
        - List of aggregated file paths
    """
    # Import the API client from the local directory
    try:
        from api_client import AMRApiClient
    except ImportError:
        # Try alternative import paths
        import sys
        import os
        # Add the streamlit directory to path if needed
        streamlit_dir = os.path.dirname(os.path.abspath(__file__))
        if streamlit_dir not in sys.path:
            sys.path.insert(0, streamlit_dir)
        from api_client import AMRApiClient
    
    # Initialize the API client with the proper base URL
    try:
        # Try to import config to get the AMR API URL
        try:
            import config
            api_url = config.AMR_API_URL
        except ImportError:
            # Fallback to environment variable or default URL
            import os
            api_url = os.environ.get("AMR_API_URL", "http://localhost:8000")
        
        # Create the API client with the base URL
        api_client = AMRApiClient(base_url=api_url)
        logger.info(f"Initialized AMR API client with base URL: {api_url}")
    except Exception as e:
        logger.error(f"Error initializing AMR API client: {str(e)}")
        # Use a default base URL as fallback
        api_client = AMRApiClient(base_url="http://amr_api:8000")
        logger.info("Using fallback URL for AMR API client: http://amr_api:8000")
    
    # Initialize lists to store data and file paths
    job_data_list = []
    prediction_files = []
    aggregated_files = []
    
    try:
        # Get all jobs with Completed status
        all_jobs = api_client.get_jobs(status="Completed")
        
        if not isinstance(all_jobs, list):
            logger.error(f"Unexpected response format from API: {type(all_jobs)}")
            return [], [], []
        
        # Process each job to collect its files
        for job in all_jobs:
            job_id = job.get("id") or job.get("job_id")
            
            if not job_id:
                logger.warning("Job without ID found in API response")
                continue
                
            # Add job data to the list
            job_data_list.append(job)
            
            # Check for result file paths
            result_file_path = job.get("result_file")
            if result_file_path:
                # When working with Docker volumes shared between containers,
                # use the Docker container paths directly without checking if they exist
                # Both containers (API and Streamlit) share the same Docker volume mounted at /app/results/
                prediction_files.append(result_file_path)
                logger.info(f"Added prediction file path: {result_file_path}")
            
            # Check for aggregated file paths
            aggregated_file_path = job.get("aggregated_result_file")
            if aggregated_file_path:
                # Same approach for aggregated files - use Docker paths directly
                aggregated_files.append(aggregated_file_path)
                logger.info(f"Added aggregated file path: {aggregated_file_path}")
        
        logger.info(f"Collected {len(job_data_list)} jobs, {len(prediction_files)} prediction files, and {len(aggregated_files)} aggregated files")
        
    except Exception as e:
        logger.error(f"Error fetching job data from API: {str(e)}")
    
    return job_data_list, prediction_files, aggregated_files

def load_file_with_auto_detection(file_path: str) -> pd.DataFrame:
    """
    Load a CSV/TSV file with automatic delimiter detection.
    Handles Docker container paths by properly mapping between the shared Docker volume.
    
    Args:
        file_path: Path to the file to load (Docker container path)
    
    Returns:
        DataFrame containing file contents
    """
    try:
        # Handle Docker container path mapping
        # The API and Streamlit containers share the same Docker volume mounted at /app/results
        # So we can use the API-provided container paths directly
        logger.info(f"Attempting to read file: {file_path}")
        
        # First try direct access (for when paths are correctly shared between containers)
        try:
            # Read a small sample of the file to detect the actual delimiter
            with open(file_path, 'r') as f:
                sample = f.read(1000)  # Read first 1000 characters as sample
            
            # Count delimiters to auto-detect format
            tab_count = sample.count('\t')
            comma_count = sample.count(',')
            
            # Use the more frequent delimiter
            if comma_count > tab_count:
                separator = ','
                logger.info(f"Using comma separator for {file_path}")
            else:
                separator = '\t'
                logger.info(f"Using tab separator for {file_path}")
            
            # Load the file with the detected separator
            df = pd.read_csv(file_path, sep=separator)
            logger.info(f"Successfully loaded file using direct path: {file_path}")
            return df
            
        except FileNotFoundError:
            # If the file is not found directly, try alternative approaches
            if '/app/results/' in file_path:
                # Extract just the filename
                filename = os.path.basename(file_path)
                
                # Try local results directory (useful for development)
                local_results_path = f"/Users/alakob/projects/gast-app-streamlit/results/{filename}"
                
                if os.path.exists(local_results_path):
                    logger.info(f"Using local results path: {local_results_path}")
                    df = pd.read_csv(local_results_path, sep=',' if '.csv' in filename else '\t')
                    return df
            
            # If we got here, we couldn't find the file via any of our approaches
            logger.error(f"File not found after trying multiple paths: {file_path}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        # Return empty DataFrame on error
        return pd.DataFrame()

def display_consolidated_history(db_manager=None) -> None:
    """
    Display consolidated history of all completed AMR prediction jobs.
    
    Args:
        db_manager: Database manager instance (optional, not used with API approach)
    """
    # Initialize pagination state
    init_pagination_state()
    
    # Collect all completed job data and files
    job_data_list, prediction_files, aggregated_files = collect_completed_job_files()
    
    if not job_data_list:
        st.info("No completed AMR prediction jobs found.")
        return
    
    # Display a summary of available jobs
    st.write(f"Found {len(job_data_list)} completed AMR prediction jobs")
    
    # Load and consolidate prediction data
    all_predictions = pd.DataFrame()
    for file_path in prediction_files:
        try:
            df = load_file_with_auto_detection(file_path)
            if not df.empty:
                # Extract job_id from the filename
                filename = os.path.basename(file_path)
                job_id = filename.split('_')[-1].split('.')[0]  # Extract ID from filename pattern
                
                # Add job_id column
                df['job_id'] = job_id
                
                # Concatenate to the main DataFrame
                all_predictions = pd.concat([all_predictions, df], ignore_index=True)
                logger.info(f"Added {len(df)} rows from prediction file {file_path}")
        except Exception as e:
            logger.error(f"Error processing prediction file {file_path}: {str(e)}")
    
    # Load and consolidate aggregated data
    all_aggregated = pd.DataFrame()
    for file_path in aggregated_files:
        try:
            df = load_file_with_auto_detection(file_path)
            if not df.empty:
                # Extract job_id from the filename
                filename = os.path.basename(file_path)
                job_id = filename.split('_')[-2].split('.')[0]  # Extract ID from filename pattern for aggregated files
                
                # Add job_id column
                df['job_id'] = job_id
                
                # Add job execution time (from job data)
                for job in job_data_list:
                    if (job.get('id') == job_id or job.get('job_id') == job_id) and 'start_time' in job:
                        df['execution_time'] = job.get('start_time', '')
                        break
                
                # Concatenate to the main DataFrame
                all_aggregated = pd.concat([all_aggregated, df], ignore_index=True)
                logger.info(f"Added {len(df)} rows from aggregated file {file_path}")
        except Exception as e:
            logger.error(f"Error processing aggregated file {file_path}: {str(e)}")
    
    # Display the combined data with pagination
    if not all_predictions.empty:
        display_prediction_table(all_predictions)
    else:
        st.warning("No prediction data available from completed jobs.")
    
    if not all_aggregated.empty:
        display_aggregated_table(all_aggregated)
    else:
        st.warning("No aggregated sequence data available from completed jobs.")
    
    # Display summary statistics if we have aggregated data
    if not all_aggregated.empty:
        display_summary_statistics(all_aggregated)

def display_prediction_table(predictions_df: pd.DataFrame) -> None:
    """
    Display the consolidated predictions table with pagination.
    
    Args:
        predictions_df: DataFrame containing all prediction data
    """
    st.subheader("Antimicrobial Resistance Predictions")
    
    # Get total number of rows and calculate total pages
    total_rows = len(predictions_df)
    rows_per_page = st.session_state.rows_per_page
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page  # Ceiling division
    
    # Create pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("← Previous", disabled=st.session_state.prediction_page <= 0):
            st.session_state.prediction_page -= 1
            st.rerun()
    
    with col2:
        st.write(f"Page {st.session_state.prediction_page + 1} of {max(1, total_pages)}")
    
    with col3:
        if st.button("Next →", disabled=st.session_state.prediction_page >= total_pages - 1):
            st.session_state.prediction_page += 1
            st.rerun()
    
    # Get data for current page
    start_idx = st.session_state.prediction_page * rows_per_page
    end_idx = start_idx + rows_per_page
    
    page_df = predictions_df.iloc[start_idx:end_idx]
    
    # Format column names to Title Case
    page_df = format_column_names(page_df)
    
    # Apply styling for resistance column if present
    if 'Prediction' in page_df.columns:
        def highlight_prediction(value):
            if isinstance(value, str) and value.upper() in ["RESISTANT", "R"]:
                return 'background-color: #ffcccb'  # Light red
            elif isinstance(value, str) and value.upper() in ["SUSCEPTIBLE", "S"]:
                return 'background-color: #ccffcc'  # Light green
            return ''
        
        # Apply styles
        styled_df = page_df.style.applymap(
            highlight_prediction, 
            subset=['Prediction'] if 'Prediction' in page_df.columns else []
        )
        
        # Display the styled dataframe
        st.dataframe(styled_df, use_container_width=True)
    else:
        # Display without styling if prediction column is not present
        st.dataframe(page_df, use_container_width=True)

def display_aggregated_table(aggregated_df: pd.DataFrame) -> None:
    """
    Display the consolidated sequence-level aggregated table with pagination and filtering.
    
    Args:
        aggregated_df: DataFrame containing all aggregated data
    """
    st.subheader("Sequence-Level Aggregated Results")
    
    # Format column names to Title Case before filtering (for better UI)
    aggregated_df = format_column_names(aggregated_df)
    
    # Apply the dataframe filtering UI - this creates expandable filter controls
    filtered_df = filter_dataframe(aggregated_df)
    
    # Show the total number of rows before and after filtering
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        st.write(f"Total records: {len(aggregated_df)}")
    with col_stats2:
        if len(filtered_df) < len(aggregated_df):
            st.write(f"Filtered records: {len(filtered_df)}")
    
    # Get total number of rows and calculate total pages based on filtered data
    total_rows = len(filtered_df)
    rows_per_page = st.session_state.rows_per_page
    total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)  # Ceiling division
    
    # Reset page if filter reduces total pages below current page
    if st.session_state.aggregated_page >= total_pages and total_pages > 0:
        st.session_state.aggregated_page = total_pages - 1
    
    # Create pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("← Previous", key="agg_prev", disabled=st.session_state.aggregated_page <= 0):
            st.session_state.aggregated_page -= 1
            st.rerun()
    
    with col2:
        st.write(f"Page {st.session_state.aggregated_page + 1} of {total_pages}")
    
    with col3:
        if st.button("Next →", key="agg_next", disabled=st.session_state.aggregated_page >= total_pages - 1):
            st.session_state.aggregated_page += 1
            st.rerun()
    
    # Get data for current page from filtered dataframe
    if total_rows > 0:  # Only paginate if we have data
        start_idx = st.session_state.aggregated_page * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)  # Ensure end_idx doesn't exceed total rows
        page_df = filtered_df.iloc[start_idx:end_idx].copy()
    else:
        # Empty dataframe if no data after filtering
        page_df = filtered_df.copy()
    
    # Apply styling for resistance columns if present
    # Define only the specific columns that should be colored as requested
    red_color = "#ff9494"  # Bright red that shows well on dark background
    
    # Create a simplified function to style only the requested columns
    def highlight_resistance(df):
        styles = pd.DataFrame(index=df.index, columns=df.columns, dtype='object')
        styles.fillna('', inplace=True)
        
        # These are the title-cased column names we want to style
        target_columns = {
            "Any Resistance": lambda val: "RESIST" in str(val).upper(),
            "Majority Vote": lambda val: "RESISTANT" in str(val).upper() or str(val).upper() == "R",
            "Avg Resistance Prob": lambda val: float(val) > 0.5 if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()) else False,
            "Avg Classification": lambda val: "RESISTANT" in str(val).upper() or str(val).upper() == "R"
        }
        
        # Apply styling to matched columns
        for idx in df.index:
            for col in df.columns:
                # Check if this column should be colored
                for target_col, condition_func in target_columns.items():
                    # Match by exact name or similar name (handling slight variations)
                    if col == target_col or col.lower().replace(" ", "") == target_col.lower().replace(" ", ""):
                        try:
                            if condition_func(df.loc[idx, col]):
                                styles.loc[idx, col] = f'color: {red_color}; font-weight: bold;'
                        except (ValueError, TypeError):
                            # Skip if value can't be processed (e.g., non-numeric in probability column)
                            pass
        
        return styles
    
    # Format column names to Title Case
    page_df = format_column_names(page_df)
    
    # Apply the styling function
    styled_df = page_df.style.apply(highlight_resistance, axis=None)
    
    # Display the styled dataframe
    st.dataframe(styled_df, use_container_width=True)

def display_summary_statistics(aggregated_df: pd.DataFrame) -> None:
    """
    Display summary statistics based on the aggregated data.
    
    Args:
        aggregated_df: DataFrame containing consolidated aggregated data
    """
    st.subheader("Summary")
    
    # Get total unique sequences
    total_sequences = 0
    resistant_sequences = 0
    resistance_percentage = 0
    
    # Check for sequence_id column
    if 'sequence_id' in aggregated_df.columns:
        total_sequences = aggregated_df['sequence_id'].nunique()
    else:
        # Fallback to counting rows
        total_sequences = len(aggregated_df)
    
    # Count resistant sequences based on any_resistance or similar column
    resistant_values = ["RESISTANT", "R", "Resistant"]
    resistance_col = None
    
    # Try different possible column names for resistance classification
    for col_name in ['any_resistance', 'majority_vote', 'avg_classification']:
        if col_name in aggregated_df.columns:
            resistance_col = col_name
            break
    
    if resistance_col:
        resistant_sequences = aggregated_df[resistance_col].apply(
            lambda x: str(x).upper() in [r.upper() for r in resistant_values]
        ).sum()
        
        # Calculate resistance percentage
        if total_sequences > 0:
            resistance_percentage = round(resistant_sequences / total_sequences * 100, 1)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sequence/Genome", total_sequences)
    with col2:
        st.metric("Resistant", resistant_sequences)
    with col3:
        st.metric("Resistance %", f"{resistance_percentage}%")
