"""
Aggregation module for AMR Predictor results.

This module provides functionality for aggregating AMR prediction results from
multiple models or genomic files, including various aggregation methods for
determining resistance status.
"""

import os
import glob
import re
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime
import time

from ..core.utils import logger, timer, ProgressTracker, ensure_directory_exists

class PredictionAggregator:
    """
    Aggregator for AMR prediction results across multiple models or files.
    
    This class provides methods to:
    - Process multiple prediction files
    - Apply various aggregation strategies
    - Generate summary statistics
    - Save aggregated results
    """
    
    def __init__(self, 
                 model_suffix: str = "_all_107_sequences_prediction",
                 resistance_threshold: float = 0.5,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the prediction aggregator.
        
        Args:
            model_suffix: Suffix to remove from filenames when extracting model names
            resistance_threshold: Threshold for resistance classification
            progress_tracker: Optional progress tracker
        """
        self.model_suffix = model_suffix
        self.resistance_threshold = resistance_threshold
        self.progress_tracker = progress_tracker
    
    def extract_genomic_filename(self, sequence_id: str) -> Optional[str]:
        """
        Extract the genomic file name from the sequence_id.
        Takes everything up to the first colon.
        
        Args:
            sequence_id: The sequence ID to parse
            
        Returns:
            The extracted genomic file name or None if not found
        """
        try:
            # Extract everything up to the first colon
            match = re.search(r'^([^:]+):', sequence_id)
            if match:
                return match.group(1)
            
            logger.debug(f"Could not extract genomic filename from: {sequence_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting genomic filename from {sequence_id}: {str(e)}")
            return None
    
    def process_prediction_files(self, input_files: List[str], output_dir: str, model_suffix: str) -> pd.DataFrame:
        """
        Process prediction files and aggregate results.
        
        Args:
            input_files: List of prediction file paths
            output_dir: Directory to save aggregated results
            model_suffix: Suffix to identify model-specific files
            
        Returns:
            DataFrame containing aggregated results
        """
        if not input_files:
            logger.warning("No prediction files provided")
            return pd.DataFrame()
        
        # Initialize empty DataFrame to store all results
        all_results = pd.DataFrame()
        
        # Process each prediction file
        for i, file_path in enumerate(input_files, 1):
            logger.info(f"Processing file {i}/{len(input_files)}: {os.path.basename(file_path)}")
            
            try:
                # Read the prediction file
                df = pd.read_csv(file_path)
                
                # Verify required columns exist
                required_columns = ["Sequence_ID", "Resistant", "Susceptible"]
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
                
                # Extract genomic ID from sequence ID
                df['genomic_id'] = df['Sequence_ID'].apply(self.extract_genomic_filename)
                
                # Group by genomic ID and calculate statistics
                grouped = df.groupby('genomic_id').agg({
                    'Sequence_ID': 'count',
                    'Resistant': lambda x: (x > self.resistance_threshold).any(),
                    'Susceptible': lambda x: (x > self.resistance_threshold).any()
                }).rename(columns={
                    'Sequence_ID': 'sequence_count',
                    'Resistant': 'any_resistance',
                    'Susceptible': 'any_susceptible'
                })
                
                # Calculate majority voting
                grouped['majority_vote'] = df.groupby('genomic_id').apply(
                    lambda x: 'Resistant' if (x['Resistant'] > self.resistance_threshold).mean() > 0.5 else 'Susceptible'
                )
                
                # Calculate average probabilities
                grouped['avg_resistant'] = df.groupby('genomic_id')['Resistant'].mean()
                grouped['avg_susceptible'] = df.groupby('genomic_id')['Susceptible'].mean()
                grouped['avg_classification'] = grouped.apply(
                    lambda x: 'Resistant' if x['avg_resistant'] > x['avg_susceptible'] else 'Susceptible',
                    axis=1
                )
                
                # Calculate method agreement
                grouped['methods_agree'] = grouped.apply(
                    lambda x: x['majority_vote'] == x['avg_classification'],
                    axis=1
                )
                
                # Add to all results
                all_results = pd.concat([all_results, grouped])
                
                # Log resistance statistics
                total_sequences = len(df)
                resistant_sequences = (df['Resistant'] > self.resistance_threshold).sum()
                susceptible_sequences = (df['Susceptible'] > self.resistance_threshold).sum()
                
                logger.info(f"File statistics:")
                logger.info(f"  Total sequences: {total_sequences}")
                logger.info(f"  Resistant sequences: {resistant_sequences} ({resistant_sequences/total_sequences*100:.1f}%)")
                logger.info(f"  Susceptible sequences: {susceptible_sequences} ({susceptible_sequences/total_sequences*100:.1f}%)")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
        
        if all_results.empty:
            logger.warning("No results were generated from the prediction files")
            return pd.DataFrame()
        
        # Calculate overall statistics
        total_files = len(all_results)
        files_with_resistance = all_results['any_resistance'].sum()
        files_with_majority_resistance = (all_results['majority_vote'] == 'Resistant').sum()
        files_with_avg_resistance = (all_results['avg_classification'] == 'Resistant').sum()
        method_agreement = all_results['methods_agree'].mean() * 100
        
        logger.info("\nAggregation Summary:")
        logger.info(f"Total genomic files processed: {total_files}")
        logger.info(f"Files with any resistance: {files_with_resistance} ({files_with_resistance/total_files*100:.1f}%)")
        logger.info(f"Files with majority resistance: {files_with_majority_resistance} ({files_with_majority_resistance/total_files*100:.1f}%)")
        logger.info(f"Files with average resistance: {files_with_avg_resistance} ({files_with_avg_resistance/total_files*100:.1f}%)")
        logger.info(f"Method agreement rate: {method_agreement:.1f}%")
        
        # Reset index to make genomic_id a column
        all_results = all_results.reset_index()
        
        return all_results
    
    def find_prediction_files(self, 
                           input_dir: Optional[str] = None,
                           input_pattern: Optional[str] = None,
                           input_files: Optional[List[str]] = None,
                           file_pattern: str = "*_all_107_sequences_prediction.txt") -> List[str]:
        """
        Find prediction files based on input parameters.
        
        Args:
            input_dir: Directory containing prediction files
            input_pattern: Glob pattern to match prediction files
            input_files: Specific prediction files to process
            file_pattern: File pattern to match when using input_dir
            
        Returns:
            List of file paths to process
        """
        prediction_files = []
        
        if input_files:
            logger.debug(f"Using explicitly provided file list with {len(input_files)} files")
            prediction_files = input_files
        elif input_pattern:
            logger.debug(f"Searching for files matching pattern: {input_pattern}")
            prediction_files = glob.glob(input_pattern)
            logger.debug(f"Found {len(prediction_files)} files matching pattern")
        elif input_dir:
            # Ensure the input directory exists
            if not os.path.isdir(input_dir):
                logger.error(f"Error: Input directory '{input_dir}' does not exist.")
                return []
            
            logger.debug(f"Searching for files in directory: {input_dir} with pattern: {file_pattern}")
            
            # Get full paths to files
            prediction_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                               if os.path.isfile(os.path.join(input_dir, f)) and 
                               glob.fnmatch.fnmatch(f, file_pattern)]
            
            logger.debug(f"Found {len(prediction_files)} files matching pattern in directory")
        
        if not prediction_files:
            logger.warning("No prediction files found")
        else:
            logger.info(f"Found {len(prediction_files)} prediction files to process")
        
        return prediction_files


# Standalone functions for backward compatibility

def process_amr_files(prediction_files: List[str], 
                     output_file: str, 
                     model_suffix: str = "_all_107_sequences_prediction") -> pd.DataFrame:
    """
    Process multiple AMR prediction files and aggregate results.
    Standalone function for backward compatibility.
    
    Args:
        prediction_files: List of file paths to AMR prediction files
        output_file: Path to save the aggregated results CSV
        model_suffix: Suffix to remove from filenames when extracting model names
        
    Returns:
        DataFrame containing the aggregated results
    """
    aggregator = PredictionAggregator(model_suffix=model_suffix)
    return aggregator.process_prediction_files(prediction_files, output_file, model_suffix)
