"""
Command-line interface for AMR Predictor.

This module provides a unified command-line interface for all AMR Predictor 
functionality, including prediction, aggregation, and visualization.
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

from ..core.utils import logger, setup_logger, print_banner, ProgressTracker
from ..core.prediction import PredictionPipeline
from ..processing.aggregation import PredictionAggregator
from ..processing.sequence_processing import SequenceProcessor
from ..processing.visualization import VisualizationGenerator

class CLIProgressTracker(ProgressTracker):
    """
    CLI-specific progress tracker that displays progress on the console.
    """
    
    def __init__(self, total_steps: int = 100):
        """Initialize the CLI progress tracker"""
        super().__init__(total_steps=total_steps, callback=self._print_progress)
    
    def _print_progress(self, tracker):
        """Print progress to the console"""
        percentage = f"{tracker.percentage:.1f}%"
        status = tracker.status
        elapsed = f"{tracker.elapsed_time:.1f}s"
        
        # If terminal supports it, use carriage return to update the same line
        sys.stdout.write(f"\r{percentage} | {status} | Elapsed: {elapsed}")
        sys.stdout.flush()
        
        # If we've completed or have an error, add a newline
        if tracker.percentage >= 100 or tracker.error:
            print()
            if tracker.error:
                print(f"Error: {tracker.error}")


def predict_command(args) -> int:
    """
    Run the prediction command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set up logging
    logger_instance = setup_logger(level=args.verbose and logging.DEBUG or logging.INFO)
    
    # Print banner
    print_banner("AMR Predictor", "1.0.0")
    
    # Initialize progress tracker
    progress_tracker = CLIProgressTracker(total_steps=100)
    
    # Initialize pipeline
    pipeline = PredictionPipeline(
        model_name=args.model,
        batch_size=args.batch_size,
        segment_length=args.segment_length,
        segment_overlap=args.segment_overlap,
        device=args.cpu and "cpu" or None,
        progress_tracker=progress_tracker,
        enable_sequence_aggregation=not args.no_aggregation,
        resistance_threshold=args.threshold
    )
    
    # Process the FASTA file
    results = pipeline.process_fasta_file(args.fasta, args.output)
    
    # Check for errors
    if "error" in results and results["error"]:
        logger.error(f"Prediction failed: {results['error']}")
        return 1
    
    logger.info(f"Prediction completed successfully")
    logger.info(f"Results saved to: {results['output_file']}")
    
    return 0


