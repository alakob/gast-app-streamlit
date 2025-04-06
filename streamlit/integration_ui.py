#!/usr/bin/env python3
"""
UI components for integrated analysis of Bakta annotation and AMR prediction data.

This module provides Streamlit components for displaying relationships between 
genome annotations and antimicrobial resistance predictions.
"""

import os
import time
import asyncio
import logging
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

from amr_predictor.core.models import AMRJob
from amr_predictor.bakta.models import BaktaJob
from amr_predictor.bakta.job_manager import BaktaJobManager
from amr_predictor.core.database_manager import AMRDatabaseManager
from amr_predictor.bakta.integration import (
    get_linked_jobs,
    get_amr_data_for_job,
    find_resistance_genes_near_features,
    integrate_feature_with_amr,
    calculate_amr_feature_correlations,
    create_integrated_visualization_data
)
from amr_predictor.bakta.data_processing import create_feature_dataframe

# Import shared UI utilities
from streamlit.utils import run_async, show_error, get_url_params, update_url_params

# Configure logging
logger = logging.getLogger("integration-ui")


def show_integration_selector():
    """Display a selector for integrated analysis."""
    st.header("Integrated Analysis")
    
    # Initialize session state for integration
    if "integration_bakta_job_id" not in st.session_state:
        st.session_state.integration_bakta_job_id = None
    if "integration_amr_job_id" not in st.session_state:
        st.session_state.integration_amr_job_id = None
    
    # Get URL parameters
    params = get_url_params()
    bakta_job_id = params.get("bakta_job_id", None)
    amr_job_id = params.get("amr_job_id", None)
    
    # Update session state from URL parameters
    if bakta_job_id and bakta_job_id != st.session_state.integration_bakta_job_id:
        st.session_state.integration_bakta_job_id = bakta_job_id
    if amr_job_id and amr_job_id != st.session_state.integration_amr_job_id:
        st.session_state.integration_amr_job_id = amr_job_id
    
    # Get linked jobs
    try:
        linked_jobs = run_async(get_linked_jobs, None, None, None)
        if not linked_jobs:
            st.info("No linked Bakta and AMR jobs found. Please submit annotation and AMR prediction jobs for the same genome.")
            return False
        
        # Create a DataFrame for selection
        jobs_df = pd.DataFrame(linked_jobs)
        
        # Create selection columns
        col1, col2 = st.columns(2)
        
        # For readability in the dropdown
        jobs_df["bakta_display"] = jobs_df.apply(
            lambda row: f"{row['bakta_job_name']} ({row['bakta_job_id'][:8]}...)", axis=1
        )
        jobs_df["amr_display"] = jobs_df.apply(
            lambda row: f"{row['amr_job_name']} ({row['amr_job_id'][:8]}...)" if row['amr_job_id'] else "None", axis=1
        )
        
        # Get unique Bakta jobs
        bakta_options = jobs_df[["bakta_job_id", "bakta_display"]].drop_duplicates()
        
        with col1:
            st.subheader("Select Bakta Job")
            selected_bakta_display = st.selectbox(
                "Bakta Annotation Job",
                options=bakta_options["bakta_display"].tolist(),
                index=0 if not st.session_state.integration_bakta_job_id else 
                      bakta_options[bakta_options["bakta_job_id"] == st.session_state.integration_bakta_job_id].index[0]
            )
            
            # Get the actual job ID
            selected_bakta_job = bakta_options[bakta_options["bakta_display"] == selected_bakta_display]["bakta_job_id"].iloc[0]
            
        # Get AMR jobs linked to the selected Bakta job
        amr_options = jobs_df[jobs_df["bakta_job_id"] == selected_bakta_job][["amr_job_id", "amr_display"]].drop_duplicates()
        
        with col2:
            st.subheader("Select AMR Job")
            selected_amr_display = st.selectbox(
                "AMR Prediction Job",
                options=amr_options["amr_display"].tolist(),
                index=0 if not st.session_state.integration_amr_job_id else 
                      amr_options[amr_options["amr_job_id"] == st.session_state.integration_amr_job_id].index[0]
            )
            
            # Get the actual job ID
            selected_amr_job = amr_options[amr_options["amr_display"] == selected_amr_display]["amr_job_id"].iloc[0]
        
        # Update session state
        st.session_state.integration_bakta_job_id = selected_bakta_job
        st.session_state.integration_amr_job_id = selected_amr_job
        
        # Update URL parameters
        update_url_params({
            "bakta_job_id": selected_bakta_job,
            "amr_job_id": selected_amr_job
        })
        
        return True
    
    except Exception as e:
        show_error(f"Error loading linked jobs: {str(e)}")
        logger.error(f"Error in integration selector: {str(e)}", exc_info=True)
        return False


