"""
Sequence processing module for AMR Predictor.

This module provides functionality for processing AMR prediction results at
the sequence level, including extracting sequence information and aggregating
segment predictions.
"""

import os
import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime

from ..core.utils import logger, timer, ProgressTracker, ensure_directory_exists

class SequenceProcessor:
    """
    Processor for AMR prediction results at the sequence level.
    
    This class provides methods to:
    - Process sequence prediction files
    - Extract sequence information from IDs
    - Aggregate results for segmented sequences
    """
    
    def __init__(self, 
                 resistance_threshold: float = 0.5,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the sequence processor.
        
        Args:
            resistance_threshold: Threshold for resistance classification
            progress_tracker: Optional progress tracker
        """
        self.resistance_threshold = resistance_threshold
        self.progress_tracker = progress_tracker
    
    def parse_sequence_id(self, sequence_id: str) -> Tuple[str, int, int]:
        """
        Parse the sequence ID to extract contig, start, and end positions.
        
        Example sequence_ID: fasta_27215228:27215228mrsa_S13_L001_R1_001_(paired)_contig_1_1_6000
        
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
                
                # Assume each segment is 6000 bp (or use a configurable value)
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
    
    def process_prediction_file(self, input_file: str, output_file: str) -> pd.DataFrame:
        """
        Process a prediction file and generate sequence-level results.
        
        Args:
            input_file: Path to the input prediction file
            output_file: Path to save the processed results
            
        Returns:
            DataFrame containing the processed results
        """
        try:
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(status="Starting sequence processing", increment=5)
            
            # Read the prediction file
            logger.info(f"Processing AMR prediction file: {input_file}")
            with timer("read_prediction_file"):
                df = pd.read_csv(input_file)
            
            # Log file info
            logger.info(f"Loaded prediction file with {len(df)} rows and {len(df.columns)} columns")
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(status="File loaded successfully", increment=10)
            
            # Verify required columns exist
            required_columns = ["Sequence_ID", "Resistant", "Susceptible"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Input file is missing required columns: {', '.join(missing_columns)}"
                logger.error(error_msg)
                if self.progress_tracker:
                    self.progress_tracker.set_error(error_msg)
                return pd.DataFrame()
            
            # Parse sequence IDs to extract contig, start, and end
            logger.info("Parsing sequence IDs to extract contig, start, and end positions")
            parsed_data = [self.parse_sequence_id(seq_id) for seq_id in df['Sequence_ID']]
            
            # Add new columns for contig, start, and end
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


# Standalone function for backward compatibility

def process_prediction_file(input_file: str, 
                          output_file: str, 
                          resistance_threshold: float = 0.5) -> pd.DataFrame:
    """
    Process an AMR prediction file, extract sequence information, and apply aggregation methods.
    Standalone function for backward compatibility.
    
    Args:
        input_file: Path to the input prediction file
        output_file: Path to save the processed results
        resistance_threshold: Threshold for resistance classification
        
    Returns:
        DataFrame containing the processed results
    """
    processor = SequenceProcessor(resistance_threshold=resistance_threshold)
    return processor.process_prediction_file(input_file, output_file)
