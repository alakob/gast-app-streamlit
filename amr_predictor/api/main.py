#!/usr/bin/env python3
"""
Main API entrypoint for the AMR Predictor application.

This module integrates all API components and starts the FastAPI application.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from amr_predictor.api.amr_db_integration import router as amr_router
from amr_predictor.auth.api import router as auth_router
from amr_predictor.monitoring.api import router as monitoring_router
from amr_predictor.maintenance.scheduled_tasks import start_scheduled_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("amr-api")

# Initialize FastAPI app
app = FastAPI(
    title="AMR Predictor API",
    description="API for AMR Prediction and Analysis",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(amr_router)
app.include_router(monitoring_router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting AMR Predictor API")
    
    # Start scheduled maintenance tasks
    start_scheduled_tasks()


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down AMR Predictor API")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint, provides basic information."""
    return {
        "message": "Welcome to the AMR Predictor API",
        "version": app.version,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api_version": app.version,
    }
