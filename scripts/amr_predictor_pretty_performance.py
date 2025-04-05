#!/usr/bin/env python
# coding: utf-8

import argparse
import os
import sys
import logging
import time
import json
import csv
import statistics
import platform
import shutil
import re
import subprocess
import traceback
from datetime import datetime
import textwrap
from contextlib import contextmanager
from collections import Counter
import threading
import queue
from pathlib import Path
import math  # Added for Shannon entropy calculation
import gzip  # Added for compression ratio calculation

# Try to import the AMRPerformanceAnalyzer for prediction
try:
    from model.amr_performance_analysis import AMRPerformanceAnalyzer
    PERFORMANCE_ANALYZER_AVAILABLE = True
except ImportError:
    PERFORMANCE_ANALYZER_AVAILABLE = False

# Conditionally import psutil if available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False



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

@contextmanager
def timer(name, metrics_dict=None):
    """Context manager for timing code blocks and recording metrics"""
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        if metrics_dict is not None:
            metrics_dict[name] = duration
        logger = logging.getLogger("amr_predictor")
        logger.debug(f"Timing - {name}: {duration:.4f} seconds")


def collect_system_info() -> dict:
    """Collect detailed system information for performance analysis
    
    Returns:
        dict: Dictionary containing system specifications
    """
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "time": datetime.now().isoformat(),
    }
    
    # Get CPU model name on different platforms
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        system_info["cpu_model"] = line.split(":")[1].strip()
                        break
        except Exception as e:
            system_info["cpu_model"] = f"Error retrieving CPU model: {str(e)}"
    elif platform.system() == "Darwin":  # macOS
        try:
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], 
                                   capture_output=True, text=True, check=True)
            system_info["cpu_model"] = result.stdout.strip()
        except Exception as e:
            system_info["cpu_model"] = f"Error retrieving CPU model: {str(e)}"
    elif platform.system() == "Windows":
        try:
            result = subprocess.run(["wmic", "cpu", "get", "name"], 
                                   capture_output=True, text=True, check=True)
            # Parse the output (skip the header)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                system_info["cpu_model"] = lines[1].strip()
        except Exception as e:
            system_info["cpu_model"] = f"Error retrieving CPU model: {str(e)}"
    
    # Get total RAM
    try:
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            system_info["total_ram_gb"] = round(mem.total / (1024**3), 2)
            system_info["available_ram_gb"] = round(mem.available / (1024**3), 2)
            system_info["ram_percent_used"] = mem.percent
        else:
            # Fallback for total RAM
            if platform.system() == "Linux":
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if "MemTotal" in line:
                                mem_kb = int(line.split()[1])
                                system_info["total_ram_gb"] = round(mem_kb / (1024**2), 2)
                                break
                except Exception:
                    pass
            elif platform.system() == "Darwin":  # macOS
                try:
                    result = subprocess.run(["sysctl", "-n", "hw.memsize"], 
                                           capture_output=True, text=True, check=True)
                    mem_bytes = int(result.stdout.strip())
                    system_info["total_ram_gb"] = round(mem_bytes / (1024**3), 2)
                except Exception:
                    pass
            elif platform.system() == "Windows":
                try:
                    result = subprocess.run(["wmic", "computersystem", "get", "totalphysicalmemory"], 
                                           capture_output=True, text=True, check=True)
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        mem_bytes = int(lines[1].strip())
                        system_info["total_ram_gb"] = round(mem_bytes / (1024**3), 2)
                except Exception:
                    pass
    except Exception as e:
        system_info["ram_error"] = str(e)
    
    # Get disk information
    try:
        if PSUTIL_AVAILABLE:
            disk = psutil.disk_usage('/')
            system_info["disk_total_gb"] = round(disk.total / (1024**3), 2)
            system_info["disk_free_gb"] = round(disk.free / (1024**3), 2)
            system_info["disk_percent_used"] = disk.percent
        else:
            # Basic disk info using shutil
            total, used, free = shutil.disk_usage('/')
            system_info["disk_total_gb"] = round(total / (1024**3), 2)
            system_info["disk_free_gb"] = round(free / (1024**3), 2)
            system_info["disk_percent_used"] = round((used / total) * 100, 2)
    except Exception as e:
        system_info["disk_error"] = str(e)
    
    # Try to get GPU info if available
    try:
        # Import torch here to avoid circular import issues
        import torch
        if torch.cuda.is_available():
            system_info["gpu_available"] = True
            system_info["gpu_name"] = torch.cuda.get_device_name(0)
            system_info["gpu_count"] = torch.cuda.device_count()
            system_info["cuda_version"] = torch.version.cuda
            
            # Try to get GPU memory info
            try:
                gpu_mem_allocated = round(torch.cuda.memory_allocated(0) / (1024**3), 2)
                gpu_mem_reserved = round(torch.cuda.memory_reserved(0) / (1024**3), 2)
                system_info["gpu_memory_allocated_gb"] = gpu_mem_allocated
                system_info["gpu_memory_reserved_gb"] = gpu_mem_reserved
            except Exception:
                pass
                
            # Try to get total GPU memory using nvidia-smi if available
            try:
                result = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], 
                                       capture_output=True, text=True, check=True)
                gpu_mem_total = int(result.stdout.strip())
                system_info["gpu_memory_total_mb"] = gpu_mem_total
            except Exception:
                pass
        else:
            system_info["gpu_available"] = False
    except Exception as e:
        system_info["gpu_error"] = str(e)
        
    return system_info


def max_consecutive_repeats(sequence: str, k: int = 2) -> int:
    """Calculate the maximum number of consecutive repeats of any k-mer

    Args:
        sequence: DNA sequence string
        k: Length of the k-mer (default: 2)

    Returns:
        int: Maximum number of consecutive repeats
    """
    if len(sequence) < k:
        return 0
    max_repeats = 1
    for i in range(len(sequence) - k):
        repeat = 1
        while (i + k * repeat < len(sequence) and 
               sequence[i:i+k] == sequence[i + k*repeat:i + k*(repeat+1)]):
            repeat += 1
        max_repeats = max(max_repeats, repeat)
    return max_repeats


