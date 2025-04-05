#!/usr/bin/env python3
"""
Parsers for Bakta result files.

This module provides parsers for various file formats produced by Bakta:
- GFF3 (General Feature Format version 3)
- TSV (Tab-Separated Values)
- JSON (JavaScript Object Notation)
- EMBL (European Molecular Biology Laboratory format)
- GenBank (GenBank format)
- FASTA (FASTA format)

Each parser extracts structured data from its respective format.
"""

import os
import json
import csv
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Iterator, TextIO, Tuple, Type, TypeVar
from pathlib import Path
from dataclasses import dataclass

from amr_predictor.bakta.exceptions import BaktaParserError

# Import all parser classes
# This is needed to ensure all parsers are available for get_parser_for_format
__all__ = [
    'BaktaParser',
    'GFF3Parser',
    'TSVParser',
    'JSONParser',
    'EMBLParser',
    'GenBankParser',
    'FASTAParser',
    'ParseResult',
    'get_parser_for_format',
    'parse_file'
]

logger = logging.getLogger("bakta-parsers")

# Define a type for parse results
@dataclass
class ParseResult:
    """Result of a parsing operation."""
    format: str
    metadata: Dict[str, Any]
    features: List[Dict[str, Any]]
    sequences: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None

# Type variable for parser classes
T = TypeVar('T', bound='BaktaParser')

class BaktaParser(ABC):
    """Base class for all Bakta result file parsers."""
    
    def __init__(self, file_path: Union[str, Path, TextIO] = None, content: str = None):
        """Initialize the parser with either a file path or content string.
        
        Args:
            file_path: Path to the file to parse, or a file-like object
            content: Content string to parse
            
        Raises:
            BaktaParserError: If neither file_path nor content is provided
        """
        if file_path is None and content is None:
            raise BaktaParserError("Either file_path or content must be provided")
        
        self.file_path = file_path
        self.content = content
        self._parsed_data = None
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """Parse the file or content and return structured data.
        
        Returns:
            Dict containing structured data extracted from the file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        raise NotImplementedError("Subclasses must implement the parse method")
    
    def _get_content(self) -> str:
        """Get content from either the file or the content string.
        
        Returns:
            Content as a string
            
        Raises:
            BaktaParserError: If reading the file fails
        """
        if self.content is not None:
            return self.content
        
        try:
            if isinstance(self.file_path, (str, Path)):
                with open(self.file_path, 'r') as f:
                    return f.read()
            else:  # Assume file-like object
                current_pos = self.file_path.tell()
                self.file_path.seek(0)
                content = self.file_path.read()
                self.file_path.seek(current_pos)  # Restore position
                return content if isinstance(content, str) else content.decode('utf-8')
        except Exception as e:
            raise BaktaParserError(f"Failed to read file content: {str(e)}")
    
    def _get_file_handle(self) -> TextIO:
        """Get a file handle for the file path or content.
        
        Returns:
            File-like object
            
        Raises:
            BaktaParserError: If opening the file fails
        """
        try:
            if isinstance(self.file_path, (str, Path)):
                return open(self.file_path, 'r')
            elif self.file_path is not None:
                return self.file_path
            else:
                import io
                return io.StringIO(self.content)
        except Exception as e:
            raise BaktaParserError(f"Failed to open file: {str(e)}")
    
    @property
    def parsed_data(self) -> Dict[str, Any]:
        """Get the parsed data, parsing the file if necessary.
        
        Returns:
            Dict containing structured data extracted from the file
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse()
        return self._parsed_data


