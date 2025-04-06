"""
Reusable UI components for the AMR Streamlit app.
"""
import streamlit as st
import pandas as pd
import json
import os
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple

# Set up logging
logger = logging.getLogger("ui_components")

# Import column formatting utility
from utils import format_column_names

# Import Bakta visualizations and summary if available
try:
    import bakta_visualizations
    BAKTA_VIZ_AVAILABLE = True
except ImportError:
    BAKTA_VIZ_AVAILABLE = False
    
try:
    import bakta_summary
    BAKTA_SUMMARY_AVAILABLE = True
except ImportError:
    BAKTA_SUMMARY_AVAILABLE = False

def create_sidebar() -> None:
    """Create the application sidebar with configuration options."""
    import config
    
# ------------------ Sidebar ------------------ #
    import os
    # Get the current script directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the logo file
    logo_path = os.path.join(current_dir, "logo.png")
    st.sidebar.image(logo_path)


    st.sidebar.title("Model Settings")
    
    # Model selection
    model_options = [
        "DraGNOME-50m-v1",
        "DraGNOME-2.5b-v1",  # should be default model
        "DraPLASMID-2.5b-v1",
        "DraGNOME-500m-v1",  # New models
       "DraGNOME-50m-v2"
    ]
    selected_model = st.sidebar.selectbox(
        "Select Model", 
        model_options, 
        index=0,  # Set DraGNOME-2.5b-v1 as default
        help="Select the AMR prediction model to use"
    )
    
    # Store the full model name in session state (for API calls)
    # Changed from model_id to model_name to match the API's expected parameter name
    st.session_state.amr_params["model_name"] = f"alakob/{selected_model}"
    
    # For backwards compatibility, also store as model_id
    st.session_state.amr_params["model_id"] = f"alakob/{selected_model}"
    
    # Model description
    model_descriptions = {
        "DraGNOME-2.5b-v1": "Specialized model for bacterial genome analysis and AMR prediction",
        "DraPLASMID-2.5b-v1": "Specialized model for plasmid analysis and AMR prediction",
        "DraGNOME-500m-v1": "Medium-sized model (500M parameters) for bacterial genome analysis",
        "DraGNOME-50m-v1": "Lightweight model (50M parameters, version 1) for rapid genome analysis",
        "DraGNOME-50m-v2": "Improved lightweight model (50M parameters, version 2) with enhanced accuracy"
    }
    
    st.sidebar.markdown(f"**Description**: {model_descriptions.get(selected_model, '')}")
    
    # Model Parameters section
    with st.sidebar.expander("Model Parameters", expanded=False):
        # Add AMR prediction parameters
        if "amr_params" not in st.session_state:
            st.session_state.amr_params = {}
        
        # Max sequence length for tokenizer
        st.session_state.amr_params["max_seq_length"] = st.slider(
            "Max Sequence Length for Tokenizer", 
            min_value=100, 
            max_value=2000, 
            value=1000,
            step=100,
            help="Maximum sequence length for the tokenizer"
        )
        
        # Trust remote code
        st.session_state.amr_params["trust_remote_code"] = st.checkbox(
            "Trust Remote Code",
            value=True,
            help="Allow the model to execute remote code"
        )


    # Computation device
    st.sidebar.subheader("Select Computation Device")

    with st.sidebar.expander("Device", expanded=False):
        # Device selection
        device = st.sidebar.radio(
            "Device",
            options=["CPU", "GPU"],
            index=0,
            horizontal=False,
            help="Select the device to run predictions on"
        )
        st.session_state.amr_params["device"] = device
    
    # Processing settings
    st.sidebar.subheader("Analysis Settings")

    with st.sidebar.expander("⚡ Processing Settings", expanded=False):
        # Batch size
        st.session_state.amr_params["batch_size"] = st.slider(
            "Batch Size",
            min_value=1,
            max_value=32,
            value=8,
            step=1,
            help="Number of sequences to process in a single batch"
        )
        
        # Segment length
        st.session_state.amr_params["segment_length"] = st.slider(
            "Segment Length",
            min_value=0,
            max_value=10000,
            value=6000,
            step=100,
            help="Length of sequence segments for processing"
        )
        
        # Segment overlap
        st.session_state.amr_params["segment_overlap"] = st.slider(
            "Segment Overlap",
            min_value=0,
            max_value=2000,
            value=1200,
            step=100,
            help="Overlap between adjacent segments"
        )
        
        # Minimum segment length
        st.session_state.amr_params["min_segment_length"] = st.slider(
            "Minimum Segment Length",
            min_value=6,
            max_value=100,
            value=6,
            step=1,
            help="Minimum length of sequence segments"
        )
    
    # Sequence processing settings
    with st.sidebar.expander("Thresholds Settings", expanded=False):
        # Aggregation method
        st.session_state.amr_params["aggregation_method"] = st.selectbox(
            "Aggregation Method",
            options=["average", "majority", "any"],
            index=0,
            help="Method used to aggregate predictions across segments"
        )
        
        # Resistance threshold
        st.session_state.amr_params["resistance_threshold"] = st.slider(
            "Resistance Threshold", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.5,
            step=0.01,
            help="Minimum confidence threshold for AMR detection"
        )
    
    st.sidebar.markdown("---")
    
    # Status indicators
    st.sidebar.subheader("Status")
    
    # AMR API Status
    amr_status = st.sidebar.empty()
    bakta_status = st.sidebar.empty()
    
    # Set initial status icons
    amr_status.markdown("⚪ **AMR API**: Not connected")
    bakta_status.markdown("⚪ **Bakta API**: Not connected")
    
    # Allow updating status from main app
    st.session_state.update_amr_status = lambda s, c: amr_status.markdown(
        f"{get_status_icon(c)} **AMR API**: {s}"
    )
    
    st.session_state.update_bakta_status = lambda s, c: bakta_status.markdown(
        f"{get_status_icon(c)} **Bakta API**: {s}"
    )
    
    st.sidebar.markdown("---")
    
    # Footer
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "This app allows prediction of antimicrobial resistance "
        "genes in bacterial genomes and optional genome annotation "
        "using Bakta."
    )
    st.sidebar.markdown("Created by [Blaise Alako](https://www.linkedin.com/in/blaisealako/).")
    # Add "GitHub" link to the sidebar
    st.sidebar.markdown(
        "[GitHub](https://github.com/alakob/)"
    )
    st.sidebar.markdown("""---""")


