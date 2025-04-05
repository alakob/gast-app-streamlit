"""
Visualization module for AMR Predictor results.

This module provides functionality for converting AMR prediction results to
various visualization formats, including WIG format for genome browsers.
"""

import os
import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from ..core.utils import logger, timer, ProgressTracker, ensure_directory_exists, parse_sequence_id

class VisualizationGenerator:
    """
    Generator for visualization files from AMR prediction results.
    
    This class provides methods to:
    - Convert prediction results to WIG format
    - Process prediction files for visualization
    """
    
    def __init__(self, 
                 step_size: int = 1200,
                 processing_dir: Optional[str] = None,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the visualization generator.
        
        Args:
            step_size: Step size in base pairs for WIG format
            processing_dir: Directory to save intermediate files
            progress_tracker: Optional progress tracker
        """
        self.step_size = step_size
        self.progress_tracker = progress_tracker
        
        # Set default processing directory if not provided
        if processing_dir is None:
            self.processing_dir = os.path.join(os.getcwd(), 'processing')
        else:
            self.processing_dir = processing_dir
        
        # Ensure processing directory exists
        ensure_directory_exists(self.processing_dir)
        logger.debug(f"Processing directory: {self.processing_dir}")
    
    def process_prediction_file(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Process the AMR prediction file and extract sequence information.
        
        Args:
            input_file: Path to the AMR prediction file (CSV or TSV)
            output_file: Path to save the processed DataFrame
            
        Returns:
            Processed DataFrame with contig, start, end columns
        """
        if self.progress_tracker:
            self.progress_tracker.update(
                status="Processing prediction file for visualization",
                increment=10,
                additional_info={"input_file": input_file}
            )
        
        try:
            # Read the prediction file
            logger.info(f"Reading prediction file: {input_file}")
            with timer("read_prediction_file"):
                df = pd.read_csv(input_file)
            
            # Check if required columns exist
            if 'Sequence_ID' not in df.columns or 'Resistant' not in df.columns:
                error_msg = f"Required columns not found in {input_file}"
                logger.error(error_msg)
                if self.progress_tracker:
                    self.progress_tracker.set_error(error_msg)
                return pd.DataFrame()
            
            # Create new columns for contig, start, and end
            logger.info("Parsing sequence IDs to extract contig, start, and end positions")
            
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Parsing sequence IDs",
                    increment=20,
                    additional_info={"total_sequences": len(df)}
                )
            
            with timer("parse_sequence_ids"):
                # Use the utility function to parse sequence IDs
                parsed_data = [self._parse_sequence_id_for_viz(seq_id) for seq_id in df['Sequence_ID']]
                
                df['contig'] = [data[0] for data in parsed_data]
                df['start'] = [data[1] for data in parsed_data]
                df['end'] = [data[2] for data in parsed_data]
            
            # Rename Resistant column to prob_resistance for clarity
            df['prob_resistance'] = df['Resistant']
            
            # Save processed DataFrame if output_file is provided
            if output_file:
                ensure_directory_exists(os.path.dirname(output_file))
                logger.info(f"Saving processed data to {output_file}")
                with timer("save_processed_data"):
                    df.to_csv(output_file, index=False)
            
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Prediction file processed successfully",
                    increment=10,
                    additional_info={
                        "total_contigs": df['contig'].nunique(),
                        "sequences_processed": len(df)
                    }
                )
            
            return df
        
        except Exception as e:
            error_msg = f"Error processing prediction file: {str(e)}"
            logger.error(error_msg)
            if self.progress_tracker:
                self.progress_tracker.set_error(error_msg)
            return pd.DataFrame()
    
    def _parse_sequence_id_for_viz(self, sequence_id: str) -> Tuple[str, int, int]:
        """
        Parse the sequence ID to extract contig, start, and end positions.
        
        Example sequence_ID: OXA-264:27215228mrsa_S13_L001_R1_001_(paired)_contig_1_segment_1_300
        
        Args:
            sequence_id: The sequence ID from the AMR predictor output
            
        Returns:
            Tuple of (contig_id, start, end)
        """
        try:
            # Split the sequence_ID on all underscores
            parts = sequence_id.split("_")
            
            # Check if this is a segmented sequence
            if "segment" in sequence_id:
                # Handle segmented sequence IDs
                # Extract contig ID (everything before "_segment_")
                contig_pattern = r"(.+)_segment_\d+"
                contig_match = re.search(contig_pattern, sequence_id)
                contig_id = contig_match.group(1) if contig_match else sequence_id
                
                # Extract segment number
                segment_pattern = r"_segment_(\d+)"
                segment_match = re.search(segment_pattern, sequence_id)
                segment_num = int(segment_match.group(1)) if segment_match else 1
                
                # Extract start and end positions
                pos_pattern = r"_(\d+)_(\d+)$"
                pos_match = re.search(pos_pattern, sequence_id)
                if pos_match:
                    start = int(pos_match.group(1))
                    end = int(pos_match.group(2))
                else:
                    # If positions not found, use segment number to calculate
                    segment_length = 6000
                    start = (segment_num - 1) * segment_length + 1
                    end = segment_num * segment_length
                
                return contig_id, start, end
            else:
                # Handle non-segmented sequence IDs
                # The last two parts are start and end
                start, end = parts[-2:]
                
                # Recombine the parts to get the contig ID
                contig_id = "_".join(parts[:-2])
                
                # Convert start and end to integers
                try:
                    start = int(start)
                    end = int(end)
                except ValueError:
                    logger.warning(f"Could not parse start/end as integers for {sequence_id}")
                    start, end = 1, 6000  # Default values
                
                return contig_id, start, end
        except Exception as e:
            logger.error(f"Error parsing sequence ID {sequence_id}: {str(e)}")
            # Return default values if parsing fails
            return sequence_id, 1, 6000
    
    def create_wiggle_file(self, df: pd.DataFrame, output_wig: Optional[str] = None) -> Optional[str]:
        """
        Create a WIG file from the processed prediction data using fixedStep format.
        
        Args:
            df: DataFrame with contig, start, end, and prob_resistance columns
            output_wig: Path to save the WIG file. If None, a file will be created in the processing directory.
            
        Returns:
            Path to the created WIG file if successful, None otherwise
        """
        if df.empty:
            logger.warning("Cannot create WIG file from empty DataFrame")
            return None
        
        # Check if required columns exist
        required_columns = ['contig', 'start', 'end', 'prob_resistance']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Required columns missing for WIG file creation: {', '.join(missing_columns)}")
            return None
        
        # If no output path is provided, create one in the processing directory
        if output_wig is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_wig = os.path.join(self.processing_dir, f"amr_visualization_{timestamp}.wig")
        
        if self.progress_tracker:
            self.progress_tracker.update(
                status="Creating WIG file",
                increment=10,
                additional_info={
                    "step_size": self.step_size,
                    "output_file": output_wig
                }
            )
        
        try:
            logger.info(f"Creating WIG file with step size {self.step_size}bp: {output_wig}")
            
            # Ensure the directory exists
            ensure_directory_exists(os.path.dirname(output_wig))
            
            # Ensure data is sorted by contig and start position
            with timer("sort_data"):
                df = df.sort_values(by=['contig', 'start'])
            
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Writing WIG file",
                    increment=20,
                    additional_info={
                        "total_contigs": df['contig'].nunique(),
                        "total_positions": len(df)
                    }
                )
            
            with timer("write_wig_file"):
                with open(output_wig, 'w') as f:
                    # Write track header
                    f.write("track type=wiggle_0 name='AMR Resistance Probability'\n")
                    
                    current_contig = None
                    prev_end = 0  # Initialize prev_end
                    
                    for _, row in df.iterrows():
                        if row['contig'] != current_contig:
                            current_contig = row['contig']
                            start_pos = row['start']
                            prev_end = 0  # Reset prev_end for new contig
                            f.write(f"fixedStep chrom={row['contig']} start={start_pos} step={self.step_size} span={self.step_size}\n")
                        else:
                            # For continuing the same contig but with a gap, create a new fixedStep section
                            if row['start'] > prev_end + self.step_size:
                                start_pos = row['start']
                                f.write(f"fixedStep chrom={row['contig']} start={start_pos} step={self.step_size} span={self.step_size}\n")
                        
                        # Calculate positions based on step size
                        pos = row['start']
                        while pos <= row['end']:
                            # Write the resistance probability for this position
                            f.write(f"{row['prob_resistance']}\n")
                            pos += self.step_size
                        
                        # Keep track of the end position for this contig
                        prev_end = row['end']
            
            logger.info(f"WIG file created successfully: {output_wig}")
            
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="WIG file created successfully",
                    increment=10,
                    additional_info={"output_file": output_wig}
                )
            
            return output_wig
        
        except Exception as e:
            error_msg = f"Error creating WIG file: {str(e)}"
            logger.error(error_msg)
            if self.progress_tracker:
                self.progress_tracker.set_error(error_msg)
            return None
    
    def prediction_to_wig(self, input_file: str, output_wig: Optional[str] = None,
                       processed_file: Optional[str] = None) -> Optional[str]:
        """
        Convert AMR prediction results to WIG format.
        
        Args:
            input_file: Path to the AMR prediction TSV file
            output_wig: Path to save the WIG file
            processed_file: Path to save the processed prediction data
            
        Returns:
            Path to the created WIG file if successful, None otherwise
        """
        logger.info(f"Converting predictions to WIG: {input_file}")
        
        if self.progress_tracker:
            self.progress_tracker.update(
                status="Starting prediction to WIG conversion",
                increment=5,
                additional_info={"input_file": input_file}
            )
        
        # Process the prediction file
        processed_df = self.process_prediction_file(input_file, processed_file)
        
        if processed_df.empty:
            logger.error("Failed to process prediction file")
            return None
        
        # Create the WIG file
        return self.create_wiggle_file(processed_df, output_wig)


# Standalone functions for backward compatibility

def process_prediction_file(input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
    """
    Process the AMR prediction file and extract sequence information.
    Standalone function for backward compatibility.
    
    Args:
        input_file: Path to the AMR prediction file (CSV or TSV)
        output_file: Path to save the processed DataFrame
        
    Returns:
        Processed DataFrame with contig, start, end columns
    """
    generator = VisualizationGenerator()
    return generator.process_prediction_file(input_file, output_file)

def create_wiggle_file(df: pd.DataFrame, output_wig: Optional[str] = None, step_size: int = 1200) -> Optional[str]:
    """
    Create a WIG file from the processed prediction data.
    Standalone function for backward compatibility.
    
    Args:
        df: DataFrame with contig, start, end, and prob_resistance columns
        output_wig: Path to save the WIG file
        step_size: Step size in base pairs for WIG format
        
    Returns:
        Path to the created WIG file if successful, None otherwise
    """
    generator = VisualizationGenerator(step_size=step_size)
    return generator.create_wiggle_file(df, output_wig)
