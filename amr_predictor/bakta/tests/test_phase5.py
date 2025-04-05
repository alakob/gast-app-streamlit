#!/usr/bin/env python3
"""
Phase 5 Testing for Bakta Query Interface.

This module executes and reports on all Phase 5 tests for the Bakta query interface,
including correctness validation and performance benchmarking.
"""

import os
import time
import pytest
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bakta-phase5-tests")

# Test modules to import and run
TEST_MODULES = [
    'amr_predictor.bakta.tests.test_query_correctness',
    'amr_predictor.bakta.tests.test_query_performance'
]

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Performance metrics to collect
PERFORMANCE_METRICS = [
    "filter_by_feature_type_performance",
    "query_builder_performance",
    "sort_performance",
    "cached_query_performance",
    "range_query_performance",
    "query_interface_performance",
    "batch_processing_performance"
]

def run_tests() -> Dict[str, Any]:
    """
    Run all Phase 5 tests and collect results.
    
    Returns:
        Dictionary with test results and metrics
    """
    logger.info("Starting Phase 5 tests for Bakta query interface")
    
    start_time = time.time()
    
    # Run tests and collect results
    correctness_result = run_test_module('amr_predictor.bakta.tests.test_query_correctness')
    performance_result = run_test_module('amr_predictor.bakta.tests.test_query_performance')
    
    end_time = time.time()
    
    # Collect results into a report
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": end_time - start_time,
        "correctness_tests": {
            "total": correctness_result["total"],
            "passed": correctness_result["passed"],
            "failed": correctness_result["failed"],
            "skipped": correctness_result["skipped"],
            "success_rate": correctness_result["success_rate"]
        },
        "performance_tests": {
            "total": performance_result["total"],
            "passed": performance_result["passed"],
            "failed": performance_result["failed"],
            "skipped": performance_result["skipped"],
            "success_rate": performance_result["success_rate"]
        },
        "performance_metrics": extract_performance_metrics(performance_result["raw_output"])
    }
    
    # Save results to file
    save_results(results)
    
    # Log summary
    logger.info(f"Tests completed in {results['execution_time']:.2f} seconds")
    logger.info(f"Correctness tests: {results['correctness_tests']['passed']}/{results['correctness_tests']['total']} passed")
    logger.info(f"Performance tests: {results['performance_tests']['passed']}/{results['performance_tests']['total']} passed")
    
    return results

def run_test_module(module_name: str) -> Dict[str, Any]:
    """
    Run tests from a specific module.
    
    Args:
        module_name: Name of the module to run tests from
        
    Returns:
        Dictionary with test results
    """
    logger.info(f"Running tests from {module_name}")
    
    # Capture stdout to parse performance metrics
    # Run pytest on the module
    pytest_args = [
        module_name,
        "-v",
        "--no-header",
        "--tb=native"
    ]
    
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        result = pytest.main(pytest_args)
    
    output = f.getvalue()
    
    # Parse test results
    total, passed, failed, skipped = parse_test_results(output)
    
    success_rate = passed / total if total > 0 else 0
    
    return {
        "module": module_name,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "success_rate": success_rate,
        "raw_output": output
    }

def parse_test_results(output: str) -> tuple:
    """
    Parse test results from pytest output.
    
    Args:
        output: Raw pytest output
        
    Returns:
        Tuple of (total, passed, failed, skipped)
    """
    # Count test results from pytest output
    passed = output.count(" PASSED ")
    failed = output.count(" FAILED ")
    skipped = output.count(" SKIPPED ")
    error = output.count(" ERROR ")
    
    total = passed + failed + skipped + error
    
    return total, passed, failed + error, skipped

