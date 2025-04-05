#!/usr/bin/env python3
"""
Test the correctness of query operations for the Bakta API.

This module contains tests that verify the correctness of various
query operations, including filtering, sorting, and pagination.
"""

import os
import uuid
import random
import string
import pytest
from typing import List, Dict, Any, Callable, Optional

# Set dataset size from environment variable, default to 200, with max of 500
# to avoid excessive memory usage in correctness tests
DATASET_SIZE = min(
    int(os.environ.get("BAKTA_TEST_DATASET_SIZE", "200")),
    500
)

# Print the dataset size for visibility
print(f"Running correctness tests with dataset size: {DATASET_SIZE}")

from amr_predictor.bakta.models import BaktaAnnotation
from amr_predictor.bakta.dao.query_builder import (
    QueryBuilder, QueryCondition, FilterOperator, LogicalOperator
)
from amr_predictor.bakta.query_interface import (
    BaktaQueryInterface, QueryOptions, SortOrder
)

class MockRepository:
    """Mock repository for testing the query interface."""
    
    def __init__(self, annotations: List[BaktaAnnotation]):
        """Initialize the mock repository with a list of annotations."""
        self.annotations = annotations
    
    def get_annotations(self, job_id: str) -> List[BaktaAnnotation]:
        """Get all annotations for a job."""
        return [ann for ann in self.annotations if ann.job_id == job_id]


@pytest.fixture
def annotation_data() -> List[BaktaAnnotation]:
    """
    Create a dataset of random annotations for testing.
    
    Returns:
        List of BaktaAnnotation objects
    """
    job_id = str(uuid.uuid4())
    feature_types = ["CDS", "gene", "tRNA", "rRNA", "misc_feature"]
    contigs = [f"contig_{i}" for i in range(1, 6)]
    strands = ["+", "-"]
    
    annotations = []
    
    for i in range(DATASET_SIZE):
        feature_type = random.choice(feature_types)
        contig = random.choice(contigs)
        start = random.randint(1, 10000)
        end = start + random.randint(100, 1000)
        strand = random.choice(strands)
        
        # Create random attributes
        attributes = {}
        
        # Add attribute based on feature type
        if feature_type == "CDS":
            attributes["product"] = f"protein_{i}"
            attributes["gene"] = f"gene_{i}"
            attributes["locus_tag"] = f"locus_{i}"
            attributes["note"] = "Coding sequence"
        
        elif feature_type == "gene":
            attributes["name"] = f"gene_{i}"
            attributes["locus_tag"] = f"locus_{i}"
        
        elif feature_type == "tRNA":
            attributes["product"] = f"tRNA-{random.choice(['Ala', 'Arg', 'Asn', 'Asp'])}"
            attributes["note"] = "Transfer RNA"
        
        elif feature_type == "rRNA":
            attributes["product"] = f"{random.choice(['5S', '16S', '23S'])} ribosomal RNA"
            attributes["note"] = "Ribosomal RNA"
        
        else:  # misc_feature
            attributes["note"] = "Miscellaneous feature"
        
        # Add common attributes
        attributes["codon_start"] = random.randint(1, 3)
        attributes["score"] = round(random.random() * 100, 2)
        
        annotation = BaktaAnnotation(
            id=str(i),
            job_id=job_id,
            feature_id=f"feature_{i}",
            feature_type=feature_type,
            contig=contig,
            start=start,
            end=end,
            strand=strand,
            attributes=attributes
        )
        
        annotations.append(annotation)
    
    return annotations


@pytest.fixture
def query_interface(annotation_data: List[BaktaAnnotation]) -> BaktaQueryInterface:
    """
    Create a query interface with the test dataset.
    
    Args:
        annotation_data: Test dataset
        
    Returns:
        BaktaQueryInterface instance
    """
    repository = MockRepository(annotation_data)
    return BaktaQueryInterface(repository)


def test_simple_filter_by_feature_type(query_interface, annotation_data):
    """
    Test filtering annotations by feature type.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Filter by feature type
    feature_type = "CDS"
    result = query_interface.get_annotations(job_id, feature_type)
    
    # Verify results
    assert all(ann.feature_type == feature_type for ann in result.items)
    
    # Count manually for verification
    expected_count = len([ann for ann in annotation_data 
                          if ann.job_id == job_id and ann.feature_type == feature_type])
    
    assert len(result.items) == expected_count
    assert result.total_count == expected_count


def test_filter_by_range(query_interface, annotation_data):
    """
    Test filtering annotations by genomic range.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Get a contig from the dataset
    contig = annotation_data[0].contig
    
    # Define a range
    start = 5000
    end = 8000
    
    # Get annotations in range
    result = query_interface.get_annotations_in_range(job_id, contig, start, end)
    
    # Verify results manually
    expected = [
        ann for ann in annotation_data
        if (ann.job_id == job_id and 
            ann.contig == contig and 
            not (ann.end < start or ann.start > end))
    ]
    
    assert len(result) == len(expected)
    
    # Verify that all results are in the range
    for ann in result:
        assert ann.contig == contig
        assert not (ann.end < start or ann.start > end)


