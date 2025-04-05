#!/usr/bin/env python3
"""
Data transformers for Bakta result files.

This module provides transformers to convert parsed data from various
Bakta result formats into database model objects.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from amr_predictor.bakta.models import (
    BaktaAnnotation, 
    BaktaSequence, 
    BaktaResultFile
)
from amr_predictor.bakta.exceptions import BaktaParserError

logger = logging.getLogger("bakta-transformers")

class BaseTransformer:
    """
    Base class for all Bakta data transformers.
    """
    
    def __init__(self, job_id: str):
        """
        Initialize the transformer with a job ID.
        
        Args:
            job_id: The ID of the job the data is associated with
        """
        self.job_id = job_id
    
    def transform(self, data: Dict[str, Any]) -> List[Any]:
        """
        Transform parsed data into database model objects.
        
        Args:
            data: Parsed data from a Bakta result file
            
        Returns:
            List of model objects
            
        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement the transform method")


class SequenceTransformer(BaseTransformer):
    """
    Transformer for FASTA sequences.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaSequence]:
        """
        Transform parsed FASTA data into BaktaSequence objects.
        
        Args:
            data: Parsed data from a FASTA file
            
        Returns:
            List of BaktaSequence objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "fasta" or "sequences" not in data:
            raise BaktaParserError("Invalid FASTA data format")
        
        sequences = []
        for seq_data in data["sequences"]:
            header = seq_data.get("header", "")
            sequence = seq_data.get("sequence", "")
            length = len(sequence)
            
            sequence_obj = BaktaSequence(
                job_id=self.job_id,
                header=header,
                sequence=sequence,
                length=length
            )
            sequences.append(sequence_obj)
        
        return sequences


class GFF3Transformer(BaseTransformer):
    """
    Transformer for GFF3 annotations.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaAnnotation]:
        """
        Transform parsed GFF3 data into BaktaAnnotation objects.
        
        Args:
            data: Parsed data from a GFF3 file
            
        Returns:
            List of BaktaAnnotation objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "gff3" or "features" not in data:
            raise BaktaParserError("Invalid GFF3 data format")
        
        annotations = []
        for feature in data["features"]:
            # Skip features without proper attributes
            if "attributes" not in feature or not feature["attributes"]:
                continue
            
            # Extract feature ID (using ID attribute or creating a synthetic one)
            feature_id = feature["attributes"].get("ID", f"{feature['seqid']}_{feature['start']}_{feature['end']}")
            
            annotation = BaktaAnnotation(
                job_id=self.job_id,
                feature_id=feature_id,
                feature_type=feature["type"],
                contig=feature["seqid"],
                start=feature["start"],
                end=feature["end"],
                strand=feature["strand"],
                attributes=feature["attributes"]
            )
            annotations.append(annotation)
        
        return annotations


class TSVTransformer(BaseTransformer):
    """
    Transformer for TSV annotations.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaAnnotation]:
        """
        Transform parsed TSV data into BaktaAnnotation objects.
        
        Args:
            data: Parsed data from a TSV file
            
        Returns:
            List of BaktaAnnotation objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "tsv" or "rows" not in data or "headers" not in data:
            raise BaktaParserError("Invalid TSV data format")
        
        annotations = []
        headers = data["headers"]
        
        # Find key column indices
        locus_tag_idx = _find_column_index(headers, ["locus_tag", "Locus Tag"])
        type_idx = _find_column_index(headers, ["type", "Type"])
        start_idx = _find_column_index(headers, ["start", "Start"])
        end_idx = _find_column_index(headers, ["end", "End"])
        strand_idx = _find_column_index(headers, ["strand", "Strand"])
        contig_idx = _find_column_index(headers, ["contig", "Contig", "seqid", "Seqid"])
        
        if any(idx is None for idx in [locus_tag_idx, type_idx, start_idx, end_idx, strand_idx]):
            raise BaktaParserError("TSV file missing required columns")
        
        for row in data["rows"]:
            attributes = {}
            for i, header in enumerate(headers):
                if i not in [type_idx, start_idx, end_idx, strand_idx, contig_idx]:
                    attributes[header] = row[header]
            
            feature_id = row[headers[locus_tag_idx]] if locus_tag_idx is not None else f"feature_{len(annotations) + 1}"
            feature_type = row[headers[type_idx]]
            start = int(row[headers[start_idx]])
            end = int(row[headers[end_idx]])
            strand = row[headers[strand_idx]]
            contig = row[headers[contig_idx]] if contig_idx is not None else "unknown"
            
            annotation = BaktaAnnotation(
                job_id=self.job_id,
                feature_id=feature_id,
                feature_type=feature_type,
                contig=contig,
                start=start,
                end=end,
                strand=strand,
                attributes=attributes
            )
            annotations.append(annotation)
        
        return annotations


