#!/usr/bin/env python3
"""
Data models for the Bakta annotation service.

This module defines the data models used throughout the
Bakta integration, including models for jobs, annotations,
query results, and other entities.
"""

import time
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union

class JobStatus(str, Enum):
    """Status of a Bakta annotation job."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"

class SortOrder(str, Enum):
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"

class BaktaException(Exception):
    """Base exception for Bakta integration."""
    pass

class BaktaApiError(BaktaException):
    """Exception raised for Bakta API errors."""
    pass

class BaktaDatabaseError(BaktaException):
    """Exception raised for database errors."""
    pass

class BaktaParseError(BaktaException):
    """Exception raised for parsing errors."""
    pass

class BaktaFileType(str, Enum):
    """Enum for Bakta result file types."""
    GFF3 = "gff3"
    JSON = "json"
    TSV = "tsv"
    GENBANK = "gbff"
    FASTA = "faa"
    FASTA_RNA = "ffn"

class FilterOperator(str, Enum):
    """Enum for query filter operators."""
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    LIKE = "like"
    IN = "in"
    BETWEEN = "between"

@dataclass
class BaktaJob:
    """Represents a Bakta annotation job."""
    id: str
    name: str
    status: str
    config: Dict[str, Any]
    secret: str
    fasta_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaktaJob':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BaktaSequence:
    """Represents a genomic sequence in a Bakta job."""
    job_id: str
    header: str
    sequence: str
    length: int
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaktaSequence':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BaktaResultFile:
    """Represents a result file from a Bakta annotation job."""
    job_id: str
    file_type: str
    file_path: str
    download_url: Optional[str] = None
    downloaded_at: Optional[str] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaktaResultFile':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BaktaAnnotation:
    """Represents an annotation result from Bakta."""
    job_id: str
    feature_id: str
    feature_type: str
    contig: str
    start: int
    end: int
    strand: str
    attributes: Dict[str, Any]
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaktaAnnotation':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BaktaJobStatusHistory:
    """Represents a job status history entry."""
    job_id: str
    status: str
    timestamp: str
    message: Optional[str] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaktaJobStatusHistory':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class BaktaResult:
    """Represents a complete Bakta annotation result."""
    job: BaktaJob
    sequences: List[BaktaSequence] = field(default_factory=list)
    result_files: List[BaktaResultFile] = field(default_factory=list)
    annotations: List[BaktaAnnotation] = field(default_factory=list)
    status_history: List[BaktaJobStatusHistory] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job": self.job.to_dict(),
            "sequences": [seq.to_dict() for seq in self.sequences],
            "result_files": [rf.to_dict() for rf in self.result_files],
            "annotations": [ann.to_dict() for ann in self.annotations],
            "status_history": [sh.to_dict() for sh in self.status_history]
        }

@dataclass
class Filter:
    """Filter for query conditions."""
    field: str
    operator: FilterOperator
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }

@dataclass
class QueryOptions:
    """Options for database queries."""
    filters: List[Filter] = field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    limit: Optional[int] = None
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filters": [f.to_dict() for f in self.filters],
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "limit": self.limit,
            "offset": self.offset
        }

@dataclass
class QueryResult:
    """Result of a database query."""
    items: List[Any]
    total: int
    limit: Optional[int] = None
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "items": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

class QueryBuilder:
    """Builder for database queries."""
    
    def __init__(self, job_id: str):
        """Initialize the query builder."""
        self.job_id = job_id
        self.options = QueryOptions()
    
    def filter(self, field: str, operator: Union[FilterOperator, str], value: Any) -> 'QueryBuilder':
        """Add a filter condition."""
        # Convert string operator to enum if needed
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        
        self.options.filters.append(Filter(field=field, operator=operator, value=value))
        return self
    
    def sort(self, field: str, order: str = "asc") -> 'QueryBuilder':
        """Set sort field and order."""
        self.options.sort_by = field
        self.options.sort_order = order.lower()
        return self
    
    def paginate(self, limit: Optional[int] = None, offset: int = 0) -> 'QueryBuilder':
        """Set pagination parameters."""
        self.options.limit = limit
        self.options.offset = offset
        return self
    
    def build(self) -> QueryOptions:
        """Build the query options."""
        return self.options 