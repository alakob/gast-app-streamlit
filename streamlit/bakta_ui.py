#!/usr/bin/env python3
"""
Streamlit UI components for Bakta annotation results.

This module provides UI components for displaying Bakta annotation results
in the Streamlit application, including job submission, status monitoring,
and results visualization.
"""

import os
import time
import asyncio
import logging
from io import StringIO
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

from amr_predictor.bakta.client import BaktaClient
from amr_predictor.bakta.job_manager import BaktaJobManager
from amr_predictor.bakta.models import BaktaJob, BaktaAnnotation
from amr_predictor.bakta.exceptions import BaktaException, BaktaJobError
from amr_predictor.bakta.config import get_bakta_job_config, get_available_presets

# Import UI utilities
from streamlit.ui_components import (
    show_success, 
    show_info, 
    show_error,
    show_warning,
    create_download_link
)

# Configure logging
logger = logging.getLogger("bakta-ui")

# Initialize session state
def init_bakta_state():
    """Initialize session state for Bakta UI components."""
    # Try to get parameters from URL query
    params = st.experimental_get_query_params()
    
    # Initialize basic job tracking state
    if 'bakta_job_id' not in st.session_state:
        # Try to get job ID from URL parameters
        if 'job_id' in params:
            st.session_state.bakta_job_id = params['job_id'][0]
        else:
            st.session_state.bakta_job_id = None
    
    if 'bakta_job_status' not in st.session_state:
        st.session_state.bakta_job_status = None
    
    if 'bakta_job_name' not in st.session_state:
        st.session_state.bakta_job_name = None
    
    # Selected job tracking
    if 'bakta_selected_job' not in st.session_state:
        # Try to get selected job from URL parameters
        if 'selected_job' in params:
            st.session_state.bakta_selected_job = params['selected_job'][0]
        else:
            st.session_state.bakta_selected_job = None
    
    # Feature type filtering
    if 'bakta_selected_feature_type' not in st.session_state:
        if 'feature_type' in params:
            st.session_state.bakta_selected_feature_type = params['feature_type'][0]
        else:
            st.session_state.bakta_selected_feature_type = None
    
    # Result files storage
    if 'bakta_result_files' not in st.session_state:
        st.session_state.bakta_result_files = {}
    
    # Pagination state
    if 'bakta_annotation_page' not in st.session_state:
        if 'page' in params:
            try:
                st.session_state.bakta_annotation_page = int(params['page'][0])
            except ValueError:
                st.session_state.bakta_annotation_page = 0
        else:
            st.session_state.bakta_annotation_page = 0
    
    if 'bakta_annotations_per_page' not in st.session_state:
        if 'per_page' in params:
            try:
                st.session_state.bakta_annotations_per_page = int(params['per_page'][0])
            except ValueError:
                st.session_state.bakta_annotations_per_page = 25
        else:
            st.session_state.bakta_annotations_per_page = 25
    
    # Feature types cache
    if 'bakta_feature_types' not in st.session_state:
        st.session_state.bakta_feature_types = []
        
    # AMR job linking state
    if 'linked_amr_job_id' not in st.session_state:
        if 'amr_job_id' in params:
            st.session_state.linked_amr_job_id = params['amr_job_id'][0]
        else:
            st.session_state.linked_amr_job_id = None

# Function to update URL parameters based on session state
def update_url_params():
    """Update URL query parameters based on current session state."""
    params = {}
    
    # Add job ID if present
    if st.session_state.bakta_job_id:
        params['job_id'] = st.session_state.bakta_job_id
    
    # Add selected job if different from current job
    if st.session_state.bakta_selected_job and st.session_state.bakta_selected_job != st.session_state.bakta_job_id:
        params['selected_job'] = st.session_state.bakta_selected_job
    
    # Add feature type filter if present
    if st.session_state.bakta_selected_feature_type:
        params['feature_type'] = st.session_state.bakta_selected_feature_type
    
    # Add pagination details
    if st.session_state.bakta_annotation_page > 0:
        params['page'] = str(st.session_state.bakta_annotation_page)
    
    if st.session_state.bakta_annotations_per_page != 25:  # Default value
        params['per_page'] = str(st.session_state.bakta_annotations_per_page)
    
    # Add linked AMR job if present
    if hasattr(st.session_state, 'linked_amr_job_id') and st.session_state.linked_amr_job_id:
        params['amr_job_id'] = st.session_state.linked_amr_job_id
    
    # Update URL parameters
    st.experimental_set_query_params(**params)

# Create async-compatible job manager
def get_job_manager(environment: str = 'prod') -> BaktaJobManager:
    """Get a BaktaJobManager instance."""
    return BaktaJobManager(environment=environment)