class JSONTransformer(BaseTransformer):
    """
    Transformer for JSON annotations.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaAnnotation]:
        """
        Transform parsed JSON data into BaktaAnnotation objects.
        
        Args:
            data: Parsed data from a JSON file
            
        Returns:
            List of BaktaAnnotation objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "json":
            raise BaktaParserError("Invalid JSON data format")
        
        annotations = []
        
        # Handle Bakta's specific JSON format
        features = data.get("features", [])
        for feature in features:
            if not isinstance(feature, dict):
                continue
                
            feature_id = feature.get("id", f"feature_{len(annotations) + 1}")
            feature_type = feature.get("type", "unknown")
            start = feature.get("start", 0)
            end = feature.get("end", 0)
            strand = feature.get("strand", ".")
            contig = feature.get("contig", "unknown")
            
            # Create attributes dictionary with all remaining fields
            attributes = {}
            for key, value in feature.items():
                if key not in ["id", "type", "start", "end", "strand", "contig"]:
                    attributes[key] = value
            
            annotation = BaktaAnnotation(
                job_id=self.job_id,
                feature_id=feature_id,
                feature_type=feature_type,
                contig=contig,
                start=start,
                end=end,
                strand=strand,
                attributes=attributes
            )
            annotations.append(annotation)
        
        return annotations


class GenBankTransformer(BaseTransformer):
    """
    Transformer for GenBank annotations.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaAnnotation]:
        """
        Transform parsed GenBank data into BaktaAnnotation objects.
        
        Args:
            data: Parsed data from a GenBank file
            
        Returns:
            List of BaktaAnnotation objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "genbank" or "features" not in data:
            raise BaktaParserError("Invalid GenBank data format")
        
        annotations = []
        for feature in data["features"]:
            # Get contig name from metadata if available
            contig = data.get("metadata", {}).get("locus", "unknown")
            
            # Extract feature ID (using locus_tag or other qualifier)
            qualifiers = feature.get("qualifiers", {})
            feature_id = qualifiers.get("locus_tag", 
                         qualifiers.get("gene", 
                         qualifiers.get("product", f"feature_{len(annotations) + 1}")))
            
            annotation = BaktaAnnotation(
                job_id=self.job_id,
                feature_id=str(feature_id),
                feature_type=feature["type"],
                contig=contig,
                start=feature["start"] or 0,
                end=feature["end"] or 0,
                strand="+" if feature.get("location", "").startswith("complement") else "-",
                attributes=qualifiers
            )
            annotations.append(annotation)
        
        return annotations


class EMBLTransformer(BaseTransformer):
    """
    Transformer for EMBL annotations.
    """
    
    def transform(self, data: Dict[str, Any]) -> List[BaktaAnnotation]:
        """
        Transform parsed EMBL data into BaktaAnnotation objects.
        
        Args:
            data: Parsed data from an EMBL file
            
        Returns:
            List of BaktaAnnotation objects
            
        Raises:
            BaktaParserError: If the data format is invalid
        """
        if "format" not in data or data["format"] != "embl" or "features" not in data:
            raise BaktaParserError("Invalid EMBL data format")
        
        annotations = []
        for feature in data["features"]:
            # Get contig name from metadata if available
            contig = data.get("metadata", {}).get("id", "unknown")
            
            # Extract feature ID (using locus_tag or other qualifier)
            qualifiers = feature.get("qualifiers", {})
            feature_id = qualifiers.get("locus_tag", 
                         qualifiers.get("gene", 
                         qualifiers.get("product", f"feature_{len(annotations) + 1}")))
            
            # Determine strand by checking for "complement" in location
            location = feature.get("location", "")
            strand = "-" if "complement" in location else "+"
            
            annotation = BaktaAnnotation(
                job_id=self.job_id,
                feature_id=str(feature_id),
                feature_type=feature["type"],
                contig=contig,
                start=feature["start"] or 0,
                end=feature["end"] or 0,
                strand=strand,
                attributes=qualifiers
            )
            annotations.append(annotation)
        
        return annotations


def _find_column_index(headers: List[str], possible_names: List[str]) -> Optional[int]:
    """
    Find the index of a column in headers with any of the possible names.
    
    Args:
        headers: List of header names
        possible_names: List of possible column names to look for
        
    Returns:
        Index of the column or None if not found
    """
    for name in possible_names:
        if name in headers:
            return headers.index(name)
    return None


def get_transformer_for_format(format_type: str, job_id: str) -> BaseTransformer:
    """
    Get the appropriate transformer for a given format type.
    
    Args:
        format_type: Format type (gff3, tsv, json, etc.)
        job_id: Job ID associated with the data
        
    Returns:
        Transformer instance for the format
        
    Raises:
        BaktaParserError: If no transformer is available for the format
    """
    format_type = format_type.lower()
    
    if format_type == "gff3":
        return GFF3Transformer(job_id)
    elif format_type == "tsv":
        return TSVTransformer(job_id)
    elif format_type == "json":
        return JSONTransformer(job_id)
    elif format_type in ["genbank", "gbff", "gb"]:
        return GenBankTransformer(job_id)
    elif format_type == "embl":
        return EMBLTransformer(job_id)
    elif format_type in ["fasta", "fna", "ffn", "faa"]:
        return SequenceTransformer(job_id)
    else:
        raise BaktaParserError(f"No transformer available for format: {format_type}") 