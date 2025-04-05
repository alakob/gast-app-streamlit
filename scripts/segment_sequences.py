#!/usr/bin/env python3
"""
Segment Sequences - A tool for segmenting genomic sequences with overlap

This script segments genomic sequences from a multifasta file into smaller chunks,
with configurable length and overlap between segments.
"""

import argparse
import os
import sys
import logging
from datetime import datetime
import time
from Bio import SeqIO
from tqdm import tqdm

# Configure colorful terminal output if colorama is available
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_AVAILABLE = True
except ImportError:
    COLOR_AVAILABLE = False
    # Create dummy color constants to avoid conditionals in the code
    class DummyColors:
        def __getattr__(self, name):
            return ""
    Fore = DummyColors()
    Style = DummyColors()

def setup_logger(verbose=False):
    """Set up a pretty logger with color-coding and timestamps"""
    logger = logging.getLogger("segment_sequences")
    
    # Set the appropriate log level
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Define custom formatter
    class ColoredFormatter(logging.Formatter):
        """Custom formatter with colors for different log levels"""
        FORMATS = {
            logging.DEBUG: Fore.CYAN + "[%(asctime)s] %(levelname)-8s: %(message)s" + Style.RESET_ALL,
            logging.INFO: Fore.GREEN + "[%(asctime)s] %(levelname)-8s: %(message)s" + Style.RESET_ALL,
            logging.WARNING: Fore.YELLOW + "[%(asctime)s] %(levelname)-8s: %(message)s" + Style.RESET_ALL,
            logging.ERROR: Fore.RED + "[%(asctime)s] %(levelname)-8s: %(message)s" + Style.RESET_ALL,
            logging.CRITICAL: Style.BRIGHT + Fore.RED + "[%(asctime)s] %(levelname)-8s: %(message)s" + Style.RESET_ALL,
            'DEFAULT': "[%(asctime)s] %(levelname)-8s: %(message)s"
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
            formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
            return formatter.format(record)

    ch.setFormatter(ColoredFormatter())
    logger.addHandler(ch)
    
    return logger

def print_banner():
    """Print a nice ASCII art banner for the tool"""
    banner = f"""
    {Fore.CYAN}╔═══════════════════════════════════════════════════════╗
    ║ {Fore.YELLOW}  ███████╗███████╗ ██████╗ ███╗   ███╗███████╗███╗   ██╗████████╗{Fore.CYAN} ║
    ║ {Fore.YELLOW}  ██╔════╝██╔════╝██╔════╝ ████╗ ████║██╔════╝████╗  ██║╚══██╔══╝{Fore.CYAN} ║
    ║ {Fore.YELLOW}  ███████╗█████╗  ██║  ███╗██╔████╔██║█████╗  ██╔██╗ ██║   ██║   {Fore.CYAN} ║
    ║ {Fore.YELLOW}  ╚════██║██╔══╝  ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║   ██║   {Fore.CYAN} ║
    ║ {Fore.YELLOW}  ███████║███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║   ██║   {Fore.CYAN} ║
    ║ {Fore.YELLOW}  ╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   {Fore.CYAN} ║
    ║                                                                 ║
    ║  {Fore.MAGENTA}Genomic Sequence Segmentation Tool v1.0{Fore.CYAN}                ║
    ╚═══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    if COLOR_AVAILABLE:
        print(banner)
    else:
        # Print simpler banner if color not available
        print("\n=== Genomic Sequence Segmentation Tool v1.0 ===\n")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description=f"{Fore.CYAN}Segment genomic sequences from a multifasta file with configurable overlap{Style.RESET_ALL}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
        {Fore.GREEN}Examples:{Style.RESET_ALL}
          # Basic usage
          {Fore.YELLOW}python segment_sequences.py --input sequences.fasta --output segmented/ --segment-length 6000{Style.RESET_ALL}
          
          # With overlap
          {Fore.YELLOW}python segment_sequences.py --input sequences.fasta --output segmented/ --segment-length 6000 --segment-overlap 1000{Style.RESET_ALL}
          
          # Output to a single file instead of multiple files
          {Fore.YELLOW}python segment_sequences.py --input sequences.fasta --output segmented/ --single-file{Style.RESET_ALL}
          
          # Verbose output
          {Fore.YELLOW}python segment_sequences.py --input sequences.fasta --output segmented/ --segment-length 6000 --verbose{Style.RESET_ALL}
        """
    )
    
    # Input/Output options
    parser.add_argument("--input", "-i", required=True,
                      help="Path to input FASTA file containing genomic sequences")
    parser.add_argument("--output", "-o", required=True,
                      help="Path to output directory for segmented sequences")
    
    # Segmentation options
    parser.add_argument("--segment-length", "-l", type=int, default=6000,
                      help="Maximum length of each segment in nucleotides (default: %(default)s)")
    parser.add_argument("--segment-overlap", "-v", type=int, default=0,
                      help="Overlap between segments in nucleotides (default: %(default)s). Must be less than segment-length.")
    parser.add_argument("--min-length", "-m", type=int, default=6,
                      help="Minimum length required for a segment (default: %(default)s)")
    
    # Output format options
    parser.add_argument("--single-file", "-s", action="store_true",
                      help="Output all segments to a single FASTA file instead of one file per input sequence")
    parser.add_argument("--prefix", "-p", default="segment",
                      help="Prefix for segment IDs (default: %(default)s)")
    
    # Other options
    parser.add_argument("--verbose", action="store_true",
                      help="Enable verbose logging")
    parser.add_argument("--no-progress", action="store_true",
                      help="Disable progress bars")
    
    return parser.parse_args()

