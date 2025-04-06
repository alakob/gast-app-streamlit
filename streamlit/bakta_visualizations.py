"""
Bakta visualization components for the Streamlit UI.
"""
import streamlit as st
import os
import base64
from pathlib import Path
import glob
import logging

logger = logging.getLogger("bakta-visualizer")

def get_latest_bakta_job_id():
    """
    Get the most recent Bakta job ID from the results directory.
    
    Returns:
        str: The latest Bakta job ID or None if no jobs found
    """
    try:
        results_dir = os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")
        
        # Look for all info.txt files which contain job metadata
        info_files = glob.glob(f"{results_dir}/*_info.txt")
        if not info_files:
            return None
            
        # Sort by modification time (newest first)
        info_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Extract job ID from filename (remove _info.txt suffix)
        latest_job_id = os.path.basename(info_files[0]).replace("_info.txt", "")
        logger.info(f"Found latest Bakta job ID: {latest_job_id}")
        return latest_job_id
        
    except Exception as e:
        logger.error(f"Error finding latest Bakta job: {str(e)}")
        return None
        
def find_visualization_files(job_id):
    """
    Find the visualization files (SVG and PNG) for a given job ID
    
    Args:
        job_id: Bakta job ID
        
    Returns:
        tuple: (svg_path, png_path) or (None, None) if not found
    """
    try:
        results_dir = os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")
        
        # Look for SVG circular plot
        svg_pattern = f"{results_dir}/{job_id}*SVGCircularPlot*"
        svg_files = glob.glob(svg_pattern)
        
        # Look for PNG circular plot
        png_pattern = f"{results_dir}/{job_id}*PNGCircularPlot*"
        png_files = glob.glob(png_pattern)
        
        svg_path = svg_files[0] if svg_files else None
        png_path = png_files[0] if png_files else None
        
        logger.info(f"Found visualization files for job {job_id}: SVG={svg_path}, PNG={png_path}")
        return svg_path, png_path
        
    except Exception as e:
        logger.error(f"Error finding visualization files: {str(e)}")
        return None, None

def get_file_as_base64(file_path):
    """
    Convert a file to base64 for embedding in HTML
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Base64 encoded file content
    """
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.error(f"Error encoding file as base64: {str(e)}")
        return None

def display_bakta_visualizations(job_id=None):
    """
    Display Bakta visualizations (SVG and PNG circular plots) in the Streamlit UI
    
    Args:
        job_id: Bakta job ID (optional, will use latest if not provided)
    """
    if not job_id:
        job_id = get_latest_bakta_job_id()
        
    if not job_id:
        st.info("No Bakta analysis results found. Please run a Bakta analysis first.")
        return
        
    # Find visualization files
    svg_path, png_path = find_visualization_files(job_id)
    
    if not svg_path and not png_path:
        st.warning("No visualization files found for this Bakta analysis.")
        return
        
    st.subheader("Bakta Genome Visualization")
    
    # Show the job ID
    st.caption(f"Job ID: {job_id}")
    
    # Create tabs for different visualization types
    viz_tabs = st.tabs(["Interactive SVG", "PNG Image"])
    
    # SVG Visualization (Interactive)
    with viz_tabs[0]:
        if svg_path:
            try:
                # Read SVG content
                with open(svg_path, "r") as f:
                    svg_content = f.read()
                    
                # Display SVG directly using HTML
                st.components.v1.html(svg_content, height=600, scrolling=True)
                
                # Download button for SVG
                svg_base64 = get_file_as_base64(svg_path)
                if svg_base64:
                    href = f'<a href="data:image/svg+xml;base64,{svg_base64}" download="{os.path.basename(svg_path)}">Download SVG</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Error displaying SVG visualization: {str(e)}")
        else:
            st.info("SVG visualization not available for this job.")
    
    # PNG Visualization (Static Image)
    with viz_tabs[1]:
        if png_path:
            try:
                # Display PNG
                st.image(png_path, caption="Circular Genome Plot")
                
                # Download button for PNG
                with open(png_path, "rb") as f:
                    btn = st.download_button(
                        label="Download PNG",
                        data=f,
                        file_name=os.path.basename(png_path),
                        mime="image/png"
                    )
                    
            except Exception as e:
                st.error(f"Error displaying PNG visualization: {str(e)}")
        else:
            st.info("PNG visualization not available for this job.")
            
    # Add a link to view in Bakta web interface if available
    try:
        info_path = f"{os.environ.get('BAKTA_RESULTS_DIR', '/app/results/bakta')}/{job_id}_info.txt"
        if os.path.exists(info_path):
            with open(info_path, "r") as f:
                lines = f.readlines()
                url_line = next((line for line in lines if line.startswith("URL:")), None)
                if url_line:
                    url = url_line.strip().replace("URL: ", "")
                    st.markdown(f"[View in Bakta Web Interface]({url})")
    except Exception as e:
        logger.error(f"Error retrieving Bakta web URL: {str(e)}")

def display_bakta_results_tab():
    """
    Main function to display the Bakta results tab.
    This includes visualizations and other result files.
    """
    st.subheader("Bakta Annotation Results")
    
    job_id = get_latest_bakta_job_id()
    
    if not job_id:
        st.info("No Bakta analysis results found. Please run a Bakta analysis first.")
        return
        
    # Display visualizations
    display_bakta_visualizations(job_id)
    
    # Show other result files
    with st.expander("All Result Files", expanded=False):
        results_dir = os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")
        result_files = glob.glob(f"{results_dir}/{job_id}*")
        
        if not result_files:
            st.info("No result files found.")
            return
            
        # Group files by type
        file_groups = {
            "Sequence Files": [f for f in result_files if any(ext in f for ext in ['.FAA', '.FNA', '.FFN'])],
            "Annotation Files": [f for f in result_files if any(ext in f for ext in ['.GFF3', '.GBFF'])],
            "Data Files": [f for f in result_files if any(ext in f for ext in ['.JSON', '.TSV'])],
            "Logs": [f for f in result_files if '.TXTLogs' in f],
            "Other": [f for f in result_files if not any(ext in f for ext in ['.FAA', '.FNA', '.FFN', '.GFF3', '.GBFF', '.JSON', '.TSV', '.TXTLogs', 'PNGCircularPlot', 'SVGCircularPlot'])]
        }
        
        # Display files by group
        for group, files in file_groups.items():
            if files:
                st.subheader(group)
                for file_path in files:
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Create a readable file size
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size/1024:.1f} KB"
                    else:
                        size_str = f"{file_size/(1024*1024):.1f} MB"
                        
                    # Display file with download button if appropriate
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"{file_name} ({size_str})")
                    
                    # Add download button for non-binary files that are reasonably sized
                    if file_size < 5 * 1024 * 1024 and any(ext in file_path for ext in ['.JSON', '.TSV', '.TXT', '.FAA', '.FNA', '.FFN', '.GFF3', '.GBFF']):
                        with col2:
                            try:
                                with open(file_path, "rb") as f:
                                    st.download_button(
                                        label="Download",
                                        data=f,
                                        file_name=file_name,
                                        mime="application/octet-stream"
                                    )
                            except Exception as e:
                                st.error(f"Error creating download button: {str(e)}")
                    else:
                        with col2:
                            st.text("(Large file)")