def get_status_icon(status: str) -> str:
    """
    Get an icon for a status string.
    
    Args:
        status: Status string ("success", "warning", "error", "info")
    
    Returns:
        Unicode icon character
    """
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
        "pending": "⏳"
    }
    
    return icons.get(status.lower(), "⚪")

def create_annotation_settings_tab() -> None:
    """Create the Annotation Settings tab content."""
    st.subheader("Bakta Annotation Settings")
    
    # Function to be called when Bakta checkbox changes
    def on_bakta_enable_change():
        # Update Bakta API status based on checkbox
        if st.session_state.enable_bakta:
            # Only try to connect if Bakta is enabled
            try:
                from api_client import create_bakta_interface
                bakta_client = create_bakta_interface()
                st.session_state.update_bakta_status("Connected", "success")
            except Exception as e:
                st.session_state.update_bakta_status(f"Not connected: {str(e)}", "error")
        else:
            # If Bakta is disabled, update status accordingly
            st.session_state.update_bakta_status("Disabled", "info")
    
    # Enable/disable Bakta annotation - always default to enabled
    # Force enable bakta if it's not explicitly set or if it's False
    if "enable_bakta" not in st.session_state or st.session_state.enable_bakta is False:
        st.session_state.enable_bakta = True
        # Trigger the on_change callback manually to ensure API connection is tested
        on_bakta_enable_change()
        
    st.checkbox(
        "Enable Bakta genome annotation",
        value=st.session_state.enable_bakta,
        key="enable_bakta",  # Use key to reference in session state
        on_change=on_bakta_enable_change,  # Run this function when value changes
        help="When enabled, the sequence will be submitted for Bakta annotation after AMR prediction"
    )
    
    if st.session_state.enable_bakta:
        # Initialize bakta params if not already present or update with new fields
        if "bakta_params" not in st.session_state:
            import config
            st.session_state.bakta_params = {}

        # Default values dictionary
        import config
        default_params = {
            "genus": config.DEFAULT_GENUS,
            "species": config.DEFAULT_SPECIES,
            "strain": "",
            "complete_genome": False,
            "translation_table": config.DEFAULT_TRANSLATION_TABLE,
            "locus": "",
            "locus_tag": "",
            "plasmid_name": "",
            "min_contig_length": 200,
            "keep_contig_headers": True,
            "compliant": False,
            "cell_envelope": "UNKNOWN",
            "prodigal_tf": None,
            "replicon_table": None,
            "skip_detection": []
        }
        
        # Update session state with any missing default values
        for key, value in default_params.items():
            if key not in st.session_state.bakta_params:
                st.session_state.bakta_params[key] = value
        
        # Optional Files Section
        st.header("Optional Files")
        
        # Prodigal Training File
        uploaded_prodigal = st.file_uploader(
            "Upload Prodigal Training File (Optional)",
            type=["trn"],
            help="Upload a Prodigal training file for custom gene prediction",
            key="prodigal_upload"
        )
        if uploaded_prodigal is not None:
            st.session_state.bakta_params["prodigal_tf"] = uploaded_prodigal
        
        # Replicon Info File
        uploaded_replicon = st.file_uploader(
            "Upload Replicon Info File (Optional)",
            type=["tsv", "csv"],
            help="Upload a replicon table file in TSV or CSV format",
            key="replicon_upload"
        )
        if uploaded_replicon is not None:
            st.session_state.bakta_params["replicon_table"] = uploaded_replicon
        
        # Configuration Options Section
        st.header("Configuration Options")
        
        col1, col2 = st.columns(2)
        with col1:
            # Minimum Contig Length
            st.session_state.bakta_params["min_contig_length"] = st.slider(
                "Minimum Contig Length",
                min_value=1,
                max_value=10000,
                value=st.session_state.bakta_params["min_contig_length"],
                help="Minimum contig length to include in the analysis"
            )
        
        with col2:
            # Translation Table
            st.session_state.bakta_params["translation_table"] = st.selectbox(
                "Translation Table",
                options=[11, 4],
                index=0,  # Default to 11 (Bacterial, Archaeal)
                help="Genetic code / translation table: 11) Bacterial, Archaeal, 4) Mycoplasma"
            )
        
        col1, col2 = st.columns(2)
        with col1:
            # Complete Genome
            st.session_state.bakta_params["complete_genome"] = st.checkbox(
                "Complete Genome",
                value=st.session_state.bakta_params["complete_genome"],
                help="Indicate if the genome is complete"
            )
        
        with col2:
            # Keep Contig Headers
            st.session_state.bakta_params["keep_contig_headers"] = st.checkbox(
                "Keep Contig Headers",
                value=st.session_state.bakta_params["keep_contig_headers"],
                help="Keep the original contig headers in the annotation"
            )
        
        # Cell envelope type
        st.session_state.bakta_params["cell_envelope"] = st.selectbox(
            "Cell Envelope Type",
            options=["UNKNOWN", "MONODERM", "DIDERM"],
            index=0,
            help="Cell envelope type: UNKNOWN, MONODERM (Gram+), or DIDERM (Gram-)"
        )
        
        # Custom Taxonomy Section
        st.header("Custom Taxonomy (Optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.bakta_params["genus"] = st.text_input(
                "Genus",
                value=st.session_state.bakta_params["genus"],
                help="Genus name for annotation"
            )
        
        with col2:
            st.session_state.bakta_params["species"] = st.text_input(
                "Species",
                value=st.session_state.bakta_params["species"],
                help="Species name for annotation"
            )
        
        # Strain
        st.session_state.bakta_params["strain"] = st.text_input(
            "Strain",
            value=st.session_state.bakta_params["strain"],
            help="Strain name for annotation (optional)"
        )
        
        # Locus Information Section
        st.header("Locus Information (Optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.bakta_params["locus"] = st.text_input(
                "Locus",
                value=st.session_state.bakta_params["locus"],
                help="Locus name prefix (optional)"
            )
        
        with col2:
            st.session_state.bakta_params["locus_tag"] = st.text_input(
                "Locus Tag",
                value=st.session_state.bakta_params["locus_tag"],
                help="Locus tag prefix (optional)"
            )
        
        # Plasmid Name
        st.session_state.bakta_params["plasmid_name"] = st.text_input(
            "Plasmid Name",
            value=st.session_state.bakta_params["plasmid_name"],
            help="Plasmid name (optional)"
        )
        
        # Additional Options Section
        st.header("Additional Options")
        
        # Create a 3-column layout for checkboxes
        col1, col2, col3 = st.columns(3)
        
        with col1:
            compliant = st.checkbox(
                "Compliant Annotation",
                value=st.session_state.bakta_params.get("compliant", False),
                help="Create INSDC compliant annotation"
            )
            st.session_state.bakta_params["compliant"] = compliant
            
            skip_trna = st.checkbox(
                "Skip tRNA Detection",
                value="trna" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip tRNA detection step"
            )
            if skip_trna and "trna" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("trna")
            elif not skip_trna and "trna" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("trna")
            
            skip_tmrna = st.checkbox(
                "Skip tmRNA Detection",
                value="tmrna" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip tmRNA detection step"
            )
            if skip_tmrna and "tmrna" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("tmrna")
            elif not skip_tmrna and "tmrna" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("tmrna")
        
        with col2:
            skip_rrna = st.checkbox(
                "Skip rRNA Detection",
                value="rrna" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip rRNA detection step"
            )
            if skip_rrna and "rrna" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("rrna")
            elif not skip_rrna and "rrna" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("rrna")
            
            skip_ncrna = st.checkbox(
                "Skip ncRNA Detection",
                value="ncrna" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip ncRNA detection step"
            )
            if skip_ncrna and "ncrna" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("ncrna")
            elif not skip_ncrna and "ncrna" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("ncrna")
            
            skip_ncrna_region = st.checkbox(
                "Skip ncRNA Region Detection",
                value="ncrna_region" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip ncRNA region detection step"
            )
            if skip_ncrna_region and "ncrna_region" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("ncrna_region")
            elif not skip_ncrna_region and "ncrna_region" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("ncrna_region")
        
        with col3:
            skip_crispr = st.checkbox(
                "Skip CRISPR Detection",
                value="crispr" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip CRISPR array detection step"
            )
            if skip_crispr and "crispr" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("crispr")
            elif not skip_crispr and "crispr" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("crispr")
            
            skip_orf = st.checkbox(
                "Skip ORF Detection",
                value="orf" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip ORF detection step"
            )
            if skip_orf and "orf" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("orf")
            elif not skip_orf and "orf" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("orf")
            
            skip_gap = st.checkbox(
                "Skip Gap Detection",
                value="gap" in st.session_state.bakta_params.get("skip_detection", []),
                help="Skip gap detection step"
            )
            if skip_gap and "gap" not in st.session_state.bakta_params.get("skip_detection", []):
                if "skip_detection" not in st.session_state.bakta_params:
                    st.session_state.bakta_params["skip_detection"] = []
                st.session_state.bakta_params["skip_detection"].append("gap")
            elif not skip_gap and "gap" in st.session_state.bakta_params.get("skip_detection", []):
                st.session_state.bakta_params["skip_detection"].remove("gap")

