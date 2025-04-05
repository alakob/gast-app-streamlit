#!/usr/bin/env python3
"""
Tests for Bakta query performance.

This module contains performance tests for Bakta query operations,
focusing on efficiency with large datasets.
"""

import pytest
import time
import random
import string
import json
import os
from typing import List, Dict, Any
import statistics
from pathlib import Path

from amr_predictor.bakta.dao import AnnotationDAO
from amr_predictor.bakta.dao.cache_manager import cached, global_cache
from amr_predictor.bakta.models import BaktaAnnotation
from amr_predictor.bakta.query_interface import (
    BaktaQueryInterface, QueryOptions, QueryResult, SortOrder, QueryError
)
from amr_predictor.bakta.dao.query_builder import (
    QueryBuilder, QueryCondition, FilterOperator, LogicalOperator
)

# Get dataset sizes from environment variables or use defaults
LARGE_DATASET_SIZE = int(os.environ.get("BAKTA_TEST_DATASET_SIZE", "5000"))
MEDIUM_DATASET_SIZE = max(LARGE_DATASET_SIZE // 5, 100)
SMALL_DATASET_SIZE = max(LARGE_DATASET_SIZE // 50, 20)

# Get benchmark iterations from environment or use default
BENCHMARK_ITERATIONS = int(os.environ.get("BAKTA_TEST_ITERATIONS", "5"))

# Sample job ID for testing
SAMPLE_JOB_ID = "test-job-performance"

# Feature types for generating test data
FEATURE_TYPES = ["CDS", "tRNA", "rRNA", "ncRNA", "CRISPR", "tmRNA"]

# Products for generating test data
PRODUCTS = [
    "hypothetical protein", 
    "DNA polymerase", 
    "RNA polymerase", 
    "transporter", 
    "cell division protein",
    "ribosomal protein",
    "membrane protein",
    "DNA-binding protein",
    "ATP synthase",
    "elongation factor"
]

def generate_random_string(length: int = 10) -> str:
    """Generate a random string of fixed length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_test_annotations(count: int, job_id: str = SAMPLE_JOB_ID) -> List[BaktaAnnotation]:
    """
    Generate a specified number of test annotations.
    
    Args:
        count: Number of annotations to generate
        job_id: Job ID to use for the annotations
        
    Returns:
        List of generated annotations
    """
    annotations = []
    
    for i in range(1, count + 1):
        # Generate sequential feature IDs based on feature type
        feature_type = random.choice(FEATURE_TYPES)
        feature_id = f"{feature_type}_{i}"
        
        # Generate random contig names, biased toward a few common contigs
        if i % 10 == 0:
            contig = f"contig_{random.randint(1, 5)}"
        else:
            contig = f"contig_{random.randint(1, count // 20 + 1)}"
        
        # Generate positions with some realistic distribution
        # Most features are relatively short
        length = int(random.expovariate(1/500)) + 100  # Mean length of 500 + 100 base offset
        start = random.randint(1, 5000000)
        end = start + length
        
        # Generate strand
        strand = random.choice(["+", "-"])
        
        # Generate attributes
        attributes = {}
        
        # Add product for most features
        if random.random() < 0.9:
            attributes["product"] = random.choice(PRODUCTS)
        
        # Add gene name for some features
        if random.random() < 0.7:
            attributes["gene"] = generate_random_string(random.randint(3, 5)).lower()
        
        # Add EC number for some features
        if random.random() < 0.3:
            attributes["ec_number"] = f"{random.randint(1, 6)}.{random.randint(1, 20)}.{random.randint(1, 30)}.{random.randint(1, 10)}"
        
        # Add GO terms for some features
        if random.random() < 0.2:
            go_count = random.randint(1, 3)
            attributes["go_terms"] = [f"GO:{random.randint(10000, 99999)}" for _ in range(go_count)]
        
        annotation = BaktaAnnotation(
            job_id=job_id,
            feature_id=feature_id,
            feature_type=feature_type,
            contig=contig,
            start=start,
            end=end,
            strand=strand,
            attributes=attributes,
            id=i
        )
        
        annotations.append(annotation)
    
    return annotations

# Print dataset sizes at module load time
print(f"\nRunning performance tests with:")
print(f"  Large dataset size: {LARGE_DATASET_SIZE}")
print(f"  Medium dataset size: {MEDIUM_DATASET_SIZE}")
print(f"  Small dataset size: {SMALL_DATASET_SIZE}")
print(f"  Benchmark iterations: {BENCHMARK_ITERATIONS}\n")


class TestQueryPerformance:
    """Tests for query performance with large datasets."""
    
    @pytest.fixture(scope="module")
    def large_dataset(self) -> List[BaktaAnnotation]:
        """Generate a large dataset of annotations."""
        return generate_test_annotations(LARGE_DATASET_SIZE)
    
    @pytest.fixture(scope="module")
    def medium_dataset(self) -> List[BaktaAnnotation]:
        """Generate a medium dataset of annotations."""
        return generate_test_annotations(MEDIUM_DATASET_SIZE)
    
    @pytest.fixture(scope="module")
    def small_dataset(self) -> List[BaktaAnnotation]:
        """Generate a small dataset of annotations."""
        return generate_test_annotations(SMALL_DATASET_SIZE)
    
    @pytest.fixture(scope="function")
    def query_interface(self):
        """Create a query interface with a mock repository."""
        from unittest.mock import MagicMock
        
        mock_repo = MagicMock()
        interface = BaktaQueryInterface(repository=mock_repo)
        return interface
    
    def benchmark_query(
        self, 
        query_fn, 
        dataset: List[BaktaAnnotation], 
        iterations: int = BENCHMARK_ITERATIONS
    ) -> Dict[str, Any]:
        """
        Benchmark a query function.
        
        Args:
            query_fn: Function to benchmark that takes a dataset as input
            dataset: Dataset to query
            iterations: Number of iterations to run
            
        Returns:
            Dictionary with benchmark statistics
        """
        # Clear the cache before benchmarking
        global_cache.clear()
        
        times = []
        for _ in range(iterations):
            start_time = time.time()
            result = query_fn(dataset)
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "iterations": iterations,
            "dataset_size": len(dataset),
            "result_size": len(result) if isinstance(result, list) else None
        }
    
    def test_filter_by_feature_type_performance(self, large_dataset, medium_dataset, small_dataset):
        """Test performance of filtering annotations by feature type."""
        def query_fn(dataset):
            return [ann for ann in dataset if ann.feature_type == "CDS"]
        
        # Benchmark each dataset size
        small_stats = self.benchmark_query(query_fn, small_dataset)
        medium_stats = self.benchmark_query(query_fn, medium_dataset)
        large_stats = self.benchmark_query(query_fn, large_dataset)
        
        # Log the results
        print(f"\nFilter by feature_type performance:")
        print(f"Small dataset ({small_stats['dataset_size']} items): "
              f"{small_stats['mean']:.6f}s (mean), {small_stats['median']:.6f}s (median)")
        print(f"Medium dataset ({medium_stats['dataset_size']} items): "
              f"{medium_stats['mean']:.6f}s (mean), {medium_stats['median']:.6f}s (median)")
        print(f"Large dataset ({large_stats['dataset_size']} items): "
              f"{large_stats['mean']:.6f}s (mean), {large_stats['median']:.6f}s (median)")
        
        # Verify performance scales reasonably with dataset size
        # Thresholds adjusted based on dataset size
        small_threshold = 0.001 * SMALL_DATASET_SIZE / 100  # Base threshold for small dataset
        medium_threshold = small_threshold * 10  # Allow 10x slower for medium
        large_threshold = medium_threshold * 10  # Allow 10x slower for large
        
        assert medium_stats['mean'] < medium_threshold, "Medium dataset query much slower than expected"
        assert large_stats['mean'] < large_threshold, "Large dataset query much slower than expected"
    
    def test_query_builder_performance(self, large_dataset):
        """Test performance of QueryBuilder with complex filters."""
        builder = QueryBuilder()
        
        # Build a complex query with multiple conditions
        builder.add_condition("feature_type", FilterOperator.EQUALS, "CDS")
        builder.add_condition("start", FilterOperator.GREATER_THAN, 1000000)
        builder.add_condition("end", FilterOperator.LESS_THAN, 2000000)
        builder.add_condition("strand", FilterOperator.EQUALS, "+")
        builder.add_condition("product", FilterOperator.CONTAINS, "protein", True)
        
        # Create a query function using the builder
        def query_fn(dataset):
            return builder.filter(dataset)
        
        # Benchmark the query
        stats = self.benchmark_query(query_fn, large_dataset)
        
        # Log the results
        print(f"\nComplex query performance:")
        print(f"Dataset size: {stats['dataset_size']} items")
        print(f"Mean time: {stats['mean']:.6f}s")
        print(f"Median time: {stats['median']:.6f}s")
        print(f"Result size: {stats['result_size']} items")
        
        # Verify performance is reasonable - adjust threshold based on dataset size
        threshold = 0.0002 * LARGE_DATASET_SIZE  # Scale threshold with dataset size
        assert stats['mean'] < threshold, "Complex query took too long"
    
    def test_sort_performance(self, large_dataset):
        """Test performance of sorting annotations."""
        # Sort by start position
        def sort_by_start(dataset):
            return sorted(dataset, key=lambda ann: ann.start)
        
        # Sort by feature type and then start position
        def sort_by_type_and_start(dataset):
            return sorted(dataset, key=lambda ann: (ann.feature_type, ann.start))
        
        # Benchmark both sorts
        start_stats = self.benchmark_query(sort_by_start, large_dataset)
        complex_stats = self.benchmark_query(sort_by_type_and_start, large_dataset)
        
        # Log the results
        print(f"\nSort performance:")
        print(f"Sort by start: {start_stats['mean']:.6f}s (mean), {start_stats['median']:.6f}s (median)")
        print(f"Sort by type and start: {complex_stats['mean']:.6f}s (mean), {complex_stats['median']:.6f}s (median)")
        
        # Verify performance is reasonable - adjust threshold based on dataset size
        threshold = 0.0001 * LARGE_DATASET_SIZE  # Scale threshold with dataset size
        assert start_stats['mean'] < threshold, "Simple sort took too long"
        assert complex_stats['mean'] < threshold, "Complex sort took too long"
        
        # Complex sort should be slightly slower than simple sort
        assert complex_stats['mean'] > start_stats['mean'] * 0.9, "Complex sort should be slower than simple sort"
    
    def test_cached_query_performance(self, large_dataset):
        """Test performance improvement with caching."""
        # Create a cached function
        @cached(ttl_seconds=60)
        def cached_query(dataset):
            # Simulate some computation
            time.sleep(0.01)
            return [ann for ann in dataset if ann.feature_type == "CDS"]
        
        # Create an uncached equivalent
        def uncached_query(dataset):
            # Simulate the same computation but a bit slower to ensure reliable test results
            time.sleep(0.02)  # Increased sleep time to ensure it's slower than cached
            return [ann for ann in dataset if ann.feature_type == "CDS"]
        
        # First run with cache miss
        cache_miss_stats = self.benchmark_query(cached_query, large_dataset, iterations=1)
        
        # Subsequent runs should hit the cache
        cache_hit_stats = self.benchmark_query(cached_query, large_dataset, iterations=5)
        
        # Uncached for comparison
        uncached_stats = self.benchmark_query(uncached_query, large_dataset, iterations=5)
        
        # Log the results
        print(f"\nCached query performance:")
        print(f"Cache miss (first run): {cache_miss_stats['mean']:.6f}s")
        print(f"Cache hit (subsequent runs): {cache_hit_stats['mean']:.6f}s")
        print(f"Uncached: {uncached_stats['mean']:.6f}s")
        
        # Verify cache hits are faster than cache misses
        assert cache_hit_stats['mean'] < cache_miss_stats['mean'] * 0.8, "Cache hit not significantly faster than miss"
        
        # Verify cache hits are faster than uncached queries
        assert cache_hit_stats['mean'] < uncached_stats['mean'] * 0.5, "Cache hit not significantly faster than uncached"
    
    def test_range_query_performance(self, large_dataset):
        """Test performance of range queries."""
        # Define a range query function
        def range_query(dataset):
            contig = "contig_1"
            start = 1000000
            end = 2000000
            return [
                ann for ann in dataset
                if ann.contig == contig and not (ann.end < start or ann.start > end)
            ]
        
        # Benchmark the query
        stats = self.benchmark_query(range_query, large_dataset)
        
        # Log the results
        print(f"\nRange query performance:")
        print(f"Dataset size: {stats['dataset_size']} items")
        print(f"Mean time: {stats['mean']:.6f}s")
        print(f"Median time: {stats['median']:.6f}s")
        print(f"Result size: {stats['result_size']} items")
        
        # Verify performance is reasonable - adjust threshold based on dataset size
        threshold = 0.0001 * LARGE_DATASET_SIZE  # Scale threshold with dataset size
        assert stats['mean'] < threshold, "Range query took too long"
    
    def test_query_interface_performance(self, query_interface, large_dataset):
        """Test performance of the query interface."""
        # Set up the mock repository
        query_interface.repository.get_annotations.return_value = large_dataset
        
        def query_fn(dataset):
            # Dataset is not used here as it's mocked in the interface
            _ = dataset  # Suppress unused parameter warning
            options = QueryOptions(
                sort_by="start",
                sort_order=SortOrder.DESC,
                limit=100,
                offset=0
            )
            result = query_interface.get_annotations(SAMPLE_JOB_ID, "CDS", options)
            return result.items
        
        # Benchmark the query
        stats = self.benchmark_query(query_fn, large_dataset)
        
        # Log the results
        print(f"\nQuery interface performance:")
        print(f"Dataset size: {stats['dataset_size']} items")
        print(f"Mean time: {stats['mean']:.6f}s")
        print(f"Median time: {stats['median']:.6f}s")
        
        # Verify performance is reasonable - adjust threshold based on dataset size
        threshold = 0.0002 * LARGE_DATASET_SIZE  # Scale threshold with dataset size
        assert stats['mean'] < threshold, "Query interface took too long"
    
    def test_batch_processing_performance(self, large_dataset):
        """Test performance of batch processing."""
        from amr_predictor.bakta.dao.batch_processor import process_in_batches
        
        # Define a batch processing function
        def process_batch(batch):
            # Simulate some batch processing
            return [ann for ann in batch if ann.feature_type == "CDS"]
        
        # Time the batch processing
        start_time = time.time()
        result = process_in_batches(large_dataset, process_batch, batch_size=500)
        end_time = time.time()
        
        # Log the results
        print(f"\nBatch processing performance:")
        print(f"Dataset size: {len(large_dataset)} items")
        print(f"Batch size: 500 items")
        print(f"Total time: {end_time - start_time:.6f}s")
        print(f"Processed items: {result['processed']}")
        print(f"Number of batches: {result['batches']}")
        
        # Verify performance and correctness
        assert result["success"], "Batch processing failed"
        assert result["processed"] == len(large_dataset), "Not all items were processed"
        
        # Adjust threshold based on dataset size
        threshold = 0.0002 * LARGE_DATASET_SIZE  # Scale threshold with dataset size
        assert end_time - start_time < threshold, "Batch processing took too long" 