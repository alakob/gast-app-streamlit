"""
Direct results viewing components for the AMR predictor Streamlit application.

This module provides simplified components for directly displaying AMR prediction results
without requiring database access or AMRJob objects.
"""

import os
import json
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional

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
    
    st.header(f"AMR Prediction Results")
    
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
    
    # Display predictions
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
            
            # Show sequence analysis section
            st.subheader("Sequence Analysis")
            
            # Check for aggregated results file
            aggregated_df = None
            if isinstance(results, dict) and "aggregated_result_file" in results and results["aggregated_result_file"] and os.path.exists(results["aggregated_result_file"]):
                try:
                    aggregated_file = results["aggregated_result_file"]
                    st.info(f"Loading sequence-level aggregated results from: {os.path.basename(aggregated_file)}")
                    
                    # Load aggregated TSV file into DataFrame
                    aggregated_df = pd.read_csv(aggregated_file, sep="\t")
                    
                    if not aggregated_df.empty:
                        # Display the aggregated results as a table
                        st.write("Sequence-Level Aggregated Results:")
                        
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
                        st.warning("No aggregated sequence data available")
                except Exception as e:
                    st.error(f"Error loading aggregated results file: {str(e)}")
            else:
                st.warning("No sequence analysis information available from the AMR API")
            
            # Extract sequence information from the results
            sequence_info = {}
            
            # Look for sequence data in results dict (direct or nested)
            if isinstance(results, dict):
                # Try main level first
                for key in ["sequence_id", "sequence_name", "sequence_length", "gc_content", "contig_count", "gene_count"]:
                    if key in results:
                        sequence_info[key] = results[key]
                
                # Look in a 'sequence' object if present
                if "sequence" in results and isinstance(results["sequence"], dict):
                    for key, value in results["sequence"].items():
                        if key not in sequence_info:
                            sequence_info[key] = value
                
                # If we have start/end positions for the predictions, use those too
                if len(df) > 0 and "start" in df.columns and "end" in df.columns:
                    sequence_info["analyzed_region"] = f"{df['start'].iloc[0]}-{df['end'].iloc[0]}"
                    if "length" in df.columns:
                        sequence_info["region_length"] = df["length"].iloc[0]
            
            # Display sequence information
            if sequence_info:
                # Determine how many columns to display (max 3 per row)
                total_items = len(sequence_info)
                rows_needed = (total_items + 2) // 3  # Ceiling division by 3
                
                for row in range(rows_needed):
                    # Create 3 columns per row
                    cols = st.columns(3)
                    # Get the slice of items for this row
                    start_idx = row * 3
                    end_idx = min(start_idx + 3, total_items)
                    
                    # Get the items for this row
                    row_items = list(sequence_info.items())[start_idx:end_idx]
                    
                    # Display metrics in this row's columns
                    for i, (key, value) in enumerate(row_items):
                        display_key = key.replace("_", " ").title()
                        cols[i].metric(display_key, value)
            else:
                st.info("No sequence information available from the AMR API")
                
            # Show summary statistics
            st.subheader("Summary")
            total_drugs = len(df)
            
            # Count resistant predictions
            resistant_count = 0
            if "prediction" in df.columns:
                resistant_values = ["RESISTANT", "R"]
                resistant_count = df["prediction"].apply(
                    lambda x: str(x).upper() in resistant_values
                ).sum()
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Antibiotics", total_drugs)
            with col2:
                st.metric("Resistant", resistant_count)
            with col3:
                if total_drugs > 0:
                    percentage = round(resistant_count / total_drugs * 100, 1)
                    st.metric("Resistance %", f"{percentage}%")
        else:
            st.warning("Prediction data format not recognized")
    else:
        st.warning("No prediction data available in the results")
    
    # Download buttons section in an expandable accordion
    with st.expander("Downloads", expanded=False):
        # Add download options
        col1, col2 = st.columns(2)
        with col1:
            download_json = st.download_button(
                "Download JSON",
                data=json.dumps(results, indent=2),
                file_name=f"amr_results_{job_id}.json",
                mime="application/json"
            )
        
        with col2:
            # Try to convert to CSV
            try:
                if has_predictions and isinstance(predictions, list):
                    df = pd.DataFrame(predictions)
                    csv_data = df.to_csv(index=False)
                    
                    download_csv = st.download_button(
                        "Download CSV",
                        data=csv_data,
                        file_name=f"amr_results_{job_id}.csv",
                        mime="text/csv"
                    )
                else:
                    # Create a flattened version of the results for CSV
                    flat_data = []
                    if isinstance(results, dict):
                        for k, v in results.items():
                            if not isinstance(v, (dict, list)):
                                flat_data.append({"key": k, "value": v})
                    
                    if flat_data:
                        df = pd.DataFrame(flat_data)
                        csv_data = df.to_csv(index=False)
                        
                        download_csv = st.download_button(
                            "Download CSV",
                            data=csv_data,
                            file_name=f"amr_results_{job_id}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("Cannot create CSV from this result format")
            except Exception as e:
                st.error(f"Error creating CSV: {str(e)}")
