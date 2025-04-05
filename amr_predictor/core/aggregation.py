import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

def aggregate_predictions(input_file: str, output_file: Optional[str] = None, 
                         min_confidence: float = 0.5, 
                         min_resistant_fraction: float = 0.5) -> Dict[str, Any]:
    """
    Aggregate predictions from a TSV file.
    
    Args:
        input_file: Path to the input TSV file
        output_file: Path to save the aggregated results (default: input_basename_aggregation.tsv)
        min_confidence: Minimum confidence threshold for predictions
        min_resistant_fraction: Minimum fraction of segments that must be resistant
        
    Returns:
        Dictionary with aggregation results and statistics
    """
    start_time = time.time()
    
    # Set default output file if not provided
    if output_file is None:
        input_basename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{input_basename}_aggregation.tsv"
        logger.info(f"Using default output file: {output_file}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "."
    ensure_directory_exists(output_dir)
    
    # Initialize results
    results = {
        "input_file": input_file,
        "output_file": output_file,
        "min_confidence": min_confidence,
        "min_resistant_fraction": min_resistant_fraction,
        "start_time": datetime.now().isoformat(),
        "aggregated_results": [],
        "processing_time": 0,
        "error": None
    } 