def create_sequence_input_tab() -> None:
    """Create the Sequence Input tab content."""
    st.subheader("Input Sequence")
    
    # Create tabs for different input methods
    input_tab1, input_tab2 = st.tabs(["Text Input", "File Upload"])
    
    # Text input method
    with input_tab1:
        # Initialize sequence in session state if not present
        if "sequence" not in st.session_state:
            st.session_state.sequence = ""
            st.session_state.sequence_valid = False
        
        # Sample sequence button
        if st.button("Load Sample Sequence"):
            from utils import read_sample_sequence
            sample_seq = read_sample_sequence()
            if sample_seq:
                st.session_state.sequence = sample_seq
                st.session_state.sequence_valid = True
        
        # Sequence text area
        sequence = st.text_area(
            "Enter DNA Sequence (FASTA format accepted)",
            value=st.session_state.sequence,
            height=200,
            help="Paste your DNA sequence here. FASTA format with headers is accepted."
        )
        
        # Update sequence in session state
        if sequence != st.session_state.sequence:
            st.session_state.sequence = sequence
            
            # Validate sequence
            from utils import is_valid_dna_sequence
            st.session_state.sequence_valid = is_valid_dna_sequence(sequence)
        
        # Show validation status
        if st.session_state.sequence:
            if st.session_state.sequence_valid:
                st.success("Valid DNA sequence")
                
                # Show sequence statistics
                from utils import get_sequence_statistics
                stats = get_sequence_statistics(st.session_state.sequence)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Sequence Length", f"{stats['length']:,} bp")
                with col2:
                    st.metric("GC Content", f"{stats['gc_content']}%")
                with col3:
                    st.metric("N Count", stats['n_count'])
            else:
                st.error("Invalid DNA sequence. Please check for non-DNA characters.")
    
    # File upload method
    with input_tab2:
        uploaded_file = st.file_uploader(
            "Upload FASTA or text file",
            type=["fasta", "fa", "txt"],
            help="Upload a file containing your DNA sequence"
        )
        
        if uploaded_file is not None:
            # Read and process the file
            file_data = uploaded_file.getvalue()
            
            # Parse FASTA file
            from utils import parse_fasta_file
            sequence, headers = parse_fasta_file(file_data)
            
            # Update sequence in session state
            st.session_state.sequence = '\n'.join(headers + [sequence])
            
            # Validate sequence
            from utils import is_valid_dna_sequence
            st.session_state.sequence_valid = is_valid_dna_sequence(sequence)
            
            # Show file info
            st.info(f"File: {uploaded_file.name}, Size: {len(file_data):,} bytes")
            
            if headers:
                with st.expander("Sequence Headers", expanded=False):
                    for header in headers:
                        st.code(header)
            
            # Show validation status
            if st.session_state.sequence_valid:
                st.success("Valid DNA sequence")
                
                # Show sequence statistics
                from utils import get_sequence_statistics
                stats = get_sequence_statistics(sequence)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Sequence Length", f"{stats['length']:,} bp")
                with col2:
                    st.metric("GC Content", f"{stats['gc_content']}%")
                with col3:
                    st.metric("N Count", stats['n_count'])
            else:
                st.error("Invalid DNA sequence. Please check the file contents.")
    
    # Submit button
    st.markdown("---")
    
    submit_disabled = not st.session_state.get("sequence_valid", False)
    submit_help = "Please provide a valid DNA sequence first" if submit_disabled else ""
    
    submit_button = st.button(
        "Submit for Analysis", 
        disabled=submit_disabled,
        help=submit_help,
        type="primary"
    )
    
    # Store button state
    st.session_state.submit_clicked = submit_button

