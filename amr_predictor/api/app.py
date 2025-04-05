"""FastAPI application for AMR Predictor."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import logging
from typing import Callable
import uuid

from .routes import router
from .errors import (
    AMRException,
    ValidationError,
    PredictionError,
    ProcessingError,
    FileError,
    RateLimitError
)
from .logging import setup_logging, RequestLogger
from .analysis import StatisticsCollector

# Setup logging
logger = setup_logging()
request_logger = RequestLogger()

app = FastAPI(
    title="AMR Predictor API",
    description="API for predicting antimicrobial resistance from DNA sequences",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log request details and track response time."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Log request
    request_logger.log_request(request, request_id)
    
    try:
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Record statistics
        StatisticsCollector.record_request(
            endpoint=request.url.path,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Log response
        request_logger.log_response(response, request_id, response_time)
        
        return response
    
    except Exception as e:
        # Log error
        request_logger.log_error(e, request_id)
        raise

@app.exception_handler(AMRException)
async def amr_exception_handler(request: Request, exc: AMRException) -> JSONResponse:
    """Handle AMR-specific exceptions."""
    logger.error(
        f"AMR Exception: {exc.message}",
        extra={
            "request_id": request.state.request_id,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.error(
        "Validation Error",
        extra={
            "request_id": request.state.request_id,
            "errors": exc.errors()
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "request_id": request.state.request_id,
            "error_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Include API routes
app.include_router(router, prefix="/api/v1") 