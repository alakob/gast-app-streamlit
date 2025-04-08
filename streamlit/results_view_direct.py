"""
Direct results viewing components for the AMR predictor Streamlit application.

This module provides simplified components for directly displaying AMR prediction results
without requiring database access or AMRJob objects.
"""

import os
import json
import pandas as pd
import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up logger
logger = logging.getLogger(__name__)

def view_amr_prediction_result(job_id: str, results: Dict[str, Any]) -> None:
    """
    Display AMR prediction results directly from API response data.
    
    Args:
        job_id: ID of the prediction job
        results: Dictionary containing prediction results from API
    """
    # Try to fetch sequence data using the /sequence endpoint if not present in results
    sequence_data = {}
    
    # First check if sequence data is already in the results
    for key in ["sequence_id", "sequence_name", "sequence_length", "gc_content"]:
        if key in results:
            sequence_data[key] = results[key]
    
    # If we don't have sequence data in results, try to extract it from the existing results
    # or as a last resort, make an API call
    if not sequence_data and "predictions" in results and results["predictions"] and not st.session_state.get("_sequence_fetch_attempted", False):
        try:
            # Mark that we've attempted to fetch the sequence to prevent infinite loops
            st.session_state["_sequence_fetch_attempted"] = True
            
            # First, check if we already have the full results with sequence data
            # This would be the case if we retrieved the complete results earlier
            sequence_fields = ["sequence_id", "sequence_name", "sequence_length", "gc_content", "contig_count", "gene_count"]
            already_have_sequence_data = any(field in results for field in sequence_fields)
            
            if already_have_sequence_data:
                # We already have what we need, just extract it
                logger.info("Sequence data already available in results")
                # Data is already in results, which we're processing later
            else:
                # We don't have sequence data yet - check if it's in the session state
                # from previous API calls to avoid redundant downloads
                full_results = st.session_state.get("amr_results", None)
                if full_results and isinstance(full_results, dict):
                    # Copy sequence data from session state results
                    for field in sequence_fields:
                        if field in full_results:
                            results[field] = full_results[field]
                else:
                    # As a last resort, make a new API call if needed
                    from api_client import create_amr_client
                    
                    # Get the original sequence if available in session state
                    sequence = st.session_state.get("sequence", "")
                    
                    # Use API to analyze sequence only if we have no better option
                    if sequence:
                        logger.info(f"Fetching sequence analysis for job {job_id} via API")
                        api_client = create_amr_client()
                        sequence_data = api_client.analyze_sequence(sequence, job_id)
                        # Store sequence data in results for future reference
                        for key, value in sequence_data.items():
                            results[key] = value
        except Exception as e:
            import logging
            logging.error(f"Error fetching sequence data: {str(e)}")
    
    # Display timestamp if available (only timestamp since job ID is already shown above)
    if isinstance(results, dict) and "timestamp" in results:
        st.metric("Timestamp", results["timestamp"])
    
    # Check if we have predictions in expected format
    has_predictions = False
    predictions = None
    
    # Look for predictions in various possible structures
    if isinstance(results, dict):
        # Direct API response with result_file path
        if "result_file" in results and results["result_file"] and os.path.exists(results["result_file"]):
            # API stores results in a TSV file on disk - read it directly
            try:
                result_file = results["result_file"]
                st.info(f"Loading results from file: {os.path.basename(result_file)}")
                
                # Load TSV file into DataFrame
                df = pd.read_csv(result_file, sep="\t")
                if not df.empty:
                    # Convert DataFrame to list of dictionaries
                    predictions = df.to_dict(orient="records")
                    has_predictions = True
            except Exception as e:
                st.error(f"Error loading result file: {str(e)}")
        elif "predictions" in results and results["predictions"]:
            predictions = results["predictions"]
            has_predictions = True
        elif "results" in results and isinstance(results["results"], dict):
            if "predictions" in results["results"] and results["results"]["predictions"]:
                predictions = results["results"]["predictions"]
                has_predictions = True
    
    # Convert non-list predictions to list format
    if has_predictions and not isinstance(predictions, list):
        # Handle dictionary-style predictions
        if isinstance(predictions, dict):
            pred_list = []
            for drug, pred_info in predictions.items():
                if isinstance(pred_info, dict):
                    # Add drug name to each prediction entry
                    pred_entry = {"drug": drug, **pred_info}
                    pred_list.append(pred_entry)
                else:
                    # Simple drug:prediction mapping
                    pred_list.append({"drug": drug, "prediction": pred_info})
            predictions = pred_list
            has_predictions = True
    
    # Display predictions section
    if has_predictions and predictions:
        st.subheader("Antimicrobial Resistance Predictions")
        
        # Create DataFrame for display
        if isinstance(predictions, list):
            df = pd.DataFrame(predictions)
            
            # Standardize column names
            column_map = {
                "antibiotic": "drug", 
                "antimicrobial": "drug",
                "probability": "confidence",
                "conf": "confidence",
                "confidence_score": "confidence"
            }
            
            for old_col, new_col in column_map.items():
                if old_col in df.columns and new_col not in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Define a function to highlight predictions
            def highlight_prediction(val):
                if isinstance(val, str):
                    if val.upper() in ["RESISTANT", "R"]:
                        return "background-color: #ffcccc"
                    elif val.upper() in ["SUSCEPTIBLE", "S"]:
                        return "background-color: #ccffcc"
                return ""
            
            # Apply styling if possible
            styled_df = df
            if "prediction" in df.columns:
                styled_df = df.style.applymap(highlight_prediction, subset=["prediction"])
            
            # Display the results table
            st.dataframe(styled_df, use_container_width=True)
            
            # Show sequence-level aggregated results (separate from general sequence analysis)
            
            # Get file paths without displaying debug information
            result_file_path = None
            if isinstance(results, dict) and "result_file_path" in results:
                result_file_path = results["result_file_path"]
            
            # Check for aggregated results file path
            aggregated_file_path = None
            for field_name in ["aggregated_result_file", "aggregated_file_path", "aggregated_file"]:
                if isinstance(results, dict) and field_name in results and results[field_name]:
                    aggregated_file_path = results[field_name]
                    break
                
            if aggregated_file_path:
                try:
                    # Handle path mapping across containers
                    aggregated_file = aggregated_file_path
                    
                    # Try additional path mappings if the file doesn't exist
                    if not os.path.exists(aggregated_file):
                        st.warning(f"Original file path not accessible: {aggregated_file}")
                        
                        # Try alternative path mappings
                        possible_paths = [
                            # Original path
                            aggregated_file,
                            # Path with /app prefix in Streamlit container
                            os.path.join('/app', os.path.basename(aggregated_file)),
                            # Path with results subdirectory in Streamlit container
                            os.path.join('/app/results', os.path.basename(aggregated_file)),
                            # Local path mapping outside container
                            os.path.join('/Users/alakob/projects/gast-app-streamlit/results', os.path.basename(aggregated_file))
                        ]
                        
                        # Check each possible path
                        for path in possible_paths:
                            if os.path.exists(path):
                                aggregated_file = path
                                st.success(f"Found file at alternative path: {path}")
                                break
                    
                    # Explicitly check if file exists before trying to read it
                    if not os.path.exists(aggregated_file):
                        st.error(f"Could not find aggregated file")
                        raise FileNotFoundError(f"Aggregated file not found: {aggregated_file}")
                    
                    # Get file stats silently for logging purposes
                    file_stat = os.stat(aggregated_file)
                    logger.info(f"Loading aggregated file: {os.path.basename(aggregated_file)}, Size: {file_stat.st_size} bytes")
                    
                    # Auto-detect delimiter based on file extension and content
                    if aggregated_file.endswith('.csv'):
                        # CSV file (comma-delimited)
                        aggregated_df = pd.read_csv(aggregated_file, sep=",")
                        logger.info(f"Loaded CSV file with comma delimiter")
                    elif aggregated_file.endswith('.tsv'):
                        # TSV file (tab-delimited)
                        aggregated_df = pd.read_csv(aggregated_file, sep="\t")
                        logger.info(f"Loaded TSV file with tab delimiter")
                    else:
                        # Try to detect delimiter by reading first few lines
                        with open(aggregated_file, 'r') as f:
                            sample = f.read(1024)  # Read a sample of the file
                            tab_count = sample.count('\t')
                            comma_count = sample.count(',')
                            logger.info(f"File sample: {sample[:100]}...")
                            logger.info(f"Delimiter counts - tabs: {tab_count}, commas: {comma_count}")
                        
                        # Use the most frequent delimiter
                        if comma_count > tab_count:
                            aggregated_df = pd.read_csv(aggregated_file, sep=",")
                            logger.info("Auto-detected comma delimiter based on content")
                        else:
                            aggregated_df = pd.read_csv(aggregated_file, sep="\t")
                            logger.info("Auto-detected tab delimiter based on content")
                    
                    if not aggregated_df.empty:
                        # Display the aggregated results as a table
                        st.subheader("Sequence-Level Aggregated Results")
                        
                        # Apply styling similar to the main prediction table
                        styled_df = aggregated_df.style
                        
                        # If resistant/susceptible columns exist, apply color highlighting
                        highlight_cols = [col for col in aggregated_df.columns if col.startswith(('Resistant', 'Susceptible'))]
                        if highlight_cols:
                            # Apply conditional styling
                            styled_df = styled_df.background_gradient(
                                cmap='RdYlGn_r', 
                                subset=highlight_cols,
                                vmin=0, 
                                vmax=1
                            )
                        
                        st.dataframe(styled_df, use_container_width=True)
                    else:
                        st.warning("Aggregated data file was found but contains no data")
                except Exception as e:
                    st.error(f"Error loading aggregated results file: {str(e)}")
            else:
                st.warning("No aggregated results file available for this job")
                
            # The Sequence Analysis section has been removed
                
            # Show summary statistics from the aggregated file
            st.subheader("Summary")
            
            # Track if we have aggregated data
            has_aggregated_data = False
            aggregated_df = None
            
            # Try to load the aggregated file if available
            if isinstance(results, dict):
                for field_name in ["aggregated_result_file", "aggregated_file_path", "aggregated_file"]:
                    if field_name in results and results[field_name]:
                        agg_file_path = results[field_name]
                        logger.info(f"Found aggregated file path: {agg_file_path}")
                        
                        # Use the Docker container path directly (following the correct pattern for Docker volumes)
                        if os.path.exists(agg_file_path):
                            try:
                                # Auto-detect delimiter based on file extension
                                if agg_file_path.endswith('.csv'):
                                    aggregated_df = pd.read_csv(agg_file_path, sep=",")
                                elif agg_file_path.endswith('.tsv'):
                                    aggregated_df = pd.read_csv(agg_file_path, sep="\t")
                                else:
                                    # Try comma first as default
                                    aggregated_df = pd.read_csv(agg_file_path, sep=",")
                                
                                has_aggregated_data = True
                                logger.info(f"Successfully loaded aggregated file for summary: {agg_file_path}")
                                break
                            except Exception as e:
                                logger.error(f"Error loading aggregated file for summary: {str(e)}")
                        else:
                            logger.warning(f"Aggregated file not found at: {agg_file_path}")
            
            # Calculate metrics from aggregated data if available
            if has_aggregated_data and aggregated_df is not None and not aggregated_df.empty:
                # Count total unique sequence IDs
                if 'sequence_id' in aggregated_df.columns:
                    total_sequences = aggregated_df['sequence_id'].nunique()
                else:
                    # Fallback to just counting rows
                    total_sequences = len(aggregated_df)
                
                # Count resistant sequences based *specifically* on the avg_classification column
                resistant_values = ["RESISTANT", "R", "Resistant"]
                resistance_col = 'avg_classification' # Target specific column
                
                if resistance_col in aggregated_df.columns:
                    resistant_sequences = aggregated_df[resistance_col].apply(
                        lambda x: str(x).upper() in [r.upper() for r in resistant_values]
                    ).sum()
                    
                    # Calculate resistance percentage
                    if total_sequences > 0:
                        resistance_percentage = round(resistant_sequences / total_sequences * 100, 1)
                    logger.info(f"Calculated resistance summary based on '{resistance_col}' column.")
                else:
                    logger.warning(f"'{resistance_col}' column not found in aggregated results. Cannot calculate resistance summary from it.")
                    # Keep resistant_sequences and resistance_percentage at their default (0)
            else:
                # Fallback to prediction data if no aggregated data
                logger.info("No valid aggregated data found, using prediction data for summary.")
                total_sequences = 1  # Assume one sequence when no aggregated data
                
                # Count resistant predictions as before
                resistant_count = 0
                if "prediction" in df.columns:
                    resistant_values_pred = ["RESISTANT", "R"]
                    resistant_count = df["prediction"].apply(
                        lambda x: str(x).upper() in resistant_values_pred
                    ).sum()
                    
                    # If any antibiotic shows resistance, mark the sequence as resistant
                    resistant_sequences = 1 if resistant_count > 0 else 0
                    resistance_percentage = 100 if resistant_sequences > 0 else 0
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sequence/Genome", total_sequences)
            with col2:
                st.metric("Resistant", resistant_sequences)
            with col3:
                st.metric("Resistance %", f"{resistance_percentage}%")
        else:
            st.warning("Prediction data format not recognized")
    else:
        st.warning("No prediction data available in the results")
    
    # Download buttons section in an expandable accordion
    with st.expander("Downloads", expanded=False):
        st.markdown("### Download Results Files")
        
        # Store file contents for downloads
        prediction_file_content = None
        aggregated_file_content = None
        
        # Get the prediction file path from results
        prediction_file_path = None
        
        # Debug log the available keys in results to help diagnose issues
        if isinstance(results, dict):
            logger.info(f"Available keys in results: {', '.join(results.keys())}")
        
        # Check for prediction file under various possible key names
        if isinstance(results, dict):
            for field_name in ["result_file", "result_file_path", "file_path"]:
                if field_name in results and results[field_name]:
                    prediction_file_path = results[field_name]
                    logger.info(f"Found prediction file path using key '{field_name}': {prediction_file_path}")
                    break
        
        # Check if prediction file exists and read its content
        if prediction_file_path:
            logger.info(f"Checking for prediction file at path: {prediction_file_path}")
            
            # First check if the file exists
            if os.path.exists(prediction_file_path):
                try:
                    with open(prediction_file_path, 'r') as f:
                        prediction_file_content = f.read()
                    logger.info(f"Successfully read prediction file: {prediction_file_path}")
                except Exception as e:
                    logger.error(f"Error reading prediction file: {str(e)}")
            else:
                logger.warning(f"Prediction file not found at path: {prediction_file_path}")
                
                # Try creating the content from the in-memory data if file doesn't exist
                if has_predictions and isinstance(predictions, list):
                    try:
                        df = pd.DataFrame(predictions)
                        prediction_file_content = df.to_csv(index=False)
                        logger.info("Generated prediction file content from in-memory data")
                    except Exception as e:
                        logger.error(f"Failed to generate prediction content from in-memory data: {str(e)}")
        
        # Get aggregated file path
        aggregated_file_path = None
        if isinstance(results, dict):
            for field_name in ["aggregated_result_file", "aggregated_file_path", "aggregated_file"]:
                if field_name in results and results[field_name]:
                    aggregated_file_path = results[field_name]
                    break
        
        # Check if aggregated file exists and read its content
        if aggregated_file_path and os.path.exists(aggregated_file_path):
            try:
                with open(aggregated_file_path, 'r') as f:
                    aggregated_file_content = f.read()
                logger.info(f"Successfully read aggregated file: {aggregated_file_path}")
            except Exception as e:
                logger.error(f"Error reading aggregated file: {str(e)}")
        
        # Create downloads section
        col1, col2, col3 = st.columns(3)
        
        # Full JSON results
        with col1:
            download_json = st.download_button(
                "Download Full Results (JSON)",
                data=json.dumps(results, indent=2),
                file_name=f"amr_results_{job_id}.json",
                mime="application/json",
                help="Download complete results data in JSON format"
            )
        
        # Prediction file download
        with col2:
            if prediction_file_content:
                file_ext = os.path.splitext(prediction_file_path)[1] or ".csv"
                download_csv = st.download_button(
                    "Download Prediction Results",
                    data=prediction_file_content,
                    file_name=f"amr_predictions_{job_id}{file_ext}",
                    mime="text/csv",
                    help="Download the prediction results file"
                )
            else:
                st.info("Prediction file unavailable for download")
        
        # Aggregated file download
        with col3:
            if aggregated_file_content:
                file_ext = os.path.splitext(aggregated_file_path)[1] or ".csv"
                download_agg = st.download_button(
                    "Download Aggregated Results",
                    data=aggregated_file_content,
                    file_name=f"amr_aggregated_{job_id}{file_ext}",
                    mime="text/csv",
                    help="Download the aggregated results file"
                )
            else:
                st.info("Aggregated file unavailable for download")