def create_results_tab() -> None:
    """Create the Results tab content."""
    st.subheader("Analysis Results")
    
    # Create tabs for current results, annotation, and results history
    current_tab, annotation_tab, history_tab = st.tabs(["Current Analysis", "Annotation", "Results History"])
    
    # Current Analysis Tab
    with current_tab:
        # Check if we have jobs or results
        has_amr_job = "amr_job_id" in st.session_state
        has_bakta_job = "bakta_job_id" in st.session_state
        
        if not (has_amr_job or has_bakta_job):
            st.info("Submit a sequence for analysis to see results here.")
        else:
            # Create tabs for AMR and Bakta results
            result_tabs = ["AMR Prediction"]
            if st.session_state.get("enable_bakta", False):
                result_tabs.append("Bakta Annotation")
            
            tab_objects = st.tabs(result_tabs)
            
            # Function to display job status with visual indicator
            def display_job_status(status: str) -> str:
                status_map = {
                    "SUBMITTED": "🔵 Submitted",
                    "PENDING": "⚪ Pending", 
                    "QUEUED": "🟠 Queued",
                    "RUNNING": "🟡 Running",
                    "PROCESSING": "🟡 Processing",
                    "SUCCESSFUL": "🟢 Completed",
                    "Completed": "🟢 Completed",
                    "FAILED": "🔴 Failed",
                    "CANCELLED": "⚫ Cancelled",
                    "ERROR": "🔴 Error",
                    "UNKNOWN": "❓ Unknown"
                }
                return status_map.get(status, f"❓ {status}")
            
            # AMR Prediction Results
            with tab_objects[0]:
                if has_amr_job:
                    amr_job_id = st.session_state.amr_job_id
                    amr_status = st.session_state.get("amr_status", "UNKNOWN")
                    
                    # Display job info with status indicator
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.info(f"Job ID: {amr_job_id}")
                    with col2:
                        st.markdown(f"**Status: {display_job_status(amr_status)}**")
                    
                    # Display progress bar for running jobs
                    if amr_status in ["RUNNING", "PROCESSING", "PENDING", "SUBMITTED", "QUEUED"]:
                        progress_placeholder = st.empty()
                        with progress_placeholder.container():
                            # Create a progress bar
                            import time
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Different messages for different stages
                            status_messages = {
                                "SUBMITTED": "Job submitted to the server...",
                                "PENDING": "Job pending in queue...",
                                "QUEUED": "Job is queued for processing...",
                                "RUNNING": "Processing sequence data...",
                                "PROCESSING": "Analyzing antimicrobial resistance..."
                            }
                            
                            # Display appropriate message
                            status_text.info(status_messages.get(amr_status, "Processing job..."))
                            
                            # Update progress value based on status
                            progress_values = {
                                "SUBMITTED": 0.1,
                                "PENDING": 0.2,
                                "QUEUED": 0.3,
                                "RUNNING": 0.6,
                                "PROCESSING": 0.8
                            }
                            progress_bar.progress(progress_values.get(amr_status, 0.5))
                            
                            # Add auto-refresh button
                            # Check if we should auto-refresh (either from force_status_check or auto_refresh_amr flag)
                            if st.session_state.get("force_status_check", False) or st.session_state.get("auto_refresh_amr", False):
                                # Reset the flags to prevent infinite loop
                                st.session_state["auto_refresh_amr"] = False
                                if "force_status_check" in st.session_state:
                                    st.session_state["force_status_check"] = False
                                # This will trigger the app's check_job_status function via rerun
                                st.rerun()
                            
                            # Manual refresh button
                            if st.button("Check Status Now", key="refresh_amr_status"):
                                # This will trigger the app's check_job_status function via rerun
                                st.rerun()
                            
                            st.warning("⏱️ Status updates automatically every few seconds. You can also use the button above to check immediately.")
                    
                    # Display results if available
                    if "amr_results" in st.session_state and st.session_state.amr_results:
                        results = st.session_state.amr_results
                        
                        # Only show mock data warning if appropriate
                        # Check if we have an actual result file for this job ID
                        # Import os within function scope to ensure it's available
                        import os as os_local
                        result_file = f"/Users/alakob/projects/gast-app-streamlit/results/amr_predictions_{amr_job_id}.tsv"
                        has_real_result = os_local.path.exists(result_file)
                        
                        # If the job has real results but is incorrectly marked as mock, fix that
                        if has_real_result and "_mock_job_ids" in st.session_state and amr_job_id in st.session_state["_mock_job_ids"]:
                            mock_job_ids = st.session_state["_mock_job_ids"]
                            mock_job_ids.remove(amr_job_id)
                            st.session_state["_mock_job_ids"] = mock_job_ids
                            st.session_state["using_real_amr_api"] = True
                            
                        # Only show mock warning if it's genuinely a mock job with no real results
                        if (amr_job_id.startswith("mock-") or 
                            ("_mock_job_ids" in st.session_state and amr_job_id in st.session_state["_mock_job_ids"])) and not has_real_result:
                            st.warning("⚠️ These are mock results for demonstration purposes.")
                        
                        try:
                            # Import the results_view_direct module to use specialized view functions
                            try:
                                from results_view_direct import view_amr_prediction_result
                            except ImportError:
                                # Try to import from the current directory
                                import sys
                                import os
                                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                                from results_view_direct import view_amr_prediction_result
                                
                            # Use the specialized view function
                            view_amr_prediction_result(amr_job_id, results)
                        except Exception as e:
                            st.error(f"Error displaying AMR results: {str(e)}")
                            
                            # Fall back to basic view
                            # Add view toggle
                            view_mode = st.radio(
                                "View as:",
                                options=["Table", "JSON"],
                                index=0,
                                horizontal=True
                            )
                            
                            if view_mode == "Table":
                                # This is a placeholder - actual implementation would depend on the structure of the results
                                if "predictions" in results:
                                    # Create a DataFrame from the predictions
                                    predictions = results["predictions"]
                                    if isinstance(predictions, list) and predictions:
                                        df = pd.DataFrame(predictions)
                                        # Format column names to Title Case
                                        df = format_column_names(df)
                                        st.dataframe(df)
                                    else:
                                        st.warning("No prediction data available")
                                else:
                                    st.json(results)
                            else:
                                # Show as formatted JSON
                                st.json(results)
                            
                            # Download options
                            col1, col2 = st.columns(2)
                            with col1:
                                download_json = st.download_button(
                                    "Download JSON",
                                    data=json.dumps(results, indent=2),
                                    file_name="amr_results.json",
                                    mime="application/json"
                                )
                            
                            with col2:
                                # Convert to CSV for download
                                from utils import convert_to_csv
                                csv_data = convert_to_csv(results)
                                
                                download_csv = st.download_button(
                                    "Download CSV",
                                    data=csv_data,
                                    file_name="amr_results.csv",
                                    mime="text/csv"
                                )
                    
                    elif "amr_error" in st.session_state:
                        st.error(f"Error: {st.session_state.amr_error}")
                    elif amr_status not in ["SUCCESSFUL", "Completed"]:
                        st.info("Waiting for AMR prediction to complete...")
                    else:
                        # If status is successful but no results, try to load them
                        st.info("Loading results data...")
                        try:
                            from api_client import create_amr_client
                            client = create_amr_client()
                            st.session_state.amr_results = client.get_prediction_results(amr_job_id)
                            st.success("Results loaded successfully!")
                            st.rerun()  # Force refresh to display results
                        except Exception as e:
                            st.error(f"Error loading results: {str(e)}")
                else:
                    st.info("Submit a sequence to run AMR prediction.")
            
            # Bakta Annotation Results
            if st.session_state.get("enable_bakta", False) and len(tab_objects) > 1:
                with tab_objects[1]:
                    if has_bakta_job:
                        bakta_job_id = st.session_state.bakta_job_id
                        bakta_status = st.session_state.get("bakta_status", "UNKNOWN")
                        
                        # Display job info with status indicator
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.info(f"Job ID: {bakta_job_id}")
                        with col2:
                            st.markdown(f"**Status: {display_job_status(bakta_status)}**")
                        
                        # Display progress bar for running jobs
                        if bakta_status in ["RUNNING", "PROCESSING", "PENDING", "SUBMITTED", "QUEUED"]:
                            progress_placeholder = st.empty()
                            with progress_placeholder.container():
                                # Create a progress bar
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                # Different messages for different stages
                                status_messages = {
                                    "SUBMITTED": "Job submitted to the server...",
                                    "PENDING": "Job pending in queue...",
                                    "QUEUED": "Job is queued for processing...",
                                    "RUNNING": "Performing genome annotation...",
                                    "PROCESSING": "Analyzing gene annotations..."
                                }
                                
                                # Display appropriate message
                                status_text.info(status_messages.get(bakta_status, "Processing job..."))
                                
                                # Update progress value based on status
                                progress_values = {
                                    "SUBMITTED": 0.1,
                                    "PENDING": 0.2,
                                    "QUEUED": 0.3,
                                    "RUNNING": 0.6,
                                    "PROCESSING": 0.8
                                }
                                progress_bar.progress(progress_values.get(bakta_status, 0.5))
                                
                                # Add auto-refresh button
                                # Check if we should auto-refresh (force_status_check or auto_refresh_bakta flag)
                                if st.session_state.get("force_status_check", False) or st.session_state.get("auto_refresh_bakta", False):
                                    # Reset the flags to prevent infinite loop
                                    st.session_state["auto_refresh_bakta"] = False
                                    if "force_status_check" in st.session_state:
                                        st.session_state["force_status_check"] = False
                                    # This will trigger the app's check_job_status function via rerun
                                    st.rerun()
                                
                                # Manual refresh button
                                if st.button("Check Status Now", key="refresh_bakta_status"):
                                    # This will trigger the app's check_job_status function
                                    st.rerun()
                                
                                st.warning("⏱️ Status updates automatically every few seconds.")
                        
                        # Initialize view_mode and results with default values
                        view_mode = "Summary"  # Default view mode
                        results = {}
                        
                        if "bakta_results" in st.session_state and st.session_state.bakta_results:
                            # Add view toggle
                            view_options = ["Summary", "Visualizations", "JSON", "Files"] if BAKTA_VIZ_AVAILABLE else ["Summary", "JSON", "Files"]
                            view_mode = st.radio(
                                "View as:",
                                options=view_options,
                                index=0,
                                horizontal=True,
                                key="bakta_view_mode"
                            )
                            
                            results = st.session_state.bakta_results
                    
                        # Now view_mode is guaranteed to be defined
                        if view_mode == "Summary":
                            # Display comprehensive annotation summary using the specialized module
                            if BAKTA_SUMMARY_AVAILABLE:
                                try:
                                    # Use the bakta_summary module to display rich summary
                                    bakta_summary.display_bakta_summary(bakta_job_id, results)
                                except Exception as e:
                                    st.error(f"Error displaying Bakta summary: {str(e)}")
                                    logger.error(f"Error in Bakta summary: {str(e)}", exc_info=True)
                                    
                                    # Fallback to basic summary if the detailed one fails
                                    st.write("Basic Annotation Summary (Fallback)")
                                    if "summary" in results:
                                        summary = results["summary"]
                                        cols = st.columns(3)
                                        for i, (key, value) in enumerate(summary.items()):
                                            cols[i % 3].metric(key, value)
                            else:
                                # Basic summary if the specialized module is not available
                                st.write("Annotation Summary")
                                
                                # Example summary metrics
                                if "summary" in results:
                                    summary = results["summary"]
                                    cols = st.columns(3)
                                    for i, (key, value) in enumerate(summary.items()):
                                        cols[i % 3].metric(key, value)
                                    
                        elif view_mode == "Visualizations" and BAKTA_VIZ_AVAILABLE:
                            # Use our Bakta visualizations module
                            try:
                                # Display the visualizations using the job ID
                                bakta_visualizations.display_bakta_visualizations(bakta_job_id)
                            except Exception as e:
                                st.error(f"Error displaying Bakta visualizations: {str(e)}")
                        
                        elif view_mode == "JSON":
                            # Show as formatted JSON
                            st.json(results)
                        
                        else:  # Files view
                            if "result_files" in results:
                                st.write("Result Files")
                                
                                for file_name, file_url in results["result_files"].items():
                                    st.markdown(f"* [{file_name}]({file_url})")
                                
                                # Download options
                                col1, col2 = st.columns(2)
                                with col1:
                                    download_json = st.download_button(
                                        "Download JSON",
                                        data=json.dumps(results, indent=2),
                                        file_name="bakta_results.json",
                                        mime="application/json",
                                        key="download_bakta_json_current"
                                    )
                                
                                with col2:
                                    # Placeholder for downloading all result files as a zip
                                    st.button("Download All Files (ZIP)", disabled=True, key="download_bakta_zip_current")
    
    # Annotation Tab
    with annotation_tab:
        st.write("Detailed annotation information for the current analysis.")
        
        # Placeholder content for the annotation tab
        if "bakta_job_id" in st.session_state and st.session_state.bakta_job_id:
            st.info(f"Showing annotation details for Bakta job: {st.session_state.bakta_job_id}")
            st.write("This tab will display detailed annotation information from Bakta.")
            
            # Add expandable section for annotation features
            with st.expander("Annotation Features"):
                st.write("This section will show detailed feature annotations from the genome.")
                st.write("- Coding sequences (CDS)")
                st.write("- RNA genes")
                st.write("- Repeat regions")
        else:
            st.warning("No active annotation job. Please run a Bakta annotation job to view results.")
    
    # Results History Tab
    with history_tab:
        st.subheader("Results History")
        
        # Import the database manager and results_history components
        try:
            from amr_predictor.bakta.database import DatabaseManager
            
            # Try different import approaches to handle various run configurations
            try:
                # First try direct import (when app.py adds the path correctly)
                import results_history
                display_consolidated_history = results_history.display_consolidated_history
            except ImportError:
                try:
                    # Try relative import (when running as a module)
                    from . import results_history
                    display_consolidated_history = results_history.display_consolidated_history
                except ImportError:
                    # Try absolute import with streamlit prefix
                    import sys
                    import os
                    # Add the streamlit directory to path if needed
                    streamlit_dir = os.path.dirname(os.path.abspath(__file__))
                    if streamlit_dir not in sys.path:
                        sys.path.insert(0, streamlit_dir)
                    import results_history
                    display_consolidated_history = results_history.display_consolidated_history
            
            # Initialize database manager with the project path
            db_manager = DatabaseManager()
            
            # Display the consolidated history with all completed jobs
            display_consolidated_history(db_manager)
            
        except Exception as e:
            st.error(f"Could not load the results history components: {str(e)}")
            st.info("Make sure the AMR predictor package is properly installed and the results_history.py file exists.")

