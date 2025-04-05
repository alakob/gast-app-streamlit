#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import os
import argparse
import sys
import logging
import time
from colorama import Fore, Style, init
from datetime import datetime
import re

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ASCII art banner for the application
BANNER = """
    ___    __  _______   _____                                        
   /   |  /  |/  / __ \ / ___/___  ____ ___  _____  ____  __________ 
  / /| | / /|_/ / /_/ / \__ \/ _ \/ __ `/ / / / _ \/ __ \/ ___/ ___/ 
 / ___ |/ /  / / _, _/ ___/ /  __/ /_/ / /_/ /  __/ / / / /__(__  )  
/_/  |_/_/  /_/_/ |_(_)____/\___/\__, /\__,_/\___/_/ /_/\___/____/   
                                   /_/                               
 ____               ___      __  _           
/ __ \_________  __/ (_)____/ /_(_)___  ____ 
/ /_/ / ___/ _ \/ /_/ / ___/ __/ / __ \/ __ \\
/ ____/ /  /  __/ __/ / /__/ /_/ / /_/ / / / /
/_/   /_/   \___/_/ /_/\___/\__/_/\____/_/ /_/ 
"""

def print_banner():
    """Print the ASCII art banner with colorful formatting"""
    print(f"{Fore.CYAN}{BANNER}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}AMR Sequence Prediction Processor{Style.RESET_ALL}")
    print(f"Version 1.0.0 - {datetime.now().strftime('%Y-%m-%d')}")
    print("="*80)

def parse_sequence_id(sequence_id):
    """
    Parse the sequence_ID to extract the original ID, start, and end positions.
    
    Args:
        sequence_id (str): The sequence ID from the prediction file
        
    Returns:
        tuple: (original_id, start, end)
    """
    # Split the sequence_ID on all underscores
    parts = sequence_id.split("_")
    
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
            logger.warning(f"Could not parse start/end positions from sequence ID: {sequence_id}")
            return sequence_id, None, None
    else:
        # Not enough parts to extract start and end
        logger.warning(f"Sequence ID does not have expected format: {sequence_id}")
        return sequence_id, None, None

def process_prediction_file(input_file, output_file, resistance_threshold=0.5):
    """
    Process an AMR prediction file, extract sequence information, and apply aggregation methods.
    
    Args:
        input_file (str): Path to the input prediction file
        output_file (str): Path to save the processed results
        resistance_threshold (float): Threshold for resistance classification
        
    Returns:
        pandas.DataFrame: DataFrame containing the processed results
    """
    start_time = time.time()
    logger.info(f"{Fore.CYAN}Processing AMR prediction file: {input_file}{Style.RESET_ALL}")
    
    try:
        # Read the prediction file
        df = pd.read_csv(input_file, sep='\t')
        logger.info(f"Loaded prediction file with {len(df)} rows and {len(df.columns)} columns")
        logger.info(f"Columns: {', '.join(df.columns)}")
        
        # Basic data validation
        required_columns = ['Sequence_ID', 'Resistant', 'Susceptible']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"{Fore.RED}Input file is missing required columns: {', '.join(missing_columns)}{Style.RESET_ALL}")
            sys.exit(1)
        
        # Parse sequence IDs to extract original ID, start, and end
        logger.info("Parsing sequence IDs to extract start and end positions...")
        parsed_data = [parse_sequence_id(seq_id) for seq_id in df['Sequence_ID']]
        
        # Add new columns for original ID, start, and end
        df['original_id'] = [data[0] for data in parsed_data]
        df['start'] = [data[1] for data in parsed_data]
        df['end'] = [data[2] for data in parsed_data]
        
        # Log statistics on parsed data
        valid_positions = df['start'].notna() & df['end'].notna()
        logger.info(f"Successfully parsed positions for {valid_positions.sum()} out of {len(df)} sequences")
        
        # Group by original_id
        logger.info("Grouping sequences by original_id...")
        grouped = df.groupby('original_id')
        unique_ids = len(grouped)
        logger.info(f"Found {unique_ids} unique sequence IDs")
        
        # Initialize results
        results = []
        
        # Process each group
        logger.info(f"Applying aggregation methods with resistance threshold: {resistance_threshold}")
        for original_id, group in grouped:
            # Method 1: Any Resistance
            any_resistant = (group['Resistant'] > resistance_threshold).any()
            any_resistant_count = (group['Resistant'] > resistance_threshold).sum()
            any_resistance_result = "Resistant" if any_resistant else "Susceptible"
            
            # Method 2: Majority Voting
            majority_resistant = (group['Resistant'] > group['Susceptible']).mean() > 0.5
            majority_vote_count = (group['Resistant'] > group['Susceptible']).sum()
            majority_vote_result = "Resistant" if majority_resistant else "Susceptible"
            
            # Method 3: Probability Averaging
            avg_resistance = group['Resistant'].mean()
            avg_susceptible = group['Susceptible'].mean()
            avg_classification = "Resistant" if avg_resistance > resistance_threshold else "Susceptible"
            
            # Find the min start and max end across all segments
            min_start = group['start'].min() if group['start'].notna().any() else None
            max_end = group['end'].max() if group['end'].notna().any() else None
            
            # Store results
            results.append({
                'sequence_id': original_id,
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
        
        # Save to CSV
        logger.info(f"Saving results to: {output_file}")
        results_df.to_csv(output_file, index=False)
        
        end_time = time.time()
        logger.info(f"{Fore.GREEN}Processing completed in {end_time - start_time:.2f} seconds{Style.RESET_ALL}")
        
        return results_df
        
    except Exception as e:
        logger.error(f"{Fore.RED}Error processing prediction file: {str(e)}{Style.RESET_ALL}")
        logger.error(f"Traceback: {e.__traceback__}")
        sys.exit(1)

def parse_args():
    """
    Parse command-line arguments
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description=f"{Fore.CYAN}Process AMR prediction files and extract sequence information{Style.RESET_ALL}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--input", "-i", required=True,
                      help="Path to input prediction file from amr_predictor_pretty_performance.py")
    
    parser.add_argument("--output", "-o", required=True,
                      help="Path to output CSV file")
    
    parser.add_argument("--threshold", "-t", type=float, default=0.5,
                      help="Resistance threshold for classification (default: 0.5)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Enable verbose logging")
    
    return parser.parse_args()

def main():
    """Main function to run the sequence prediction processing"""
    # Parse command-line arguments
    args = parse_args()
    
    # Show banner
    print_banner()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Process the prediction file
    process_prediction_file(
        input_file=args.input,
        output_file=args.output,
        resistance_threshold=args.threshold
    )

if __name__ == "__main__":
    main()
