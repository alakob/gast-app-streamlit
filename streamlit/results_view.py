"""
Results viewing components for the AMR predictor Streamlit application.

This module provides components for displaying results tables and
visualizations for both AMR prediction and Bakta annotation results.
"""

import os
import json
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import streamlit as st
import pandas as pd
import sqlalchemy
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# Import column formatting utility
from utils import format_column_names

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob

# Helper functions for file handling
def get_file_as_base64(file_path: str) -> str:
    """Convert a file to base64 encoding for embedding in HTML."""
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def display_image_file(file_path: str, caption: Optional[str] = None) -> None:
    """Display an image file (PNG, JPG) using Streamlit."""
    if os.path.exists(file_path):
        image = Image.open(file_path)
        st.image(image, caption=caption, use_column_width=True)
    else:
        st.error(f"Image file not found: {file_path}")

def display_svg_file(file_path: str, width: str = "100%") -> None:
    """Display an SVG file using HTML."""
    if os.path.exists(file_path):
        svg_content = get_file_as_base64(file_path)
        svg_html = f'<img src="data:image/svg+xml;base64,{svg_content}" width="{width}">'
        st.markdown(svg_html, unsafe_allow_html=True)
    else:
        st.error(f"SVG file not found: {file_path}")

def format_datetime(dt_str: Optional[str]) -> str:
    """Format a datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return dt_str

# Results table components
def display_results_table(db_manager: DatabaseManager) -> None:
    """Display a table of all completed prediction and annotation jobs."""
    
    # Create tabs for different result types
    amr_tab, bakta_tab = st.tabs(["AMR Prediction Results", "Bakta Annotation Results"])
    
    with amr_tab:
        display_amr_results_table(db_manager)
    
    with bakta_tab:
        display_bakta_results_table(db_manager)

def display_amr_results_table(db_manager: DatabaseManager) -> None:
    """Display a table of completed AMR prediction jobs."""
    st.subheader("AMR Prediction Results")
    
    # Query all completed AMR jobs with metadata
    amr_dao = AMRJobDAO(db_manager)
    all_jobs = amr_dao.get_all_jobs()
    
    # Filter for completed jobs
    completed_jobs = [job for job in all_jobs if job.status == "COMPLETED"]
    
    if completed_jobs:
        # Convert to DataFrame for display
        jobs_data = [{
            "id": job.id,
            "job_name": job.job_name,
            "created_at": format_datetime(job.created_at),
            "completed_at": format_datetime(job.completed_at),
            "view_results": "View Results"
        } for job in completed_jobs]
        
        df = pd.DataFrame(jobs_data)
        
        # Create a clickable dataframe with a callback for the view results button
        st.dataframe(
            df,
            column_config={
                "id": None,  # Hide ID column
                "job_name": st.column_config.TextColumn("Job Name"),
                "created_at": st.column_config.TextColumn("Created"),
                "completed_at": st.column_config.TextColumn("Completed"),
                "view_results": st.column_config.LinkColumn(
                    "Actions", 
                    display_text="View Results",
                    help="Click to view the prediction results"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Handle result viewing when a row is clicked
        if "view_results" in st.session_state and st.session_state.view_results:
            job_id = st.session_state.view_results
            job = next((j for j in completed_jobs if j.id == job_id), None)
            if job:
                view_amr_prediction_result(job, db_manager)
                
    else:
        st.info("No completed AMR prediction jobs found.")

def display_bakta_results_table(db_manager: DatabaseManager) -> None:
    """Display a table of completed Bakta annotation jobs."""
    st.subheader("Bakta Annotation Results")
    
    # Query completed Bakta jobs
    with db_manager._get_connection() as conn:
        query = """
        SELECT id, job_name, created_at, completed_at, result_file_path 
        FROM bakta_jobs 
        WHERE status = 'COMPLETED' 
        ORDER BY completed_at DESC
        """
        cursor = conn.execute(query)
        jobs = [dict(row) for row in cursor.fetchall()]
    
    if jobs:
        # Convert to DataFrame for display
        jobs_data = [{
            "id": job["id"],
            "job_name": job["job_name"],
            "created_at": format_datetime(job["created_at"]),
            "completed_at": format_datetime(job["completed_at"]),
            "view_results": "View Results"
        } for job in jobs]
        
        df = pd.DataFrame(jobs_data)
        
        # Create a clickable dataframe
        st.dataframe(
            df,
            column_config={
                "id": None,  # Hide ID column
                "job_name": st.column_config.TextColumn("Job Name"),
                "created_at": st.column_config.TextColumn("Created"),
                "completed_at": st.column_config.TextColumn("Completed"),
                "view_results": st.column_config.LinkColumn(
                    "Actions", 
                    display_text="View Results",
                    help="Click to view the annotation results"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Handle result viewing when a row is clicked
        if "view_bakta_results" in st.session_state and st.session_state.view_bakta_results:
            job_id = st.session_state.view_bakta_results
            job = next((j for j in jobs if j["id"] == job_id), None)
            if job:
                view_bakta_annotation_result(job, db_manager)
    else:
        st.info("No completed Bakta annotation jobs found.")

# Result visualization handlers
def view_amr_prediction_result(job: AMRJob, db_manager: DatabaseManager) -> None:
    """Display AMR prediction results for a specific job."""
    st.header(f"AMR Prediction Results: {job.job_name}")
    
    # Display job metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Job ID", job.id)
    with col2:
        st.metric("Created", format_datetime(job.created_at))
    with col3:
        st.metric("Completed", format_datetime(job.completed_at))
    
    # Get job parameters
    amr_dao = AMRJobDAO(db_manager)
    job_params = amr_dao.get_job_params(job.id)
    
    if job_params:
        st.subheader("Job Parameters")
        params_df = pd.DataFrame({
            "Parameter": ["Model", "Batch Size", "Segment Length", "Segment Overlap", "Use CPU"],
            "Value": [
                job_params.model_name,
                job_params.batch_size,
                job_params.segment_length,
                job_params.segment_overlap,
                "Yes" if job_params.use_cpu else "No"
            ]
        })
        st.table(params_df)
    
    # Check if we're using real API to decide what data to display
    using_real_api = st.session_state.get("using_real_amr_api", False)
    
    # Create tabs for different result views
    sequence_tab, results_tab, download_tab = st.tabs(["Sequence Analysis", "Prediction Results", "Downloads"])
    
    # Check if result file exists
    if job.result_file_path and os.path.exists(job.result_file_path):
        try:
            # Load results from file - handle both JSON and TSV formats
            results = None
            
            # Enhanced file format detection and logging
            logger.info(f"Processing result file: {job.result_file_path}")
            
            # First check file extension
            if job.result_file_path.lower().endswith('.json'):
                # Handle JSON format
                with open(job.result_file_path, 'r') as f:
                    content = f.read()
                    logger.info(f"File content preview: {content[:100]}")
                    results = json.loads(content)
                    st.info(f"Loaded JSON results from {job.result_file_path}")
                    logger.info(f"Successfully parsed JSON with {len(results.keys() if isinstance(results, dict) else results)} top-level items")
            elif job.result_file_path.lower().endswith(('.tsv', '.csv')):
                # Content-based separator detection - don't trust file extension
                try:
                    import pandas as pd
                    
                    # Read a small sample of the file to detect the actual delimiter
                    with open(job.result_file_path, 'r') as f:
                        sample = f.read(1000)  # Read first 1000 characters as sample
                    
                    logger.info(f"File content preview: {sample[:100]}")
                    
                    # Count delimiters to auto-detect format
                    tab_count = sample.count('\t')
                    comma_count = sample.count(',')
                    logger.info(f"Format detection - tabs: {tab_count}, commas: {comma_count}")
                    
                    # Use the more frequent delimiter
                    if comma_count > tab_count:
                        separator = ','
                        logger.warning(f"File has .tsv extension but appears to be CSV format (using comma separator)")
                    else:
                        separator = '\t'
                        logger.info(f"Using tab separator for {job.result_file_path}")
                    
                    # Load the file with the detected separator
                    df = pd.read_csv(job.result_file_path, sep=separator)
                    
                    # Log column names for debugging
                    logger.info(f"Loaded columns: {', '.join(df.columns.tolist())}")
                    st.info(f"Loaded tabular data from {job.result_file_path} with {len(df)} rows and {len(df.columns)} columns")
                    
                    # Convert DataFrame to a structured format similar to expected JSON
                    results = {
                        "predictions": df.to_dict(orient='records'),
                        "format": "tabular",
                        "source_file": job.result_file_path
                    }
                except Exception as e:
                    st.error(f"Error loading TSV file: {str(e)}")
                    # Create an empty result structure
                    results = {"predictions": [], "error": str(e)}
            else:
                # For other file types, try to read as text
                try:
                    with open(job.result_file_path, 'r') as f:
                        content = f.read()
                    st.info(f"Loaded text content from {job.result_file_path}")
                    # Create a simple result structure with the text content
                    results = {"text_content": content, "format": "text"}
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
                    results = {"error": str(e)}
            
            # Sequence Analysis Tab - Output from /sequence endpoint
            with sequence_tab:
                st.subheader("Sequence Analysis")
                if using_real_api:
                    # Try to fetch sequence analysis results from AMR API
                    try:
                        from api_client import create_amr_client
                        client = create_amr_client()
                        # This would be the real call if the API supported it
                        # sequence_results = client._make_request("GET", f"/sequence/{job.id}")
                        
                        # For now, use a mock implementation
                        st.info("Sequence analysis would normally be shown here from the AMR API /sequence endpoint")
                        
                        # Example sequence stats display (mockup)
                        st.json({
                            "sequence_length": 12345,
                            "gc_content": 0.52,
                            "sequence_quality": "high",
                            "possible_species": ["E. coli", "K. pneumoniae"],
                            "analysis_timestamp": "2025-04-04T11:40:00Z"
                        })
                    except Exception as e:
                        st.error(f"Error fetching sequence analysis: {str(e)}")
                else:
                    st.warning("Using mock AMR API mode. Connect to a real AMR API to see sequence analysis.")
                    # Mock sequence analysis display
                    st.json({
                        "sequence_length": 12345,
                        "gc_content": 0.52,
                        "sequence_quality": "high",
                        "possible_species": ["E. coli", "K. pneumoniae"],
                        "analysis_timestamp": "2025-04-04T11:40:00Z"
                    })
            
            # Prediction Results Tab
            with results_tab:
                st.subheader("Prediction Results")
                
                # Check if we have predictions in the expected format
                has_predictions = False
                predictions = []
                
                # Display the file format information
                if results and isinstance(results, dict):
                    file_format = results.get("format", "unknown")
                    source_file = results.get("source_file", job.result_file_path)
                    st.caption(f"Data source: {source_file} (Format: {file_format})")
                
                # Handle tabular data format (from TSV/CSV)
                if results and isinstance(results, dict) and results.get("format") == "tabular":
                    if "predictions" in results and isinstance(results["predictions"], list):
                        predictions = results["predictions"]
                        has_predictions = True
                        st.success(f"Loaded {len(predictions)} prediction records from tabular data")
                
                # Look for predictions in both the top level and in a nested results structure (JSON format)
                elif isinstance(results, dict):
                    if "predictions" in results and results["predictions"]:
                        predictions = results["predictions"]
                        has_predictions = True
                        st.success(f"Loaded {len(predictions)} prediction records from JSON data")
                    elif "results" in results and isinstance(results["results"], dict):
                        if "predictions" in results["results"] and results["results"]["predictions"]:
                            # Handle both list and dict formats of predictions
                            if isinstance(results["results"]["predictions"], list):
                                predictions = results["results"]["predictions"]
                                has_predictions = True
                            elif isinstance(results["results"]["predictions"], dict):
                                # Convert dict predictions to list format for display
                                predictions = []
                                for drug, pred_info in results["results"]["predictions"].items():
                                    if isinstance(pred_info, dict):
                                        predictions.append({"drug": drug, **pred_info})
                                    else:
                                        predictions.append({"drug": drug, "prediction": pred_info})
                                has_predictions = True
                
                # For text content format 
                elif results and isinstance(results, dict) and "text_content" in results:
                    text_content = results["text_content"]
                    st.text_area("Raw File Content", text_content, height=300)
                    
                    # Log content sample for debugging
                    logger.info(f"Raw text content preview: {text_content[:100]}")
                    
                    # Auto-detect delimiter
                    tab_count = text_content.count('\t')
                    comma_count = text_content.count(',')
                    logger.info(f"Content format detection - tabs: {tab_count}, commas: {comma_count}")
                    
                    # Try to parse as tabular data with auto-detected delimiter
                    try:
                        import io
                        import pandas as pd
                        
                        # Choose delimiter based on frequency
                        delimiter = '\t' if tab_count > comma_count else ','
                        logger.info(f"Using {delimiter} as delimiter for parsing text content")
                        
                        df = pd.read_csv(io.StringIO(text_content), sep=delimiter)
                        logger.info(f"Successfully parsed with columns: {', '.join(df.columns.tolist())}")
                        st.success(f"Parsed tabular data with {len(df)} rows and {len(df.columns)} columns")
                        st.dataframe(df)
                        predictions = df.to_dict(orient='records')
                        has_predictions = True
                    except Exception as e:
                        logger.error(f"Failed to parse as tabular data: {str(e)}")
                
                if has_predictions:
                    # View toggle options with additional options for tabular data
                    view_options = ["Table", "JSON"]
                    if results and isinstance(results, dict) and results.get("format") == "tabular":
                        view_options = ["Interactive Table", "Raw Table", "JSON"]
                    
                    view_mode = st.radio(
                        "View as:",
                        options=view_options,
                        index=0,
                        horizontal=True,
                        key=f"amr_view_mode_{job.id}"
                    )
                    
                    if view_mode in ["Table", "Interactive Table"]:
                        # For tabular data from TSV/CSV, show interactive table with filtering
                        if results and isinstance(results, dict) and results.get("format") == "tabular" and view_mode == "Interactive Table":
                            import pandas as pd
                            # Convert predictions back to DataFrame for better display
                            df = pd.DataFrame(predictions)
                            # Format column names to Title Case
                            df = format_column_names(df)
                            st.dataframe(df, use_container_width=True, height=400)
                            
                            # Additional statistics
                            if len(df) > 0 and "resistance_score" in df.columns:
                                st.subheader("Resistance Statistics")
                                resistant_count = df[df["resistance_score"] > 0.5].shape[0]
                                st.metric("Resistant Drugs", resistant_count, f"{resistant_count/len(df):.1%}")
                        
                        # Traditional table format (normalized for display)
                        elif view_mode == "Raw Table" and results and isinstance(results, dict) and results.get("format") == "tabular":
                            # Show the raw dataframe
                            import pandas as pd
                            raw_df = pd.read_csv(results.get("source_file"), sep='\t')
                            st.dataframe(raw_df, use_container_width=True)
                        else:
                            # Display predictions in a table format
                            # Normalize the prediction data for better display
                            table_data = []
                        
                        for pred in predictions:
                            # Handle different prediction data formats
                            if "drug" in pred:
                                drug = pred.get("drug", "Unknown")
                                prediction = pred.get("prediction", "Unknown")
                                probability = pred.get("probability", 0)
                                gene = pred.get("gene", "")
                            else:
                                # Handle different key structure
                                # Some APIs might return predictions with different keys
                                drug = next((v for k, v in pred.items() if k.lower() in ["drug", "antibiotic", "antimicrobial"]), "Unknown")
                                prediction = next((v for k, v in pred.items() if k.lower() in ["prediction", "result", "classification"]), "Unknown")
                                probability = next((v for k, v in pred.items() if k.lower() in ["probability", "confidence", "score"]), 0)
                                gene = next((v for k, v in pred.items() if k.lower() in ["gene", "resistance_gene"]), "")
                            
                            # Format the row for display
                            row = {
                                "Drug": drug,
                                "Prediction": prediction,
                                "Probability": probability,  # Keep raw value for sorting
                                "Probability %": f"{float(probability)*100:.2f}%" if isinstance(probability, (int, float)) else probability,
                                "Gene": gene or "N/A"
                            }
                            table_data.append(row)
                        
                        # Sort by probability descending
                        table_data = sorted(table_data, key=lambda x: float(x["Probability"]) if isinstance(x["Probability"], (int, float)) else 0, reverse=True)
                        
                        # Create display DataFrame without raw probability column
                        display_cols = ["Drug", "Prediction", "Probability %", "Gene"]
                        display_data = [{k: v for k, v in row.items() if k in display_cols} for row in table_data]
                        pred_df = pd.DataFrame(display_data)
                        # Format column names to Title Case
                        pred_df = format_column_names(pred_df)
                        
                        # Apply styling to the dataframe
                        def highlight_prediction(val):
                            if val == "Resistant":
                                return 'background-color: rgba(255, 0, 0, 0.2)'
                            elif val == "Susceptible":
                                return 'background-color: rgba(0, 255, 0, 0.2)'
                            return ''
                        
                        # Display the dataframe with styling
                        st.dataframe(pred_df.style.applymap(highlight_prediction, subset=["Prediction"]), use_container_width=True)
                        
                        # Show summary statistics
                        total = len(table_data)
                        resistant_count = sum(1 for row in table_data if row["Prediction"] == "Resistant")
                        resistant_pct = (resistant_count / total * 100) if total > 0 else 0
                        
                        # Add DSM Antibiotics section above the Summary
                        st.subheader("DSM Antibiotics")
                        
                        # Create a collapsible accordion for the DSM Antibiotics table (collapsed by default)
                        with st.expander("View DSM Antibiotics Database", expanded=False):
                            try:
                                # Connect to the database
                                conn_str = f"postgresql://postgres:postgres@postgres:5432/amr_predictor_dev"
                                engine = sqlalchemy.create_engine(conn_str)
                                
                                # Query the amr_dsm_antibiotics table
                                query = "SELECT * FROM amr_dsm_antibiotics"
                                df_antibiotics = pd.read_sql(query, engine)
                                
                                # Display the table
                                if not df_antibiotics.empty:
                                    st.dataframe(
                                        df_antibiotics,
                                        column_config={
                                            "Antibiotic": st.column_config.TextColumn("Antibiotic"),
                                            "Antibiotic_Class": st.column_config.TextColumn("Antibiotic Class"),
                                            "WGS-predicted phenotype": st.column_config.TextColumn("WGS-predicted Phenotype"),
                                            "WGS-predicted genotype": st.column_config.TextColumn("WGS-predicted Genotype"),
                                            "MIC_range": st.column_config.TextColumn("MIC Range")
                                        },
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                    st.info(f"Showing {len(df_antibiotics)} antibiotics from the DSM database")
                                else:
                                    st.warning("No antibiotic data found in the database.")
                            except Exception as e:
                                st.error(f"Error loading DSM antibiotics data: {str(e)}")
                                logger.error(f"Error connecting to PostgreSQL or loading DSM antibiotics data: {str(e)}")
                        
                        # Summary section
                        st.info(f"Summary: {resistant_count} out of {total} drugs show resistance ({resistant_pct:.1f}%)")
                        
                    else:  # JSON view
                        # Show the raw JSON data
                        st.json(results)
                    
                    # Create visualization of predictions if we have enough data
                    if len(predictions) > 0:
                        st.subheader("Visualizations")
                        
                        # Only show visualization if we have probabilities
                        if any("probability" in p for p in predictions):
                            # Create bar chart of prediction probabilities
                            fig, ax = plt.figure(figsize=(10, 6)), plt.axes()
                            
                            # Format data for chart
                            drug_names = []
                            prob_values = []
                            colors = []
                            
                            for pred in sorted(predictions, 
                                               key=lambda x: float(x.get("probability", 0)) if isinstance(x.get("probability", 0), (int, float)) else 0,
                                               reverse=True):
                                drug = pred.get("drug", "Unknown")
                                probability = pred.get("probability", 0)
                                prediction = pred.get("prediction", "")
                                
                                if isinstance(probability, (int, float)):
                                    drug_names.append(drug)
                                    prob_values.append(float(probability) * 100)  # Convert to percentage
                                    colors.append('red' if prediction == "Resistant" else 'green')
                            
                            # Create horizontal bar chart
                            bars = ax.barh(drug_names, prob_values, color=colors)
                            ax.set_xlabel("Probability (%)")
                            ax.set_ylabel("Drug")
                            ax.set_title("AMR Prediction Probabilities")
                            ax.set_xlim(0, 100)
                            
                            # Add a legend
                            from matplotlib.patches import Patch
                            legend_elements = [
                                Patch(facecolor='red', label='Resistant'),
                                Patch(facecolor='green', label='Susceptible')
                            ]
                            ax.legend(handles=legend_elements, loc='lower right')
                            
                            st.pyplot(fig)
                            
                            # Add a pie chart for resistant vs susceptible
                            if resistant_count > 0:
                                pie_fig, pie_ax = plt.subplots(figsize=(6, 6))
                                pie_ax.pie([resistant_count, total - resistant_count], 
                                          labels=['Resistant', 'Susceptible'],
                                          colors=['red', 'green'],
                                          autopct='%1.1f%%',
                                          startangle=90)
                                pie_ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                                pie_ax.set_title("Resistance Profile")
                                
                                st.pyplot(pie_fig)
                else:
                    # No predictions found or results in unexpected format
                    st.warning("No prediction data found or results are in an unexpected format.")
                    st.json(results)
            
            # Downloads Tab
            with download_tab:
                st.subheader("Download Options")
                
                # Download prediction results as JSON
                st.download_button(
                    label="Download Results as JSON",
                    data=json.dumps(results, indent=2),
                    file_name=f"amr_prediction_{job.id}.json",
                    mime="application/json",
                    key=f"download_json_{job.id}"
                )
                
                # Check if we have prediction data for CSV download
                if isinstance(results, dict) and "predictions" in results and results["predictions"]:
                    predictions = results["predictions"]
                    pred_df = pd.DataFrame(predictions)
                    # Format column names to Title Case
                    pred_df = format_column_names(pred_df)
                    csv = pred_df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name=f"amr_prediction_{job.id}.csv",
                        mime="text/csv",
                        key=f"download_csv_{job.id}"
                    )
                
                # API Download section
                st.subheader("API Downloads")
                
                if using_real_api:
                    # Try to actually download data from the real API
                    try:
                        from api_client import create_amr_client
                        client = create_amr_client()
                        
                        # List of file types that could be available from the API
                        download_types = [
                            ("Complete Results", "zip"),
                            ("Detailed Report", "pdf"),
                            ("Raw Prediction Data", "json")
                        ]
                        
                        # Create a download button for each file type
                        for label, file_type in download_types:
                            try:
                                # This would be the actual API call in a production environment
                                # response = client._make_request("GET", f"/job/{job.id}/download?type={file_type}", stream=True)
                                # If we have a valid response, enable the download button
                                
                                # For now, since we're still setting up the API endpoints, display buttons with proper status
                                st.button(
                                    f"Download {label} ({file_type.upper()})",
                                    key=f"api_download_{file_type}_{job.id}",
                                    help=f"Download {label} in {file_type.upper()} format from the AMR API",
                                    on_click=lambda ft=file_type: st.toast(f"Download endpoint for {ft} files not yet implemented in API")
                                )
                            except Exception as e:
                                st.button(
                                    f"Download {label} ({file_type.upper()})",
                                    key=f"api_download_failed_{file_type}_{job.id}",
                                    help=f"Error: {str(e)}",
                                    disabled=True
                                )
                    except Exception as e:
                        st.error(f"Error connecting to AMR API for downloads: {str(e)}")
                else:
                    st.warning("Using mock AMR API mode. API downloads are unavailable.")
                    st.info("Connect to a real AMR API to enable direct downloads from the API server.")
                
        except (json.JSONDecodeError, FileNotFoundError) as e:
            for tab in [sequence_tab, results_tab, download_tab]:
                with tab:
                    st.error(f"Error loading results file: {str(e)}")
    else:
        for tab in [sequence_tab, results_tab, download_tab]:
            with tab:
                st.error("Result file not found or job not completed")

def view_bakta_annotation_result(job: Dict[str, Any], db_manager: DatabaseManager) -> None:
    """Display Bakta annotation results for a specific job."""
    st.header(f"Bakta Annotation Results: {job['job_name']}")
    
    # Display job metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Job ID", job["id"])
    with col2:
        st.metric("Created", format_datetime(job["created_at"]))
    with col3:
        st.metric("Completed", format_datetime(job["completed_at"]))
    
    # Check if result files exist
    result_dir = None
    if job["result_file_path"] and os.path.exists(job["result_file_path"]):
        result_dir = os.path.dirname(job["result_file_path"])
    
    if result_dir and os.path.isdir(result_dir):
        st.subheader("Annotation Results")
        
        # Find visualization files (.png, .svg)
        visualization_files = []
        for filename in os.listdir(result_dir):
            file_path = os.path.join(result_dir, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.svg', '.jpg', '.jpeg')):
                visualization_files.append((filename, file_path))
        
        # Find results files (.json, .tsv, .txt)
        result_files = []
        for filename in os.listdir(result_dir):
            file_path = os.path.join(result_dir, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.json', '.tsv', '.txt')):
                result_files.append((filename, file_path))
        
        # Display visualizations
        if visualization_files:
            st.subheader("Visualizations")
            
            # Create visualization tabs for each file
            if len(visualization_files) > 1:
                tabs = st.tabs([os.path.basename(f[0]) for f in visualization_files])
                
                for i, (filename, file_path) in enumerate(visualization_files):
                    with tabs[i]:
                        if filename.lower().endswith('.svg'):
                            display_svg_file(file_path)
                        else:
                            display_image_file(file_path, caption=filename)
            else:
                # Just one file, no need for tabs
                filename, file_path = visualization_files[0]
                if filename.lower().endswith('.svg'):
                    display_svg_file(file_path)
                else:
                    display_image_file(file_path, caption=filename)
        
        # Display result files
        if result_files:
            st.subheader("Result Files")
            
            # Create visualization tabs for each file
            if len(result_files) > 1:
                tabs = st.tabs([os.path.basename(f[0]) for f in result_files])
                
                for i, (filename, file_path) in enumerate(result_files):
                    with tabs[i]:
                        try:
                            if filename.lower().endswith('.json'):
                                with open(file_path, 'r') as f:
                                    data = json.load(f)
                                st.json(data)
                            elif filename.lower().endswith('.tsv'):
                                df = pd.read_csv(file_path, sep='\t')
                                st.dataframe(df, use_container_width=True)
                            else:
                                with open(file_path, 'r') as f:
                                    content = f.read()
                                st.text_area(
                                    label=filename, 
                                    value=content, 
                                    height=400,
                                    disabled=True
                                )
                        except Exception as e:
                            st.error(f"Error loading file {filename}: {str(e)}")
            else:
                # Just one file, no need for tabs
                filename, file_path = result_files[0]
                try:
                    if filename.lower().endswith('.json'):
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        st.json(data)
                    elif filename.lower().endswith('.tsv'):
                        df = pd.read_csv(file_path, sep='\t')
                        st.dataframe(df, use_container_width=True)
                    else:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        st.text_area(label=filename, value=content, height=400, disabled=True)
                except Exception as e:
                    st.error(f"Error loading file {filename}: {str(e)}")
        
        # No result files found
        if not visualization_files and not result_files:
            st.warning("No result files found in the result directory.")
    else:
        st.error("Result directory not found or job not completed")