def split_sequence(seq_id, sequence, max_length=6000, min_length=6, overlap=0, id_prefix="segment"):
    """
    Split a genomic sequence into segments of specified length with overlap
    
    Args:
        seq_id (str): Sequence identifier
        sequence (str): DNA/RNA sequence
        max_length (int): Maximum length of each segment
        min_length (int): Minimum length required for a segment
        overlap (int): Number of overlapping bases between segments
        id_prefix (str): Prefix for segment IDs
        
    Returns:
        list: List of (segment_id, segment_sequence) tuples
    """
    logger = logging.getLogger("segment_sequences")
    result_segments = []
    seq_length = len(sequence)
    
    # Validate parameters
    if max_length <= 0:
        logger.warning(f"Invalid max_length {max_length}, using default of 6000")
        max_length = 6000
        
    # Ensure overlap is valid (not greater than or equal to max_length)
    effective_overlap = min(overlap, max_length - 1) if overlap > 0 else 0
    if effective_overlap != overlap and overlap > 0:
        logger.warning(f"Overlap ({overlap}) must be less than max_length ({max_length}). Using {effective_overlap} instead.")
    
    logger.debug(f"Splitting sequence '{seq_id}' (length={seq_length}) with max_length={max_length}, overlap={effective_overlap}")
    
    # If sequence is shorter than max_length, don't split
    if seq_length <= max_length:
        logger.debug(f"Sequence '{seq_id}' is shorter than max_length, no splitting needed")
        return [(seq_id, sequence)]
    
    # Calculate step size (how much to move forward after each segment)
    step_size = max_length - effective_overlap
    if step_size <= 0:  # Safety check
        step_size = 1
        logger.warning(f"Invalid step size calculated. Using step_size=1 instead.")
    
    # Split the sequence into segments with specified overlap
    segments_created = 0
    for start in range(0, seq_length, step_size):
        # Calculate end position
        end = min(start + max_length, seq_length)
        
        # Extract segment
        segment = sequence[start:end]
        
        # Only include segments meeting minimum length
        if len(segment) >= min_length:
            segment_id = f"{seq_id}_{id_prefix}_{start+1}_{end}"
            result_segments.append((segment_id, segment))
            segments_created += 1
            logger.debug(f"Created segment {segment_id} (length={len(segment)})")
            
            # For very verbose logging, show the overlap regions
            if effective_overlap > 0 and segments_created > 1 and logger.level <= logging.DEBUG:
                prev_end = start
                prev_start = max(0, prev_end - effective_overlap)
                overlap_region = sequence[prev_start:prev_end]
                logger.debug(f"Overlap with previous segment: {prev_start+1}-{prev_end} ({len(overlap_region)} bp)")
        else:
            logger.debug(f"Skipped segment {start+1}-{end} (length={len(segment)} < {min_length})")
    
    logger.info(f"Split sequence '{seq_id}' into {segments_created} segments with {effective_overlap}bp overlap")
    return result_segments