def calculate_sequence_complexity(sequence: str) -> dict:
    """Calculate complexity metrics for a DNA sequence
    
    Args:
        sequence: DNA sequence string
        
    Returns:
        dict: Dictionary containing various complexity metrics
    """
    if not sequence:
        return {}
        
    # Convert sequence to uppercase for consistency
    sequence = sequence.upper()
    
    # Calculate basic metrics
    length = len(sequence)
    metrics = {"length": length}
    
    # Nucleotide frequencies
    nucleotide_counts = Counter(sequence)
    for nucleotide in ['A', 'C', 'G', 'T', 'N']:
        metrics[f"{nucleotide}_count"] = nucleotide_counts.get(nucleotide, 0)
        metrics[f"{nucleotide}_frequency"] = (
            round(nucleotide_counts.get(nucleotide, 0) / length, 4) if length > 0 else 0
        )
    
    # GC content
    gc_count = nucleotide_counts.get('G', 0) + nucleotide_counts.get('C', 0)
    metrics["gc_content"] = round(gc_count / length, 4) if length > 0 else 0
    
    # Ambiguous bases (non-ACGT)
    acgt_count = sum(nucleotide_counts.get(n, 0) for n in ['A', 'C', 'G', 'T'])
    metrics["ambiguous_bases_count"] = length - acgt_count
    metrics["ambiguous_bases_percentage"] = (
        round((length - acgt_count) / length * 100, 2) if length > 0 else 0
    )
    
    # Calculate k-mer diversity (for k=3, trinucleotides)
    k = 3
    if length >= k:
        kmers = [sequence[i:i+k] for i in range(length - k + 1)]
        unique_kmers = len(set(kmers))
        metrics["unique_3mers"] = unique_kmers
        metrics["3mer_diversity"] = round(unique_kmers / (4**k), 4) if 4**k > 0 else 0
        metrics["3mer_complexity"] = (
            round(unique_kmers / (length - k + 1), 4) if (length - k + 1) > 0 else 0
        )
    
    # Homopolymer runs (stretches of the same nucleotide)
    max_homopolymer = 0
    current_homopolymer = 1
    for i in range(1, length):
        if sequence[i] == sequence[i-1] and sequence[i] in 'ACGT':
            current_homopolymer += 1
        else:
            max_homopolymer = max(max_homopolymer, current_homopolymer)
            current_homopolymer = 1
    max_homopolymer = max(max_homopolymer, current_homopolymer)
    metrics["max_homopolymer_length"] = max_homopolymer
    
    # Shannon entropy
    entropy = 0
    for nucleotide in ['A', 'C', 'G', 'T']:
        p = metrics[f"{nucleotide}_frequency"]
        if p > 0:
            entropy -= p * math.log2(p)
    metrics["shannon_entropy"] = round(entropy, 4)
    
    # Compression ratio
    sequence_bytes = sequence.encode('utf-8')
    compressed = gzip.compress(sequence_bytes)
    metrics["compression_ratio"] = round(len(compressed) / len(sequence_bytes), 4)
    
    # Unique 4-mers
    k = 4
    if length >= k:
        kmers = [sequence[i:i+k] for i in range(length - k + 1)]
        unique_kmers = len(set(kmers))
        metrics["unique_4mers"] = unique_kmers
        metrics["4mer_diversity"] = round(unique_kmers / (4**k), 4) if 4**k > 0 else 0
        metrics["4mer_complexity"] = (
            round(unique_kmers / (length - k + 1), 4) if (length - k + 1) > 0 else 0
        )
    
    # GC content variation
    window_size = 500
    gc_windows = []
    for i in range(0, length, window_size):
        window = sequence[i:i + window_size]
        if len(window) >= window_size // 2:  # Include partial windows if at least half size
            gc_count = window.count('G') + window.count('C')
            gc_content = gc_count / len(window)
            gc_windows.append(gc_content)
    metrics["gc_content_std"] = (
        round(statistics.stdev(gc_windows), 4) if len(gc_windows) > 1 else 0
    )
    
    # Maximum dinucleotide repeats
    metrics["max_dinucleotide_repeats"] = max_consecutive_repeats(sequence, k=2)
    
    return metrics

def setup_logger():
    """Set up a pretty logger with color-coding and timestamps"""
    logger = logging.getLogger("amr_predictor")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
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

# Global dictionary to store performance metrics
PERFORMANCE_METRICS = {
    "sequence_metrics": [],
    "global_metrics": {},
    "system_info": {}
}