class GFF3Parser(BaktaParser):
    """Parser for GFF3 format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse a GFF3 file and extract features.
        
        Returns:
            Dict containing structured data extracted from the GFF3 file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            gff_data = {
                "format": "gff3",
                "metadata": {},
                "sequences": {},
                "features": []
            }
            
            with self._get_file_handle() as f:
                current_sequence = None
                
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Handle metadata/pragma lines
                    if line.startswith('##'):
                        if line.startswith('##sequence-region'):
                            # Parse sequence region
                            parts = line.split()
                            if len(parts) >= 4:
                                seq_id = parts[1]
                                start = int(parts[2])
                                end = int(parts[3])
                                gff_data["sequences"][seq_id] = {
                                    "id": seq_id,
                                    "start": start,
                                    "end": end,
                                    "length": end - start + 1
                                }
                                current_sequence = seq_id
                        elif line.startswith('##gff-version'):
                            gff_data["metadata"]["version"] = line.split()[1]
                        elif line == '##FASTA':
                            # FASTA section begins, stop parsing GFF
                            break
                        else:
                            # Other pragma
                            key = line[2:].split(' ')[0]
                            value = line[2 + len(key) + 1:]
                            gff_data["metadata"][key] = value
                    # Skip comments
                    elif line.startswith('#'):
                        continue
                    # Parse feature line
                    else:
                        parts = line.split('\t')
                        if len(parts) != 9:
                            continue  # Invalid line
                        
                        seqid, source, type_, start, end, score, strand, phase, attributes_str = parts
                        
                        # Parse attributes
                        attributes = {}
                        for attr in attributes_str.split(';'):
                            if not attr.strip():
                                continue
                            try:
                                key, value = attr.strip().split('=', 1)
                                attributes[key] = value
                            except ValueError:
                                # Handle attribute without value
                                attributes[attr.strip()] = True
                        
                        # Create feature
                        feature = {
                            "seqid": seqid,
                            "source": source,
                            "type": type_,
                            "start": int(start),
                            "end": int(end),
                            "strand": strand,
                            "attributes": attributes
                        }
                        
                        # Add score and phase if they're not '.'
                        if score != '.':
                            try:
                                feature["score"] = float(score)
                            except ValueError:
                                feature["score"] = score
                        
                        if phase != '.':
                            feature["phase"] = phase
                        
                        gff_data["features"].append(feature)
            
            return gff_data
        except Exception as e:
            raise BaktaParserError(f"Failed to parse GFF3 file: {str(e)}")


class TSVParser(BaktaParser):
    """Parser for TSV format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse a TSV file and extract tabular data.
        
        Returns:
            Dict containing structured data extracted from the TSV file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            tsv_data = {
                "format": "tsv",
                "headers": [],
                "rows": []
            }
            
            with self._get_file_handle() as f:
                reader = csv.reader(f, delimiter='\t')
                
                # Parse headers
                try:
                    tsv_data["headers"] = next(reader)
                except StopIteration:
                    raise BaktaParserError("TSV file is empty or has no headers")
                
                # Parse rows
                for row in reader:
                    # Skip comment lines
                    if row and row[0].startswith('#'):
                        continue
                    
                    # Create a dictionary for each row
                    row_dict = {}
                    for i, header in enumerate(tsv_data["headers"]):
                        value = row[i] if i < len(row) else ""
                        row_dict[header] = value
                    
                    tsv_data["rows"].append(row_dict)
            
            return tsv_data
            
        except Exception as e:
            raise BaktaParserError(f"Failed to parse TSV file: {str(e)}")


class JSONParser(BaktaParser):
    """Parser for JSON format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse a JSON file and extract structured data.
        
        Returns:
            Dict containing structured data extracted from the JSON file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            content = self._get_content()
            json_data = json.loads(content)
            
            # Add format metadata
            if isinstance(json_data, dict):
                json_data["format"] = "json"
            
            return json_data
            
        except json.JSONDecodeError as e:
            raise BaktaParserError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise BaktaParserError(f"Failed to parse JSON file: {str(e)}")


def parse_location(location_str: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse a location string into start and end coordinates.
    
    Args:
        location_str: Location string in the format "start..end" or similar
        
    Returns:
        Tuple of (start, end) coordinates
    """
    # Try to find numbers using regex
    numbers = re.findall(r'(\d+)', location_str)
    
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        return int(numbers[0]), int(numbers[0])
    else:
        return None, None