def extract_performance_metrics(output: str) -> Dict[str, Any]:
    """
    Extract performance metrics from test output.
    
    Args:
        output: Raw test output
        
    Returns:
        Dictionary with performance metrics
    """
    metrics = {}
    
    # Extract filter by feature type performance
    if "Filter by feature_type performance:" in output:
        section = output.split("Filter by feature_type performance:")[1].split("\n\n")[0]
        
        small = {}
        medium = {}
        large = {}
        
        for line in section.strip().split("\n"):
            if "Small dataset" in line:
                parts = line.split(":")
                dataset_info = parts[1].strip()
                size = int(dataset_info.split(" ")[0].strip("(").strip(")").split(" ")[0])
                mean = float(dataset_info.split("mean")[0].strip().split(" ")[-1])
                median = float(dataset_info.split("median")[0].strip().split(" ")[-1])
                small = {"size": size, "mean_time": mean, "median_time": median}
            
            elif "Medium dataset" in line:
                parts = line.split(":")
                dataset_info = parts[1].strip()
                size = int(dataset_info.split(" ")[0].strip("(").strip(")").split(" ")[0])
                mean = float(dataset_info.split("mean")[0].strip().split(" ")[-1])
                median = float(dataset_info.split("median")[0].strip().split(" ")[-1])
                medium = {"size": size, "mean_time": mean, "median_time": median}
            
            elif "Large dataset" in line:
                parts = line.split(":")
                dataset_info = parts[1].strip()
                size = int(dataset_info.split(" ")[0].strip("(").strip(")").split(" ")[0])
                mean = float(dataset_info.split("mean")[0].strip().split(" ")[-1])
                median = float(dataset_info.split("median")[0].strip().split(" ")[-1])
                large = {"size": size, "mean_time": mean, "median_time": median}
        
        metrics["filter_performance"] = {
            "small": small,
            "medium": medium,
            "large": large
        }
    
    # Extract complex query performance
    if "Complex query performance:" in output:
        section = output.split("Complex query performance:")[1].split("\n\n")[0]
        complex_query = {}
        
        for line in section.strip().split("\n"):
            if "Dataset size:" in line:
                complex_query["dataset_size"] = int(line.split(":")[1].strip().split(" ")[0])
            elif "Mean time:" in line:
                complex_query["mean_time"] = float(line.split(":")[1].strip().split(" ")[0])
            elif "Median time:" in line:
                complex_query["median_time"] = float(line.split(":")[1].strip().split(" ")[0])
            elif "Result size:" in line:
                complex_query["result_size"] = int(line.split(":")[1].strip().split(" ")[0])
        
        metrics["complex_query"] = complex_query
    
    # Extract sort performance
    if "Sort performance:" in output:
        section = output.split("Sort performance:")[1].split("\n\n")[0]
        sort_perf = {}
        
        for line in section.strip().split("\n"):
            if "Sort by start:" in line:
                parts = line.split(":")
                info = parts[1].strip()
                mean = float(info.split("mean")[0].strip().split(" ")[0])
                median = float(info.split("median")[0].strip().split(" ")[0])
                sort_perf["simple_sort"] = {"mean_time": mean, "median_time": median}
            
            elif "Sort by type and start:" in line:
                parts = line.split(":")
                info = parts[1].strip()
                mean = float(info.split("mean")[0].strip().split(" ")[0])
                median = float(info.split("median")[0].strip().split(" ")[0])
                sort_perf["complex_sort"] = {"mean_time": mean, "median_time": median}
        
        metrics["sort_performance"] = sort_perf
    
    # Extract cached query performance
    if "Cached query performance:" in output:
        section = output.split("Cached query performance:")[1].split("\n\n")[0]
        cache_perf = {}
        
        for line in section.strip().split("\n"):
            if "Cache miss" in line:
                cache_perf["miss_time"] = float(line.split(":")[1].strip().split("s")[0])
            elif "Cache hit" in line:
                cache_perf["hit_time"] = float(line.split(":")[1].strip().split("s")[0])
            elif "Uncached:" in line:
                cache_perf["uncached_time"] = float(line.split(":")[1].strip().split("s")[0])
        
        # Calculate cache efficiency
        if "miss_time" in cache_perf and "hit_time" in cache_perf:
            cache_perf["speedup_factor"] = cache_perf["miss_time"] / cache_perf["hit_time"]
        
        metrics["cache_performance"] = cache_perf
    
    # Extract batch processing performance
    if "Batch processing performance:" in output:
        section = output.split("Batch processing performance:")[1].split("\n\n")[0]
        batch_perf = {}
        
        for line in section.strip().split("\n"):
            if "Dataset size:" in line:
                batch_perf["dataset_size"] = int(line.split(":")[1].strip().split(" ")[0])
            elif "Batch size:" in line:
                batch_perf["batch_size"] = int(line.split(":")[1].strip().split(" ")[0])
            elif "Total time:" in line:
                batch_perf["total_time"] = float(line.split(":")[1].strip().split("s")[0])
            elif "Processed items:" in line:
                batch_perf["processed_items"] = int(line.split(":")[1].strip())
            elif "Number of batches:" in line:
                batch_perf["num_batches"] = int(line.split(":")[1].strip())
        
        # Calculate throughput
        if "dataset_size" in batch_perf and "total_time" in batch_perf:
            batch_perf["items_per_second"] = batch_perf["dataset_size"] / batch_perf["total_time"]
        
        metrics["batch_processing"] = batch_perf
    
    return metrics