def save_performance_metrics(output_path):
    """Save performance metrics to a file for further analysis"""
    logger = logging.getLogger("amr_predictor")
    
    # Check if output_path is a directory and generate a filename if needed
    if os.path.isdir(output_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_path, f"amr_timing_{timestamp}.csv")
        logger.info(f"Output path is a directory, using file: {output_path}")
    
    logger.info(f"Saving performance metrics to {output_path}")
    
    try:
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Save detailed metrics as CSV
        with open(output_path, 'w', newline='') as f:
            if not PERFORMANCE_METRICS["sequence_metrics"]:
                logger.warning("No performance metrics to save")
                return
                
            fieldnames = PERFORMANCE_METRICS["sequence_metrics"][0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for metrics in PERFORMANCE_METRICS["sequence_metrics"]:
                filtered_metrics = {key: metrics[key] for key in fieldnames if key in metrics}
                writer.writerow(filtered_metrics)
                
        # Save summary metrics, system info, and resource usage as JSON
        summary_path = os.path.splitext(output_path)[0] + "_summary.json"
        with open(summary_path, 'w') as f:
            json_data = {
                "global_metrics": PERFORMANCE_METRICS["global_metrics"],
                "system_info": PERFORMANCE_METRICS["system_info"]
            }
            
            # Add resource usage if available
            if "resource_usage" in PERFORMANCE_METRICS:
                json_data["resource_usage"] = PERFORMANCE_METRICS["resource_usage"]
                
            json.dump(json_data, f, indent=2)
            
        # If we have raw resource measurements, save them separately
        if "resource_usage" in PERFORMANCE_METRICS and "raw_measurements" in PERFORMANCE_METRICS["resource_usage"]:
            resource_csv_path = os.path.splitext(output_path)[0] + "_resources.csv"
            with open(resource_csv_path, 'w', newline='') as f:
                measurements = PERFORMANCE_METRICS["resource_usage"]["raw_measurements"]
                if measurements:
                    fieldnames = measurements[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for measurement in measurements:
                        writer.writerow(measurement)
                    logger.info(f"Resource usage details saved to {resource_csv_path}")
            
        logger.info(f"Performance metrics saved successfully. Summary available at {summary_path}")
    except Exception as e:
        logger.error(f"Error saving performance metrics: {str(e)}")

def monitor_system_resources(interval=1.0, stop_event=None):
    """Monitor system resources (CPU, memory, GPU) at regular intervals
    
    Args:
        interval: Seconds between measurements
        stop_event: Threading event to signal monitoring to stop
        
    Returns:
        dict: Dictionary with resource usage statistics
    """
    if not PSUTIL_AVAILABLE:
        return {"error": "psutil not available for resource monitoring"}
        
    measurements = []
    start_time = time.time()
    
    try:
        while not stop_event.is_set():
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            
            measurement = {
                "timestamp": time.time() - start_time,
                "cpu_percent": cpu_percent,
                "memory_percent": mem.percent,
                "memory_used_gb": round(mem.used / (1024**3), 2)
            }
            
            # Add GPU metrics if available
            try:
                import torch
                if torch.cuda.is_available():
                    measurement["gpu_memory_allocated_gb"] = round(torch.cuda.memory_allocated(0) / (1024**3), 2)
                    measurement["gpu_memory_reserved_gb"] = round(torch.cuda.memory_reserved(0) / (1024**3), 2)
                    if hasattr(torch.cuda, "memory_stats") and callable(torch.cuda.memory_stats):
                        stats = torch.cuda.memory_stats(0)
                        if "active.all.current" in stats:
                            measurement["gpu_active_blocks"] = stats["active.all.current"]
            except Exception:
                pass
                
            measurements.append(measurement)
            time.sleep(interval)
    except Exception as e:
        measurements.append({"error": str(e)})
        
    # Calculate summary statistics
    if measurements:
        # Safely get the timestamp from the last measurement if it exists
        last_measurement = measurements[-1]
        last_timestamp = last_measurement.get("timestamp", 0) if "timestamp" in last_measurement else 0
        
        summary = {
            "monitoring_duration": last_timestamp,
            "sample_count": len(measurements),
            "cpu_percent": {
                "min": min([m.get("cpu_percent", 0) for m in measurements if "cpu_percent" in m], default=0),
                "max": max([m.get("cpu_percent", 0) for m in measurements if "cpu_percent" in m], default=0),
                "avg": sum([m.get("cpu_percent", 0) for m in measurements if "cpu_percent" in m]) / 
                        len([m for m in measurements if "cpu_percent" in m]) if any("cpu_percent" in m for m in measurements) else 0
            },
            "memory_percent": {
                "min": min([m.get("memory_percent", 0) for m in measurements if "memory_percent" in m], default=0),
                "max": max([m.get("memory_percent", 0) for m in measurements if "memory_percent" in m], default=0),
                "avg": sum([m.get("memory_percent", 0) for m in measurements if "memory_percent" in m]) / 
                        len([m for m in measurements if "memory_percent" in m]) if any("memory_percent" in m for m in measurements) else 0
            },
            "raw_measurements": measurements[:50]  # Store first 50 measurements for detailed analysis
        }
        
        # Add GPU stats if available
        if any("gpu_memory_allocated_gb" in m for m in measurements):
            summary["gpu_memory_allocated_gb"] = {
                "min": min([m.get("gpu_memory_allocated_gb", 0) for m in measurements if "gpu_memory_allocated_gb" in m], default=0),
                "max": max([m.get("gpu_memory_allocated_gb", 0) for m in measurements if "gpu_memory_allocated_gb" in m], default=0),
                "avg": sum([m.get("gpu_memory_allocated_gb", 0) for m in measurements if "gpu_memory_allocated_gb" in m]) / 
                        len([m for m in measurements if "gpu_memory_allocated_gb" in m]) if any("gpu_memory_allocated_gb" in m for m in measurements) else 0
            }
        
        return summary
    
    return {"error": "No measurements collected"}


def print_performance_summary():
    """Print a summary of performance metrics to the console"""
    if not PERFORMANCE_METRICS["sequence_metrics"]:
        return
        
    print("\n" + "="*50)
    print(f"{Fore.CYAN}PERFORMANCE METRICS SUMMARY{Style.RESET_ALL}")
    print("="*50)
    
    # Extract sequence lengths and processing times
    seq_lengths = [m["sequence_length"] for m in PERFORMANCE_METRICS["sequence_metrics"]]
    proc_times = [m["total_processing_time"] for m in PERFORMANCE_METRICS["sequence_metrics"]]
    
    # Calculate statistics
    avg_time = statistics.mean(proc_times)
    max_time = max(proc_times)
    min_time = min(proc_times)
    
    print(f"\n{Fore.YELLOW}Prediction Time Statistics:{Style.RESET_ALL}")
    print(f"  Average time per sequence: {avg_time:.4f} seconds")
    print(f"  Minimum time: {min_time:.4f} seconds")
    print(f"  Maximum time: {max_time:.4f} seconds")
    
    # Add correlation info
    if len(seq_lengths) > 1:
        try:
            import numpy as np
            correlation = np.corrcoef(seq_lengths, proc_times)[0, 1]
            print(f"\n{Fore.YELLOW}Correlation Analysis:{Style.RESET_ALL}")
            print(f"  Correlation between sequence length and processing time: {correlation:.4f}")
        except ImportError:
            pass
            
    print("\n" + "="*50)

def print_banner():
    """Print a nice ASCII art banner for the tool"""
    banner = f"""
    {Fore.CYAN}╔═══════════════════════════════════════════════════════╗
    ║ {Fore.YELLOW}   █████╗ ███╗   ███╗██████╗{Fore.GREEN}     ██████╗ ██████╗   {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██╔══██╗████╗ ████║██╔══██╗{Fore.GREEN}    ██╔══██╗██╔══██╗  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ███████║██╔████╔██║██████╔╝{Fore.GREEN}    ██████╔╝██████╔╝  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██╔══██║██║╚██╔╝██║██╔══██╗{Fore.GREEN}    ██╔═══╝ ██╔══██╗  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ██║  ██║██║ ╚═╝ ██║██║  ██║{Fore.GREEN}    ██║     ██║  ██║  {Fore.CYAN}║
    ║ {Fore.YELLOW}  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝{Fore.GREEN}    ╚═╝     ╚═╝  ╚═╝  {Fore.CYAN}║
    ║                                                       ║
    ║  {Fore.MAGENTA}Antimicrobial Resistance Predictor v1.0{Fore.CYAN}            ║
    ╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    if COLOR_AVAILABLE:
        print(banner)
    else:
        # Print simpler banner if color not available
        print("\n=== Antimicrobial Resistance Predictor v1.0 ===\n")

def predict_total_processing_time(fasta_file, logger, output_dir=None):
    """
    Predict the total processing time for a FASTA file using the AMRPerformanceAnalyzer
    
    Args:
        fasta_file (str): Path to the FASTA file
        logger (logging.Logger): Logger to use for output
        output_dir (str): Output directory for prediction results
        
    Returns:
        float: Predicted total processing time in seconds, or None if prediction fails
    """
    if not PERFORMANCE_ANALYZER_AVAILABLE:
        logger.error("AMRPerformanceAnalyzer is not available. Make sure model/amr_performance_analysis.py is in your path.")
        return None
        
    try:
        # Load sequences to make prediction
        sequences = []
        
        try:
            from Bio import SeqIO
            logger.info(f"Reading sequences from {fasta_file} for time prediction")
            
            # Parse FASTA file
            for record in SeqIO.parse(fasta_file, "fasta"):
                sequences.append(str(record.seq))
                
            logger.info(f"Loaded {len(sequences)} sequences for time prediction")
            
        except ImportError:
            logger.error("BioPython is required for processing FASTA files. Install with 'pip install biopython'")
            return None
            
        if not sequences:
            logger.warning(f"No sequences found in {fasta_file}")
            return None
            
        # Initialize the analyzer
        output_dir = Path(output_dir if output_dir else ".")
        analyzer = AMRPerformanceAnalyzer(output_dir=output_dir)
        
        # Search for models in the default location
        model_dir = output_dir / 'models'
        model_path = None
        
        if model_dir.exists():
            # Find all model files
            model_files = list(model_dir.glob('best_model_*.joblib'))
            if model_files:
                # Sort by modification time, most recent first
                model_path = str(sorted(model_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                logger.info(f"Using model: {model_path}")
            
        # If no model found, warn the user
        if not model_path:
            logger.warning("No prediction model found. Run amr_performance_analysis.py analyze first to create a model.")
            return None
            
        # Predict total processing time
        total_time = analyzer.predict_total_processing_time(sequences, model_path)
        
        if total_time is not None:
            # Get file stats
            fasta_path = Path(fasta_file)
            file_size_mb = fasta_path.stat().st_size / (1024 * 1024)
            
            # Print pretty summary
            if COLOR_AVAILABLE:
                print(f"\n{Fore.GREEN}╔{'═' * 78}╗")
                print(f"║ {Fore.CYAN}Processing Time Prediction for {Fore.YELLOW}{fasta_path.name}{Fore.GREEN}{' ' * (43 - len(fasta_path.name))}║")
                print(f"╠{'═' * 78}╣")
                print(f"║ {Fore.WHITE}Total sequences: {Fore.YELLOW}{len(sequences):<10}{Fore.WHITE}File size: {Fore.YELLOW}{file_size_mb:.2f} MB{' ' * 35}║")
                print(f"║ {Fore.WHITE}Predicted processing time: {Fore.YELLOW}{total_time:.2f} seconds {Fore.WHITE}({total_time/60:.2f} minutes){' ' * 15}║")
                print(f"╚{'═' * 78}╝{Style.RESET_ALL}")
            else:
                print(f"\nProcessing Time Prediction for {fasta_path.name}")
                print(f"Total sequences: {len(sequences)}     File size: {file_size_mb:.2f} MB")
                print(f"Predicted processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
                
        return total_time
        
    except Exception as e:
        logger.error(f"Error predicting processing time: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def main():
    # Setup colored logger
    logger = setup_logger()
    
    # Collect system information at startup
    PERFORMANCE_METRICS["system_info"] = collect_system_info()
    
    # Create parser with fancy help formatting
    parser = argparse.ArgumentParser(
        description=f"{Fore.CYAN}Predict Antimicrobial Resistance (AMR) from genomic sequences{Style.RESET_ALL}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
        {Fore.GREEN}Examples:{Style.RESET_ALL}
          # Basic usage
          {Fore.YELLOW}python amr_predictor.py --fasta your_sequences.fasta{Style.RESET_ALL}
          
          # Advanced usage with custom model and parameters
          {Fore.YELLOW}python amr_predictor.py --fasta your_sequences.fasta --model your/custom-model --batch-size 32 --segment-length 6000 --segment-overlap 120 --output results.tsv{Style.RESET_ALL}
          
          # Force CPU inference
          {Fore.YELLOW}python amr_predictor.py --fasta your_sequences.fasta --cpu{Style.RESET_ALL}
          
          # Disable sequence splitting
          {Fore.YELLOW}python amr_predictor.py --fasta your_sequences.fasta --segment-length 0{Style.RESET_ALL}
          
          # Run with verbose logging
          {Fore.YELLOW}python amr_predictor.py --fasta your_sequences.fasta --verbose{Style.RESET_ALL}

        {Fore.CYAN}Report issues at: github.com/alakob/amr-predictor/issues{Style.RESET_ALL}
        """)
    )
    
    # Create argument groups for better organization
    input_group = parser.add_argument_group(f'{Fore.CYAN}Input Options{Style.RESET_ALL}')
    model_group = parser.add_argument_group(f'{Fore.CYAN}Model Options{Style.RESET_ALL}')
    output_group = parser.add_argument_group(f'{Fore.CYAN}Output Options{Style.RESET_ALL}')
    performance_group = parser.add_argument_group(f'{Fore.CYAN}Performance Options{Style.RESET_ALL}')
    
    # Input options
    input_group.add_argument("--fasta", "-f", required=True, 
                      help="Path to input FASTA file containing genomic sequences")
    
    # Model options
    model_group.add_argument("--model", "-m", default="alakob/amr-predictor-2025-03-08_12.55.32", 
                      help="HuggingFace model name or path (default: %(default)s)")
    
    # Performance options
    performance_group.add_argument("--batch-size", "-b", type=int, default=8, 
                          help="Batch size for predictions (default: %(default)s)")
    performance_group.add_argument("--segment-length", "-s", type=int, default=6000, 
                          help="Maximum segment length, 0 to disable splitting (default: %(default)s)")
    performance_group.add_argument("--segment-overlap", "-o", type=int, default=0, 
                          help="Overlap between segments in nucleotides for long sequences (default: %(default)s). Must be less than --segment-length.")
    performance_group.add_argument("--cpu", action="store_true", 
                          help="Force CPU inference instead of GPU")
    
    # Output options
    output_group.add_argument("--output", 
                      help="Path to output file (default: amr_predictions_<timestamp>.tsv)")
    output_group.add_argument("--perf-metrics", 
                      help="Path to output file for performance metrics (default: amr_timing_<timestamp>.csv)")
    output_group.add_argument("--verbose", "-v", action="store_true", 
                      help="Enable verbose logging")
    output_group.add_argument("--predict-only", action="store_true",
                      help="Only predict processing time without running actual analysis")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show banner if not just displaying help
    if len(sys.argv) > 1 and not (len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']):
        print_banner()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Set default output filename if not provided
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"amr_predictions_{timestamp}.tsv"
        
    # Set default performance metrics filename if not provided
    if args.perf_metrics is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.perf_metrics = f"amr_timing_{timestamp}.csv"
    
    # Only import heavy libraries if we're actually running the program
    # (not just showing help)
    if len(sys.argv) > 1 and not (len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']):
        try:
            # Import heavy libraries here
            logger.info("Loading required libraries...")
            import torch
            import gc
            from Bio import SeqIO
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, logging as transformers_logging
            from peft import PeftModel, PeftConfig
            from tqdm import tqdm
            transformers_logging.set_verbosity_error()

            # After imports, define the remaining functions and execute the main logic
            
            # Class names for prediction output
            CLASS_NAMES = ["Susceptible", "Resistant"]

            def clear_gpu_memory():
                """Clear GPU memory to prevent out-of-memory errors"""
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    logger.debug("GPU memory cleared")

            def load_model_and_tokenizer(model_name):
                """
                Load PEFT model and tokenizer
                
                Args:
                    model_name (str): HuggingFace model name or path
                    
                Returns:
                    tuple: (model, tokenizer)
                """
                logger.info(f"Loading model configuration from '{model_name}'")
                # Load configuration
                config = PeftConfig.from_pretrained(model_name)
                
                logger.info(f"Loading base model '{config.base_model_name_or_path}'")
                # Load base model
                base_model = AutoModelForSequenceClassification.from_pretrained(
                    config.base_model_name_or_path,
                    num_labels=len(CLASS_NAMES),
                    trust_remote_code=True
                )
                
                logger.info("Applying PEFT adaptations to model")
                # Load fine-tuned model with PEFT
                model = PeftModel.from_pretrained(base_model, model_name)
                
                logger.info("Loading tokenizer")
                # Load tokenizer
                tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path, trust_remote_code=True)
                
                return model, tokenizer

            def predict_amr(sequences, model, tokenizer, device, max_length=1000, metrics=None):
                """
                Predict AMR status for a batch of sequences
                
                Args:
                    sequences (list): List of DNA/RNA sequences
                    model: The loaded model
                    tokenizer: The loaded tokenizer
                    device: Device to run inference on
                    max_length (int): Maximum sequence length for tokenizer
                    metrics (dict): Optional dictionary to store timing metrics
                    
                Returns:
                    numpy.ndarray: Prediction probabilities
                """
                batch_metrics = {}
                
                with timer("tokenization", batch_metrics):
                    logger.debug(f"Tokenizing batch of {len(sequences)} sequences (max_length={max_length})")
                    # Tokenize sequences
                    inputs = tokenizer(
                        sequences,
                        padding=True,
                        truncation=True,
                        max_length=max_length,
                        return_tensors="pt"
                    ).to(device)
                
                with timer("inference", batch_metrics):
                    # Make predictions
                    model.eval()
                    with torch.no_grad():
                        logger.debug("Running model inference")
                        outputs = model(**inputs)
                
                # Get probabilities
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # Store metrics if a metrics dict was provided
                if metrics is not None:
                    for key, value in batch_metrics.items():
                        metrics[key] = metrics.get(key, 0) + value
                    
                return probs.cpu().numpy()

            def load_fasta(file_path):
                """
                Load sequences from a FASTA file
                
                Args:
                    file_path (str): Path to FASTA file
                    
                Returns:
                    tuple: (sequences, ids)
                """
                logger.info(f"Reading sequences from '{file_path}'")
                sequences = []
                ids = []
                
                try:
                    for record in SeqIO.parse(file_path, "fasta"):
                        sequences.append(str(record.seq))
                        ids.append(str(record.id))
                        
                    logger.info(f"Successfully loaded {len(sequences)} sequences")
                    if len(sequences) == 0:
                        logger.warning("No sequences found in the FASTA file!")
                    
                    if logger.level <= logging.DEBUG:
                        for i, (seq_id, seq) in enumerate(zip(ids, sequences)):
                            if i < 3:  # Show only first 3 sequences in debug mode
                                logger.debug(f"Sequence {i+1}: ID={seq_id}, Length={len(seq)}, Preview={seq[:50]}...")
                        if len(sequences) > 3:
                            logger.debug(f"... and {len(sequences)-3} more sequences")
                    
                except Exception as e:
                    logger.error(f"Error reading FASTA file: {str(e)}")
                    sys.exit(1)
                    
                return sequences, ids

            def split_sequence(seq_id, sequence, max_length=6000, min_length=6, overlap=0):
                """
                Split a genomic sequence into segments of specified length with overlap
                
                Args:
                    seq_id (str): Sequence identifier
                    sequence (str): DNA/RNA sequence
                    max_length (int): Maximum length of each segment
                    min_length (int): Minimum length required for a segment
                    overlap (int): Number of overlapping bases between segments
                    
                Returns:
                    tuple: (segment_sequences, segment_ids)
                """
                # Validate parameters
                if max_length <= 0:
                    logger.warning(f"Invalid max_length {max_length}, using default of 6000")
                    max_length = 6000
                    
                # Ensure overlap is valid (not greater than or equal to max_length)
                effective_overlap = min(overlap, max_length - 1) if overlap > 0 else 0
                if effective_overlap != overlap and overlap > 0:
                    logger.warning(f"Overlap ({overlap}) must be less than max_length ({max_length}). Using {effective_overlap} instead.")
                
                logger.debug(f"Splitting sequence '{seq_id}' (length={len(sequence)}) with max_length={max_length}, overlap={effective_overlap}")
                segment_sequences = []
                segment_ids = []
                seq_length = len(sequence)
                
                # If sequence is shorter than max_length, don't split
                if seq_length <= max_length:
                    segment_sequences.append(sequence)
                    segment_ids.append(seq_id)
                    logger.debug(f"  Sequence '{seq_id}' is shorter than max_length, no splitting needed")
                    return segment_sequences, segment_ids
                
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
                        segment_sequences.append(segment)
                        segment_id = f"{seq_id}_{start+1}_{end}"
                        segment_ids.append(segment_id)
                        segments_created += 1
                        logger.debug(f"  Created segment {segment_id} (length={len(segment)})")
                        
                        # For very verbose logging, show the overlap regions
                        if effective_overlap > 0 and segments_created > 1 and logger.level <= logging.DEBUG:
                            prev_end = start
                            prev_start = max(0, prev_end - effective_overlap)
                            overlap_region = sequence[prev_start:prev_end]
                            logger.debug(f"    Overlap with previous segment: {prev_start+1}-{prev_end} ({len(overlap_region)} bp)")
                    else:
                        logger.debug(f"  Skipped segment {start+1}-{end} (length={len(segment)} < {min_length})")
                
                logger.info(f"Split sequence '{seq_id}' into {segments_created} segments with {effective_overlap}bp overlap")
                return segment_sequences, segment_ids

            def process_fasta_file(fasta_path, model_name, batch_size=8, segment_length=6000, 
                                segment_overlap=0, output_file=None, device=None):
                """
                Process a FASTA file and predict AMR status for each sequence
                
                Args:
                    fasta_path (str): Path to input FASTA file
                    model_name (str): HuggingFace model name or path
                    batch_size (int): Batch size for predictions
                    segment_length (int): Maximum segment length for splitting sequences
                    segment_overlap (int): Overlap between segments
                    output_file (str): Path to output file (optional)
                    device: Device to run inference on
                    
                Returns:
                    list: Results containing sequence IDs and predictions
                """
                # Initialize metrics for overall process timing
                global_timing = {}
                process_start_time = time.time()
                # Set device
                if device is None:
                    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                logger.info(f"Using device: {device}")
                
                # Load model and tokenizer
                with timer("model_loading", global_timing):
                    model, tokenizer = load_model_and_tokenizer(model_name)
                    model = model.to(device)
                logger.info(f"Model loaded and moved to {device}")
                
                # Load sequences
                with timer("sequence_loading", global_timing):
                    fasta_sequences, fasta_ids = load_fasta(fasta_path)
                
                # Validate segment parameters
                if segment_length > 0 and segment_overlap >= segment_length:
                    logger.warning(f"Segment overlap ({segment_overlap}) must be less than segment length ({segment_length})")
                    segment_overlap = segment_length // 10  # Default to 10% overlap as a fallback
                    logger.warning(f"Setting segment overlap to {segment_overlap} bp")
                    
                # Split sequences if needed
                splitting_timing = {}
                with timer("sequence_splitting", global_timing):
                    if segment_length > 0 and any(len(seq) > segment_length for seq in fasta_sequences):
                        long_seqs = sum(1 for seq in fasta_sequences if len(seq) > segment_length)
                        logger.info(f"Splitting {long_seqs} sequences longer than {segment_length} bp with {segment_overlap}bp overlap")
                        all_segments = []
                        all_segment_ids = []
                        
                        # Process sequences with a progress bar if there are many to split
                        process_iter = fasta_ids
                        if long_seqs > 10:
                            process_iter = tqdm(
                                zip(fasta_ids, fasta_sequences),
                                total=len(fasta_ids),
                                desc="Splitting sequences",
                                unit="seq",
                                bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.BLUE, Style.RESET_ALL) if COLOR_AVAILABLE else None
                            )
                            iterate_with_idx = False
                        else:
                            iterate_with_idx = True
                            
                        if iterate_with_idx:
                            for i, (seq_id, sequence) in enumerate(zip(fasta_ids, fasta_sequences)):
                                if len(sequence) > segment_length:
                                    segments, segment_ids = split_sequence(
                                        seq_id, sequence, 
                                        max_length=segment_length, 
                                        overlap=segment_overlap
                                    )
                                    all_segments.extend(segments)
                                    all_segment_ids.extend(segment_ids)
                                else:
                                    all_segments.append(sequence)
                                    all_segment_ids.append(seq_id)
                        else:
                            for seq_id, sequence in process_iter:
                                if len(sequence) > segment_length:
                                    segments, segment_ids = split_sequence(
                                        seq_id, sequence, 
                                        max_length=segment_length, 
                                        overlap=segment_overlap
                                    )
                                    all_segments.extend(segments)
                                    all_segment_ids.extend(segment_ids)
                                else:
                                    all_segments.append(sequence)
                                    all_segment_ids.append(seq_id)
                        
                        # Calculate statistics for reporting
                        num_segments = len(all_segments)
                        avg_segment_len = sum(len(s) for s in all_segments) / max(1, num_segments)
                        
                        logger.info(f"After splitting: {num_segments} segments in total (average length: {avg_segment_len:.1f} bp)")
                        logger.info(f"Overlap between segments: {segment_overlap} bp ({segment_overlap/segment_length*100:.1f}% of segment length)")
                        
                        fasta_sequences = all_segments
                        fasta_ids = all_segment_ids
                    else:
                        if segment_length == 0:
                            logger.info("Sequence splitting disabled")
                        else:
                            logger.info("No sequences need splitting")
                
                logger.info(f"Making predictions on {len(fasta_sequences)} sequences in batches of {batch_size}")
                predictions = []
                
                # Initialize the sequence metrics for mapping original sequences to their segments
                original_seq_map = {}
                for seq_id, seq in zip(fasta_ids, fasta_sequences):
                    # Check if this is a segment (has parent sequence ID)
                    parts = seq_id.split('_')
                    if len(parts) >= 3 and parts[0] != "":
                        # This is a segment, get the original sequence ID
                        original_id = parts[0]  # Extract parent sequence ID
                        if original_id not in original_seq_map:
                            original_seq_map[original_id] = {
                                "segments": [],
                                "total_time": 0,
                                "length": 0,  # Will be updated with original sequence length
                                "segment_count": 0
                            }
                        original_seq_map[original_id]["segments"].append(seq_id)
                        original_seq_map[original_id]["segment_count"] += 1
                    else:
                        # This is an original sequence (not split)
                        if seq_id not in original_seq_map:
                            original_seq_map[seq_id] = {
                                "segments": [seq_id],
                                "total_time": 0,
                                "length": len(seq),
                                "segment_count": 1
                            }
                
                # Process in batches with progress bar
                progress_bar = tqdm(
                    range(0, len(fasta_sequences), batch_size),
                    desc="Analyzing sequences",
                    unit="batch",
                    bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Style.RESET_ALL) if COLOR_AVAILABLE else None
                )
                
                prediction_timing = {}
                with timer("total_prediction", global_timing):
                    for i in progress_bar:
                        batch = fasta_sequences[i:i+batch_size]
                        batch_ids = fasta_ids[i:i+batch_size]
                        batch_size_actual = len(batch)
                        
                        progress_bar.set_postfix({"current_ids": ", ".join(batch_ids[:2]) + ("..." if batch_size_actual > 2 else "")})
                        logger.debug(f"Processing batch {i//batch_size + 1}: {batch_size_actual} sequences")
                        
                        # Measure batch processing time
                        batch_metrics = {}
                        batch_start_time = time.time()
                        
                        batch_predictions = predict_amr(batch, model, tokenizer, device, metrics=batch_metrics)
                        predictions.extend(batch_predictions)
                        
                        batch_end_time = time.time()
                        batch_total_time = batch_end_time - batch_start_time
                        
                        # Record metrics for each sequence in the batch
                        for j, (seq_id, sequence) in enumerate(zip(batch_ids, batch)):
                            # Calculate per-sequence timing (approximate by dividing batch time)
                            seq_metrics = {
                                "sequence_id": seq_id,
                                "sequence_length": len(sequence),
                                "tokenization_time": batch_metrics.get("tokenization", 0) / batch_size_actual,
                                "inference_time": batch_metrics.get("inference", 0) / batch_size_actual,
                                "total_processing_time": batch_total_time / batch_size_actual,
                                "batch_size": batch_size_actual,
                                "device": str(device)
                            }
                            
                            # Calculate sequence complexity metrics
                            complexity_metrics = calculate_sequence_complexity(sequence)
                            seq_metrics.update(complexity_metrics)
                            
                            # Add segment-specific metrics
                            if segment_length > 0:
                                seq_metrics["segment_length"] = segment_length
                                seq_metrics["segment_overlap"] = segment_overlap
                                
                                # Check if this is a segment of a larger sequence
                                parts = seq_id.split('_')
                                if len(parts) >= 3 and parts[0] != "":
                                    seq_metrics["is_segment"] = True
                                    seq_metrics["parent_sequence_id"] = parts[0]
                                    
                                    # Update timing in the original sequence map
                                    if parts[0] in original_seq_map:
                                        original_seq_map[parts[0]]["total_time"] += seq_metrics["total_processing_time"]
                                else:
                                    seq_metrics["is_segment"] = False
                                    if seq_id in original_seq_map:
                                        original_seq_map[seq_id]["total_time"] = seq_metrics["total_processing_time"]
                            else:
                                seq_metrics["is_segment"] = False
                                if seq_id in original_seq_map:
                                    original_seq_map[seq_id]["total_time"] = seq_metrics["total_processing_time"]
                            
                            # Add to global performance metrics
                            PERFORMANCE_METRICS["sequence_metrics"].append(seq_metrics)
                        
                        # Clear GPU memory periodically
                        if (i + batch_size) % (batch_size * 10) == 0:
                            clear_gpu_memory()
                
                # Format results
                with timer("format_results", global_timing):
                    results = []
                    for seq_id, pred in zip(fasta_ids, predictions):
                        result = {
                            "id": seq_id,
                            "predictions": {class_name: float(prob) for class_name, prob in zip(CLASS_NAMES, pred)}
                        }
                        results.append(result)
                
                logger.info(f"Completed predictions for {len(results)} sequences")
                
                # Calculate global metrics
                process_end_time = time.time()
                PERFORMANCE_METRICS["global_metrics"] = {
                    "total_execution_time": process_end_time - process_start_time,
                    "model_loading_time": global_timing.get("model_loading", 0),
                    "sequence_loading_time": global_timing.get("sequence_loading", 0),
                    "sequence_splitting_time": global_timing.get("sequence_splitting", 0),
                    "prediction_time": global_timing.get("total_prediction", 0),
                    "format_results_time": global_timing.get("format_results", 0),
                    "segment_length": segment_length,
                    "segment_overlap": segment_overlap,
                    "batch_size": batch_size,
                    "device": str(device),
                    "sequence_count": len(set([m.get("parent_sequence_id", m["sequence_id"]) for m in PERFORMANCE_METRICS["sequence_metrics"]]))
                }
                
                # Add metrics for original sequences by aggregating segment metrics
                for original_id, data in original_seq_map.items():
                    if data["segment_count"] > 1:  # This sequence was split into segments
                        PERFORMANCE_METRICS["sequence_metrics"].append({
                            "sequence_id": original_id,
                            "sequence_length": data["length"],
                            "total_processing_time": data["total_time"],
                            "segment_count": data["segment_count"],
                            "is_original": True,
                            "segment_length": segment_length,
                            "segment_overlap": segment_overlap,
                            "device": str(device)
                        })
                
                # Write results to file if specified
                if output_file:
                    write_results(results, output_file)
                
                # Print results to console
                print_results(results)
                
                return results

            def write_results(results, output_file):
                """Write results to a file"""
                logger.info(f"Writing results to '{output_file}'")
                try:
                    with open(output_file, 'w') as f:
                        f.write("Sequence_ID\t" + "\t".join(CLASS_NAMES) + "\n")
                        for result in results:
                            pred_values = [str(result["predictions"][class_name]) for class_name in CLASS_NAMES]
                            f.write(f"{result['id']}\t" + "\t".join(pred_values) + "\n")
                    logger.info(f"Successfully wrote results for {len(results)} sequences to {output_file}")
                except Exception as e:
                    logger.error(f"Error writing to output file: {str(e)}")

            def print_results(results):
                """Print formatted results to console"""
                if not results:
                    logger.warning("No results to display")
                    return
                    
                # Only print first few results if there are many
                display_count = min(len(results), 10)
                
                print("\n" + "="*50)
                print(f"{Fore.CYAN}PREDICTION RESULTS{Style.RESET_ALL} (showing {display_count} of {len(results)})")
                print("="*50)
                
                for i, result in enumerate(results[:display_count]):
                    print(f"\n{Fore.YELLOW}Sequence: {Style.BRIGHT}{result['id']}{Style.RESET_ALL}")
                    
                    # Find the class with highest probability for highlighting
                    best_class = max(CLASS_NAMES, key=lambda c: result["predictions"][c])
                    
                    for class_name in CLASS_NAMES:
                        prob = result["predictions"][class_name]
                        if class_name == best_class:
                            print(f"  {Fore.GREEN}{class_name}: {Style.BRIGHT}{prob:.4f}{Style.RESET_ALL}")
                        else:
                            print(f"  {class_name}: {prob:.4f}")
                
                if len(results) > display_count:
                    print(f"\n{Fore.YELLOW}... and {len(results) - display_count} more sequences{Style.RESET_ALL}")
                    
                print("\n" + "="*50)
                print(f"Full results written to: {Fore.CYAN}{args.output}{Style.RESET_ALL}")
                print("="*50 + "\n")
                    
            # Set device
            if args.cpu:
                device = torch.device("cpu")
                logger.info("Using CPU for inference (as requested)")
            else:
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                if device.type == "cuda":
                    logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
                else:
                    logger.warning("GPU not available, falling back to CPU")
            
            # Set up resource monitoring in a separate thread
            resource_monitor_stop = threading.Event()
            resource_metrics = queue.Queue()
            resource_monitor_thread = None
            
            if PSUTIL_AVAILABLE:
                logger.info("Starting system resource monitoring")
                resource_monitor_thread = threading.Thread(
                    target=lambda q, stop_event: q.put(monitor_system_resources(interval=1.0, stop_event=stop_event)),
                    args=(resource_metrics, resource_monitor_stop)
                )
                resource_monitor_thread.daemon = True
                resource_monitor_thread.start()
                logger.info("Resource monitoring started")
            
            # Check if we're only predicting processing time
            if args.predict_only:
                logger.info("Prediction-only mode enabled, estimating processing time...")
                
                # Create output directory if it doesn't exist
                output_dir = os.path.dirname(args.perf_metrics) if args.perf_metrics else None
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    
                # Predict processing time
                predicted_time = predict_total_processing_time(args.fasta, logger, output_dir)
                
                if predicted_time is None:
                    logger.error("Failed to predict processing time. Run amr_performance_analysis.py analyze first.")
                    sys.exit(1)
                    
                # Exit after prediction
                sys.exit(0)
            
            # Process FASTA file
            try:
                logger.info("Starting AMR prediction pipeline")
                process_fasta_file(
                    args.fasta, 
                    args.model, 
                    args.batch_size, 
                    args.segment_length,
                    args.segment_overlap,
                    args.output,
                    device
                )
                logger.info("AMR prediction completed successfully")
                
                # Stop resource monitoring and get results
                if PSUTIL_AVAILABLE and resource_monitor_thread:
                    logger.info("Stopping system resource monitoring")
                    resource_monitor_stop.set()
                    
                    if resource_monitor_thread.is_alive():
                        resource_monitor_thread.join(timeout=5)
                        logger.info("Resource monitoring thread has completed.")
                    else:
                        logger.warning("Resource monitoring thread is not alive.")
                    
                    # Get resource monitoring results
                    try:
                        if not resource_metrics.empty():
                            PERFORMANCE_METRICS["resource_usage"] = resource_metrics.get(timeout=1)
                            logger.info(f"Resource monitoring collected {PERFORMANCE_METRICS['resource_usage'].get('sample_count', 0)} samples")
                        else:
                            logger.warning("Resource metrics queue is empty.")
                    except queue.Empty:
                        logger.warning("Resource monitoring data not available")
                
                # Save performance metrics to file
                if hasattr(args, "perf_metrics") and args.perf_metrics:
                    save_performance_metrics(args.perf_metrics)
                    print_performance_summary()
            except Exception as e:
                logger.error(f"Error during processing: {str(e)}")
                if args.verbose:
                    import traceback
                    logger.error(traceback.format_exc())
                sys.exit(1)
                
        except ImportError as e:
            logger.error(f"Required library not found: {str(e)}")
            logger.error("Please install required packages: pip install torch transformers biopython peft tqdm colorama")
            sys.exit(1)