def create_job_management_tab() -> None:
    """Create the Job Management tab content."""
    st.subheader("Job Management")
    
    # Initialize jobs list in session state if not present
    if "jobs" not in st.session_state:
        st.session_state.jobs = []
    
    if not st.session_state.jobs:
        st.info("No jobs have been submitted yet.")
        return
    
    # Display jobs in a table
    jobs_data = []
    for job in st.session_state.jobs:
        jobs_data.append({
            "Job ID": job.get("job_id", "Unknown"),
            "Type": job.get("type", "Unknown"),
            "Status": job.get("status", "Unknown"),
            "Submitted": job.get("submitted_at", "Unknown"),
            "Actions": f"View_{job.get('job_id', '')}"  # Used as a key for buttons
        })
    
    if jobs_data:
        df = pd.DataFrame(jobs_data)
        # Format column names to Title Case
        df = format_column_names(df)
        st.dataframe(df, hide_index=True)
        
        # Job selection and actions
        selected_job_id = st.selectbox(
            "Select Job",
            options=[job["Job ID"] for job in jobs_data],
            index=0
        )
        
        # Find the selected job
        selected_job = next(
            (job for job in st.session_state.jobs if job.get("job_id") == selected_job_id),
            None
        )
        
        if selected_job:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("View Results", key=f"view_{selected_job_id}"):
                    # Logic to view results
                    st.session_state.selected_job_for_results = selected_job_id
            
            with col2:
                if st.button("Refresh Status", key=f"refresh_{selected_job_id}"):
                    # Logic to refresh job status
                    pass
            
            with col3:
                if st.button("Delete Job", key=f"delete_{selected_job_id}"):
                    # Logic to delete job
                    st.session_state.jobs = [
                        job for job in st.session_state.jobs 
                        if job.get("job_id") != selected_job_id
                    ]
                    st.rerun()
            
            # Job details
            with st.expander("Job Details", expanded=False):
                st.json(selected_job)

def add_job_to_history(job_data: Dict[str, Any]) -> None:
    """
    Add a job to the job history.
    
    Args:
        job_data: Job information dictionary
    """
    if "jobs" not in st.session_state:
        st.session_state.jobs = []
    
    # Check if job already exists
    existing_job = next(
        (job for job in st.session_state.jobs if job.get("job_id") == job_data.get("job_id")),
        None
    )
    
    if existing_job:
        # Update existing job
        for key, value in job_data.items():
            existing_job[key] = value
    else:
        # Add new job
        st.session_state.jobs.append(job_data)