# Run async function in Streamlit
def run_async(func, *args, **kwargs):
    """Run an async function from Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(func(*args, **kwargs))
    loop.close()
    return result

def display_bakta_submission_form():
    """Display the Bakta job submission form."""
    st.subheader("Submit New Bakta Annotation Job")
    
    # Get available presets
    presets = ["default"] + get_available_presets()
    
    # Create form for job submission
    with st.form("bakta_submission_form"):
        # Basic information
        job_name = st.text_input("Job Name", value="Bakta Annotation Job", help="Name for this annotation job")
        uploaded_file = st.file_uploader("Upload FASTA file", type=["fasta", "fa", "fna"], help="FASTA file containing the genome sequence(s) to annotate")
        
        # Configuration options
        col1, col2 = st.columns(2)
        with col1:
            preset = st.selectbox("Configuration Preset", options=presets, index=0, help="Select a configuration preset for common organism types")
        with col2:
            translate_table = st.selectbox("Translation Table", options=[11, 4], index=0, help="Genetic code used for translation")
        
        # Advanced options in expander
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            with col1:
                genus = st.text_input("Genus", value="", help="Taxonomic genus of the organism")
                species = st.text_input("Species", value="", help="Taxonomic species of the organism")
                strain = st.text_input("Strain", value="", help="Strain designation of the organism")
            with col2:
                complete = st.checkbox("Complete Genome", value=False, help="Is this a complete genome?")
                gram_type = st.selectbox(
                    "Cell Wall Type", 
                    options=["Unknown", "Monoderm (Gram-positive)", "Diderm (Gram-negative)"],
                    index=0, 
                    help="Cell wall type of the organism"
                )
                locus_tag = st.text_input("Locus Tag", value="", help="Locus tag prefix for CDS features")
        
        # Submit button
        submit = st.form_submit_button("Submit Annotation Job")
        
        if submit:
            if not uploaded_file:
                show_error("Please upload a FASTA file")
                return
                
            # Save uploaded file
            fasta_content = uploaded_file.getvalue().decode("utf-8")
            temp_file = Path(f"/tmp/{uploaded_file.name}")
            with open(temp_file, "w") as f:
                f.write(fasta_content)
            
            # Map gram type to API values
            derm_type = None
            if gram_type == "Monoderm (Gram-positive)":
                derm_type = "MONODERM"
            elif gram_type == "Diderm (Gram-negative)":
                derm_type = "DIDERM"
            
            # Create config
            config = get_bakta_job_config(
                preset=preset if preset != "default" else None,
                genus=genus if genus else None,
                species=species if species else None,
                strain=strain if strain else None,
                locus_tag=locus_tag if locus_tag else None,
                complete_genome=complete,
                translation_table=translate_table,
                derm_type=derm_type
            )
            
            # Submit job
            try:
                job = run_async(
                    submit_bakta_job,
                    job_name=job_name,
                    fasta_path=temp_file,
                    config=config
                )
                
                # Store job info in session state
                st.session_state.bakta_job_id = job.id
                st.session_state.bakta_job_name = job.name
                st.session_state.bakta_job_status = job.status
                
                show_success(f"Job submitted successfully! Job ID: {job.id}")
                
                # Remove temporary file
                temp_file.unlink()
                
                # Force refresh of the page to show status
                st.experimental_rerun()
                
            except Exception as e:
                show_error(f"Error submitting job: {str(e)}")
                
                # Remove temporary file
                if temp_file.exists():
                    temp_file.unlink()

async def submit_bakta_job(job_name: str, fasta_path: Path, config: Dict[str, Any]) -> BaktaJob:
    """Submit a Bakta annotation job."""
    job_manager = get_job_manager()
    return await job_manager.submit_job(
        job_name=job_name,
        fasta_path=fasta_path,
        config=config
    )

def display_bakta_job_status():
    """Display the status of the current Bakta job."""
    # Check if we should use selected job from selector
    if not st.session_state.bakta_job_id and st.session_state.bakta_selected_job:
        st.session_state.bakta_job_id = st.session_state.bakta_selected_job
        st.session_state.bakta_selected_job = None
        # Update URL parameters
        update_url_params()
        
    if not st.session_state.bakta_job_id:
        st.info("No active Bakta job. Submit a new job to start annotation.")
        return
        
    st.subheader("Bakta Job Status")
    
    job_id = st.session_state.bakta_job_id
    
    # Get current job status
    try:
        job = run_async(get_bakta_job, job_id)
        
        if not job:
            show_error(f"Job {job_id} not found")
            st.session_state.bakta_job_id = None
            st.session_state.bakta_job_name = None
            st.session_state.bakta_job_status = None
            # Update URL parameters to remove invalid job
            update_url_params()
            return
            
        # Update session state
        st.session_state.bakta_job_status = job.status
        
        # Display job information
        col1, col2, col3 = st.columns(3)
        col1.metric("Job Name", job.name)
        col2.metric("Job ID", job.id)
        col3.metric("Status", job.status)
        
        # Display linked AMR job if exists
        if hasattr(st.session_state, 'linked_amr_job_id') and st.session_state.linked_amr_job_id:
            st.write(f"**Linked AMR Job:** {st.session_state.linked_amr_job_id}")
        
        # Add progress bar for running jobs
        if job.status in ["RUNNING", "QUEUED", "CREATED"]:
            if job.status == "RUNNING":
                progress = 0.65  # Approximate progress
                st.progress(progress, text="Processing annotation...")
            elif job.status == "QUEUED":
                st.progress(0.25, text="Job is queued, waiting to start...")
            else:
                st.progress(0.1, text="Job is being prepared...")
                
            # Add auto-refresh button
            if st.button("Refresh Status"):
                # Force URL params update before refresh
                update_url_params()
            
            # Add message
            st.info("This job is still processing. Please wait or check back later.")
            
            # Add automatic refresh script
            st.markdown("""
            <script>
            // Auto refresh every 20 seconds for running jobs
            setTimeout(function() {
                window.location.reload();
            }, 20000);
            </script>
            """, unsafe_allow_html=True)
            
        elif job.status == "COMPLETED":
            show_success("Job completed successfully!")
            
            # Check if results are already downloaded
            if not st.session_state.bakta_result_files:
                # Offer to download results
                if st.button("View Results"):
                    result_files = run_async(download_bakta_results, job_id)
                    st.session_state.bakta_result_files = result_files
                    
                    # Also import annotations
                    gff_file = result_files.get("gff3")
                    json_file = result_files.get("json")
                    if gff_file and json_file:
                        run_async(
                            import_bakta_annotations,
                            job_id=job_id,
                            gff_file=gff_file,
                            json_file=json_file
                        )
                    
                    # Update URL parameters
                    update_url_params()
                    
                    # Force refresh to show results
                    st.experimental_rerun()
        
        # AMR Job Linking Section
        st.subheader("Link with AMR Prediction")
        
        # Get currently linked job
        linked_job_id = st.session_state.linked_amr_job_id if hasattr(st.session_state, 'linked_amr_job_id') else None
        
        # Show current link or create new one
        if linked_job_id:
            st.success(f"Currently linked to AMR job: {linked_job_id}")
            if st.button("Remove Link"):
                st.session_state.linked_amr_job_id = None
                update_url_params()
                st.experimental_rerun()
                
            # Add button to navigate to AMR results
            if st.button("View AMR Results"):
                # Here you would redirect to AMR results page with the job ID
                # This is a placeholder - you'd implement the actual redirect
                st.markdown(f"<a href='/amr?job_id={linked_job_id}' target='_self'>View AMR Results</a>", unsafe_allow_html=True)
        else:
            # Provide a way to link to an AMR job
            st.info("Link this annotation job to an AMR prediction job for integrated analysis")
            amr_job_id = st.text_input("Enter AMR Job ID to link", key="amr_job_link_input")
            if st.button("Link Jobs") and amr_job_id:
                st.session_state.linked_amr_job_id = amr_job_id
                update_url_params()
                show_success(f"Linked to AMR job: {amr_job_id}")
                st.experimental_rerun()
            
        elif job.status == "FAILED":
            show_error("Job failed")
            
            # Add option to see logs
            if st.button("View Logs"):
                # This would fetch and display logs
                st.write("Log functionality will be implemented soon")
            # Add option to retry or submit a new job
            if st.button("Submit New Job"):
                st.session_state.bakta_job_id = None
                st.session_state.bakta_job_name = None
                st.session_state.bakta_job_status = None
                st.experimental_rerun()
                
        elif job.status == "EXPIRED":
            show_warning("Job expired")
            # Add option to submit a new job
            if st.button("Submit New Job"):
                st.session_state.bakta_job_id = None
                st.session_state.bakta_job_name = None
                st.session_state.bakta_job_status = None
                st.experimental_rerun()
                
    except Exception as e:
        show_error(f"Error checking job status: {str(e)}")

async def get_bakta_job(job_id: str) -> Optional[BaktaJob]:
    """Get Bakta job details."""
    job_manager = get_job_manager()
    return await job_manager.get_job(job_id)

async def download_bakta_results(job_id: str) -> Dict[str, str]:
    """Download results for a completed Bakta job."""
    job_manager = get_job_manager()
    return await job_manager.download_results(job_id)

async def import_bakta_annotations(job_id: str, gff_file: str, json_file: str) -> int:
    """Import annotations from result files."""
    job_manager = get_job_manager()
    return await job_manager.import_annotations(
        job_id=job_id,
        gff_file=gff_file,
        json_file=json_file
    )

def display_bakta_job_selector():
    """Display a selector for Bakta jobs."""
    st.subheader("Select Bakta Job")
    
    # Get all jobs
    try:
        jobs = run_async(get_bakta_jobs)
        
        if not jobs:
            st.info("No Bakta jobs found")
            return
            
        # Create a dataframe for display
        job_data = []
        for job in jobs:
            # Add indicator for linked AMR job
            linked_indicator = ""
            if hasattr(st.session_state, 'linked_amr_job_id') and st.session_state.linked_amr_job_id:
                if st.session_state.bakta_job_id == job.id:
                    linked_indicator = "🔗 "
                    
            job_data.append({
                "Job ID": job.id,
                "Name": f"{linked_indicator}{job.name}",
                "Status": job.status,
                "Created": job.created_at,
                "Updated": job.updated_at
            })
            
        job_df = pd.DataFrame(job_data)
        
        # Allow filtering by status
        status_filter = st.multiselect(
            "Filter by status",
            options=["CREATED", "QUEUED", "RUNNING", "COMPLETED", "FAILED"],
            default=[]
        )
        
        if status_filter:
            job_df = job_df[job_df["Status"].isin(status_filter)]
        
        # Display job table
        st.dataframe(job_df)
        
        # Job selection
        job_ids = [job.id for job in jobs]
        selected_id = st.selectbox(
            "Select Job to View", 
            options=job_ids,
            format_func=lambda x: f"{x} - {next((j.name for j in jobs if j.id == x), 'Unknown')}"
        )
        
        # Options for job selection
        col1, col2 = st.columns(2)
        with col1:
            view_button = st.button("View Selected Job")
        with col2:
            link_to_amr = st.checkbox("Link to AMR job", help="Link this job to an AMR prediction job")
        
        if view_button:
            # Store in session state
            selected_job = next((j for j in jobs if j.id == selected_id), None)
            if selected_job:
                st.session_state.bakta_selected_job = selected_job.id  # Store ID rather than object for better serialization
                st.session_state.bakta_job_id = selected_job.id
                st.session_state.bakta_job_name = selected_job.name
                st.session_state.bakta_job_status = selected_job.status
                
                # If linking to AMR is checked, show AMR job selection
                if link_to_amr:
                    # In a real implementation, get actual AMR jobs
                    # Here we just provide a placeholder for manual entry
                    st.session_state.show_amr_link_input = True
                
                # If job is completed, get feature types
                if selected_job.status == "COMPLETED":
                    # Get result files if needed
                    if not st.session_state.bakta_result_files:
                        result_files = run_async(download_bakta_results, selected_job.id)
                        st.session_state.bakta_result_files = result_files
                        
                        # Also import annotations if needed
                        gff_file = result_files.get("gff3")
                        json_file = result_files.get("json")
                        if gff_file and json_file:
                            run_async(
                                import_bakta_annotations,
                                job_id=selected_job.id,
                                gff_file=gff_file,
                                json_file=json_file
                            )
                    
                    # Get feature types
                    feature_types = run_async(get_bakta_feature_types, selected_job.id)
                    st.session_state.bakta_feature_types = feature_types
                
                # Update URL parameters to persist state
                update_url_params()
                st.experimental_rerun()
        
        # Show AMR linking input if needed
        if hasattr(st.session_state, 'show_amr_link_input') and st.session_state.show_amr_link_input:
            st.subheader("Link to AMR Prediction Job")
            amr_job_id = st.text_input("Enter AMR Job ID")
            if st.button("Link Jobs") and amr_job_id:
                st.session_state.linked_amr_job_id = amr_job_id
                update_url_params()
                show_success(f"Linked Bakta job to AMR job: {amr_job_id}")
                st.experimental_rerun()
            
    except Exception as e:
        show_error(f"Error loading jobs: {str(e)}")

async def get_bakta_jobs() -> List[BaktaJob]:
    """Get all Bakta jobs."""
    job_manager = get_job_manager()
    return await job_manager.list_jobs(limit=50)

async def get_bakta_feature_types(job_id: str) -> List[str]:
    """Get feature types for a job."""
    job_manager = get_job_manager()
    return await job_manager.get_feature_types(job_id)

def display_bakta_results():
    """Display Bakta annotation results."""
    if not st.session_state.bakta_job_id or st.session_state.bakta_job_status != "COMPLETED":
        return
        
    st.header("Bakta Annotation Results")
    
    job_id = st.session_state.bakta_job_id
    
    # Create tabs for different views following Phase 4 specification
    tabs = st.tabs([
        "Overview", 
        "Genomic Features", 
        "Sequence Viewer", 
        "Functional Analysis",
        "Raw Data"
    ])
    
    # Overview tab: Summary statistics and key findings
    with tabs[0]:
        display_bakta_overview(job_id)
    
    # Genomic Features tab: Detailed list of annotated features
    with tabs[1]:
        display_bakta_feature_table(job_id)
    
    # Sequence Viewer tab: Interactive view of annotated sequences
    with tabs[2]:
        display_bakta_sequence_view(job_id)
    
    # Functional Analysis tab: Pathway and functional annotations
    with tabs[3]:
        display_bakta_functional_analysis(job_id)
    
    # Raw Data tab: Access to raw annotation files
    with tabs[4]:
        display_bakta_downloads(job_id)

def display_bakta_overview(job_id: str):
    """Display an overview of the Bakta annotation results."""
    try:
        # Check if we have cached results
        cache_key = f"bakta_summary_{job_id}"
        
        if cache_key not in st.session_state:
            # Create a progress spinner for loading data
            with st.spinner("Processing annotation data..."):
                # Import the data processing utilities
                from amr_predictor.bakta.data_processing import (
                    extract_feature_statistics,
                    extract_gene_functions,
                    extract_genome_statistics,
                    create_visualization_data
                )
                
                # Get job details
                job_manager = get_job_manager()
                job = run_async(job_manager.get_job, job_id)
                
                # Get all annotations asynchronously - this is more efficient than getting counts individually
                annotations = run_async(job_manager.get_annotations, job_id)
                
                # Get sequences
                sequences = run_async(job_manager.repository.get_sequences, job_id)
                
                # Process the annotation data
                feature_stats = extract_feature_statistics(annotations)
                gene_stats = extract_gene_functions(annotations)
                genome_stats = extract_genome_statistics(annotations, sequences)
                viz_data = create_visualization_data(annotations)
                
                # Prepare summary data
                summary = {
                    "job_id": job_id,
                    "job_name": job.name if job else "Unknown",
                    "created_at": job.created_at if job else None,
                    "status": job.status if job else "Unknown",
                    "feature_stats": feature_stats,
                    "gene_stats": gene_stats,
                    "genome_stats": genome_stats,
                    "visualization_data": viz_data,
                    "config": job.config if job else {}
                }
                
                # Cache the results for quick access
                st.session_state[cache_key] = summary
        else:
            # Use cached results
            summary = st.session_state[cache_key]
        
        # Display summary metrics
        st.subheader("Annotation Summary")
        
        # Top-level metrics
        total_features = summary["feature_stats"]["total_features"]
        feature_types = summary["feature_stats"]["feature_types"]
        
        # Create metrics row
        cols = st.columns(4)
        cols[0].metric("Total Features", total_features)
        
        # Show genome statistics
        genome_stats = summary["genome_stats"]
        cols[1].metric("Genome Size", f"{genome_stats['genome_size']:,} bp")
        cols[2].metric("GC Content", f"{genome_stats['gc_content']}%")
        cols[3].metric("Coding Density", f"{genome_stats['coding_density']}%")
        
        # Feature type distribution
        st.subheader("Feature Distribution")
        col1, col2 = st.columns([3, 2])
        
        # Feature types table
        with col1:
            feature_table = []
            for ftype, count in feature_types.items():
                percentage = (count / total_features * 100) if total_features > 0 else 0
                feature_table.append({
                    "Feature Type": ftype,
                    "Count": count,
                    "Percentage": f"{percentage:.1f}%"
                })
            
            if feature_table:
                st.table(pd.DataFrame(feature_table))
        
        # Bar chart
        with col2:
            if feature_types:
                chart_data = pd.DataFrame({
                    'Feature Type': list(feature_types.keys()),
                    'Count': list(feature_types.values())
                })
                
                # Create interactive Plotly chart
                fig = px.bar(
                    chart_data,
                    x='Feature Type',
                    y='Count',
                    title='Feature Type Distribution',
                    color='Feature Type',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # Sort by count for better visualization
                chart_data = chart_data.sort_values('Count', ascending=False)
        
        # Gene function analysis
        gene_stats = summary["gene_stats"]
        if gene_stats["total_genes"] > 0:
            st.subheader("Gene Function Analysis")
            
            # Gene statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total CDS", gene_stats["total_genes"])
                st.metric("Hypothetical Proteins", gene_stats["hypothetical_genes"])
                st.metric("Characterized Genes", gene_stats["characterized_genes"])
            
            with col2:
                # Show functional categories with an interactive pie chart
                if gene_stats["functional_categories"]:
                    chart_data = pd.DataFrame([
                        {"Category": k.replace('_', ' ').title(), "Count": v}
                        for k, v in gene_stats["functional_categories"].items()
                        if v > 0  # Only include non-zero categories
                    ])
                    
                    if not chart_data.empty:
                        fig = px.pie(
                            chart_data, 
                            values='Count', 
                            names='Category',
                            title='Functional Categories',
                            hole=0.4,  # Create a donut chart
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
                        st.plotly_chart(fig, use_container_width=True)
            
            # Show top products with an interactive horizontal bar chart
            if gene_stats["top_functions"]:
                st.subheader("Top Gene Products")
                top_prods = []
                for product, count in gene_stats["top_functions"]:
                    # Truncate very long product names for better visualization
                    display_product = product if len(product) < 50 else product[:47] + "..."
                    top_prods.append({"Product": display_product, "Count": count, "Full_Product": product})
                
                top_df = pd.DataFrame(top_prods)
                
                # Create interactive horizontal bar chart
                fig = px.bar(
                    top_df,
                    y='Product',
                    x='Count',
                    orientation='h',
                    title='Most Common Gene Products',
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Viridis,
                    hover_data=['Full_Product', 'Count']
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
        
        # Sequence statistics
        st.subheader("Contig Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Number of Contigs", genome_stats["num_contigs"])
            st.metric("N50", f"{genome_stats['n50']:,} bp")
            st.metric("Longest Contig", f"{genome_stats['longest_contig']:,} bp")
        
        with col2:
            # Contig distribution if available with interactive visualization
            viz_data = summary["visualization_data"]
            contig_data = viz_data.get("contig_data", [])
            
            if contig_data:
                chart_data = pd.DataFrame(contig_data)
                
                # Only show top 10 contigs if there are many
                if len(chart_data) > 10:
                    chart_data = chart_data.sort_values('count', ascending=False).head(10)
                    title = 'Top 10 Contigs by Feature Count'
                else:
                    title = 'Contigs by Feature Count'
                
                fig = px.bar(
                    chart_data,
                    x='contig',
                    y='count',
                    title=title,
                    color='count',
                    color_continuous_scale=px.colors.sequential.Viridis
                )
                fig.update_layout(
                    xaxis_title="Contig",
                    yaxis_title="Number of Features",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Add additional visualizations in an expander
        with st.expander("Advanced Analysis", expanded=False):
            # Length distribution visualization
            st.subheader("Feature Length Distribution")
            length_data = viz_data.get("length_histogram_data", [])
            
            if length_data:
                # Create DataFrame and ensure correct ordering
                len_df = pd.DataFrame(length_data)
                length_ranges = ["< 500 bp", "500-1000 bp", "1000-2000 bp", "2000-5000 bp", "> 5000 bp"]
                len_df['range'] = pd.Categorical(len_df['range'], categories=length_ranges, ordered=True)
                len_df = len_df.sort_values('range')
                
                # Create interactive histogram
                fig = px.bar(
                    len_df,
                    x='range',
                    y='count',
                    title='Feature Length Distribution',
                    color='range',
                    color_discrete_sequence=px.colors.sequential.Plasma
                )
                fig.update_layout(
                    xaxis_title="Length Range",
                    yaxis_title="Number of Features",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Strand distribution visualization
            st.subheader("Strand Distribution")
            strand_data = viz_data.get("strand_data", [])
            
            if strand_data:
                strand_df = pd.DataFrame(strand_data)
                
                fig = px.pie(
                    strand_df,
                    values='count',
                    names='strand',
                    title='Coding Strand Distribution',
                    color_discrete_sequence=["#2d70de", "#de412d"]
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        
        # Add option to refresh the analysis
        if st.button("Refresh Analysis"):
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.experimental_rerun()
            
    except Exception as e:
        show_error(f"Error loading overview: {str(e)}")

async def get_bakta_annotation_count(job_id: str, feature_type: str) -> int:
    """Get annotation count for a job and feature type."""
    job_manager = get_job_manager()
    return await job_manager.get_annotation_count(job_id, feature_type)

def display_bakta_feature_table(job_id: str):
    """Display a table of Bakta annotations with interactive filters and expandable details."""
    try:
        st.subheader("Feature Table")
        
        # Check if we have cached data
        feature_cache_key = f"bakta_features_{job_id}"
        
        # Get all annotations if not already cached
        if feature_cache_key not in st.session_state:
            with st.spinner("Loading annotation data..."):
                # Import data processing utilities
                from amr_predictor.bakta.data_processing import create_feature_dataframe
                
                # Get all annotations asynchronously
                job_manager = get_job_manager()
                all_annotations = run_async(job_manager.get_annotations, job_id)
                
                if not all_annotations:
                    st.info("No annotations found")
                    return
                
                # Create a dataframe for easier manipulation
                features_df = create_feature_dataframe(all_annotations)
                
                # Cache the dataframe
                st.session_state[feature_cache_key] = features_df
        else:
            # Use cached data
            features_df = st.session_state[feature_cache_key]
            
            if features_df.empty:
                st.info("No annotations found")
                return
        
        # Get feature types for filtering
        feature_types = list(features_df['feature_type'].unique())
        
        # Save feature types to session state if needed
        if not st.session_state.bakta_feature_types:
            st.session_state.bakta_feature_types = feature_types
        
        # Create a filter section
        st.subheader("Filter Features")
        
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # Add filter by feature type with multi-select
            selected_types = st.multiselect(
                "Feature Types",
                options=feature_types,
                default=["CDS"] if "CDS" in feature_types else [],
                help="Select one or more feature types to display"
            )
            
            # Add contig filter if multiple contigs
            contigs = list(features_df['contig'].unique())
            selected_contigs = []
            if len(contigs) > 1:
                selected_contigs = st.multiselect(
                    "Contigs",
                    options=contigs,
                    default=[],
                    help="Select specific contigs to view"
                )
        
        with filter_col2:
            # Add text search
            search_term = st.text_input(
                "Search in product, gene, or feature ID",
                placeholder="Enter search terms..."
            )
            
            # Add length filter
            min_length = int(features_df['length'].min()) if not features_df.empty else 0
            max_length = int(features_df['length'].max()) if not features_df.empty else 10000
            
            length_range = st.slider(
                "Feature Length (bp)",
                min_value=min_length,
                max_value=max_length,
                value=(min_length, max_length)
            )
        
        # Advanced filters in expander
        with st.expander("Advanced Filters"):
            # Strand filter
            strand_options = st.multiselect(
                "Strand",
                options=["+", "-"],
                default=[]
            )
            
            # Gene presence filter
            if 'has_function' in features_df.columns:
                has_function = st.checkbox("Only show features with known function", value=False)
        
        # Apply filters to dataframe
        filtered_df = features_df.copy()
        
        # Feature type filter
        if selected_types:
            filtered_df = filtered_df[filtered_df['feature_type'].isin(selected_types)]
        
        # Contig filter
        if selected_contigs:
            filtered_df = filtered_df[filtered_df['contig'].isin(selected_contigs)]
        
        # Text search
        if search_term:
            # Search across multiple columns
            search_mask = filtered_df['product'].str.contains(search_term, case=False, na=False)
            search_mask |= filtered_df['feature_id'].str.contains(search_term, case=False, na=False)
            
            if 'gene' in filtered_df.columns:
                search_mask |= filtered_df['gene'].str.contains(search_term, case=False, na=False)
            
            if 'locus_tag' in filtered_df.columns:
                search_mask |= filtered_df['locus_tag'].str.contains(search_term, case=False, na=False)
                
            filtered_df = filtered_df[search_mask]
        
        # Length filter
        filtered_df = filtered_df[
            (filtered_df['length'] >= length_range[0]) & 
            (filtered_df['length'] <= length_range[1])
        ]
        
        # Strand filter
        if strand_options:
            filtered_df = filtered_df[filtered_df['strand'].isin(strand_options)]
        
        # Known function filter
        if 'has_function' in filtered_df.columns and 'has_function' in locals() and has_function:
            filtered_df = filtered_df[filtered_df['has_function']]
        
        # Get total count after filtering
        filtered_count = len(filtered_df)
        
        # Show filter summary
        st.write(f"Showing {filtered_count} features out of {len(features_df)} total annotations")
        
        # Pagination setup
        rows_per_page = st.selectbox(
            "Rows per page",
            options=[10, 25, 50, 100],
            index=1
        )
        
        # Update session state
        st.session_state.bakta_annotations_per_page = rows_per_page
        
        # Calculate pagination
        max_pages = (filtered_count - 1) // rows_per_page + 1 if filtered_count > 0 else 1
        
        # Make sure current page is valid
        if not hasattr(st.session_state, 'bakta_annotation_page') or st.session_state.bakta_annotation_page >= max_pages:
            st.session_state.bakta_annotation_page = 0
        
        page = st.session_state.bakta_annotation_page
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("Previous", disabled=page == 0, key="prev_btn"):
                st.session_state.bakta_annotation_page = max(0, page - 1)
                st.experimental_rerun()
        with col2:
            st.write(f"Page {page + 1} of {max_pages} ({filtered_count} features)")
        with col3:
            if st.button("Next", disabled=page >= max_pages - 1, key="next_btn"):
                st.session_state.bakta_annotation_page = min(max_pages - 1, page + 1)
                st.experimental_rerun()
        
        # Get paginated data
        start_idx = page * rows_per_page
        end_idx = min(start_idx + rows_per_page, filtered_count)
        
        display_df = filtered_df.iloc[start_idx:end_idx].copy()
        
        # Add feature details expander
        if not display_df.empty:
            # Create interactive table
            st.dataframe(
                display_df,
                column_config={
                    "Feature ID": st.column_config.TextColumn("Feature ID"),
                    "Type": st.column_config.TextColumn("Type"),
                    "Contig": st.column_config.TextColumn("Contig"),
                    "Start": st.column_config.NumberColumn("Start"),
                    "End": st.column_config.NumberColumn("End"),
                    "Strand": st.column_config.TextColumn("Strand"),
                    "Length": st.column_config.NumberColumn("Length (bp)"),
                    "Gene": st.column_config.TextColumn("Gene"),
                    "Product": st.column_config.TextColumn("Product"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Feature detail viewer
            selected_feature = st.selectbox(
                "Select feature to view details",
                options=display_df['feature_id'].tolist(),
                format_func=lambda x: f"{x} - {display_df[display_df['feature_id'] == x]['product'].values[0] if 'product' in display_df else ''}"
            )
            
            if selected_feature:
                # Get feature details
                feature_row = display_df[display_df['feature_id'] == selected_feature].iloc[0]
                
                with st.expander("Feature Details", expanded=True):
                    # Create a nice detailed view
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Feature ID:** {feature_row['feature_id']}")
                        st.markdown(f"**Type:** {feature_row['feature_type']}")
                        st.markdown(f"**Location:** {feature_row['contig']}:{feature_row['start']}-{feature_row['end']} ({feature_row['strand']})")
                        st.markdown(f"**Length:** {feature_row['length']} bp")
                    
                    with col2:
                        if 'gene' in feature_row and feature_row['gene']:
                            st.markdown(f"**Gene:** {feature_row['gene']}")
                        if 'product' in feature_row and feature_row['product']:
                            st.markdown(f"**Product:** {feature_row['product']}")
                        if 'protein_id' in feature_row and feature_row['protein_id']:
                            st.markdown(f"**Protein ID:** {feature_row['protein_id']}")
                    
                    # Show all attributes in JSON format
                    with st.expander("All Attributes"):
                        attributes = {col: feature_row[col] for col in feature_row.index if col not in ['id', 'feature_id', 'feature_type', 'contig', 'start', 'end', 'strand', 'length'] and not pd.isna(feature_row[col])}
                        st.json(attributes)
                    
                    # Add buttons for potential actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Show Sequence Context"):
                            st.info("Sequence context view will be implemented in a future update.")
                    with col2:
                        if st.button("Find Similar Features"):
                            st.info("Similar feature search will be implemented in a future update.")
        else:
            st.info("No features match the current filters")
            
        # Add a refresh button to clear the cache and reload data
        if st.button("Refresh Data"):
            if feature_cache_key in st.session_state:
                del st.session_state[feature_cache_key]
            st.experimental_rerun()
            
    except Exception as e:
        show_error(f"Error loading feature table: {str(e)}")
        st.error(f"Stack trace: {traceback.format_exc()}")

async def get_bakta_annotations(
    job_id: str, 
    feature_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[BaktaAnnotation]:
    """Get annotations for a job."""
    job_manager = get_job_manager()
    return await job_manager.get_annotations(
        job_id=job_id,
        feature_type=feature_type,
        limit=limit,
        offset=offset
    )

def display_bakta_sequence_view(job_id: str):
    """Display a sequence view of Bakta annotations."""
    st.subheader("Sequence View")
    st.info("Sequence visualization will be implemented in a future update.")

def display_bakta_functional_analysis(job_id: str):
    """Display functional analysis of Bakta annotations, including pathways and functional categories."""
    st.subheader("Functional Analysis")
    
    # Create a progress spinner for loading data
    with st.spinner("Loading functional analysis data..."):
        # Import the data processing utilities
        from amr_predictor.bakta.data_processing import (
            extract_gene_functions,
            create_feature_dataframe,
            create_interactive_charts
        )
        
        # Cache key for functional analysis
        cache_key = f"bakta_functional_{job_id}"
        
        if cache_key not in st.session_state:
            # Get job manager and annotations
            job_manager = get_job_manager()
            annotations = run_async(job_manager.get_annotations, job_id)
            
            if not annotations:
                st.info("No annotations found for functional analysis.")
                return
            
            # Create feature dataframe for advanced analysis
            features_df = create_feature_dataframe(annotations)
            
            # Get functional data
            gene_stats = extract_gene_functions(annotations)
            charts = create_interactive_charts(features_df)
            
            # Store in session state
            st.session_state[cache_key] = {
                "gene_stats": gene_stats,
                "features_df": features_df,
                "charts": charts
            }
        else:
            # Use cached data
            cached_data = st.session_state[cache_key]
            gene_stats = cached_data["gene_stats"]
            features_df = cached_data["features_df"]
            charts = cached_data["charts"]
        
        # Create tabs for different functional analyses
        func_tabs = st.tabs(["Functional Overview", "Pathway Analysis", "Protein Domains", "COG Categories"])
        
        # Functional Overview tab
        with func_tabs[0]:
            # Gene function overview
            st.subheader("Gene Function Overview")
            
            # Create metrics for functional stats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_genes = gene_stats["total_genes"]
                characterized = gene_stats["characterized_genes"]
                st.metric("Total CDS Features", total_genes)
            
            with col2:
                hypothetical = gene_stats["hypothetical_genes"]
                st.metric("Hypothetical Proteins", f"{hypothetical} ({int(hypothetical/total_genes*100)}% of total)" if total_genes > 0 else "0")
            
            with col3:
                st.metric("Characterized Genes", f"{characterized} ({int(characterized/total_genes*100)}% of total)" if total_genes > 0 else "0")
            
            # Functional categories visualization
            st.subheader("Functional Categories")
            
            if "functional_category_chart" in charts:
                # Get the data and prepare for plotting
                category_data = pd.DataFrame(charts["functional_category_chart"]["data"])
                
                if not category_data.empty:
                    # Create the pie chart
                    fig = px.pie(
                        category_data,
                        values="Count",
                        names="Category",
                        title="Functional Category Distribution",
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show the data table
                    with st.expander("View Category Counts"):
                        st.dataframe(
                            category_data,
                            hide_index=True,
                            use_container_width=True
                        )
            else:
                st.info("No functional category data available.")
            
            # Top gene products
            if gene_stats["top_functions"]:
                st.subheader("Top Gene Products")
                top_func_df = pd.DataFrame(gene_stats["top_functions"], columns=["Product", "Count"])
                
                # Create horizontal bar chart for top functions
                fig = px.bar(
                    top_func_df,
                    y="Product",
                    x="Count",
                    orientation="h",
                    title="Most Common Gene Products",
                    color="Count",
                    color_continuous_scale=px.colors.sequential.Viridis
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
        
        # Pathway Analysis tab (placeholder)
        with func_tabs[1]:
            st.subheader("Metabolic Pathway Analysis")
            st.info("Pathway analysis will be available in a future update. This will include KEGG pathway mapping and MetaCyc pathway analysis.")
            
            # Create a placeholder visualization
            with st.expander("Development Preview"):
                st.write("""
                This section will include:
                - KEGG pathway mapping
                - MetaCyc pathway integration
                - Interactive pathway diagrams
                - Pathway enrichment analysis
                - Metabolic network visualization
                """)
        
        # Protein Domains tab (placeholder)
        with func_tabs[2]:
            st.subheader("Protein Domains and Motifs")
            st.info("Protein domain analysis will be available in a future update. This will include domain identification and visualization.")
            
            # Create a placeholder for domain visualization
            with st.expander("Development Preview"):
                st.write("""
                This section will include:
                - Protein domain identification
                - Domain architecture visualization
                - Conserved domain database integration
                - Protein family classification
                - Structural motif analysis
                """)
        
        # COG Categories tab (placeholder)
        with func_tabs[3]:
            st.subheader("COG Categories")
            st.info("COG (Clusters of Orthologous Groups) category analysis will be available in a future update.")
            
            # Create a placeholder for COG visualization
            with st.expander("Development Preview"):
                st.write("""
                This section will include:
                - COG category distribution
                - Functional category enrichment
                - Comparison with reference genomes
                - Interactive COG visualizations
                - Evolutionary insights based on COG distribution
                """)
        
        # Add option to refresh the analysis
        if st.button("Refresh Functional Analysis"):
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.experimental_rerun()

def display_bakta_downloads(job_id: str):
    """Display download links for Bakta result files."""
    st.subheader("Download Result Files")
    
    result_files = st.session_state.bakta_result_files
    
    if not result_files:
        st.info("No result files available")
        return
    
    # Display download links
    for file_type, file_path in result_files.items():
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            st.download_button(
                label=f"Download {file_type.upper()} file",
                data=file_content,
                file_name=file_name,
                mime="application/octet-stream"
            )

def display_bakta_ui():
    """Main entry point for Bakta UI."""
    # Initialize session state
    init_bakta_state()
    
    st.title("Bakta Genome Annotation")
    
    # Display tabs for different sections
    tabs = st.tabs(["Submit Job", "Job Status", "Select Existing Job"])
    
    # Submit job tab
    with tabs[0]:
        display_bakta_submission_form()
    
    # Job status tab
    with tabs[1]:
        display_bakta_job_status()
        
        # If job is completed, also show results
        if st.session_state.bakta_job_status == "COMPLETED":
            display_bakta_results()
    
    # Select existing job tab
    with tabs[2]:
        display_bakta_job_selector()

if __name__ == "__main__":
    display_bakta_ui()
