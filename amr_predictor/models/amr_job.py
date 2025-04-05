#!/usr/bin/env python3
"""
AMR Job models for database interactions.

This module defines models for AMR prediction jobs and their parameters.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel


class AMRJobStatus(str, Enum):
    """Status values for AMR prediction jobs"""
    SUBMITTED = "Submitted"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    ERROR = "Error"
    ARCHIVED = "Archived"
    CANCELLED = "Cancelled"


class AMRJobParams(BaseModel):
    """Parameters for an AMR prediction job"""
    model_name: str
    batch_size: int
    segment_length: int
    segment_overlap: int
    use_cpu: bool = False
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "AMRJobParams":
        """Create an instance from a database row"""
        return cls(
            model_name=row["model_name"],
            batch_size=row["batch_size"],
            segment_length=row["segment_length"],
            segment_overlap=row["segment_overlap"],
            use_cpu=bool(row["use_cpu"])
        )

class AMRJob(BaseModel):
    """Model representing an AMR prediction job"""
    id: str
    user_id: Optional[str] = None
    job_name: str
    status: str
    progress: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    input_file_path: Optional[str] = None
    result_file_path: Optional[str] = None
    params: Optional[AMRJobParams] = None
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "AMRJob":
        """Create an instance from a database row"""
        return cls(
            id=row["id"],
            user_id=row.get("user_id"),
            job_name=row["job_name"],
            status=row["status"],
            progress=row.get("progress", 0.0),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            error=row.get("error"),
            input_file_path=row.get("input_file_path"),
            result_file_path=row.get("result_file_path")
        )