def aggregate_command(args: argparse.Namespace) -> None:
    """
    Handle the aggregate command.
    
    Args:
        args: Command line arguments
    """
    try:
        # Set up logging based on verbosity
        logger_instance = setup_logger(level=args.verbose and logging.DEBUG or logging.INFO)
        
        # Print banner
        print_banner("AMR Aggregator", "1.0.0")
        
        # Initialize progress tracker
        progress_tracker = CLIProgressTracker()
        
        # Initialize aggregator with model suffix
        aggregator = PredictionAggregator(
            model_suffix=args.model_suffix,
            resistance_threshold=args.threshold,
            progress_tracker=progress_tracker
        )
        
        # Get input file basename for output file
        input_basename = os.path.splitext(os.path.basename(args.input_files[0]))[0]
        output_file = os.path.join(args.output, f"{input_basename}_genome_aggregate.csv")
        
        # Process prediction files
        results = aggregator.process_prediction_files(
            input_files=args.input_files,
            output_dir=args.output,
            model_suffix=args.model_suffix
        )
        
        if results.empty:
            logger.warning("No results were generated from the prediction files")
            return
        
        # Save results to CSV
        results.to_csv(output_file, index=False)
        
        # Log summary statistics
        total_files = len(results)
        files_with_resistance = results['any_resistance'].sum()
        files_with_majority_resistance = (results['majority_vote'] == 'Resistant').sum()
        files_with_avg_resistance = (results['avg_classification'] == 'Resistant').sum()
        method_agreement = results['methods_agree'].mean() * 100
        
        logger.info("\nAggregation Summary:")
        logger.info(f"Total genomic files processed: {total_files}")
        logger.info(f"Files with any resistance: {files_with_resistance} ({files_with_resistance/total_files*100:.1f}%)")
        logger.info(f"Files with majority resistance: {files_with_majority_resistance} ({files_with_majority_resistance/total_files*100:.1f}%)")
        logger.info(f"Files with average resistance: {files_with_avg_resistance} ({files_with_avg_resistance/total_files*100:.1f}%)")
        logger.info(f"Method agreement rate: {method_agreement:.1f}%")
        logger.info(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error in aggregate command: {str(e)}")
        raise


def sequence_command(args) -> int:
    """
    Run the sequence processing command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set up logging
    logger_instance = setup_logger(level=args.verbose and logging.DEBUG or logging.INFO)
    
    # Print banner
    print_banner("AMR Sequence Processor", "1.0.0")
    
    # Initialize progress tracker
    progress_tracker = CLIProgressTracker(total_steps=100)
    
    # Initialize processor
    processor = SequenceProcessor(
        resistance_threshold=args.threshold,
        progress_tracker=progress_tracker
    )
    
    # Get input file basename for output file
    input_basename = os.path.splitext(os.path.basename(args.input))[0]
    output_file = os.path.join(args.output, f"{input_basename}_sequence_processed.csv")
    
    # Process the prediction file
    results = processor.process_prediction_file(args.input, output_file)
    
    if results.empty:
        logger.error("Sequence processing failed: no results generated")
        return 1
    
    logger.info(f"Sequence processing completed successfully")
    logger.info(f"Results saved to: {output_file}")
    
    return 0


def visualization_command(args) -> int:
    """
    Run the visualization command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set up logging
    logger_instance = setup_logger(level=args.verbose and logging.DEBUG or logging.INFO)
    
    # Print banner
    print_banner("AMR Visualizer", "1.0.0")
    
    # Initialize progress tracker
    progress_tracker = CLIProgressTracker(total_steps=100)
    
    # Initialize generator
    generator = VisualizationGenerator(
        step_size=args.step_size,
        progress_tracker=progress_tracker
    )
    
    # Set default output file if not provided
    if not args.output:
        input_base = os.path.splitext(args.input)[0]
        args.output = f"{input_base}.wig"
    
    # Process the prediction file
    processed_df = generator.process_prediction_file(args.input, args.processed)
    
    if processed_df is not None:
        # Create the WIG file with the specified step size
        success = generator.create_wiggle_file(processed_df, args.output)
        
        if success:
            logger.info(f"Conversion completed successfully with step size {args.step_size}bp")
            return 0
    
    logger.error("Conversion failed")
    return 1


def create_parser() -> argparse.ArgumentParser:
    """
    Create the command-line argument parser.
    
    Returns:
        The configured argument parser
    """
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="AMR Predictor: A tool for predicting antimicrobial resistance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create the predict command parser
    predict_parser = subparsers.add_parser(
        "predict",
        help="Predict antimicrobial resistance from FASTA sequences",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Prediction command arguments
    predict_parser.add_argument("--fasta", "-f", required=True, 
                            help="Path to input FASTA file containing genomic sequences")
    predict_parser.add_argument("--model", "-m", default="alakob/DraGNOME-2.5b-v1", 
                            help="HuggingFace model name or path")
    predict_parser.add_argument("--batch-size", "-b", type=int, default=8, 
                            help="Batch size for predictions")
    predict_parser.add_argument("--segment-length", "-s", type=int, default=6000, 
                            help="Maximum segment length, 0 to disable splitting")
    predict_parser.add_argument("--segment-overlap", "-o", type=int, default=0, 
                            help="Overlap between segments in nucleotides for long sequences. Must be less than --segment-length.")
    predict_parser.add_argument("--cpu", action="store_true", 
                            help="Force CPU inference instead of GPU")
    predict_parser.add_argument("--output", 
                            help="Path to output file (default: amr_predictions_<timestamp>.tsv)")
    predict_parser.add_argument("--verbose", "-v", action="store_true", 
                            help="Enable verbose logging")
    predict_parser.add_argument("--threshold", "-t", type=float, default=0.5,
                            help="Resistance threshold for classification (default: 0.5)")
    predict_parser.add_argument("--no-aggregation", action="store_true",
                            help="Disable sequence-level aggregation")
    predict_parser.set_defaults(func=predict_command)
    
    # Create the aggregate command parser
    aggregate_parser = subparsers.add_parser(
        "aggregate",
        help="Aggregate AMR prediction results across multiple models or files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Input options (mutually exclusive)
    input_group = aggregate_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-dir", "-i",
                         help="Directory containing prediction files to process")
    input_group.add_argument("--input-pattern",
                         help="Glob pattern to match prediction files (e.g., '*_prediction.txt')")
    input_group.add_argument("--input-files", nargs="+",
                         help="Specific prediction files to process")
    
    # Other aggregation options
    aggregate_parser.add_argument("--output", "-o", default="amr_aggregated_results.csv",
                              help="Path for the output CSV file or directory")
    aggregate_parser.add_argument("--file-pattern", default="*_all_107_sequences_prediction.txt",
                              help="File pattern to match when using --input-dir")
    aggregate_parser.add_argument("--model-suffix", default="_all_107_sequences_prediction",
                              help="Suffix to remove from filenames when extracting model names")
    aggregate_parser.add_argument("--threshold", "-t", type=float, default=0.5,
                              help="Resistance threshold for classification (default: 0.5)")
    aggregate_parser.add_argument("--verbose", "-v", action="count", default=0,
                              help="Increase verbosity level (use -v for INFO, -vv for DEBUG)")
    aggregate_parser.set_defaults(func=aggregate_command)
    
    # Create the sequence command parser
    sequence_parser = subparsers.add_parser(
        "sequence",
        help="Process prediction results at the sequence level",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Sequence command arguments
    sequence_parser.add_argument("--input", "-i", required=True,
                             help="Path to input prediction file from predict command")
    sequence_parser.add_argument("--output", "-o", required=True,
                             help="Path to output CSV file")
    sequence_parser.add_argument("--threshold", "-t", type=float, default=0.5,
                             help="Resistance threshold for classification")
    sequence_parser.add_argument("--verbose", "-v", action="store_true",
                             help="Enable verbose logging")
    sequence_parser.set_defaults(func=sequence_command)
    
    # Create the visualization command parser
    viz_parser = subparsers.add_parser(
        "visualize",
        help="Convert prediction results to visualization formats",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Visualization command arguments
    viz_parser.add_argument("--input", "-i", required=True,
                        help="Path to the AMR prediction TSV file")
    viz_parser.add_argument("--output", "-o",
                        help="Path to save the WIG file (default: input_file_base.wig)")
    viz_parser.add_argument("--processed", "-p",
                        help="Path to save the processed prediction data (optional)")
    viz_parser.add_argument("--step-size", "-s", type=int, default=1200,
                        help="Step size in base pairs for the WIG file")
    viz_parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    viz_parser.set_defaults(func=visualization_command)
    
    return parser


def main() -> int:
    """
    Main entry point for the AMR Predictor CLI.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Create the argument parser
    parser = create_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is specified, print help and exit
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute the appropriate command
    return args.func(args)


if __name__ == "__main__":
    # Import logging here to avoid circular imports
    sys.exit(main())
