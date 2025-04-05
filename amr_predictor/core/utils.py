"""
Core utilities for the AMR Predictor module.

This module contains common utility functions used across the AMR Predictor package,
including logging setup, progress tracking, file handling, and other shared functionality.
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Union, Callable
from contextlib import contextmanager
import re

# Try to import colorama for colored terminal output
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

# Configure module logger
logger = logging.getLogger("amr_predictor")

class ProgressTracker:
    """
    Progress tracking system for long-running operations.
    
    This class provides methods to track and report progress of multi-step operations,
    which can be used by a UI to display current processing status.
    """
    
    def __init__(self, total_steps: int = 100, callback: Optional[Callable] = None):
        """
        Initialize a new progress tracker.
        
        Args:
            total_steps: Total number of steps in the operation
            callback: Optional callback function to be called on progress updates
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.status = "Initializing"
        self.start_time = time.time()
        self.callback = callback
        self.additional_info = {}
        self.error = None
    
    def update(self, step: Optional[int] = None, increment: Optional[int] = None, 
               status: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the progress state.
        
        Args:
            step: Set the current step to this value (or increment if not provided)
            increment: Increment the current step by this value
            status: Update the status message
            additional_info: Additional information to store with this update
        """
        if step is not None:
            self.current_step = min(step, self.total_steps)
        elif increment is not None:
            self.current_step = min(self.current_step + increment, self.total_steps)
        
        if status is not None:
            self.status = status
        
        if additional_info is not None:
            self.additional_info.update(additional_info)
        
        # Call the callback if provided
        if self.callback is not None:
            self.callback(self)
    
    def set_error(self, error: str) -> None:
        """Set an error message and update status to Error"""
        self.error = error
        self.status = "Error"
        if self.callback is not None:
            self.callback(self)
    
    @property
    def percentage(self) -> float:
        """Get the current progress as a percentage"""
        return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
    
    @property
    def elapsed_time(self) -> float:
        """Get the elapsed time in seconds"""
        return time.time() - self.start_time
    
    def get_state(self) -> Dict[str, Any]:
        """Get the current state as a dictionary suitable for serialization"""
        return {
            "percentage": self.percentage,
            "step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.status,
            "elapsed_time": self.elapsed_time,
            "additional_info": self.additional_info,
            "error": self.error
        }


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with colored output if available.
    
    Args:
        level: The logging level to use
        
    Returns:
        The configured logger
    """
    logger = logging.getLogger("amr_predictor")
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(level)
    
    # Create a colored formatter if colorama is available
    if COLOR_AVAILABLE:
        class ColoredFormatter(logging.Formatter):
            """Custom formatter with colors for different log levels"""
            FORMATS = {
                logging.DEBUG: Fore.BLUE + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
                logging.INFO: Fore.GREEN + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
                logging.WARNING: Fore.YELLOW + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
                logging.ERROR: Fore.RED + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
                logging.CRITICAL: Fore.RED + Style.BRIGHT + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL
            }
            
            def format(self, record):
                log_fmt = self.FORMATS.get(record.levelno)
                formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
                return formatter.format(record)
        
        # Create console handler with colored formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
    else:
        # Create standard console handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


@contextmanager
def timer(name: str, metrics_dict: Optional[Dict[str, float]] = None):
    """
    Context manager for timing code blocks and recording metrics.
    
    Args:
        name: Name of the operation being timed
        metrics_dict: Optional dictionary to store timing results
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        if metrics_dict is not None:
            metrics_dict[name] = duration
        logger.debug(f"Timing - {name}: {duration:.4f} seconds")


def print_banner(app_name: str = "AMR Predictor", version: str = "1.0.0") -> None:
    """
    Print a nice ASCII art banner for the tool.
    
    Args:
        app_name: Name of the application
        version: Version string
    """
    banner = f"""
    {Fore.CYAN}╔═══════════════════════════════════════════════════════╗
    ║ {Fore.YELLOW}   █████╗ ███╗   ███╗██████╗{Fore.GREEN}     ██████╗ ██████╗   {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██╔══██╗████╗ ████║██╔══██╗{Fore.GREEN}    ██╔══██╗██╔══██╗  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ███████║██╔████╔██║██████╔╝{Fore.GREEN}    ██████╔╝██████╔╝  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██╔══██║██║╚██╔╝██║██╔══██╗{Fore.GREEN}    ██╔═══╝ ██╔══██╗  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██║  ██║██║ ╚═╝ ██║██║  ██║{Fore.GREEN}    ██║     ██║  ██║  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝{Fore.GREEN}    ╚═╝     ╚═╝  ╚═╝  {Fore.CYAN}║
    ║                                                       ║
    ║  {Fore.MAGENTA}{app_name} v{version}{Fore.CYAN}            ║
    ╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    if COLOR_AVAILABLE:
        print(banner)
    else:
        # Print simpler banner if color not available
        print(f"\n=== {app_name} v{version} ===\n")


def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
    """
    if directory_path and not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        logger.debug(f"Created directory: {directory_path}")


def get_default_output_path(prefix: str, extension: str = "txt", input_file: Optional[str] = None) -> str:
    """
    Generate a default output path with timestamp.
    
    Args:
        prefix: Prefix for the filename
        extension: File extension (without dot)
        input_file: Optional path to input file, whose basename will be prepended to the output filename
    
    Returns:
        Path string with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If input file is provided, prepend its basename (without extension)
    if input_file:
        input_basename = os.path.splitext(os.path.basename(input_file))[0]
        return f"{input_basename}_{prefix}_{timestamp}.{extension}"
    
    return f"{prefix}_{timestamp}.{extension}"


def parse_sequence_id(sequence_id: str) -> tuple:
    """
    Parse the sequence ID to extract relevant information.
    
    This is a unified sequence ID parser that handles different formats from
    the various AMR predictor scripts.
    
    Args:
        sequence_id: The sequence ID to parse
        
    Returns:
        Tuple of (original_id, start, end) or (contig_id, start, end)
    """
    try:
        # Check for segmented sequence format
        if "segment" in sequence_id:
            # Extract original ID (everything before "_segment_")
            pattern = r"(.+)_segment_(\d+)"
            match = re.search(pattern, sequence_id)
            if match:
                original_id = match.group(1)
                segment_num = int(match.group(2))
                # Assume standard segment length of 6000 bp
                segment_length = 6000
                start = (segment_num - 1) * segment_length + 1
                end = segment_num * segment_length
                return original_id, start, end
        
        # Handle standard format with positions at the end
        parts = sequence_id.split("_")
        
        # Check if the last two parts could be start/end positions
        if len(parts) >= 3:
            try:
                # Try to parse the last two parts as integers
                start = int(parts[-2])
                end = int(parts[-1])
                # Reconstruct the original ID
                original_id = "_".join(parts[:-2])
                return original_id, start, end
            except ValueError:
                pass
        
        # Try to extract genomic filename (for predictions_aggregation.py)
        match = re.search(r'(fasta_[^:]+)', sequence_id)
        if match:
            filename = match.group(1)
            return filename, None, None
            
        # If all else fails, return the original ID with default positions
        logger.warning(f"Could not parse positions from sequence ID: {sequence_id}")
        return sequence_id, 1, 6000
        
    except Exception as e:
        logger.error(f"Error parsing sequence ID {sequence_id}: {str(e)}")
        return sequence_id, 1, 6000