def test_compound_filter(query_interface, annotation_data):
    """
    Test filtering annotations with multiple conditions.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Create query options with filters
    options = QueryOptions()
    options.filters = [
        QueryCondition("feature_type", FilterOperator.EQUALS, "CDS"),
        QueryCondition("strand", FilterOperator.EQUALS, "+")
    ]
    
    # Get filtered annotations
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify results
    assert all(ann.feature_type == "CDS" and ann.strand == "+" for ann in result.items)
    
    # Count manually for verification
    expected_count = len([
        ann for ann in annotation_data
        if ann.job_id == job_id and ann.feature_type == "CDS" and ann.strand == "+"
    ])
    
    assert len(result.items) == expected_count
    assert result.total_count == expected_count


def test_attribute_filter(query_interface, annotation_data):
    """
    Test filtering annotations by attribute.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Create query options with attribute filter
    options = QueryOptions()
    options.filters = [
        QueryCondition("product", FilterOperator.CONTAINS, "tRNA", is_attribute=True)
    ]
    
    # Get filtered annotations
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify results
    for ann in result.items:
        assert "product" in ann.attributes
        assert "tRNA" in ann.attributes["product"]
    
    # Count manually for verification
    expected_count = len([
        ann for ann in annotation_data
        if (ann.job_id == job_id and
            "product" in ann.attributes and
            "tRNA" in ann.attributes["product"])
    ])
    
    assert len(result.items) == expected_count
    assert result.total_count == expected_count


def test_sorting(query_interface, annotation_data):
    """
    Test sorting annotations by field.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Create query options with sorting
    options = QueryOptions(sort_by="start", sort_order=SortOrder.ASC)
    
    # Get sorted annotations
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify sorting
    for i in range(1, len(result.items)):
        assert result.items[i-1].start <= result.items[i].start
    
    # Test descending sort
    options = QueryOptions(sort_by="start", sort_order=SortOrder.DESC)
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify sorting
    for i in range(1, len(result.items)):
        assert result.items[i-1].start >= result.items[i].start


def test_pagination(query_interface, annotation_data):
    """
    Test paginating annotations.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Get all annotations for reference
    all_annotations = [ann for ann in annotation_data if ann.job_id == job_id]
    total_count = len(all_annotations)
    
    # Create query options with pagination
    page_size = 10
    options = QueryOptions(limit=page_size, offset=0, sort_by="feature_id")
    
    # Get first page
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify pagination
    assert len(result.items) == page_size
    assert result.total_count == total_count
    assert result.offset == 0
    assert result.limit == page_size
    
    # Get second page
    options.offset = page_size
    result2 = query_interface.get_annotations(job_id, options=options)
    
    # Verify pagination
    assert len(result2.items) == page_size
    assert result2.total_count == total_count
    assert result2.offset == page_size
    assert result2.limit == page_size
    
    # Verify no overlap between pages
    first_page_ids = {ann.id for ann in result.items}
    second_page_ids = {ann.id for ann in result2.items}
    assert not first_page_ids.intersection(second_page_ids)


def test_complex_query(query_interface, annotation_data):
    """
    Test complex query with multiple filters, sorting, and pagination.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Create query options with multiple filters
    options = QueryOptions(
        sort_by="start",
        sort_order=SortOrder.ASC,
        limit=5,
        offset=0
    )
    
    options.filters = [
        QueryCondition("feature_type", FilterOperator.IN, ["CDS", "gene"]),
        QueryCondition("start", FilterOperator.GREATER_THAN, 1000),
        QueryCondition("end", FilterOperator.LESS_THAN, 9000)
    ]
    
    # Get results
    result = query_interface.get_annotations(job_id, options=options)
    
    # Verify results
    assert len(result.items) <= 5
    
    for ann in result.items:
        assert ann.feature_type in ["CDS", "gene"]
        assert ann.start > 1000
        assert ann.end < 9000
    
    # Verify sorting
    for i in range(1, len(result.items)):
        assert result.items[i-1].start <= result.items[i].start
    
    # Verify total count
    expected_count = len([
        ann for ann in annotation_data
        if (ann.job_id == job_id and
            ann.feature_type in ["CDS", "gene"] and
            ann.start > 1000 and
            ann.end < 9000)
    ])
    
    assert result.total_count == expected_count


def test_get_feature_types(query_interface, annotation_data):
    """
    Test getting distinct feature types.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Get feature types
    feature_types = query_interface.get_feature_types(job_id)
    
    # Verify results
    expected_types = sorted(set(ann.feature_type for ann in annotation_data if ann.job_id == job_id))
    assert feature_types == expected_types


def test_get_contigs(query_interface, annotation_data):
    """
    Test getting distinct contigs.
    
    Args:
        query_interface: Query interface fixture
        annotation_data: Test dataset
    """
    # Get a job ID from the dataset
    job_id = annotation_data[0].job_id
    
    # Get contigs
    contigs = query_interface.get_contigs(job_id)
    
    # Verify results
    expected_contigs = sorted(set(ann.contig for ann in annotation_data if ann.job_id == job_id))
    assert contigs == expected_contigs 