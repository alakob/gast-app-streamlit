"""Batch processing for AMR Predictor."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from amr_predictor.core.sequence import SequenceSet
from amr_predictor.core.prediction import PredictionEngine
from amr_predictor.processing.sequence_processing import SequenceProcessor, ProcessingConfig
from amr_predictor.api.errors import PredictionError, ProcessingError

class BatchPredictionRequest(BaseModel):
    """Request model for batch prediction."""
    sequence_sets: List[Dict[str, str]] = Field(..., description="List of sequence sets to process")
    batch_size: Optional[int] = Field(default=32, description="Batch size for each set")
    max_workers: Optional[int] = Field(default=4, description="Maximum number of parallel workers")
    model_id: Optional[str] = Field(default="default", description="Model ID to use")

class BatchProcessingRequest(BaseModel):
    """Request model for batch processing."""
    prediction_sets: List[Dict[str, Dict[str, float]]] = Field(..., description="List of prediction sets to process")
    config: Optional[ProcessingConfig] = Field(default=None, description="Processing configuration")
    max_workers: Optional[int] = Field(default=4, description="Maximum number of parallel workers")

class BatchResult(BaseModel):
    """Result model for batch operations."""
    id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    results: Optional[List[Dict[str, Any]]]
    error: Optional[str]

class BatchManager:
    """Manager for batch processing operations."""
    
    _jobs: Dict[str, BatchResult] = {}
    
    @classmethod
    async def create_batch_prediction(cls, request: BatchPredictionRequest) -> BatchResult:
        """Create a new batch prediction job."""
        job_id = f"batch_pred_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        job = BatchResult(
            id=job_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        cls._jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(cls._process_batch_prediction(job_id, request))
        
        return job
    
    @classmethod
    async def create_batch_processing(cls, request: BatchProcessingRequest) -> BatchResult:
        """Create a new batch processing job."""
        job_id = f"batch_proc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        job = BatchResult(
            id=job_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        cls._jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(cls._process_batch_processing(job_id, request))
        
        return job
    
    @classmethod
    async def get_job_status(cls, job_id: str) -> Optional[BatchResult]:
        """Get status of a batch job."""
        return cls._jobs.get(job_id)
    
    @classmethod
    async def _process_batch_prediction(cls, job_id: str, request: BatchPredictionRequest) -> None:
        """Process a batch prediction job."""
        job = cls._jobs[job_id]
        try:
            job.status = "processing"
            
            # Create sequence sets
            sequence_sets = [
                SequenceSet(sequences)
                for sequences in request.sequence_sets
            ]
            
            # Initialize prediction engine
            engine = PredictionEngine()
            
            # Process in parallel
            with ThreadPoolExecutor(max_workers=request.max_workers) as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(
                        executor,
                        engine.predict,
                        seq_set,
                        request.batch_size
                    )
                    for seq_set in sequence_sets
                ]
                results = await asyncio.gather(*tasks)
            
            job.results = results
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            raise PredictionError(
                message="Failed to process batch prediction",
                details={"error": str(e)}
            )
    
    @classmethod
    async def _process_batch_processing(cls, job_id: str, request: BatchProcessingRequest) -> None:
        """Process a batch processing job."""
        job = cls._jobs[job_id]
        try:
            job.status = "processing"
            
            # Initialize processor
            processor = SequenceProcessor(request.config or ProcessingConfig())
            
            # Process in parallel
            with ThreadPoolExecutor(max_workers=request.max_workers) as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(
                        executor,
                        processor.process_predictions,
                        pred_set
                    )
                    for pred_set in request.prediction_sets
                ]
                results = await asyncio.gather(*tasks)
            
            job.results = [result.to_dict() for result in results]
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            raise ProcessingError(
                message="Failed to process batch",
                details={"error": str(e)}
            ) 