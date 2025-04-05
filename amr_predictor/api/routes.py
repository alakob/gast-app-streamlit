"""API routes for AMR Predictor."""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime

from amr_predictor.core.sequence import SequenceSet
from amr_predictor.core.prediction import PredictionEngine
from amr_predictor.processing.aggregation import PredictionAggregator, AggregationMethod
from amr_predictor.processing.sequence_processing import SequenceProcessor, ProcessingConfig
from amr_predictor.processing.visualization import VisualizationEngine, VisualizationConfig, VisualizationFormat
from amr_predictor.api.errors import (
    SequenceError,
    PredictionError,
    ProcessingError,
    FileError,
    ValidationError
)
from .models import ModelRegistry, ModelInfo
from .batch import BatchManager, BatchPredictionRequest, BatchProcessingRequest
from .analysis import PredictionAnalyzer, AnalysisRequest
from .jobs import JobManager, JobRequest, Job, JobStatus, JobType
from .websocket import WebSocketManager, WebSocketHandler

router = APIRouter()

# Initialize managers
model_registry = ModelRegistry()
batch_manager = BatchManager()
job_manager = JobManager()
websocket_manager = WebSocketManager()
websocket_handler = WebSocketHandler(websocket_manager)

# Model Management Routes
@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List available AMR prediction models."""
    return model_registry.list_models()

@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get information about a specific model."""
    model = model_registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model

# Batch Processing Routes
@router.post("/batch/predict")
async def batch_predict(request: BatchPredictionRequest, background_tasks: BackgroundTasks):
    """Process multiple sequence sets in parallel."""
    try:
        job = await job_manager.create_job(JobRequest(
            job_type=JobType.PREDICTION,
            parameters=request.dict(),
            priority=1
        ))
        background_tasks.add_task(job_manager.process_job, job.id)
        return {"job_id": job.id}
    except Exception as e:
        raise PredictionError(f"Failed to create batch prediction job: {str(e)}")

@router.post("/batch/process")
async def batch_process(request: BatchProcessingRequest, background_tasks: BackgroundTasks):
    """Process multiple prediction sets in parallel."""
    try:
        job = await job_manager.create_job(JobRequest(
            job_type=JobType.PROCESSING,
            parameters=request.dict(),
            priority=1
        ))
        background_tasks.add_task(job_manager.process_job, job.id)
        return {"job_id": job.id}
    except Exception as e:
        raise ProcessingError(f"Failed to create batch processing job: {str(e)}")

# Analysis Routes
@router.post("/analyze")
async def analyze_predictions(request: AnalysisRequest):
    """Perform statistical analysis on predictions."""
    try:
        analyzer = PredictionAnalyzer()
        result = analyzer.analyze(request)
        return result
    except Exception as e:
        raise ValidationError(f"Failed to analyze predictions: {str(e)}")

# Job Management Routes
@router.post("/jobs", response_model=Job)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Create a new prediction job."""
    try:
        job = await job_manager.create_job(request)
        background_tasks.add_task(job_manager.process_job, job.id)
        return job
    except Exception as e:
        raise ValidationError(f"Failed to create job: {str(e)}")

@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """Get the status of a prediction job."""
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs", response_model=List[Job])
async def list_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = 100,
    offset: int = 0
):
    """List jobs with optional filtering."""
    return await job_manager.list_jobs(status, job_type, limit, offset)

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a prediction job."""
    success = await job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"message": "Job cancelled successfully"}

# WebSocket Route
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time job updates."""
    await websocket_handler.handle_connection(websocket, client_id)

# Existing Routes
@router.post("/predict")
async def predict_sequences(request: Dict[str, str], background_tasks: BackgroundTasks):
    """Predict AMR for a set of sequences."""
    try:
        job = await job_manager.create_job(JobRequest(
            job_type=JobType.PREDICTION,
            parameters={"sequences": request},
            priority=2
        ))
        background_tasks.add_task(job_manager.process_job, job.id)
        return {"job_id": job.id}
    except Exception as e:
        raise PredictionError(f"Failed to create prediction job: {str(e)}")

@router.post("/aggregate")
async def aggregate_predictions(request: Dict[str, List[Dict[str, float]]]):
    """Aggregate multiple prediction results."""
    try:
        result = await batch_manager.aggregate_predictions(request)
        return result
    except Exception as e:
        raise ProcessingError(f"Failed to aggregate predictions: {str(e)}")

@router.post("/process")
async def process_predictions(request: Dict[str, Dict[str, float]]):
    """Process prediction results."""
    try:
        result = await batch_manager.process_predictions(request)
        return result
    except Exception as e:
        raise ProcessingError(f"Failed to process predictions: {str(e)}")

@router.post("/visualize")
async def visualize_predictions(request: Dict[str, Dict[str, float]]):
    """Generate visualizations for prediction results."""
    try:
        result = await batch_manager.visualize_predictions(request)
        return result
    except Exception as e:
        raise ProcessingError(f"Failed to visualize predictions: {str(e)}")

@router.post("/upload")
async def upload_sequences(file: bytes):
    """Upload sequences from a file."""
    try:
        sequences = await batch_manager.parse_sequences(file)
        return {"sequences": sequences}
    except Exception as e:
        raise FileError(f"Failed to upload sequences: {str(e)}") 