def process_fasta_file(input_file, output_dir, segment_length, segment_overlap, min_length, 
                       single_file=False, id_prefix="segment", show_progress=True):
    """
    Process a FASTA file and segment each sequence
    
    Args:
        input_file (str): Path to input FASTA file
        output_dir (str): Path to output directory
        segment_length (int): Maximum segment length
        segment_overlap (int): Overlap between segments
        min_length (int): Minimum length required for a segment
        single_file (bool): Whether to output all segments to a single file
        id_prefix (str): Prefix for segment IDs
        show_progress (bool): Whether to show progress bars
        
    Returns:
        tuple: (total_sequences, total_segments, total_bp)
    """
    logger = logging.getLogger("segment_sequences")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up output file if using single-file mode
    if single_file:
        output_path = os.path.join(output_dir, f"all_segments.fasta")
        output_handle = open(output_path, "w")
    else:
        output_handle = None  # Will be set for each sequence
    
    # Parse FASTA file
    try:
        # Count sequences first for the progress bar
        sequence_count = sum(1 for _ in SeqIO.parse(input_file, "fasta"))
        logger.info(f"Found {sequence_count} sequences in {input_file}")
        
        # Setup progress tracking
        total_segments = 0
        total_bp_processed = 0
        
        # Process each sequence
        sequences = SeqIO.parse(input_file, "fasta")
        if show_progress and sequence_count > 1:
            sequences = tqdm(sequences, total=sequence_count, desc="Processing sequences",
                           unit="seq", bar_format="{l_bar}%s{bar}%s{r_bar}" % 
                           (Fore.GREEN, Style.RESET_ALL) if COLOR_AVAILABLE else None)
        
        for record in sequences:
            seq_id = record.id
            sequence = str(record.seq)
            seq_length = len(sequence)
            total_bp_processed += seq_length
            
            # Set up per-sequence output file if not using single-file mode
            if not single_file:
                output_path = os.path.join(output_dir, f"{seq_id}_segments.fasta")
                output_handle = open(output_path, "w")
            
            # Split the sequence
            segments = split_sequence(
                seq_id, sequence, 
                max_length=segment_length, 
                min_length=min_length,
                overlap=segment_overlap,
                id_prefix=id_prefix
            )
            
            # Write segments to file
            for segment_id, segment_seq in segments:
                output_handle.write(f">{segment_id}\n")
                # Write sequence with 60 nucleotides per line
                for i in range(0, len(segment_seq), 60):
                    output_handle.write(f"{segment_seq[i:i+60]}\n")
            
            total_segments += len(segments)
            
            # Close per-sequence output file if not using single-file mode
            if not single_file:
                output_handle.close()
                logger.info(f"Wrote {len(segments)} segments to {output_path}")
        
        # Close output file if using single-file mode
        if single_file:
            output_handle.close()
            logger.info(f"Wrote {total_segments} segments to {output_path}")
        
        return sequence_count, total_segments, total_bp_processed
    
    except Exception as e:
        logger.error(f"Error processing FASTA file: {str(e)}")
        if output_handle is not None:
            output_handle.close()
        raise

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logger
    logger = setup_logger(args.verbose)
    
    # Show banner
    print_banner()
    
    # Log important parameters
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Segment length: {args.segment_length}")
    logger.info(f"Segment overlap: {args.segment_overlap}")
    logger.info(f"Minimum segment length: {args.min_length}")
    logger.info(f"Output mode: {'Single file' if args.single_file else 'Multiple files'}")
    
    # Validate segment parameters
    if args.segment_overlap >= args.segment_length:
        logger.warning(f"Segment overlap ({args.segment_overlap}) must be less than segment length ({args.segment_length})")
        args.segment_overlap = args.segment_length // 10  # Default to 10% overlap as a fallback
        logger.warning(f"Setting segment overlap to {args.segment_overlap} bp")
    
    # Validate input file
    if not os.path.exists(args.input):
        logger.error(f"Input file '{args.input}' does not exist")
        sys.exit(1)
    
    try:
        # Start timer
        start_time = time.time()
        
        # Process FASTA file
        num_sequences, num_segments, total_bp = process_fasta_file(
            args.input, 
            args.output,
            args.segment_length,
            args.segment_overlap,
            args.min_length,
            args.single_file,
            args.prefix,
            not args.no_progress
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log summary statistics
        logger.info("=" * 50)
        logger.info("Segmentation Summary:")
        logger.info(f"Input sequences: {num_sequences}")
        logger.info(f"Output segments: {num_segments}")
        logger.info(f"Segments per sequence (avg): {num_segments / num_sequences:.2f}")
        logger.info(f"Total base pairs processed: {total_bp:,} bp")
        
        if args.segment_overlap > 0:
            total_overlap_bp = (num_segments - num_sequences) * args.segment_overlap
            logger.info(f"Total overlap: {total_overlap_bp:,} bp ({total_overlap_bp/total_bp*100:.2f}% of input)")
        
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        logger.info(f"Processing speed: {total_bp / processing_time / 1000:.2f} Kbp/s")
        logger.info("=" * 50)
        
        logger.info(f"Segmentation completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