def save_results(results: Dict[str, Any]) -> None:
    """
    Save test results to a JSON file.
    
    Args:
        results: Dictionary with test results
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"phase5_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {filename}")

def main():
    """Execute Phase 5 tests and report results."""
    results = run_tests()
    
    # Print summary report
    print("\n" + "=" * 80)
    print("PHASE 5 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests completed in {results['execution_time']:.2f} seconds")
    print(f"Correctness tests: {results['correctness_tests']['passed']}/{results['correctness_tests']['total']} passed ({results['correctness_tests']['success_rate']:.1%})")
    print(f"Performance tests: {results['performance_tests']['passed']}/{results['performance_tests']['total']} passed ({results['performance_tests']['success_rate']:.1%})")
    
    # Performance metrics
    if "filter_performance" in results["performance_metrics"]:
        fp = results["performance_metrics"]["filter_performance"]
        print("\nFilter Performance:")
        print(f"  Small dataset ({fp['small']['size']} items): {fp['small']['mean_time']:.6f}s (mean)")
        print(f"  Medium dataset ({fp['medium']['size']} items): {fp['medium']['mean_time']:.6f}s (mean)")
        print(f"  Large dataset ({fp['large']['size']} items): {fp['large']['mean_time']:.6f}s (mean)")
    
    if "complex_query" in results["performance_metrics"]:
        cq = results["performance_metrics"]["complex_query"]
        print("\nComplex Query Performance:")
        print(f"  Dataset size: {cq['dataset_size']} items")
        print(f"  Mean time: {cq['mean_time']:.6f}s")
        print(f"  Result size: {cq.get('result_size', 'N/A')} items")
    
    if "cache_performance" in results["performance_metrics"]:
        cp = results["performance_metrics"]["cache_performance"]
        print("\nCache Performance:")
        print(f"  Cache miss: {cp['miss_time']:.6f}s")
        print(f"  Cache hit: {cp['hit_time']:.6f}s")
        print(f"  Speedup factor: {cp.get('speedup_factor', 'N/A'):.2f}x")
    
    if "batch_processing" in results["performance_metrics"]:
        bp = results["performance_metrics"]["batch_processing"]
        print("\nBatch Processing Performance:")
        print(f"  Dataset size: {bp['dataset_size']} items")
        print(f"  Total time: {bp['total_time']:.6f}s")
        print(f"  Throughput: {bp.get('items_per_second', 'N/A'):.1f} items/sec")
    
    # Success criteria verification
    success_criteria_met = (
        results['correctness_tests']['success_rate'] >= 0.95 and  # At least 95% of correctness tests pass
        results['performance_tests']['success_rate'] >= 0.90      # At least 90% of performance tests pass
    )
    
    print("\n" + "=" * 80)
    if success_criteria_met:
        print("SUCCESS: Phase 5 testing criteria met!")
    else:
        print("FAILURE: Phase 5 testing criteria not met.")
    print("=" * 80)
    
    return 0 if success_criteria_met else 1

if __name__ == "__main__":
    exit(main()) 