class EMBLParser(BaktaParser):
    """Parser for EMBL format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse an EMBL file and extract sequence and feature data.
        
        Returns:
            Dict containing structured data extracted from the EMBL file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            embl_data = {
                "format": "embl",
                "metadata": {},
                "features": [],
                "sequence": ""
            }
            
            with self._get_file_handle() as f:
                section = "header"
                current_feature = None
                sequence_lines = []
                
                for line in f:
                    line = line.rstrip()
                    
                    # Empty lines
                    if not line:
                        continue
                    
                    # Check for section changes
                    if line.startswith("ID   "):
                        section = "header"
                        id_parts = line[5:].split(";")
                        embl_data["metadata"]["id"] = id_parts[0].strip()
                        if len(id_parts) > 2:
                            embl_data["metadata"]["molecule_type"] = id_parts[1].strip()
                            embl_data["metadata"]["taxonomy"] = id_parts[2].strip()
                    elif line.startswith("FH   "):
                        section = "features_header"
                    elif line.startswith("FT   "):
                        section = "features"
                    elif line.startswith("SQ   "):
                        section = "sequence"
                        continue
                    elif line.startswith("//"):
                        break
                    
                    # Process content based on section
                    if section == "header":
                        if line.startswith("AC   "):
                            embl_data["metadata"]["accession"] = line[5:].strip().rstrip(';')
                        elif line.startswith("DE   "):
                            embl_data["metadata"]["description"] = line[5:].strip()
                        elif line.startswith("KW   "):
                            embl_data["metadata"]["keywords"] = line[5:].strip().split(";")
                        elif line.startswith("OS   "):
                            embl_data["metadata"]["organism"] = line[5:].strip()
                        elif line.startswith("OC   "):
                            # Initialize taxonomy as a list if it doesn't exist or convert it to a list if it's a string
                            if "taxonomy" not in embl_data["metadata"]:
                                embl_data["metadata"]["taxonomy"] = []
                            elif isinstance(embl_data["metadata"]["taxonomy"], str):
                                embl_data["metadata"]["taxonomy"] = [embl_data["metadata"]["taxonomy"]]
                            
                            # Add taxonomy terms
                            taxonomy_terms = [t.strip() for t in line[5:].strip().split(";") if t.strip()]
                            embl_data["metadata"]["taxonomy"].extend(taxonomy_terms)
                    
                    elif section == "features":
                        if not line.startswith("FT   "):
                            continue
                            
                        # Extract content after FT prefix
                        content = line[5:].strip()
                        
                        # Skip empty lines
                        if not content:
                            continue
                        
                        # Process feature line
                        if not content.startswith('/'):
                            # This is a new feature line with type and location
                            # Save previous feature if exists
                            if current_feature:
                                embl_data["features"].append(current_feature)
                            
                            parts = content.split(None, 1)  # Split on first whitespace
                            if len(parts) >= 2:
                                feature_type = parts[0]
                                location_str = parts[1]
                                
                                # Parse the location using our helper function
                                start, end = parse_location(location_str)
                                
                                # Create new feature
                                current_feature = {
                                    "type": feature_type,
                                    "location": location_str,
                                    "start": start,
                                    "end": end,
                                    "qualifiers": {}
                                }
                        elif content.startswith('/'):
                            # This is a qualifier line
                            if not current_feature:
                                continue
                                
                            # Remove the leading slash
                            content = content[1:]
                            
                            # Check if it has an equals sign (name=value)
                            if '=' in content:
                                name, value = content.split('=', 1)
                                
                                # If value is quoted, remove the quotes if the line ends with a quote
                                if value.startswith('"'):
                                    value = value[1:]  # Remove opening quote
                                    if value.endswith('"'):
                                        value = value[:-1]  # Remove closing quote if present
                                        
                                # Store the qualifier
                                current_feature["qualifiers"][name] = value
                            else:
                                # Flag qualifier (no value)
                                current_feature["qualifiers"][content] = True
                        else:
                            # This is a continuation line for a qualifier
                            if not current_feature or not current_feature["qualifiers"]:
                                continue
                                
                            # Get the last qualifier
                            qualifiers = current_feature["qualifiers"]
                            last_qualifier = list(qualifiers.keys())[-1]
                            
                            # Only append if the last qualifier is a string
                            if isinstance(qualifiers[last_qualifier], str):
                                # Handle quoted values
                                if content.endswith('"'):
                                    content = content[:-1]  # Remove closing quote
                                
                                # Append to the last qualifier
                                qualifiers[last_qualifier] += content
                    
                    elif section == "sequence":
                        # Collect sequence lines (remove numbers and spaces)
                        if not line.startswith("SQ   ") and not line.startswith("//"):
                            seq_part = ''.join(line.strip().split()[:-1])  # Remove the number at the end
                            sequence_lines.append(seq_part)
                
                # Add the last feature if exists
                if current_feature:
                    embl_data["features"].append(current_feature)
                
                # Join sequence lines
                embl_data["sequence"] = ''.join(sequence_lines).upper()
            
            return embl_data
            
        except Exception as e:
            raise BaktaParserError(f"Failed to parse EMBL file: {str(e)}")


class GenBankParser(BaktaParser):
    """Parser for GenBank format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse a GenBank file and extract sequence and feature data.
        
        Returns:
            Dict containing structured data extracted from the GenBank file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            gb_data = {
                "format": "genbank",
                "metadata": {},
                "features": [],
                "sequence": ""
            }
            
            with self._get_file_handle() as f:
                section = "header"
                current_feature = None
                sequence_lines = []
                
                for line in f:
                    line = line.rstrip()
                    
                    # Empty lines
                    if not line:
                        continue
                    
                    # Check for section changes
                    if line.startswith("LOCUS "):
                        section = "header"
                        parts = line[6:].split()
                        if len(parts) > 0:
                            gb_data["metadata"]["locus"] = parts[0]
                        if len(parts) > 1:
                            gb_data["metadata"]["length"] = parts[1]
                        if len(parts) > 2 and parts[2] in ["bp", "aa"]:
                            gb_data["metadata"]["unit"] = parts[2]
                    elif line.startswith("FEATURES "):
                        section = "features"
                        continue
                    elif line.startswith("ORIGIN"):
                        section = "sequence"
                        continue
                    elif line.startswith("//"):
                        break
                    
                    # Process content based on section
                    if section == "header":
                        if line.startswith("DEFINITION "):
                            gb_data["metadata"]["definition"] = line[11:].strip()
                        elif line.startswith("ACCESSION "):
                            gb_data["metadata"]["accession"] = line[10:].strip()
                        elif line.startswith("VERSION "):
                            gb_data["metadata"]["version"] = line[8:].strip()
                        elif line.startswith("KEYWORDS "):
                            gb_data["metadata"]["keywords"] = line[9:].strip().split(";")
                        elif line.startswith("SOURCE "):
                            gb_data["metadata"]["source"] = line[7:].strip()
                        elif line.startswith("  ORGANISM "):
                            gb_data["metadata"]["organism"] = line[10:].strip()
                    
                    elif section == "features":
                        # Feature lines start with 5 spaces
                        if line.startswith("     "):
                            content = line[5:]
                            # New feature - starts with no spaces
                            if not content.startswith(" "):
                                # Save previous feature if exists
                                if current_feature:
                                    gb_data["features"].append(current_feature)
                                
                                # Parse feature type and location
                                parts = content.strip().split()
                                feature_type = parts[0]
                                location_str = ' '.join(parts[1:])
                                
                                # Parse the location using our helper function
                                start, end = parse_location(location_str)
                                
                                current_feature = {
                                    "type": feature_type,
                                    "location": location_str,
                                    "start": start,
                                    "end": end,
                                    "qualifiers": {}
                                }
                            # Qualifier - starts with /
                            elif content.strip().startswith('/'):
                                if not current_feature:
                                    continue
                                
                                content = content.strip()
                                # Parse qualifier
                                qual_parts = content[1:].split('=', 1)
                                qual_name = qual_parts[0]
                                
                                if len(qual_parts) == 1:
                                    # Flag qualifier with no value
                                    current_feature["qualifiers"][qual_name] = True
                                else:
                                    qual_value = qual_parts[1]
                                    # Handle quoted values
                                    if qual_value.startswith('"'):
                                        qual_value = qual_value[1:]
                                        if qual_value.endswith('"'):
                                            qual_value = qual_value[:-1]
                                    
                                    current_feature["qualifiers"][qual_name] = qual_value
                            # Continuation of a qualifier
                            elif current_feature and content.strip():
                                # Check if there are qualifiers before trying to access the last one
                                if current_feature["qualifiers"] and len(current_feature["qualifiers"]) > 0:
                                    # Find the last qualifier
                                    last_qualifier = list(current_feature["qualifiers"].keys())[-1]
                                    # Append the content to the last qualifier
                                    value = current_feature["qualifiers"][last_qualifier]
                                    if isinstance(value, str):
                                        content_stripped = content.strip()
                                        if content_stripped.endswith('"'):
                                            content_stripped = content_stripped[:-1]
                                        current_feature["qualifiers"][last_qualifier] = value + content_stripped
                                else:
                                    # Skip continuation lines if no qualifiers exist yet
                                    continue
                    
                    elif section == "sequence":
                        # Collect sequence lines (ignore numbers and spaces)
                        if not line.startswith("ORIGIN"):
                            # Remove line numbers and spaces
                            seq_part = ''.join(line.strip().split()[1:])
                            sequence_lines.append(seq_part)
                
                # Add the last feature if exists
                if current_feature:
                    gb_data["features"].append(current_feature)
                
                # Join sequence lines
                gb_data["sequence"] = ''.join(sequence_lines).upper()
            
            return gb_data
            
        except Exception as e:
            raise BaktaParserError(f"Failed to parse GenBank file: {str(e)}")


