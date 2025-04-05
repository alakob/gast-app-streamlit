import pandas as pd
import os
import glob
import re
import argparse
import sys
import logging
import time
from colorama import Fore, Style, init
from datetime import datetime

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
    ___    __  _______   ____                 ___      __  _           
   /   |  /  |/  / __ \ / __ \___  _____    /   | ___/ /_(_)___ _____ 
  / /| | / /|_/ / /_/ // / / / _ \/ ___/   / /| |/ __/ __/ / __ `/ __ \
 / ___ |/ /  / / _, _// /_/ /  __/ /      / ___ / /_/ /_/ / /_/ / / / /
/_/  |_/_/  /_/_/ |_(_)____/\___/_/      /_/  |_\__/\__/_/\__, /_/ /_/ 
                                                          /____/      
"""

def extract_genomic_filename(sequence_id):
    """Extract the genomic file name from the sequence_id (everything from 'fasta_' up to the first colon)"""
    logger.debug(f"Extracting genomic filename from sequence ID: {sequence_id}")
    match = re.search(r'(fasta_[^:]+)', sequence_id)
    if match:
        filename = match.group(1)
        logger.debug(f"Extracted genomic filename: {filename}")
        return filename
    logger.debug(f"Failed to extract genomic filename from: {sequence_id}")
    return None

def process_amr_files(prediction_files, output_file, model_suffix="_all_107_sequences_prediction"):
    """
    Process multiple AMR prediction files and aggregate results
    
    Parameters:
    -----------
    prediction_files : list
        List of file paths to AMR prediction files
    output_file : str
        Path to save the aggregated results CSV
    model_suffix : str, optional
        Suffix to remove from filenames when extracting model names
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame containing the aggregated results
    """
    start_time = time.time()
    logger.info(f"{Fore.CYAN}Starting AMR prediction file processing{Style.RESET_ALL}")
    logger.info(f"Processing {len(prediction_files)} prediction files with model suffix: '{model_suffix}'")
    
    # Create an empty DataFrame to store all results
    all_results = pd.DataFrame()
    total_files_processed = 0
    total_genomic_files_processed = 0
    
    for file_index, file_path in enumerate(prediction_files, 1):
        file_start_time = time.time()
        # Extract model name from the file path
        model_name = os.path.basename(file_path).split(model_suffix)[0]
        logger.info(f"{Fore.BLUE}Processing file {file_index}/{len(prediction_files)}: {os.path.basename(file_path)} (Model: {model_name}){Style.RESET_ALL}")
        
        # Read the prediction file
        try:
            logger.debug(f"Reading file: {file_path}")
            df = pd.read_csv(file_path, sep='\t')
            logger.debug(f"File loaded with {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"Columns: {', '.join(df.columns)}")
        except Exception as e:
            logger.error(f"{Fore.RED}Error reading file {file_path}: {str(e)}{Style.RESET_ALL}")
            continue
        
        # Basic data validation
        required_columns = ['Sequence_ID', 'Resistant', 'Susceptible']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"{Fore.RED}File {file_path} is missing required columns: {', '.join(missing_columns)}{Style.RESET_ALL}")
            continue
            
        # Log data statistics
        logger.debug(f"Resistant probability stats: min={df['Resistant'].min():.4f}, max={df['Resistant'].max():.4f}, mean={df['Resistant'].mean():.4f}")
        logger.debug(f"Susceptible probability stats: min={df['Susceptible'].min():.4f}, max={df['Susceptible'].max():.4f}, mean={df['Susceptible'].mean():.4f}")
        
        # Extract genomic file name
        logger.debug(f"Extracting genomic filenames from sequence IDs")
        df['genomic_file'] = df['Sequence_ID'].apply(extract_genomic_filename)
        
        # Check for missing genomic filenames
        missing_count = df['genomic_file'].isna().sum()
        if missing_count > 0:
            logger.warning(f"{Fore.YELLOW}Warning: {missing_count} sequences ({missing_count/len(df)*100:.2f}%) could not be matched to a genomic file{Style.RESET_ALL}")
            # Filter out rows with missing genomic filenames
            df = df.dropna(subset=['genomic_file'])
            logger.debug(f"Proceeding with {len(df)} sequences after removing entries with missing genomic filenames")
        
        # Group by genomic file name
        logger.debug(f"Grouping sequences by genomic file")
        grouped = df.groupby('genomic_file')
        unique_genomic_files = len(grouped)
        logger.info(f"Found {unique_genomic_files} unique genomic files in this prediction file")
        
        # Initialize results for this file
        file_results = []
        resistance_threshold = 0.5  # Hardcoded threshold for resistance classification
        logger.debug(f"Using resistance threshold of {resistance_threshold} for classification")
        
        # Process each genomic file group
        logger.debug(f"Processing each genomic file group")
        for genomic_file, group in grouped:
            process_start = time.time()
            logger.debug(f"Processing genomic file: {genomic_file} with {len(group)} sequences")
            
            # Method 1: Any Resistance
            any_resistant = (group['Resistant'] > resistance_threshold).any()
            any_resistant_count = (group['Resistant'] > resistance_threshold).sum()
            logger.debug(f"Method 1 (Any Resistance): {any_resistant_count}/{len(group)} resistant sequences -> {'Resistant' if any_resistant else 'Susceptible'}")
            
            # Method 2: Majority Voting
            majority_resistant = (group['Resistant'] > group['Susceptible']).mean() > resistance_threshold
            majority_vote_count = (group['Resistant'] > group['Susceptible']).sum()
            logger.debug(f"Method 2 (Majority Vote): {majority_vote_count}/{len(group)} sequences voted resistant -> {'Resistant' if majority_resistant else 'Susceptible'}")
            
            # Method 3: Probability Averaging
            avg_resistance = group['Resistant'].mean()
            avg_susceptible = group['Susceptible'].mean()
            avg_classification = "Resistant" if avg_resistance > resistance_threshold else "Susceptible"
            logger.debug(f"Method 3 (Avg Probability): Resistance={avg_resistance:.4f}, Susceptible={avg_susceptible:.4f} -> {avg_classification}")
            
            # Check for method agreement
            methods_agree = (any_resistant == majority_resistant) and (majority_resistant == (avg_resistance > resistance_threshold))
            logger.debug(f"Method agreement: {'All methods agree' if methods_agree else 'Methods disagree'}")
            
            # Store results
            file_results.append({
                'genomic_file': genomic_file,
                'model': model_name,
                'sequence_count': len(group),
                'any_resistance': "Resistant" if any_resistant else "Susceptible",
                'majority_vote': "Resistant" if majority_resistant else "Susceptible",
                'avg_resistance_prob': avg_resistance,
                'avg_susceptible_prob': avg_susceptible,
                'avg_classification': avg_classification
            })
            
            process_end = time.time()
            logger.debug(f"Finished processing genomic file in {process_end - process_start:.4f} seconds")
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(file_results)
        logger.debug(f"Created results DataFrame with {len(results_df)} genomic files")
        
        # Log resistance statistics for this file
        resistant_any = (results_df['any_resistance'] == "Resistant").sum()
        resistant_majority = (results_df['majority_vote'] == "Resistant").sum()
        resistant_avg = (results_df['avg_classification'] == "Resistant").sum()
        
        logger.info(f"Resistance summary for model {model_name}:")
        logger.info(f"  - Any resistance method: {resistant_any}/{len(results_df)} ({resistant_any/len(results_df)*100:.2f}%) classified as resistant")
        logger.info(f"  - Majority vote method: {resistant_majority}/{len(results_df)} ({resistant_majority/len(results_df)*100:.2f}%) classified as resistant")
        logger.info(f"  - Avg probability method: {resistant_avg}/{len(results_df)} ({resistant_avg/len(results_df)*100:.2f}%) classified as resistant")
        
        # Append to all results
        all_results = pd.concat([all_results, results_df])
        total_genomic_files_processed += unique_genomic_files
        
        file_end_time = time.time()
        logger.info(f"{Fore.GREEN}Completed processing file in {file_end_time - file_start_time:.2f} seconds{Style.RESET_ALL}")
        total_files_processed += 1
    
    # Save to CSV
    logger.info(f"{Fore.CYAN}Preparing to save aggregated results{Style.RESET_ALL}")
    
    # Check if output_file is a directory, and if so, append a default filename
    if os.path.isdir(output_file):
        output_path = os.path.join(output_file, "amr_aggregated_results.csv")
        logger.debug(f"Output is a directory, using default filename: amr_aggregated_results.csv")
    else:
        output_path = output_file
        logger.debug(f"Using specified output path: {output_path}")
        
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        logger.debug(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)
    
    # Log overall statistics before saving
    logger.info(f"Overall aggregation statistics:")
    logger.info(f"  - Total files processed: {total_files_processed}/{len(prediction_files)}")
    logger.info(f"  - Total unique models: {all_results['model'].nunique()}")
    logger.info(f"  - Total unique genomic files: {all_results['genomic_file'].nunique()}")
    logger.info(f"  - Total aggregated results: {len(all_results)} records")
    
    # Calculate and log overall resistance percentages
    any_resistant_pct = (all_results['any_resistance'] == "Resistant").mean() * 100
    majority_resistant_pct = (all_results['majority_vote'] == "Resistant").mean() * 100
    avg_resistant_pct = (all_results['avg_classification'] == "Resistant").mean() * 100
    logger.info(f"  - Average resistance (Any method): {any_resistant_pct:.2f}%")
    logger.info(f"  - Average resistance (Majority method): {majority_resistant_pct:.2f}%")
    logger.info(f"  - Average resistance (Avg probability method): {avg_resistant_pct:.2f}%")
    
    # Save the results
    try:
        all_results.to_csv(output_path, index=False)
        logger.info(f"{Fore.GREEN}Results successfully saved to {output_path}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Error saving results to {output_path}: {str(e)}{Style.RESET_ALL}")
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f"{Fore.GREEN}AMR prediction processing completed in {total_time:.2f} seconds{Style.RESET_ALL}")
    
    return all_results

def parse_args():
    """
    Parse command-line arguments for the AMR prediction aggregation script
    
    Returns:
    --------
    argparse.Namespace
        Parsed command-line arguments
    """
    logger.debug("Parsing command-line arguments")
    
    parser = argparse.ArgumentParser(
        description="Aggregate AMR prediction results across multiple models and genomic files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input-dir", "-i",
        help="Directory containing prediction files to process"
    )
    input_group.add_argument(
        "--input-pattern",
        help="Glob pattern to match prediction files (e.g., '*_prediction.txt')"
    )
    input_group.add_argument(
        "--input-files",
        nargs="+",
        help="Specific prediction files to process"
    )
    
    # Output arguments
    parser.add_argument(
        "--output", "-o",
        default="amr_aggregated_results.csv",
        help="Path for the output CSV file or directory (if only a directory is provided, amr_aggregated_results.csv will be used as the filename)"
    )
    
    # Optional pattern argument
    parser.add_argument(
        "--file-pattern",
        default="*_all_107_sequences_prediction.txt",
        help="File pattern to match when using --input-dir (default pattern matches standard AMR prediction files)"
    )
    
    # Optional model name extraction argument
    parser.add_argument(
        "--model-suffix",
        default="_all_107_sequences_prediction",
        help="Suffix to remove from filenames when extracting model names"
    )
    
    # Add logging verbosity argument
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity level (use -v for INFO, -vv for DEBUG)"
    )
    
    args = parser.parse_args()
    logger.debug(f"Arguments parsed successfully: {vars(args)}")
    
    return args

def run_aggregation():
    """
    Main function to run the AMR prediction aggregation with command-line arguments
    """
    start_time = time.time()
    
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging level based on verbosity
    if args.verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        # Keep the default level from the basicConfig
        pass
    
    logger.info(f"{Fore.CYAN}{BANNER}{Style.RESET_ALL}")
    logger.info(f"{Fore.YELLOW}AMR Predictions Aggregation Tool{Style.RESET_ALL}")
    logger.info(f"Version: 1.2.0  Runtime: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    logger.info("-" * 80)
    
    logger.info(f"Starting AMR prediction aggregation tool at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Log the run configuration
    logger.info(f"Configuration:")
    if args.input_files:
        logger.info(f"  - Input mode: Specific files")
        logger.info(f"  - Number of files specified: {len(args.input_files)}")
    elif args.input_pattern:
        logger.info(f"  - Input mode: Glob pattern")
        logger.info(f"  - Pattern: {args.input_pattern}")
    else:
        logger.info(f"  - Input mode: Directory")
        logger.info(f"  - Directory: {args.input_dir}")
        logger.info(f"  - File pattern: {args.file_pattern}")
    
    logger.info(f"  - Output: {args.output}")
    logger.info(f"  - Model suffix: {args.model_suffix}")
    
    # Determine which prediction files to process based on input arguments
    logger.debug("Determining files to process based on input arguments")
    
    prediction_files = []
    if args.input_files:
        logger.debug(f"Using explicitly provided file list with {len(args.input_files)} files")
        prediction_files = args.input_files
    elif args.input_pattern:
        logger.debug(f"Searching for files matching pattern: {args.input_pattern}")
        prediction_files = glob.glob(args.input_pattern)
        logger.debug(f"Found {len(prediction_files)} files matching pattern")
    else:  # args.input_dir is set
        # Ensure the input directory exists
        if not os.path.isdir(args.input_dir):
            logger.error(f"{Fore.RED}Error: Input directory '{args.input_dir}' does not exist.{Style.RESET_ALL}")
            sys.exit(1)
        
        logger.debug(f"Searching for files in directory: {args.input_dir} with pattern: {args.file_pattern}")
        # Get the current working directory before changing to input directory
        original_dir = os.getcwd()
        logger.debug(f"Current working directory: {original_dir}")
        
        # Change to the input directory and get files matching pattern
        logger.debug(f"Changing to input directory: {args.input_dir}")
        os.chdir(args.input_dir)
        matching_files = glob.glob(args.file_pattern)
        logger.debug(f"Found {len(matching_files)} files matching pattern in directory")
        
        # Get full paths to files relative to the original directory
        prediction_files = [os.path.join(args.input_dir, file) for file in matching_files]
        
        # Change back to the original directory
        logger.debug(f"Changing back to original directory: {original_dir}")
        os.chdir(original_dir)
    
    # Check if any files were found
    if not prediction_files:
        logger.error(f"{Fore.RED}No prediction files found. Please check your input arguments.{Style.RESET_ALL}")
        sys.exit(1)
    
    logger.info(f"{Fore.GREEN}Found {len(prediction_files)} prediction files to process.{Style.RESET_ALL}")
    
    # Process the prediction files
    logger.info(f"{Fore.CYAN}Starting prediction file processing{Style.RESET_ALL}")
    results = process_amr_files(prediction_files, args.output, args.model_suffix)
    
    # Print detailed summary
    logger.info(f"{Fore.CYAN}\nFinal Summary:{Style.RESET_ALL}")
    logger.info(f"Total genomic files processed: {results['genomic_file'].nunique()}")
    logger.info(f"Total models: {results['model'].nunique()}")
    
    # Resistance statistics
    any_resistant_count = (results['any_resistance'] == "Resistant").sum()
    logger.info(f"Genomic files with any resistance: {any_resistant_count} ({any_resistant_count/len(results)*100:.2f}%)")
    
    majority_resistant_count = (results['majority_vote'] == "Resistant").sum()
    logger.info(f"Genomic files with majority resistance: {majority_resistant_count} ({majority_resistant_count/len(results)*100:.2f}%)")
    
    avg_resistant_count = (results['avg_classification'] == "Resistant").sum()
    logger.info(f"Genomic files with average resistance > 0.5: {avg_resistant_count} ({avg_resistant_count/len(results)*100:.2f}%)")
    
    # Method agreement statistics
    if all(col in results.columns for col in ['any_resistance', 'majority_vote', 'avg_classification']):
        results['methods_agree'] = (
            (results['any_resistance'] == results['majority_vote']) & 
            (results['majority_vote'] == results['avg_classification'])
        )
        agreement_rate = results['methods_agree'].mean() * 100
        logger.info(f"Method agreement rate: {agreement_rate:.2f}% of genomic files have all three methods in agreement")
    
    # Log by model statistics if multiple models are present
    if results['model'].nunique() > 1:
        logger.info(f"\nResistance rates by model:")
        model_stats = results.groupby('model').apply(lambda x: {
            'any_resistance': (x['any_resistance'] == "Resistant").mean() * 100,
            'majority_vote': (x['majority_vote'] == "Resistant").mean() * 100,
            'avg_classification': (x['avg_classification'] == "Resistant").mean() * 100,
            'count': len(x)
        }).to_dict()
        
        for model, stats in model_stats.items():
            logger.info(f"Model: {model} ({stats['count']} genomic files)")
            logger.info(f"  - Any resistance method: {stats['any_resistance']:.2f}%")
            logger.info(f"  - Majority vote method: {stats['majority_vote']:.2f}%")
            logger.info(f"  - Avg probability method: {stats['avg_classification']:.2f}%")
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f"{Fore.GREEN}AMR prediction aggregation completed in {total_time:.2f} seconds{Style.RESET_ALL}")
    logger.info("-" * 80)

# Run the script if it's the main module
if __name__ == "__main__":
    try:
        run_aggregation()
    except KeyboardInterrupt:
        logger.warning(f"{Fore.YELLOW}Process interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"{Fore.RED}Unhandled exception: {str(e)}{Style.RESET_ALL}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)