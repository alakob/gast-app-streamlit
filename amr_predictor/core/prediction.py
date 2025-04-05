"""
Core prediction functionality for the AMR Predictor module.

This module provides the main prediction pipeline for processing FASTA files
and predicting antimicrobial resistance.
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Union, Callable
import csv
import pandas as pd

from .utils import logger, timer, ProgressTracker, ensure_directory_exists, get_default_output_path
from .models import ModelManager
from .sequence import load_fasta, split_sequence, calculate_sequence_complexity
from ..processing.sequence_aggregation import SequenceAggregator

class PredictionPipeline:
    """
    Main prediction pipeline for AMR prediction.
    
    This class orchestrates the prediction process, including:
    - Loading sequences from FASTA files
    - Splitting sequences if necessary
    - Loading the model and tokenizer
    - Running predictions
    - Saving results
    """
    
    def __init__(self, 
                 model_name: Optional[str] = None,
                 batch_size: int = 8,
                 segment_length: int = 6000,
                 segment_overlap: int = 0,
                 device: Optional[str] = None,
                 progress_tracker: Optional[ProgressTracker] = None,
                 enable_sequence_aggregation: bool = True,
                 resistance_threshold: float = 0.5):
        """
        Initialize the prediction pipeline.
        
        Args:
            model_name: HuggingFace model name or path to local model
            batch_size: Batch size for predictions
            segment_length: Maximum segment length, 0 to disable splitting
            segment_overlap: Overlap between segments in nucleotides
            device: Device to run predictions on ('cpu', 'cuda', etc.)
            progress_tracker: Optional progress tracker
        """
        self.batch_size = batch_size
        self.segment_length = segment_length
        self.segment_overlap = segment_overlap
        self.progress_tracker = progress_tracker
        self.enable_sequence_aggregation = enable_sequence_aggregation
        self.resistance_threshold = resistance_threshold
        
        # Check segment parameters
        if segment_length > 0 and segment_overlap >= segment_length:
            logger.warning(f"Segment overlap ({segment_overlap}) must be less than segment length ({segment_length})")
            self.segment_overlap = max(0, segment_length // 2)
        
        # Initialize model manager
        self.model_manager = ModelManager(
            model_name=model_name,
            device=device,
            progress_tracker=progress_tracker
        )
        
        # Initialize tracking variables
        self.num_sequences = 0
        self.num_segments = 0
        self.original_seq_map = {}  # Mapping of original sequence IDs to segment IDs
    
    def load_model(self) -> bool:
        """
        Load the model and tokenizer.
        
        Returns:
            True if loading was successful, False otherwise
        """
        model, tokenizer = self.model_manager.load()
        return model is not None and tokenizer is not None
    
    def process_fasta_file(self, fasta_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a FASTA file and generate predictions.
        
        Args:
            fasta_file: Path to the input FASTA file
            output_file: Optional path to save results (default: amr_predictions_<timestamp>.csv)
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = time.time()
        
        # Validate input file
        if not os.path.exists(fasta_file):
            error_msg = f"FASTA file not found: {fasta_file}"
            logger.error(error_msg)
            if self.progress_tracker:
                self.progress_tracker.set_error(error_msg)
            return {"error": error_msg}
        
        # Set default output file if not provided
        if output_file is None:
            # Extract model name from the full model path
            model_name = self.model_manager.model_name.split('/')[-1]  # Get the last part of the model path
            output_file = get_default_output_path(f"{model_name}_amr_predictions", "csv", fasta_file)
            logger.info(f"Using default output file: {output_file}")
        
        # Handle directory output path
        if output_file.endswith('/') or output_file.endswith('\\'):
            # If output_file is a directory, create the full path with the default filename
            output_dir = output_file
            # Extract model name from the full model path
            model_name = self.model_manager.model_name.split('/')[-1]  # Get the last part of the model path
            output_file = os.path.join(output_dir, get_default_output_path(f"{model_name}_amr_predictions", "csv", fasta_file))
            logger.info(f"Output directory provided, using file: {output_file}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "."
        ensure_directory_exists(output_dir)
        
        # Initialize results
        results = {
            "fasta_file": fasta_file,
            "output_file": output_file,
            "model_name": self.model_manager.model_name,
            "batch_size": self.batch_size,
            "segment_length": self.segment_length,
            "segment_overlap": self.segment_overlap,
            "device": self.model_manager.device,
            "start_time": datetime.now().isoformat(),
            "sequences": [],
            "processing_time": 0,
            "error": None
        }
        
        try:
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(status="Loading FASTA file", increment=5)
            
            # Load sequences from FASTA file
            logger.info(f"Loading sequences from {fasta_file}")
            with timer("load_fasta"):
                fasta_data = load_fasta(fasta_file)
            
            self.num_sequences = len(fasta_data)
            logger.info(f"Loaded {self.num_sequences} sequences from FASTA file")
            
            if self.num_sequences == 0:
                error_msg = f"No sequences found in {fasta_file}"
                logger.error(error_msg)
                if self.progress_tracker:
                    self.progress_tracker.set_error(error_msg)
                return {"error": error_msg, **results}
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Processing sequences", 
                    increment=5,
                    additional_info={"total_sequences": self.num_sequences}
                )
            
            # Split sequences if needed
            logger.info(f"Splitting sequences (max length: {self.segment_length}, overlap: {self.segment_overlap})")
            with timer("split_sequences"):
                all_segments = []
                all_segment_ids = []
                self.original_seq_map = {}
                
                # Check if any sequences need splitting
                needs_splitting = any(len(seq) > self.segment_length for _, seq in fasta_data) if self.segment_length > 0 else False
                
                if needs_splitting and self.segment_length > 0:
                    for seq_id, sequence in fasta_data:
                        segments = split_sequence(
                            seq_id=seq_id,
                            sequence=sequence,
                            max_length=self.segment_length,
                            overlap=self.segment_overlap
                        )
                        
                        for segment_id, segment_seq in segments:
                            all_segments.append(segment_seq)
                            all_segment_ids.append(segment_id)
                        
                        # Keep track of which segments belong to which original sequence
                        if seq_id not in self.original_seq_map:
                            self.original_seq_map[seq_id] = []
                        self.original_seq_map[seq_id].append(segment_id)
                    
                    fasta_sequences = all_segments
                    fasta_ids = all_segment_ids
                    
                    logger.info(f"Split {self.num_sequences} sequences into {len(fasta_sequences)} segments")
                    if self.segment_overlap > 0:
                        overlap_pct = self.segment_overlap / self.segment_length * 100
                        logger.info(f"Overlap between segments: {self.segment_overlap} bp ({overlap_pct:.1f}% of segment length)")
                else:
                    # No splitting needed
                    if self.segment_length == 0:
                        logger.info("Sequence splitting disabled")
                    else:
                        logger.info("No sequences need splitting")
                    
                    fasta_sequences = [seq for _, seq in fasta_data]
                    fasta_ids = [seq_id for seq_id, _ in fasta_data]
            
            self.num_segments = len(fasta_sequences)
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Loading model", 
                    increment=10,
                    additional_info={
                        "total_sequences": self.num_sequences,
                        "total_segments": self.num_segments
                    }
                )
            
            # Load model and tokenizer if not already loaded
            if self.model_manager.model is None:
                logger.info("Loading model and tokenizer")
                if not self.load_model():
                    error_msg = "Failed to load model and tokenizer"
                    logger.error(error_msg)
                    if self.progress_tracker:
                        self.progress_tracker.set_error(error_msg)
                    return {"error": error_msg, **results}
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Making predictions", 
                    increment=10,
                    additional_info={
                        "total_sequences": self.num_sequences,
                        "total_segments": self.num_segments
                    }
                )
            
            # Make predictions
            logger.info(f"Making predictions on {self.num_segments} sequences in batches of {self.batch_size}")
            with timer("predict"):
                predictions = self.model_manager.predict(
                    sequences=fasta_sequences,
                    batch_size=self.batch_size
                )
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Processing results", 
                    increment=10,
                    additional_info={
                        "total_sequences": self.num_sequences,
                        "total_segments": self.num_segments,
                        "predictions_made": len(predictions)
                    }
                )
            
            # Check if predictions were successful
            if len(predictions) != self.num_segments:
                error_msg = f"Number of predictions ({len(predictions)}) does not match number of segments ({self.num_segments})"
                logger.error(error_msg)
                if self.progress_tracker:
                    self.progress_tracker.set_error(error_msg)
                return {"error": error_msg, **results}
            
            # Prepare results
            prediction_results = []
            for i, (prediction, seq_id, sequence) in enumerate(zip(predictions, fasta_ids, fasta_sequences)):
                result = {
                    "Sequence_ID": seq_id,
                    "Length": len(sequence),
                    **prediction
                }
                prediction_results.append(result)
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Saving results", 
                    increment=5,
                    additional_info={
                        "total_sequences": self.num_sequences,
                        "total_segments": self.num_segments,
                        "predictions_made": len(predictions)
                    }
                )
            
            # Write results to file
            logger.info(f"Writing results to {output_file}")
            self.write_results(prediction_results, output_file)
            
            # Run sequence-level aggregation if enabled
            if self.enable_sequence_aggregation:
                # Generate aggregated output file name by adding "_aggregated" suffix
                output_base, output_ext = os.path.splitext(output_file)
                aggregated_output = f"{output_base}_aggregated{output_ext}"
                
                logger.info(f"Running sequence-level aggregation with threshold: {self.resistance_threshold}")
                
                # Create sequence aggregator
                aggregator = SequenceAggregator(
                    resistance_threshold=self.resistance_threshold,
                    progress_tracker=self.progress_tracker
                )
                
                # Process the prediction file
                aggregated_df = aggregator.process_prediction_file(input_file=output_file, output_file=aggregated_output)
                
                if not aggregated_df.empty:
                    logger.info(f"Sequence-level aggregation saved to: {aggregated_output}")
                    results["aggregated_output_file"] = aggregated_output
                    results["num_aggregated_sequences"] = len(aggregated_df)
                else:
                    logger.warning("Sequence-level aggregation failed or produced no results")
            
            # Calculate statistics
            resistant_count = sum(1 for pred in prediction_results if pred.get("Resistant", 0) > 0.5)
            resistant_pct = resistant_count / len(prediction_results) * 100 if prediction_results else 0
            
            # Complete results
            results.update({
                "sequences": prediction_results,
                "processing_time": time.time() - start_time,
                "end_time": datetime.now().isoformat(),
                "total_sequences": self.num_sequences,
                "total_segments": self.num_segments,
                "resistant_count": resistant_count,
                "resistant_percentage": resistant_pct
            })
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Completed successfully", 
                    increment=5,
                    additional_info={
                        "total_sequences": self.num_sequences,
                        "total_segments": self.num_segments,
                        "resistant_count": resistant_count,
                        "resistant_percentage": resistant_pct,
                        "processing_time": results["processing_time"]
                    }
                )
            
            logger.info(f"Processing completed in {results['processing_time']:.2f} seconds")
            logger.info(f"Found {resistant_count} resistant sequences ({resistant_pct:.2f}%)")
            
            return results
            
        except Exception as e:
            error_msg = f"Error processing FASTA file: {str(e)}"
            logger.error(error_msg)
            if self.progress_tracker:
                self.progress_tracker.set_error(error_msg)
            
            results.update({
                "error": error_msg,
                "processing_time": time.time() - start_time,
                "end_time": datetime.now().isoformat()
            })
            
            return results
    
    def write_results(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Write prediction results to a CSV file.
        
        Args:
            results: List of result dictionaries
            output_file: Path to save the results
        """
        if not results:
            logger.warning("No results to write")
            return
        
        try:
            with open(output_file, 'w', newline='') as f:
                # Get all possible keys from the results
                fieldnames = set()
                for result in results:
                    fieldnames.update(result.keys())
                
                # Extract start and end positions from sequence IDs
                for result in results:
                    seq_id = result["Sequence_ID"]
                    try:
                        # Try to extract positions from the sequence ID
                        if "_segment_" in seq_id:
                            # Format: {original_id}_segment_{start}_{end}
                            parts = seq_id.split("_")
                            start = parts[-2]
                            end = parts[-1]
                        else:
                            # For non-segmented sequences, use the full length
                            start = "1"
                            end = str(result["Length"])
                    except Exception as e:
                        logger.warning(f"Could not extract positions from sequence ID {seq_id}: {str(e)}")
                        start = "1"
                        end = str(result["Length"])
                    
                    result["Start"] = start
                    result["End"] = end
                
                # Ensure Sequence_ID is the first column, followed by Start and End
                ordered_fields = ["Sequence_ID", "Start", "End", "Length", "Resistant", "Susceptible"]
                
                # Add any remaining fields
                for field in fieldnames:
                    if field not in ordered_fields:
                        ordered_fields.append(field)
                
                writer = csv.DictWriter(f, fieldnames=ordered_fields, delimiter=',')
                writer.writeheader()
                writer.writerows(results)
            
            logger.info(f"Results saved to {output_file}")
        
        except Exception as e:
            logger.error(f"Error writing results to {output_file}: {str(e)}")


# Standalone function for backward compatibility
def process_fasta_file(fasta_path: str, model_name: str, 
                      batch_size: int = 8, segment_length: int = 6000, 
                      segment_overlap: int = 0, output_file: Optional[str] = None, 
                      device: Optional[str] = None, enable_sequence_aggregation: bool = True,
                      resistance_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Process a FASTA file and make AMR predictions. Standalone function for backward compatibility.
    
    Args:
        fasta_path: Path to the FASTA file
        model_name: HuggingFace model name or path to local model
        batch_size: Batch size for predictions
        segment_length: Maximum segment length, 0 to disable splitting
        segment_overlap: Overlap between segments in nucleotides
        output_file: Path to save the results (default: generated based on timestamp)
        device: Device to run predictions on ('cpu', 'cuda', etc.)
        
    Returns:
        Dictionary with processing results and statistics
    """
    pipeline = PredictionPipeline(
        model_name=model_name,
        batch_size=batch_size,
        segment_length=segment_length,
        segment_overlap=segment_overlap,
        device=device,
        enable_sequence_aggregation=enable_sequence_aggregation,
        resistance_threshold=resistance_threshold
    )
    
    return pipeline.process_fasta_file(fasta_path, output_file)