def display_integrated_analysis():
    """Display integrated analysis of Bakta and AMR data."""
    # Show job selector
    if not show_integration_selector():
        return
    
    # Get selected job IDs
    bakta_job_id = st.session_state.integration_bakta_job_id
    amr_job_id = st.session_state.integration_amr_job_id
    
    if not bakta_job_id or not amr_job_id:
        st.info("Please select both a Bakta annotation job and an AMR prediction job.")
        return
    
    # Create tabs for different views
    tabs = st.tabs([
        "Overview", 
        "Genome Map", 
        "Feature-AMR Correlation", 
        "Detailed Analysis"
    ])
    
    # Overview tab
    with tabs[0]:
        display_integration_overview(bakta_job_id, amr_job_id)
    
    # Genome Map tab
    with tabs[1]:
        display_genome_map(bakta_job_id, amr_job_id)
    
    # Feature-AMR Correlation tab
    with tabs[2]:
        display_feature_amr_correlation(bakta_job_id, amr_job_id)
    
    # Detailed Analysis tab
    with tabs[3]:
        display_detailed_analysis(bakta_job_id, amr_job_id)


def display_integration_overview(bakta_job_id: str, amr_job_id: str):
    """Display an overview of the integrated analysis."""
    st.subheader("Integrated Analysis Overview")
    
    # Cache key for overview data
    cache_key = f"integration_overview_{bakta_job_id}_{amr_job_id}"
    
    if cache_key not in st.session_state:
        with st.spinner("Processing integrated data..."):
            # Get job managers
            bakta_job_manager = run_async(lambda: BaktaJobManager())
            amr_db_manager = run_async(lambda: AMRDatabaseManager())
            
            # Get job details
            bakta_job = run_async(bakta_job_manager.get_job, bakta_job_id)
            amr_job_data = run_async(get_amr_data_for_job, amr_db_manager, amr_job_id)
            
            # Get Bakta annotations
            annotations = run_async(bakta_job_manager.get_annotations, bakta_job_id)
            features_df = create_feature_dataframe(annotations)
            
            # Get potential AMR correlations
            correlations = run_async(find_resistance_genes_near_features, 
                                    amr_db_manager, bakta_job_id, amr_job_id)
            
            # Prepare visualization data
            visualization_data = create_integrated_visualization_data(features_df, amr_job_data)
            
            # Cache the results
            st.session_state[cache_key] = {
                "bakta_job": bakta_job,
                "amr_data": amr_job_data,
                "features_df": features_df,
                "correlations": correlations,
                "visualization_data": visualization_data
            }
    
    # Use cached data
    overview_data = st.session_state[cache_key]
    bakta_job = overview_data["bakta_job"]
    amr_data = overview_data["amr_data"]
    features_df = overview_data["features_df"]
    correlations = overview_data["correlations"]
    
    # Display overview cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Bakta Annotation")
        st.metric("Job Name", bakta_job.name)
        st.metric("Status", bakta_job.status)
        st.metric("Features Identified", len(features_df) if not features_df.empty else 0)
        
        # Feature type distribution
        if not features_df.empty:
            feature_counts = features_df['feature_type'].value_counts().reset_index()
            feature_counts.columns = ['Feature Type', 'Count']
            
            fig = px.pie(
                feature_counts, 
                values='Count', 
                names='Feature Type',
                title='Feature Type Distribution',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### AMR Prediction")
        st.metric("Job ID", amr_job_id)
        st.metric("Status", amr_data.get("status", "Unknown"))
        
        # AMR result file
        result_file = amr_data.get("result_file", "")
        if result_file:
            st.markdown(f"Result File: `{os.path.basename(result_file)}`")
        
        # AMR results placeholder
        amr_results = amr_data.get("amr_results", {})
        resistance_genes = amr_results.get("resistance_genes", [])
        
        # Create placeholder visualization for resistance genes
        if resistance_genes:
            st.markdown("### Resistance Genes")
            # In a real implementation, this would show actual resistance gene data
            st.info("Resistance gene visualization will be shown here.")
        else:
            st.markdown("### Resistance Profile")
            st.info("No resistance genes found or AMR results not available.")
    
    # Correlation summary
    st.subheader("Feature-AMR Correlation Summary")
    
    if correlations:
        # Display correlation summary
        st.markdown(f"Found {len(correlations)} potential correlations between genomic features and AMR genes.")
        
        # Create a sample correlation visualization
        correlation_df = pd.DataFrame({
            "Category": ["High Correlation", "Moderate Correlation", "Low Correlation", "No Correlation"],
            "Count": [5, 10, 15, len(features_df) - 30 if not features_df.empty else 0]
        })
        
        fig = px.bar(
            correlation_df,
            x="Category",
            y="Count",
            title="AMR Correlation Distribution",
            color="Category",
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No correlations found between genomic features and AMR genes.")
    
    # Add option to refresh
    if st.button("Refresh Analysis"):
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        st.experimental_rerun()


def display_genome_map(bakta_job_id: str, amr_job_id: str):
    """Display a genome map with integrated AMR data."""
    st.subheader("Integrated Genome Map")
    
    # Cache key for map data
    cache_key = f"integration_map_{bakta_job_id}_{amr_job_id}"
    
    if cache_key not in st.session_state:
        # Check if we have overview data that includes map data
        overview_key = f"integration_overview_{bakta_job_id}_{amr_job_id}"
        if overview_key in st.session_state:
            # Use data from overview
            overview_data = st.session_state[overview_key]
            visualization_data = overview_data["visualization_data"]
            st.session_state[cache_key] = visualization_data
        else:
            with st.spinner("Generating genome map..."):
                # Get job managers
                bakta_job_manager = run_async(lambda: BaktaJobManager())
                amr_db_manager = run_async(lambda: AMRDatabaseManager())
                
                # Get annotations and AMR data
                annotations = run_async(bakta_job_manager.get_annotations, bakta_job_id)
                amr_job_data = run_async(get_amr_data_for_job, amr_db_manager, amr_job_id)
                
                # Create DataFrame
                features_df = create_feature_dataframe(annotations)
                
                # Prepare visualization data
                visualization_data = create_integrated_visualization_data(features_df, amr_job_data)
                
                # Cache the data
                st.session_state[cache_key] = visualization_data
    
    # Use cached data
    visualization_data = st.session_state[cache_key]
    
    # Get genome map data
    genome_map_data = visualization_data.get("genome_map", [])
    
    if not genome_map_data:
        st.info("No genome map data available.")
        return
    
    # Allow user to select contig
    contig_options = [contig["contig"] for contig in genome_map_data]
    selected_contig = st.selectbox("Select Contig", options=contig_options)
    
    # Find the selected contig data
    contig_data = next((c for c in genome_map_data if c["contig"] == selected_contig), None)
    
    if not contig_data:
        st.error("Selected contig data not found.")
        return
    
    # Display contig information
    st.metric("Contig Length", f"{contig_data['length']:,} bp")
    st.metric("Features", len(contig_data.get("features", [])))
    
    # Create a linear genome visualization
    with st.spinner("Rendering genome map..."):
        # Create Plotly figure for genome visualization
        fig = go.Figure()
        
        # Add contig backbone
        fig.add_shape(
            type="line",
            x0=0, x1=contig_data["length"],
            y0=0, y1=0,
            line=dict(color="gray", width=3)
        )
        
        # Add features
        colors = {
            "CDS": "blue",
            "tRNA": "green",
            "rRNA": "red",
            "tmRNA": "purple",
            "ncRNA": "orange"
        }
        
        features = contig_data.get("features", [])
        for feature in features:
            # Determine color
            color = colors.get(feature["type"], "gray")
            
            # For AMR-related features, use a different color
            if feature.get("amr_related", False):
                color = "red"
            
            # Determine y-position based on strand
            y_pos = 0.1 if feature["strand"] == "+" else -0.1
            
            # Add feature as a rectangle
            fig.add_shape(
                type="rect",
                x0=feature["start"],
                x1=feature["end"],
                y0=y_pos - 0.05,
                y1=y_pos + 0.05,
                line=dict(color=color, width=1),
                fillcolor=color,
                opacity=0.7
            )
        
        # Update layout
        fig.update_layout(
            title=f"Genome Map for Contig: {selected_contig}",
            xaxis=dict(title="Position (bp)"),
            yaxis=dict(
                title="",
                showticklabels=False,
                range=[-0.2, 0.2]
            ),
            height=300,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        
        # Show the figure
        st.plotly_chart(fig, use_container_width=True)
    
    # Add feature filter
    st.subheader("Filter Features")
    feature_types = list(set(f["type"] for f in features))
    selected_types = st.multiselect(
        "Feature Types",
        options=feature_types,
        default=feature_types
    )
    
    # Filter features
    filtered_features = [f for f in features if f["type"] in selected_types]
    
    # Show feature table
    if filtered_features:
        # Convert to DataFrame for display
        features_df = pd.DataFrame(filtered_features)
        
        # Add readable names
        features_df["Position"] = features_df.apply(lambda row: f"{row['start']}-{row['end']}", axis=1)
        features_df["Feature"] = features_df.apply(lambda row: f"{row['name']}" if row['name'] else f"{row['type']} at {row['start']}-{row['end']}", axis=1)
        
        # Display table
        st.dataframe(
            features_df[["Feature", "type", "Position", "strand"]],
            column_config={
                "Feature": st.column_config.TextColumn("Feature"),
                "type": st.column_config.TextColumn("Type"),
                "Position": st.column_config.TextColumn("Position"),
                "strand": st.column_config.TextColumn("Strand")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No features match the selected filters.")


def display_feature_amr_correlation(bakta_job_id: str, amr_job_id: str):
    """Display correlation analysis between genomic features and AMR genes."""
    st.subheader("Feature-AMR Correlation Analysis")
    
    # Cache key
    cache_key = f"integration_correlation_{bakta_job_id}_{amr_job_id}"
    
    if cache_key not in st.session_state:
        # Check if we have overview data
        overview_key = f"integration_overview_{bakta_job_id}_{amr_job_id}"
        if overview_key in st.session_state:
            # Use data from overview
            overview_data = st.session_state[overview_key]
            features_df = overview_data["features_df"]
            amr_data = overview_data["amr_data"]
            correlations = overview_data["correlations"]
            
            # Calculate correlation statistics
            correlation_stats = calculate_amr_feature_correlations(features_df, amr_data)
            
            # Store in cache
            st.session_state[cache_key] = {
                "features_df": features_df,
                "amr_data": amr_data,
                "correlations": correlations,
                "correlation_stats": correlation_stats
            }
        else:
            with st.spinner("Calculating correlations..."):
                # Get job managers
                bakta_job_manager = run_async(lambda: BaktaJobManager())
                amr_db_manager = run_async(lambda: AMRDatabaseManager())
                
                # Get annotations and AMR data
                annotations = run_async(bakta_job_manager.get_annotations, bakta_job_id)
                amr_job_data = run_async(get_amr_data_for_job, amr_db_manager, amr_job_id)
                
                # Create DataFrame
                features_df = create_feature_dataframe(annotations)
                
                # Get correlations
                correlations = run_async(find_resistance_genes_near_features, 
                                        amr_db_manager, bakta_job_id, amr_job_id)
                
                # Calculate correlation statistics
                correlation_stats = calculate_amr_feature_correlations(features_df, amr_job_data)
                
                # Cache the data
                st.session_state[cache_key] = {
                    "features_df": features_df,
                    "amr_data": amr_job_data,
                    "correlations": correlations,
                    "correlation_stats": correlation_stats
                }
    
    # Use cached data
    correlation_data = st.session_state[cache_key]
    features_df = correlation_data["features_df"]
    amr_data = correlation_data["amr_data"]
    correlations = correlation_data["correlations"]
    correlation_stats = correlation_data["correlation_stats"]
    
    # Display correlation statistics
    st.markdown("### Statistical Correlation Analysis")
    
    if not correlation_stats.empty:
        # Create bar chart for correlation scores
        fig = px.bar(
            correlation_stats,
            x="feature_category",
            y="amr_relevance_score",
            color="significant",
            title="AMR Relevance by Feature Category",
            labels={
                "feature_category": "Feature Category",
                "amr_relevance_score": "AMR Relevance Score",
                "significant": "Statistically Significant"
            },
            color_discrete_map={True: "green", False: "gray"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display data table
        with st.expander("View Correlation Statistics"):
            st.dataframe(
                correlation_stats,
                column_config={
                    "feature_category": st.column_config.TextColumn("Feature Category"),
                    "amr_relevance_score": st.column_config.NumberColumn("AMR Relevance Score", format="%.2f"),
                    "p_value": st.column_config.NumberColumn("P-Value", format="%.3f"),
                    "significant": st.column_config.CheckboxColumn("Significant")
                },
                hide_index=True
            )
    else:
        st.info("No correlation statistics available.")
    
    # Display individual feature correlations
    st.markdown("### Individual Feature Correlations")
    
    if correlations:
        # Convert to DataFrame
        correlations_df = pd.DataFrame(correlations)
        
        # Add a filter for feature type
        feature_types = correlations_df["feature_type"].unique().tolist()
        selected_types = st.multiselect(
            "Filter by Feature Type",
            options=feature_types,
            default=["CDS"]
        )
        
        # Filter by selected types
        filtered_df = correlations_df[correlations_df["feature_type"].isin(selected_types)]
        
        if not filtered_df.empty:
            # Display as interactive table
            st.dataframe(
                filtered_df,
                column_config={
                    "feature_id": st.column_config.TextColumn("Feature ID"),
                    "feature_type": st.column_config.TextColumn("Type"),
                    "contig": st.column_config.TextColumn("Contig"),
                    "position": st.column_config.TextColumn("Position"),
                    "strand": st.column_config.TextColumn("Strand"),
                    "product": st.column_config.TextColumn("Product"),
                    "potential_amr_relevance": st.column_config.TextColumn("AMR Relevance")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No features match the selected filter.")
    else:
        st.info("No feature correlation data available.")


def display_detailed_analysis(bakta_job_id: str, amr_job_id: str):
    """Display detailed analysis for specific features and AMR genes."""
    st.subheader("Detailed Analysis")
    
    # Check if we have overview data
    overview_key = f"integration_overview_{bakta_job_id}_{amr_job_id}"
    if overview_key not in st.session_state:
        st.info("Please view the Overview tab first to load the data.")
        return
    
    # Get overview data
    overview_data = st.session_state[overview_key]
    features_df = overview_data["features_df"]
    
    # Allow user to select a feature
    if not features_df.empty:
        # Create feature selector
        feature_options = []
        for _, row in features_df.iterrows():
            display_name = f"{row['feature_type']}: "
            if 'gene' in row and row['gene']:
                display_name += f"{row['gene']} - "
            if 'product' in row and row['product']:
                display_name += f"{row['product']}"
            else:
                display_name += f"{row['feature_id']}"
            
            feature_options.append({
                "id": row['feature_id'],
                "display": display_name
            })
        
        # Create selectbox for features
        selected_display = st.selectbox(
            "Select Feature for Detailed Analysis",
            options=[opt["display"] for opt in feature_options]
        )
        
        # Get selected feature ID
        selected_feature_id = next(opt["id"] for opt in feature_options if opt["display"] == selected_display)
        
        # Get detailed feature data
        try:
            # Get job managers
            amr_db_manager = run_async(lambda: AMRDatabaseManager())
            
            # Get integrated feature data
            feature_data = run_async(
                integrate_feature_with_amr, 
                amr_db_manager, 
                selected_feature_id,
                bakta_job_id,
                amr_job_id
            )
            
            if feature_data:
                # Display feature details
                st.markdown("### Feature Details")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Feature ID:** {feature_data['feature_id']}")
                    st.markdown(f"**Type:** {feature_data['feature_type']}")
                    st.markdown(f"**Location:** {feature_data['contig']}:{feature_data['start']}-{feature_data['end']} ({feature_data['strand']})")
                
                with col2:
                    attributes = feature_data["attributes"]
                    if "product" in attributes:
                        st.markdown(f"**Product:** {attributes['product']}")
                    if "gene" in attributes:
                        st.markdown(f"**Gene:** {attributes['gene']}")
                    if "protein_id" in attributes:
                        st.markdown(f"**Protein ID:** {attributes['protein_id']}")
                
                # Display AMR associations
                st.markdown("### AMR Associations")
                
                amr_associations = feature_data.get("amr_associations", [])
                if amr_associations:
                    # Convert to DataFrame
                    associations_df = pd.DataFrame(amr_associations)
                    
                    # Display as table
                    st.dataframe(
                        associations_df,
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Integration visualization (placeholder)
                    st.markdown("### Visualization")
                    st.info("Interactive visualization of feature-AMR relationships will be shown here.")
                else:
                    st.info("No AMR associations found for this feature.")
                
                # Show all attributes in JSON format
                with st.expander("All Feature Attributes"):
                    st.json(feature_data["attributes"])
            else:
                st.error("Feature data not found.")
        
        except Exception as e:
            show_error(f"Error loading feature details: {str(e)}")
            logger.error(f"Error in detailed analysis: {str(e)}", exc_info=True)
    else:
        st.info("No features available for analysis.")

# Main entry point for integrated analysis UI
def display_integrated_analysis_ui():
    """Main entry point for the integrated analysis UI."""
    display_integrated_analysis()

if __name__ == "__main__":
    display_integrated_analysis_ui()
