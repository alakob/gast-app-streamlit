#!/usr/bin/env python3
"""
Tests for the Bakta query interface.

This module contains tests for the Bakta query interface, which provides
flexible querying capabilities for Bakta annotations.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from amr_predictor.bakta.query_interface import (
    BaktaQueryInterface, QueryOptions, QueryResult, 
    SortOrder, QueryError
)
from amr_predictor.bakta.models import BaktaAnnotation
from amr_predictor.bakta.repository import RepositoryError

# Sample data for testing
SAMPLE_JOB_ID = "test-job-123"
SAMPLE_ANNOTATIONS = [
    BaktaAnnotation(
        job_id=SAMPLE_JOB_ID,
        id=1,
        feature_id="CDS_1",
        feature_type="CDS",
        contig="contig1",
        start=100,
        end=400,
        strand="+",
        attributes={"product": "hypothetical protein", "gene": "gene1"}
    ),
    BaktaAnnotation(
        job_id=SAMPLE_JOB_ID,
        id=2,
        feature_id="CDS_2",
        feature_type="CDS",
        contig="contig1",
        start=500,
        end=800,
        strand="-",
        attributes={"product": "transporter", "gene": "gene2"}
    ),
    BaktaAnnotation(
        job_id=SAMPLE_JOB_ID,
        id=3,
        feature_id="tRNA_1",
        feature_type="tRNA",
        contig="contig2",
        start=200,
        end=275,
        strand="+",
        attributes={"product": "tRNA-Ala", "anticodon": "GGC"}
    ),
    BaktaAnnotation(
        job_id=SAMPLE_JOB_ID,
        id=4,
        feature_id="rRNA_1",
        feature_type="rRNA",
        contig="contig2",
        start=1000,
        end=2500,
        strand="+",
        attributes={"product": "16S ribosomal RNA"}
    ),
    BaktaAnnotation(
        job_id=SAMPLE_JOB_ID,
        id=5,
        feature_id="CDS_3",
        feature_type="CDS",
        contig="contig3",
        start=300,
        end=900,
        strand="-",
        attributes={"product": "DNA polymerase", "gene": "polA"}
    )
]

class TestBaktaQueryInterface:
    """Tests for the BaktaQueryInterface class."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        mock_repo = MagicMock()
        mock_repo.get_annotations.return_value = SAMPLE_ANNOTATIONS
        return mock_repo
    
    @pytest.fixture
    def query_interface(self, mock_repository):
        """Create a QueryInterface instance with a mock repository."""
        return BaktaQueryInterface(repository=mock_repository)
    
    def test_get_annotations_no_options(self, query_interface, mock_repository):
        """Test getting annotations without options."""
        # Call the method
        result = query_interface.get_annotations(SAMPLE_JOB_ID)
        
        # Check the result
        assert isinstance(result, QueryResult)
        assert len(result.items) == 5
        assert result.total == 5
        assert result.limit is None
        assert result.offset is None
        
        # Verify repository was called correctly
        mock_repository.get_annotations.assert_called_once_with(SAMPLE_JOB_ID, None)
    
    def test_get_annotations_with_feature_type(self, query_interface, mock_repository):
        """Test getting annotations with feature type filter."""
        # Set up the mock
        mock_repository.get_annotations.return_value = [
            ann for ann in SAMPLE_ANNOTATIONS if ann.feature_type == "CDS"
        ]
        
        # Call the method
        result = query_interface.get_annotations(SAMPLE_JOB_ID, feature_type="CDS")
        
        # Check the result
        assert len(result.items) == 3
        assert all(ann.feature_type == "CDS" for ann in result.items)
        
        # Verify repository was called correctly
        mock_repository.get_annotations.assert_called_once_with(SAMPLE_JOB_ID, "CDS")
    
    def test_get_annotations_with_pagination(self, query_interface):
        """Test getting annotations with pagination."""
        # Call the method with pagination options
        options = QueryOptions(limit=2, offset=1)
        result = query_interface.get_annotations(SAMPLE_JOB_ID, options=options)
        
        # Check the result
        assert len(result.items) == 2
        assert result.total == 5
        assert result.limit == 2
        assert result.offset == 1
        assert result.items[0].id == 2
        assert result.items[1].id == 3
    
    def test_get_annotations_with_sorting(self, query_interface, mock_repository):
        """Test getting annotations with sorting."""
        # Override the mock's return value to ensure we're getting the full SAMPLE_ANNOTATIONS
        mock_repository.get_annotations.return_value = SAMPLE_ANNOTATIONS
        
        # Call the method with sorting options
        options = QueryOptions(sort_by="start", sort_order=SortOrder.DESC)
        result = query_interface.get_annotations(SAMPLE_JOB_ID, options=options)
        
        # Check the result
        assert len(result.items) == 5
        
        # Get the start values in sorted order directly from the source data
        sorted_starts = sorted([ann.start for ann in SAMPLE_ANNOTATIONS], reverse=True)
        
        # Verify that our result matches the expected ordering
        for i, expected_start in enumerate(sorted_starts):
            assert result.items[i].start == expected_start
    
    def test_get_annotations_repository_error(self, query_interface, mock_repository):
        """Test handling repository errors when getting annotations."""
        # Set up the mock to raise an error
        mock_repository.get_annotations.side_effect = RepositoryError("Test error")
        
        # Call the method and expect an error
        with pytest.raises(QueryError) as excinfo:
            query_interface.get_annotations(SAMPLE_JOB_ID)
        
        # Check the error message
        assert "Failed to get annotations: Test error" in str(excinfo.value)
    
    def test_filter_annotations(self, query_interface):
        """Test filtering annotations by criteria."""
        # Call the method with filters
        filters = {"feature_type": "CDS", "strand": "+"}
        result = query_interface.filter_annotations(SAMPLE_JOB_ID, filters)
        
        # Check the result
        assert len(result.items) == 1
        assert result.items[0].feature_id == "CDS_1"
        assert result.total == 1
    
    def test_filter_annotations_with_attribute(self, query_interface):
        """Test filtering annotations by attribute."""
        # Call the method with attribute filters
        filters = {"attribute": {"product": "DNA polymerase"}}
        result = query_interface.filter_annotations(SAMPLE_JOB_ID, filters)
        
        # Check the result
        assert len(result.items) == 1
        assert result.items[0].feature_id == "CDS_3"
    
    def test_filter_annotations_multiple_criteria(self, query_interface, mock_repository):
        """Test filtering annotations by multiple criteria."""
        # Set up the mock to return the full SAMPLE_ANNOTATIONS
        mock_repository.get_annotations.return_value = SAMPLE_ANNOTATIONS
        
        # Call the method with multiple filters
        # CDS_1 starts at 100 and ends at 400, should match these criteria
        filters = {
            "contig": "contig1",
            "min_start": 100,
            "max_end": 700
        }
        result = query_interface.filter_annotations(SAMPLE_JOB_ID, filters)
        
        # Check the result
        assert len(result.items) == 1
        assert result.items[0].feature_id == "CDS_1"
    
    def test_search_annotations(self, query_interface):
        """Test searching annotations by text."""
        # Call the method to search for text
        result = query_interface.search_annotations(SAMPLE_JOB_ID, "rna")
        
        # Check the result
        assert len(result.items) == 2
        assert "RNA" in result.items[0].feature_id
        assert "RNA" in result.items[1].feature_id
    
    def test_search_annotations_in_attributes(self, query_interface):
        """Test searching annotations in attributes."""
        # Call the method to search in attributes
        result = query_interface.search_annotations(
            SAMPLE_JOB_ID, 
            "polymerase", 
            fields=["attributes"]
        )
        
        # Check the result
        assert len(result.items) == 1
        assert result.items[0].feature_id == "CDS_3"
    
    def test_get_feature_types(self, query_interface):
        """Test getting distinct feature types."""
        # Call the method
        result = query_interface.get_feature_types(SAMPLE_JOB_ID)
        
        # Check the result
        assert sorted(result) == ["CDS", "rRNA", "tRNA"]
    
    def test_get_contigs(self, query_interface):
        """Test getting distinct contigs."""
        # Call the method
        result = query_interface.get_contigs(SAMPLE_JOB_ID)
        
        # Check the result
        assert sorted(result) == ["contig1", "contig2", "contig3"]
    
    def test_get_annotation_by_feature_id(self, query_interface):
        """Test getting an annotation by feature ID."""
        # Call the method
        result = query_interface.get_annotation_by_feature_id(SAMPLE_JOB_ID, "rRNA_1")
        
        # Check the result
        assert result is not None
        assert result.feature_id == "rRNA_1"
    
    def test_get_annotation_by_feature_id_not_found(self, query_interface):
        """Test getting a non-existent annotation by feature ID."""
        # Call the method
        result = query_interface.get_annotation_by_feature_id(SAMPLE_JOB_ID, "nonexistent")
        
        # Check the result
        assert result is None
    
    def test_get_annotations_in_range(self, query_interface):
        """Test getting annotations within a genomic range."""
        # Call the method
        result = query_interface.get_annotations_in_range(
            SAMPLE_JOB_ID,
            "contig1",
            300,
            600
        )
        
        # Check the result
        assert len(result.items) == 2
        assert result.total == 2
        assert {ann.feature_id for ann in result.items} == {"CDS_1", "CDS_2"}
    
    def test_get_annotations_in_range_no_results(self, query_interface):
        """Test getting annotations in a range with no results."""
        # Call the method
        result = query_interface.get_annotations_in_range(
            SAMPLE_JOB_ID,
            "contig1",
            1,
            50
        )
        
        # Check the result
        assert len(result.items) == 0
        assert result.total == 0
    
    def test_get_annotation_statistics(self, query_interface):
        """Test getting annotation statistics."""
        # Call the method
        stats = query_interface.get_annotation_statistics(SAMPLE_JOB_ID)
        
        # Check the result
        assert stats["total"] == 5
        assert stats["by_feature_type"] == {"CDS": 3, "tRNA": 1, "rRNA": 1}
        assert stats["by_contig"] == {"contig1": 2, "contig2": 2, "contig3": 1}
        assert stats["by_strand"] == {"+": 3, "-": 2}
        assert stats["size_stats"]["min"] == 76  # tRNA_1 (end - start + 1)
        assert stats["size_stats"]["max"] == 1501  # rRNA_1
    
    def test_sort_annotations_by_attribute(self, query_interface):
        """Test sorting annotations by attribute."""
        # Call the private method directly
        sorted_anns = query_interface._sort_annotations(
            SAMPLE_ANNOTATIONS,
            "attribute.gene"
        )
        
        # Check the result (None values first, then alphabetical)
        assert len(sorted_anns) == 5
        # First two should be the ones without gene attribute
        assert sorted_anns[0].feature_id in ["tRNA_1", "rRNA_1"]
        assert sorted_anns[1].feature_id in ["tRNA_1", "rRNA_1"]
        # Then gene1, gene2, polA
        assert sorted_anns[2].attributes["gene"] == "gene1"
        assert sorted_anns[3].attributes["gene"] == "gene2"
        assert sorted_anns[4].attributes["gene"] == "polA"
    
    def test_paginate_annotations(self, query_interface):
        """Test paginating annotations."""
        # Call the private method directly
        paginated = query_interface._paginate_annotations(
            SAMPLE_ANNOTATIONS,
            limit=2,
            offset=2
        )
        
        # Check the result
        assert len(paginated) == 2
        assert paginated[0].id == 3
        assert paginated[1].id == 4
    
    def test_paginate_annotations_offset_too_large(self, query_interface):
        """Test paginating annotations with an offset larger than the list."""
        # Call the private method directly
        paginated = query_interface._paginate_annotations(
            SAMPLE_ANNOTATIONS,
            limit=2,
            offset=10
        )
        
        # Check the result
        assert len(paginated) == 0 