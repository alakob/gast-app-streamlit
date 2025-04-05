"""Custom error types and error handling utilities."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """Standard error response model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class AMRException(HTTPException):
    """Base exception for AMR Predictor errors."""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code)
        self.code = code
        self.message = message
        self.details = details

    def to_response(self) -> ErrorResponse:
        """Convert exception to standard error response."""
        return ErrorResponse(
            code=self.code,
            message=self.message,
            details=self.details
        )

class ValidationError(AMRException):
    """Exception for validation errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details
        )

class SequenceError(AMRException):
    """Exception for sequence-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SEQUENCE_ERROR",
            message=message,
            details=details
        )

class PredictionError(AMRException):
    """Exception for prediction-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PREDICTION_ERROR",
            message=message,
            details=details
        )

class ProcessingError(AMRException):
    """Exception for processing-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PROCESSING_ERROR",
            message=message,
            details=details
        )

class FileError(AMRException):
    """Exception for file-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FILE_ERROR",
            message=message,
            details=details
        )

class ResourceNotFoundError(AMRException):
    """Exception for resource not found errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message=message,
            details=details
        )

class RateLimitError(AMRException):
    """Exception for rate limit errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_ERROR",
            message=message,
            details=details
        ) 