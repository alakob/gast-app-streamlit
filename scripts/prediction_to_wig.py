#!/usr/bin/env python
# coding: utf-8

"""
prediction_to_wig.py - Convert AMR predictor output to WIG format

This script takes the output of amr_predictor_pretty_performance.py and converts it
to a WIG (Wiggle) format file for visualization in genome browsers.
"""

import os
import argparse
import pandas as pd
import logging
import re
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Define processing directory
PROCESSING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'processing')

# Create processing directory if it doesn't exist
if not os.path.exists(PROCESSING_DIR):
    os.makedirs(PROCESSING_DIR, exist_ok=True)
    logger.info(f"Created processing directory at: {PROCESSING_DIR}")

def parse_sequence_id(sequence_id):
    """
    Parse the sequence ID to extract contig, start, and end positions.
    
    Example sequence_ID: fasta_27215228:27215228mrsa_S13_L001_R1_001_(paired)_contig_1_1_6000
    
    Args:
        sequence_id (str): The sequence ID from the AMR predictor output
        
    Returns:
        tuple: (contig_id, start, end)
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

def process_prediction_file(input_file, output_file=None):
    """
    Process the AMR prediction file and extract sequence information.
    
    Args:
        input_file (str): Path to the AMR prediction TSV file
        output_file (str, optional): Path to save the processed DataFrame
        
    Returns:
        pd.DataFrame: Processed DataFrame with contig, start, end columns
    """
    try:
        # Read the prediction file
        logger.info(f"Reading prediction file: {input_file}")
        df = pd.read_csv(input_file, sep='\t')
        
        # Check if required columns exist
        if 'Sequence_ID' not in df.columns or 'Resistant' not in df.columns:
            logger.error(f"Required columns not found in {input_file}")
            return None
        
        # Create new columns for contig, start, and end
        logger.info("Parsing sequence IDs to extract contig, start, and end positions")
        parsed_data = [parse_sequence_id(seq_id) for seq_id in df['Sequence_ID']]
        
        df['contig'] = [data[0] for data in parsed_data]
        df['start'] = [data[1] for data in parsed_data]
        df['end'] = [data[2] for data in parsed_data]
        
        # Rename Resistant column to prob_resistance for clarity
        df['prob_resistance'] = df['Resistant']
        
        # Save processed DataFrame if output_file is provided
        if output_file:
            df.to_csv(output_file, sep='\t', index=False)
            logger.info(f"Processed data saved to {output_file}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error processing prediction file: {str(e)}")
        return None

def create_wiggle_file(df, output_wig=None, step_size=1200):
    """
    Create a WIG file from the processed prediction data using fixedStep format.
    
    Args:
        df (pd.DataFrame): DataFrame with contig, start, end, and prob_resistance columns
        output_wig (str, optional): Path to save the WIG file. If None, a file will be created in the processing directory.
        step_size (int, optional): Step size in base pairs. Defaults to 1200.
        
    Returns:
        str: Path to the created WIG file if successful, None otherwise
    """
    try:
        # If no output path is provided, create one in the processing directory
        if output_wig is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_wig = os.path.join(PROCESSING_DIR, f"amr_visualization_{timestamp}.wig")
        
        logger.info(f"Creating WIG file with step size {step_size}bp: {output_wig}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_wig)), exist_ok=True)
        
        # Ensure data is sorted by contig and start position
        df = df.sort_values(by=['contig', 'start'])
        
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
                    f.write(f"fixedStep chrom={row['contig']} start={start_pos} step={step_size} span={step_size}\n")
                else:
                    # For continuing the same contig but with a gap, create a new fixedStep section
                    if row['start'] > prev_end + step_size:
                        start_pos = row['start']
                        f.write(f"fixedStep chrom={row['contig']} start={start_pos} step={step_size} span={step_size}\n")
                
                # Calculate positions based on step size
                pos = row['start']
                while pos <= row['end']:
                    # Write the resistance probability for this position
                    f.write(f"{row['prob_resistance']}\n")
                    pos += step_size
                
                # Keep track of the end position for this contig
                prev_end = row['end']
        
        logger.info(f"WIG file created successfully: {output_wig}")
        return output_wig
    
    except Exception as e:
        logger.error(f"Error creating WIG file: {str(e)}")
        return None

def main():
    """Main function to run the prediction to WIG conversion."""
    parser = argparse.ArgumentParser(description='Convert AMR predictor output to WIG format')
    parser.add_argument('--input', '-i', required=True, help='Path to the AMR prediction TSV file')
    parser.add_argument('--output', '-o', help='Path to save the WIG file (default: input_file_base.wig)')
    parser.add_argument('--processed', '-p', help='Path to save the processed prediction data (optional)')
    parser.add_argument('--step-size', '-s', type=int, default=1200, 
                      help='Step size in base pairs for the WIG file (default: 1200)')
    
    args = parser.parse_args()
    
    # Set default output file if not provided
    if not args.output:
        input_base = os.path.splitext(args.input)[0]
        args.output = f"{input_base}.wig"
    
    # Process the prediction file
    processed_df = process_prediction_file(args.input, args.processed)
    
    if processed_df is not None:
        # Create the WIG file with the specified step size
        success = create_wiggle_file(processed_df, args.output, step_size=args.step_size)
        
        if success:
            logger.info(f"Conversion completed successfully with step size {args.step_size}bp")
            return 0
    
    logger.error("Conversion failed")
    return 1

if __name__ == "__main__":
    exit(main())
