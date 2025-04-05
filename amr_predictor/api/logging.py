"""Logging configuration for AMR Predictor API."""

import logging
import logging.handlers
import json
import time
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """Formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("amr_predictor")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatters
    json_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if log directory is specified
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "amr_predictor.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    
    return logger

class RequestLogger:
    """Logger for request/response logging."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(
        self,
        request_id: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None
    ) -> None:
        """Log request details."""
        self.logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "type": "request",
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "client_ip": client_ip
            }
        )
    
    def log_response(
        self,
        request_id: str,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
        duration: float = 0.0
    ) -> None:
        """Log response details."""
        self.logger.info(
            "Outgoing response",
            extra={
                "request_id": request_id,
                "type": "response",
                "status_code": status_code,
                "headers": headers,
                "body": body,
                "duration": duration
            }
        )
    
    def log_error(
        self,
        request_id: str,
        error: Exception,
        status_code: int = 500,
        duration: float = 0.0
    ) -> None:
        """Log error details."""
        error_details = {
            "type": error.__class__.__name__,
            "message": str(error),
            "status_code": status_code
        }
        
        if hasattr(error, "details"):
            error_details["details"] = error.details
        
        self.logger.error(
            "Request error",
            extra={
                "request_id": request_id,
                "type": "error",
                "error": error_details,
                "duration": duration
            },
            exc_info=True
        ) 