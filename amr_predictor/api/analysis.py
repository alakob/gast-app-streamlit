"""Analysis and statistics for AMR Predictor."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import numpy as np
from datetime import datetime, timedelta
import json
from collections import defaultdict

class AnalysisRequest(BaseModel):
    """Request model for prediction analysis."""
    predictions: Dict[str, Dict[str, float]] = Field(..., description="Predictions to analyze")
    metrics: List[str] = Field(default=["accuracy", "precision", "recall", "f1_score"], description="Metrics to compute")
    thresholds: Optional[Dict[str, float]] = Field(default=None, description="Thresholds for classification")

class AnalysisResult(BaseModel):
    """Result model for prediction analysis."""
    metrics: Dict[str, float]
    distributions: Dict[str, Dict[str, float]]
    correlations: Dict[str, float]
    summary: Dict[str, Any]

class Statistics(BaseModel):
    """Statistics model for API usage."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    requests_by_endpoint: Dict[str, int]
    requests_by_status: Dict[int, int]
    requests_by_hour: Dict[int, int]
    last_updated: datetime

class PredictionAnalyzer:
    """Analyzer for prediction results."""
    
    @staticmethod
    def analyze(request: AnalysisRequest) -> AnalysisResult:
        """Analyze prediction results."""
        # Convert predictions to numpy arrays
        predictions = np.array([
            list(pred.values())
            for pred in request.predictions.values()
        ])
        
        # Calculate metrics
        metrics = {}
        if "accuracy" in request.metrics:
            metrics["accuracy"] = np.mean(predictions > 0.5)
        
        if "precision" in request.metrics:
            true_positives = np.sum(predictions > 0.5)
            false_positives = np.sum((predictions > 0.5) & (predictions < 0.7))
            metrics["precision"] = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        
        if "recall" in request.metrics:
            true_positives = np.sum(predictions > 0.7)
            false_negatives = np.sum((predictions > 0.5) & (predictions < 0.7))
            metrics["recall"] = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        if "f1_score" in request.metrics:
            precision = metrics.get("precision", 0)
            recall = metrics.get("recall", 0)
            metrics["f1_score"] = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Calculate distributions
        distributions = {}
        for antibiotic in request.predictions[list(request.predictions.keys())[0]].keys():
            values = [pred[antibiotic] for pred in request.predictions.values()]
            distributions[antibiotic] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "median": float(np.median(values))
            }
        
        # Calculate correlations
        correlations = {}
        antibiotics = list(request.predictions[list(request.predictions.keys())[0]].keys())
        for i, ab1 in enumerate(antibiotics):
            for ab2 in antibiotics[i+1:]:
                values1 = [pred[ab1] for pred in request.predictions.values()]
                values2 = [pred[ab2] for pred in request.predictions.values()]
                correlations[f"{ab1}_{ab2}"] = float(np.corrcoef(values1, values2)[0, 1])
        
        # Generate summary
        summary = {
            "total_sequences": len(request.predictions),
            "total_antibiotics": len(antibiotics),
            "average_predictions": float(np.mean(predictions)),
            "prediction_range": {
                "min": float(np.min(predictions)),
                "max": float(np.max(predictions))
            }
        }
        
        return AnalysisResult(
            metrics=metrics,
            distributions=distributions,
            correlations=correlations,
            summary=summary
        )

class StatisticsCollector:
    """Collector for API usage statistics."""
    
    _stats = Statistics(
        total_requests=0,
        successful_requests=0,
        failed_requests=0,
        average_response_time=0.0,
        requests_by_endpoint=defaultdict(int),
        requests_by_status=defaultdict(int),
        requests_by_hour=defaultdict(int),
        last_updated=datetime.utcnow()
    )
    
    _response_times: List[float] = []
    
    @classmethod
    def record_request(
        cls,
        endpoint: str,
        status_code: int,
        response_time: float
    ) -> None:
        """Record a request."""
        cls._stats.total_requests += 1
        cls._stats.requests_by_endpoint[endpoint] += 1
        cls._stats.requests_by_status[status_code] += 1
        cls._stats.requests_by_hour[datetime.utcnow().hour] += 1
        
        if 200 <= status_code < 300:
            cls._stats.successful_requests += 1
        else:
            cls._stats.failed_requests += 1
        
        cls._response_times.append(response_time)
        cls._stats.average_response_time = np.mean(cls._response_times)
        cls._stats.last_updated = datetime.utcnow()
    
    @classmethod
    def get_stats(cls) -> Statistics:
        """Get current statistics."""
        return cls._stats
    
    @classmethod
    def reset_stats(cls) -> None:
        """Reset statistics."""
        cls._stats = Statistics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_response_time=0.0,
            requests_by_endpoint=defaultdict(int),
            requests_by_status=defaultdict(int),
            requests_by_hour=defaultdict(int),
            last_updated=datetime.utcnow()
        )
        cls._response_times = [] 