class FASTAParser(BaktaParser):
    """Parser for FASTA format files."""
    
    def parse(self) -> Dict[str, Any]:
        """Parse a FASTA file and extract sequence data.
        
        Returns:
            Dict containing structured data extracted from the FASTA file
            
        Raises:
            BaktaParserError: If parsing fails
        """
        try:
            fasta_data = {
                "format": "fasta",
                "sequences": []
            }
            
            with self._get_file_handle() as f:
                current_header = None
                current_sequence = []
                
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Header line
                    if line.startswith('>'):
                        # Save previous sequence if exists
                        if current_header is not None and current_sequence:
                            fasta_data["sequences"].append({
                                "header": current_header,
                                "sequence": ''.join(current_sequence)
                            })
                        
                        current_header = line[1:]
                        current_sequence = []
                    # Sequence line
                    else:
                        if current_header is not None:
                            current_sequence.append(line)
                
                # Save the last sequence
                if current_header is not None and current_sequence:
                    fasta_data["sequences"].append({
                        "header": current_header,
                        "sequence": ''.join(current_sequence)
                    })
            
            return fasta_data
            
        except Exception as e:
            raise BaktaParserError(f"Failed to parse FASTA file: {str(e)}")


# Dictionary of parsers by file extension
PARSER_BY_EXTENSION = {
    '.gff': GFF3Parser,
    '.gff3': GFF3Parser,
    '.tsv': TSVParser,
    '.json': JSONParser,
    '.embl': EMBLParser,
    '.gb': GenBankParser,
    '.gbk': GenBankParser,
    '.gbff': GenBankParser,
    '.fa': FASTAParser,
    '.fasta': FASTAParser,
    '.faa': FASTAParser,
    '.ffn': FASTAParser,
    '.fna': FASTAParser,
}


def get_parser_for_format(format_name: str) -> Type[BaktaParser]:
    """Get the appropriate parser class for a given format.
    
    Args:
        format_name: Format name or file extension
        
    Returns:
        Parser class for the specified format
        
    Raises:
        BaktaParserError: If no parser is available for the format
    """
    format_name = format_name.lower()
    
    # Map format names and file extensions to parser classes
    parser_map = {
        'gff3': GFF3Parser,
        'gff': GFF3Parser,
        'tsv': TSVParser,
        'json': JSONParser,
        'embl': EMBLParser,
        'gbk': GenBankParser,
        'genbank': GenBankParser,
        'fasta': FASTAParser,
        'fa': FASTAParser,
        'fna': FASTAParser
    }
    
    if format_name not in parser_map:
        valid_formats = ', '.join(parser_map.keys())
        raise BaktaParserError(f"No parser available for format: {format_name}. "
                                f"Valid formats: {valid_formats}")
    
    return parser_map[format_name]

# Maintain backwards compatibility
get_parser_for_file = get_parser_for_format


def parse_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parse a file using the appropriate parser.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict containing structured data extracted from the file
        
    Raises:
        BaktaParserError: If parsing fails
    """
    parser = get_parser_for_file(file_path)
    return parser.parse() 