# Export key functions at the module level for easier imports
def load_model_and_tokenizer(model_name):
    """Wrapper to access the nested function"""
    # This function is defined inside main, so we need to call it from there
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from peft import PeftModel, PeftConfig
    import torch
    import gc
    
    # Set up logger
    logger = setup_logger()
    
    # Define the class names
    CLASS_NAMES = ["Susceptible", "Resistant"]
    
    # Clear GPU memory
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        logger.debug("GPU memory cleared")
    
    # Load the model and tokenizer
    logger.info(f"Loading model configuration from '{model_name}'")
    # Load configuration
    config = PeftConfig.from_pretrained(model_name)
    
    logger.info(f"Loading base model '{config.base_model_name_or_path}'")
    # Load base model
    base_model = AutoModelForSequenceClassification.from_pretrained(
        config.base_model_name_or_path,
        num_labels=len(CLASS_NAMES),
        trust_remote_code=True
    )
    
    logger.info("Applying PEFT adaptations to model")
    # Load fine-tuned model with PEFT
    model = PeftModel.from_pretrained(base_model, model_name)
    
    logger.info("Loading tokenizer")
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path, trust_remote_code=True)
    
    return model, tokenizer

def predict_amr(sequences, model, tokenizer, device, max_length=1000, metrics=None):
    """Wrapper to access the nested function"""
    import torch
    import time
    
    # Set up logger
    logger = setup_logger()
    
    # Define the class names
    CLASS_NAMES = ["Susceptible", "Resistant"]
    
    logger.info(f"Predicting AMR for {len(sequences)} sequences")
    
    # Tokenize sequences
    logger.info("Tokenizing sequences")
    tokenize_start = time.time()
    inputs = tokenizer(sequences, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    tokenize_time = time.time() - tokenize_start
    logger.info(f"Tokenization completed in {tokenize_time:.2f} seconds")
    
    # Move inputs to device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Run inference
    logger.info(f"Running model inference on {device}")
    inference_start = time.time()
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
    inference_time = time.time() - inference_start
    logger.info(f"Inference completed in {inference_time:.2f} seconds")
    
    # Convert to list
    predictions = probabilities.cpu().numpy().tolist()
    
    # Record metrics if provided
    if metrics is not None:
        metrics["tokenize_time"] = tokenize_time
        metrics["inference_time"] = inference_time
        metrics["sequences_processed"] = len(sequences)
    
    return predictions

def split_sequence(seq_id, sequence, max_length=6000, min_length=6, overlap=0):
    """Wrapper to access the nested function"""
    # Set up logger
    logger = setup_logger()
    
    logger.info(f"Splitting sequence {seq_id} (length: {len(sequence)}bp)")
    
    # If sequence is shorter than max_length, return it as is
    if len(sequence) <= max_length:
        return [sequence], [seq_id]
    
    segments = []
    segment_ids = []
    
    # Calculate step size (accounting for overlap)
    step = max_length - overlap
    
    # Generate segments
    for i in range(0, len(sequence), step):
        # Extract segment
        segment = sequence[i:i + max_length]
        
        # Skip segments that are too short
        if len(segment) < min_length:
            logger.info(f"Skipping segment {i//step + 1} (length: {len(segment)}bp) - below minimum length")
            continue
        
        # Generate segment ID
        segment_id = f"{seq_id}_segment_{i//step + 1}"
        
        segments.append(segment)
        segment_ids.append(segment_id)
        
        logger.debug(f"Created segment {segment_id} (length: {len(segment)}bp)")
    
    logger.info(f"Split sequence into {len(segments)} segments")
    return segments, segment_ids

if __name__ == "__main__":
    main()