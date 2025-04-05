"""
Sequence-level aggregation module for AMR prediction results.

This module provides functionality for aggregating AMR predictions at the sequence level,
including methods to combine segment-level predictions into sequence-level results.
"""

import os
import re
import pandas as pd
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import time

from ..core.utils import logger, timer, ProgressTracker, ensure_directory_exists

class SequenceAggregator:
    """
    Aggregator for sequence-level AMR prediction results.
    
    This class provides methods to:
    - Aggregate predictions from sequence segments
    - Apply various aggregation strategies (any resistance, majority vote, average probability)
    - Generate sequence-level summary statistics
    """
    
    def __init__(self, 
                 resistance_threshold: float = 0.5,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the sequence aggregator.
        
        Args:
            resistance_threshold: Threshold for resistance classification
            progress_tracker: Optional progress tracker
        """
        self.resistance_threshold = resistance_threshold
        self.progress_tracker = progress_tracker
    
    def process_prediction_file(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Process a prediction file and aggregate results at the sequence level.
        
        Args:
            input_file: Path to the input prediction file
            output_file: Optional path to save the aggregated results
            
        Returns:
            DataFrame containing aggregated results at the sequence level
        """
        start_time = time.time()
        logger.info(f"Processing AMR prediction file for sequence-level aggregation: {input_file}")
        
        if self.progress_tracker:
            self.progress_tracker.update(status="Loading prediction file")
        
        try:
            # Try to detect file format - check first few lines to determine separator
            with open(input_file, 'r') as f:
                first_line = f.readline().strip()
            
            # Detect if comma-separated or tab-separated
            if ',' in first_line and '\t' not in first_line:
                sep = ','
                logger.info(f"Detected CSV format, using comma as separator")
            else:
                sep = '\t'
                logger.info(f"Using tab as separator")
            
            # Read the prediction file with appropriate separator
            df = pd.read_csv(input_file, sep=sep)
            logger.info(f"Loaded prediction file with {len(df)} rows and {len(df.columns)} columns")
            
            # Basic data validation
            required_columns = ['Sequence_ID', 'Resistant', 'Susceptible']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Input file is missing required columns: {', '.join(missing_columns)}"
                logger.error(error_msg)
                if self.progress_tracker:
                    self.progress_tracker.set_error(error_msg)
                return pd.DataFrame()
            
            # Check if Start and End columns are available in the input file
            # Check if any sequence ID contains patterns we need to clean
            has_segments = any('_segment_' in id for id in df['Sequence_ID'])
            has_contigs = any('_contig_' in id for id in df['Sequence_ID'])
            
            if has_segments:
                logger.info("Detected sequence IDs with '_segment_' patterns - these will be properly cleaned during aggregation")
            if has_contigs:
                logger.info("Detected sequence IDs with '_contig_' patterns - these will be properly cleaned during aggregation")
            
            # Clean all sequence IDs by removing both segment and contig patterns completely
            # First remove segment patterns
            df['original_id'] = df['Sequence_ID'].apply(lambda x: re.sub(r'_segment_[\d_]+', '', x))
            # Then remove contig patterns
            df['original_id'] = df['original_id'].apply(lambda x: re.sub(r'_contig_[\d_]+', '', x))
            
            if has_segments or has_contigs:
                logger.info("Cleaned sequence IDs by removing segment and contig patterns")
            
            # Now handle start and end positions
            if 'Start' in df.columns and 'End' in df.columns:
                logger.info("Using explicit Start and End columns from input file...")
                df['start'] = df['Start']
                df['end'] = df['End']
            else:
                # Parse sequence IDs to extract start and end positions
                logger.info("Parsing sequence IDs to extract start and end positions...")
                df['start'] = df['Sequence_ID'].apply(lambda x: self._parse_sequence_id(x)[1])
                df['end'] = df['Sequence_ID'].apply(lambda x: self._parse_sequence_id(x)[2])
            
            # Log statistics on parsed data
            valid_positions = df['start'].notna() & df['end'].notna()
            logger.info(f"Successfully parsed positions for {valid_positions.sum()} out of {len(df)} sequences")
            
            # Group by original_id
            logger.info("Grouping sequences by original_id...")
            grouped = df.groupby('original_id')
            unique_ids = len(grouped)
            logger.info(f"Found {unique_ids} unique sequence IDs")
            
            if self.progress_tracker:
                self.progress_tracker.update(status=f"Aggregating {unique_ids} sequences")
            
            # Initialize results
            results = []
            
            # Process each group
            logger.info(f"Applying aggregation methods with resistance threshold: {self.resistance_threshold}")
            for original_id, group in grouped:
                # Method 1: Any Resistance
                any_resistant = (group['Resistant'] > self.resistance_threshold).any()
                any_resistant_count = (group['Resistant'] > self.resistance_threshold).sum()
                any_resistance_result = "Resistant" if any_resistant else "Susceptible"
                
                # Method 2: Majority Vote
                majority_resistant = (group['Resistant'] > self.resistance_threshold).sum() > len(group) / 2
                majority_vote_count = (group['Resistant'] > self.resistance_threshold).sum()
                majority_vote_result = "Resistant" if majority_resistant else "Susceptible"
                
                # Method 3: Average Probability
                avg_resistance = group['Resistant'].mean()
                avg_susceptible = group['Susceptible'].mean()
                avg_classification = "Resistant" if avg_resistance > self.resistance_threshold else "Susceptible"
                
                # Find the min start and max end across all segments
                min_start = group['start'].min() if group['start'].notna().any() else None
                max_end = group['end'].max() if group['end'].notna().any() else None
                
                # Store results
                results.append({
                    'sequence_id': original_id,  # Use the cleaned ID without segment patterns
                    'segment_count': len(group),
                    'start': min_start,
                    'end': max_end,
                    'any_resistance': any_resistance_result,
                    'any_resistance_count': any_resistant_count,
                    'majority_vote': majority_vote_result,
                    'majority_vote_count': majority_vote_count,
                    'avg_resistance_prob': avg_resistance,
                    'avg_susceptible_prob': avg_susceptible,
                    'avg_classification': avg_classification
                })
            
            # Convert results to DataFrame
            results_df = pd.DataFrame(results)
            
            # Log resistance statistics
            resistant_any = (results_df['any_resistance'] == "Resistant").sum()
            resistant_majority = (results_df['majority_vote'] == "Resistant").sum()
            resistant_avg = (results_df['avg_classification'] == "Resistant").sum()
            
            logger.info(f"Resistance summary:")
            logger.info(f"  - Any resistance method: {resistant_any}/{len(results_df)} ({resistant_any/len(results_df)*100:.2f}%) classified as resistant")
            logger.info(f"  - Majority vote method: {resistant_majority}/{len(results_df)} ({resistant_majority/len(results_df)*100:.2f}%) classified as resistant")
            logger.info(f"  - Avg probability method: {resistant_avg}/{len(results_df)} ({resistant_avg/len(results_df)*100:.2f}%) classified as resistant")
            
            # Save to CSV if output file is provided
            if output_file:
                logger.info(f"Saving sequence-level aggregated results to: {output_file}")
                results_df.to_csv(output_file, index=False)
            
            end_time = time.time()
            logger.info(f"Sequence-level aggregation completed in {end_time - start_time:.2f} seconds")
            
            if self.progress_tracker:
                self.progress_tracker.update(step=100, status="Aggregation complete")
            
            return results_df
            
        except Exception as e:
            error_msg = f"Error processing prediction file: {str(e)}"
            logger.error(error_msg)
            if self.progress_tracker:
                self.progress_tracker.set_error(error_msg)
            return pd.DataFrame()
    
    def _parse_sequence_id(self, sequence_id):
        """
        Parse the sequence_ID to extract the original ID, start, and end positions.
        Also removes segment and contig patterns like '_segment_12001_18000' or '_contig_1' from sequence IDs.
        
        Args:
            sequence_id (str): The sequence ID from the prediction file
            
        Returns:
            tuple: (original_id, start, end)
        """
        # First, check and remove any segment pattern from the sequence_id
        # This handles patterns like '_segment_12001_18000' or '_segment_1'
        cleaned_id = re.sub(r'_segment_[\d_]+', '', sequence_id)
        
        # Also remove any contig pattern
        # This handles patterns like '_contig_1' or '_contig_123'
        cleaned_id = re.sub(r'_contig_[\d_]+', '', cleaned_id)
        
        if cleaned_id != sequence_id:
            logger.debug(f"Cleaned sequence ID: {sequence_id} -> {cleaned_id}")
        
        # Split the cleaned sequence_ID on all underscores
        parts = cleaned_id.split("_")
        
        # Check if we have at least 3 parts (to extract the last two as start and end)
        if len(parts) >= 3:
            # The last two parts should be start and end
            start, end = parts[-2:]
            
            # Recombine the parts, separating at the second-to-last underscore
            # This combines all parts except the last two with underscores
            original_id = "_".join(parts[:-2])
            
            # Try to convert start and end to integers
            try:
                start_int = int(start)
                end_int = int(end)
                return original_id, start_int, end_int
            except ValueError:
                # If conversion fails, return the original ID and None for start/end
                logger.warning(f"Could not parse start/end positions from sequence ID: {cleaned_id}")
                return cleaned_id, None, None
        else:
            # Not enough parts to extract start and end
            logger.warning(f"Sequence ID does not have expected format after cleaning: {cleaned_id}")
            return cleaned_id, None, None


# Standalone function for backward compatibility
def process_prediction_file(input_file: str, output_file: str, resistance_threshold: float = 0.5) -> pd.DataFrame:
    """
    Process an AMR prediction file and apply sequence-level aggregation.
    Standalone function for backward compatibility.
    
    Args:
        input_file: Path to the input prediction file
        output_file: Path to save the processed results
        resistance_threshold: Threshold for resistance classification
        
    Returns:
        DataFrame containing the processed results
    """
    aggregator = SequenceAggregator(resistance_threshold=resistance_threshold)
    return aggregator.process_prediction_file(input_file, output_file)
