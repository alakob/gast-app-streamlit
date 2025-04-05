#!/usr/bin/env python3
"""
Visualization tool for Bakta Phase 5 test results.

This script provides visualizations for the performance metrics collected
during Phase 5 testing to help evaluate query performance.
"""

import os
import json
import glob
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
except ImportError:
    print("Error: Required visualization packages not found.")
    print("Please install the required packages:")
    print("  pip install matplotlib numpy pandas")
    sys.exit(1)

# Configure styling for plots
plt.style.use('ggplot')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12


def load_results(results_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load test results from JSON files.
    
    Args:
        results_dir: Directory containing result files. If None, uses default.
        
    Returns:
        List of result dictionaries
    """
    if results_dir is None:
        script_dir = Path(__file__).parent
        results_dir = script_dir / "results"
    else:
        results_dir = Path(results_dir)
    
    # Find all result files
    result_files = glob.glob(str(results_dir / "phase5_results_*.json"))
    
    if not result_files:
        print(f"No result files found in {results_dir}")
        return []
    
    # Load results
    results = []
    for file_path in sorted(result_files):
        try:
            with open(file_path, 'r') as f:
                results.append(json.load(f))
            print(f"Loaded results from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
    
    return results


def plot_filter_performance(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Plot filter performance metrics.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save plot. If None, shows plot.
    """
    # Extract filter performance metrics
    datasets = []
    small_times = []
    medium_times = []
    large_times = []
    
    for result in results:
        if "performance_metrics" in result and "filter_performance" in result["performance_metrics"]:
            fp = result["performance_metrics"]["filter_performance"]
            timestamp = result["timestamp"]
            
            datasets.append(timestamp)
            small_times.append(fp["small"]["mean_time"])
            medium_times.append(fp["medium"]["mean_time"])
            large_times.append(fp["large"]["mean_time"])
    
    if not datasets:
        print("No filter performance metrics found")
        return
    
    # Create plot
    plt.figure(figsize=(14, 8))
    
    # Plot data
    x = np.arange(len(datasets))
    width = 0.2
    
    plt.bar(x - width, small_times, width, label=f"Small Dataset")
    plt.bar(x, medium_times, width, label=f"Medium Dataset")
    plt.bar(x + width, large_times, width, label=f"Large Dataset")
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Mean Query Time (seconds)')
    plt.title('Filter Performance Across Test Runs')
    plt.xticks(x, [d.split(' ')[0] for d in datasets], rotation=45)
    plt.tight_layout()
    plt.legend()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "filter_performance.png"
        plt.savefig(output_path)
        print(f"Saved filter performance plot to {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_query_types_comparison(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Plot comparison of different query types.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save plot. If None, shows plot.
    """
    # Extract performance metrics for different query types
    datasets = []
    simple_filter_times = []
    complex_query_times = []
    range_query_times = []
    
    for result in results:
        if "performance_metrics" not in result:
            continue
        
        metrics = result["performance_metrics"]
        timestamp = result["timestamp"]
        
        # Get filter performance (large dataset)
        if "filter_performance" in metrics:
            datasets.append(timestamp)
            simple_filter_times.append(metrics["filter_performance"]["large"]["mean_time"])
        else:
            continue
        
        # Get complex query performance
        if "complex_query" in metrics:
            complex_query_times.append(metrics["complex_query"]["mean_time"])
        else:
            complex_query_times.append(None)
        
        # Extract range query data if available
        range_time = None
        for key, section in result.items():
            if isinstance(section, str) and "Range query performance" in section:
                lines = section.split("\n")
                for line in lines:
                    if "Mean time:" in line:
                        try:
                            range_time = float(line.split(":")[1].strip().split("s")[0])
                        except:
                            pass
        range_query_times.append(range_time)
    
    if not datasets:
        print("No query performance metrics found")
        return
    
    # Create plot
    plt.figure(figsize=(14, 8))
    
    # Plot data
    x = np.arange(len(datasets))
    width = 0.2
    
    plt.bar(x - width, simple_filter_times, width, label="Simple Filter")
    
    # Only include non-None values
    complex_x = []
    complex_y = []
    for i, val in enumerate(complex_query_times):
        if val is not None:
            complex_x.append(x[i])
            complex_y.append(val)
    if complex_x:
        plt.bar(complex_x, complex_y, width, label="Complex Query")
    
    # Only include non-None values
    range_x = []
    range_y = []
    for i, val in enumerate(range_query_times):
        if val is not None:
            range_x.append(x[i] + width)
            range_y.append(val)
    if range_x:
        plt.bar(range_x, range_y, width, label="Range Query")
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Mean Query Time (seconds)')
    plt.title('Performance Comparison of Different Query Types')
    plt.xticks(x, [d.split(' ')[0] for d in datasets], rotation=45)
    plt.tight_layout()
    plt.legend()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "query_types_comparison.png"
        plt.savefig(output_path)
        print(f"Saved query types comparison plot to {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_caching_benefits(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Plot benefits of caching.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save plot. If None, shows plot.
    """
    # Extract cache performance metrics
    datasets = []
    miss_times = []
    hit_times = []
    uncached_times = []
    speedup_factors = []
    
    for result in results:
        if "performance_metrics" in result and "cache_performance" in result["performance_metrics"]:
            cp = result["performance_metrics"]["cache_performance"]
            timestamp = result["timestamp"]
            
            datasets.append(timestamp)
            miss_times.append(cp.get("miss_time", 0))
            hit_times.append(cp.get("hit_time", 0))
            uncached_times.append(cp.get("uncached_time", 0))
            speedup_factors.append(cp.get("speedup_factor", 0))
    
    if not datasets:
        print("No cache performance metrics found")
        return
    
    # Create first plot - cache miss vs hit vs uncached
    plt.figure(figsize=(14, 8))
    
    # Plot data
    x = np.arange(len(datasets))
    width = 0.2
    
    plt.bar(x - width, miss_times, width, label="Cache Miss")
    plt.bar(x, hit_times, width, label="Cache Hit")
    plt.bar(x + width, uncached_times, width, label="Uncached")
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Query Time (seconds)')
    plt.title('Cache Performance Comparison')
    plt.xticks(x, [d.split(' ')[0] for d in datasets], rotation=45)
    plt.tight_layout()
    plt.legend()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "cache_performance.png"
        plt.savefig(output_path)
        print(f"Saved cache performance plot to {output_path}")
    else:
        plt.show()
    
    plt.close()
    
    # Create second plot - speedup factor
    plt.figure(figsize=(14, 8))
    
    plt.bar(x, speedup_factors, 0.4, color='teal')
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Speedup Factor (x times faster)')
    plt.title('Cache Speedup Factor')
    plt.xticks(x, [d.split(' ')[0] for d in datasets], rotation=45)
    plt.tight_layout()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "cache_speedup.png"
        plt.savefig(output_path)
        print(f"Saved cache speedup plot to {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_batch_processing_performance(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Plot batch processing performance.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save plot. If None, shows plot.
    """
    # Extract batch processing metrics
    datasets = []
    total_times = []
    throughputs = []
    
    for result in results:
        if "performance_metrics" in result and "batch_processing" in result["performance_metrics"]:
            bp = result["performance_metrics"]["batch_processing"]
            timestamp = result["timestamp"]
            
            datasets.append(timestamp)
            total_times.append(bp.get("total_time", 0))
            throughputs.append(bp.get("items_per_second", 0))
    
    if not datasets:
        print("No batch processing metrics found")
        return
    
    # Create plot for throughput
    plt.figure(figsize=(14, 8))
    
    plt.bar(np.arange(len(datasets)), throughputs, 0.4, color='orange')
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Items Processed per Second')
    plt.title('Batch Processing Throughput')
    plt.xticks(np.arange(len(datasets)), [d.split(' ')[0] for d in datasets], rotation=45)
    plt.tight_layout()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "batch_throughput.png"
        plt.savefig(output_path)
        print(f"Saved batch throughput plot to {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_test_results(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Plot test results over time.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save plot. If None, shows plot.
    """
    # Extract test results
    datasets = []
    correctness_rates = []
    performance_rates = []
    
    for result in results:
        if "correctness_tests" in result and "performance_tests" in result:
            timestamp = result["timestamp"]
            
            datasets.append(timestamp)
            correctness_rates.append(result["correctness_tests"]["success_rate"])
            performance_rates.append(result["performance_tests"]["success_rate"])
    
    if not datasets:
        print("No test results found")
        return
    
    # Create plot
    plt.figure(figsize=(14, 8))
    
    # Plot data
    x = np.arange(len(datasets))
    plt.plot(x, correctness_rates, 'o-', label="Correctness Tests", linewidth=2)
    plt.plot(x, performance_rates, 's-', label="Performance Tests", linewidth=2)
    
    # Add labels and title
    plt.xlabel('Test Run Timestamp')
    plt.ylabel('Success Rate')
    plt.title('Test Success Rates Over Time')
    plt.xticks(x, [d.split(' ')[0] for d in datasets], rotation=45)
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.legend()
    
    # Save or show plot
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "test_results.png"
        plt.savefig(output_path)
        print(f"Saved test results plot to {output_path}")
    else:
        plt.show()
    
    plt.close()


def generate_summary_table(results: List[Dict[str, Any]], output_dir: Optional[str] = None):
    """
    Generate a summary table of test results.
    
    Args:
        results: List of result dictionaries
        output_dir: Directory to save table. If None, prints table.
    """
    # Extract key metrics
    data = []
    for result in results:
        row = {
            'timestamp': result['timestamp'],
            'execution_time': result['execution_time'],
            'correctness_pass_rate': result['correctness_tests']['success_rate'],
            'performance_pass_rate': result['performance_tests']['success_rate'],
        }
        
        # Add filter performance metrics if available
        if "performance_metrics" in result and "filter_performance" in result["performance_metrics"]:
            fp = result["performance_metrics"]["filter_performance"]
            row['small_filter_time'] = fp["small"]["mean_time"]
            row['medium_filter_time'] = fp["medium"]["mean_time"]
            row['large_filter_time'] = fp["large"]["mean_time"]
        
        # Add cache performance metrics if available
        if "performance_metrics" in result and "cache_performance" in result["performance_metrics"]:
            cp = result["performance_metrics"]["cache_performance"]
            row['cache_speedup'] = cp.get("speedup_factor", "N/A")
        
        data.append(row)
    
    if not data:
        print("No data for summary table")
        return
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Format columns
    df['execution_time'] = df['execution_time'].map("{:.2f}s".format)
    df['correctness_pass_rate'] = df['correctness_pass_rate'].map("{:.1%}".format)
    df['performance_pass_rate'] = df['performance_pass_rate'].map("{:.1%}".format)
    
    if 'small_filter_time' in df.columns:
        df['small_filter_time'] = df['small_filter_time'].map("{:.6f}s".format)
    
    if 'medium_filter_time' in df.columns:
        df['medium_filter_time'] = df['medium_filter_time'].map("{:.6f}s".format)
    
    if 'large_filter_time' in df.columns:
        df['large_filter_time'] = df['large_filter_time'].map("{:.6f}s".format)
    
    if 'cache_speedup' in df.columns:
        df['cache_speedup'] = df['cache_speedup'].apply(lambda x: f"{x:.2f}x" if isinstance(x, (int, float)) else x)
    
    # Rename columns for better display
    df = df.rename(columns={
        'timestamp': 'Timestamp',
        'execution_time': 'Execution Time',
        'correctness_pass_rate': 'Correctness Pass Rate',
        'performance_pass_rate': 'Performance Pass Rate',
        'small_filter_time': 'Small Filter Time',
        'medium_filter_time': 'Medium Filter Time',
        'large_filter_time': 'Large Filter Time',
        'cache_speedup': 'Cache Speedup Factor'
    })
    
    # Output
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Save as CSV
        csv_path = output_dir / "summary_table.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved summary table to {csv_path}")
        
        # Save as HTML
        html_path = output_dir / "summary_table.html"
        df.to_html(html_path, index=False)
        print(f"Saved summary table to {html_path}")
    else:
        # Print table
        print("\n=== Test Results Summary ===\n")
        print(df.to_string(index=False))
        print("\n")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Visualize Bakta Phase 5 test results."
    )
    
    parser.add_argument(
        "--results-dir", 
        type=str,
        help="Directory containing result files (default: tests/results)"
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str,
        help="Directory to save visualizations (default: tests/visualizations)"
    )
    
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Generate all visualizations"
    )
    
    parser.add_argument(
        "--filter", 
        action="store_true",
        help="Generate filter performance visualization"
    )
    
    parser.add_argument(
        "--query-types", 
        action="store_true",
        help="Generate query types comparison visualization"
    )
    
    parser.add_argument(
        "--caching", 
        action="store_true",
        help="Generate caching benefits visualization"
    )
    
    parser.add_argument(
        "--batch", 
        action="store_true",
        help="Generate batch processing visualization"
    )
    
    parser.add_argument(
        "--test-results", 
        action="store_true",
        help="Generate test results visualization"
    )
    
    parser.add_argument(
        "--summary", 
        action="store_true",
        help="Generate summary table"
    )
    
    parser.add_argument(
        "--show", 
        action="store_true",
        help="Show visualizations instead of saving them"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Determine results directory
    if args.results_dir:
        results_dir = args.results_dir
    else:
        script_dir = Path(__file__).parent
        results_dir = script_dir / "results"
    
    # Determine output directory
    output_dir = None
    if not args.show:
        if args.output_dir:
            output_dir = args.output_dir
        else:
            script_dir = Path(__file__).parent
            output_dir = script_dir / "visualizations"
    
    # Load results
    results = load_results(results_dir)
    
    if not results:
        print("No results to visualize.")
        return 1
    
    # Determine which visualizations to generate
    if not any([args.all, args.filter, args.query_types, args.caching, 
                args.batch, args.test_results, args.summary]):
        args.all = True
    
    # Generate visualizations
    if args.all or args.filter:
        plot_filter_performance(results, output_dir)
    
    if args.all or args.query_types:
        plot_query_types_comparison(results, output_dir)
    
    if args.all or args.caching:
        plot_caching_benefits(results, output_dir)
    
    if args.all or args.batch:
        plot_batch_processing_performance(results, output_dir)
    
    if args.all or args.test_results:
        plot_test_results(results, output_dir)
    
    if args.all or args.summary:
        generate_summary_table(results, output_dir)
    
    print("Visualization completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 