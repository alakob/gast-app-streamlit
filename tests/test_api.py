"""Tests for AMR Predictor API."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
from datetime import datetime
import asyncio
from typing import Dict, List

from amr_predictor.api.app import app
from amr_predictor.api.models import ModelInfo
from amr_predictor.api.jobs import JobStatus, JobType
from amr_predictor.api.analysis import AnalysisResult

client = TestClient(app)

# Test Data
TEST_SEQUENCES = {
    "seq1": "ATCGATCGATCG",
    "seq2": "GCTAGCTAGCTA"
}

TEST_PREDICTIONS = {
    "seq1": {"antibiotic1": 0.8, "antibiotic2": 0.3},
    "seq2": {"antibiotic1": 0.2, "antibiotic2": 0.7}
}

# Model Management Tests
def test_list_models():
    """Test listing available models."""
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert all(isinstance(model, dict) for model in models)
    assert all("id" in model for model in models)

def test_get_model():
    """Test getting a specific model."""
    response = client.get("/api/v1/models/default")
    assert response.status_code == 200
    model = response.json()
    assert isinstance(model, dict)
    assert model["id"] == "default"
    assert "name" in model
    assert "version" in model

def test_get_nonexistent_model():
    """Test getting a nonexistent model."""
    response = client.get("/api/v1/models/nonexistent")
    assert response.status_code == 404

# Batch Processing Tests
def test_batch_predict():
    """Test batch prediction endpoint."""
    request = {
        "sequence_sets": [TEST_SEQUENCES],
        "batch_size": 2,
        "max_workers": 1
    }
    response = client.post("/api/v1/batch/predict", json=request)
    assert response.status_code == 200
    result = response.json()
    assert "job_id" in result
    assert isinstance(result["job_id"], str)

def test_batch_process():
    """Test batch processing endpoint."""
    request = {
        "prediction_sets": [TEST_PREDICTIONS],
        "config": {
            "confidence_threshold": 0.5,
            "prediction_threshold": 0.5
        },
        "max_workers": 1
    }
    response = client.post("/api/v1/batch/process", json=request)
    assert response.status_code == 200
    result = response.json()
    assert "job_id" in result
    assert isinstance(result["job_id"], str)

# Analysis Tests
def test_analyze_predictions():
    """Test prediction analysis endpoint."""
    request = {
        "predictions": TEST_PREDICTIONS,
        "metrics": ["accuracy", "precision", "recall", "f1_score"]
    }
    response = client.post("/api/v1/analyze", json=request)
    assert response.status_code == 200
    result = response.json()
    assert "metrics" in result
    assert "distributions" in result
    assert "correlations" in result
    assert "summary" in result

# Job Management Tests
def test_create_job():
    """Test job creation endpoint."""
    request = {
        "job_type": JobType.PREDICTION,
        "parameters": {"sequences": TEST_SEQUENCES},
        "priority": 1,
        "timeout": 3600
    }
    response = client.post("/api/v1/jobs", json=request)
    assert response.status_code == 200
    job = response.json()
    assert job["job_type"] == JobType.PREDICTION
    assert job["status"] == JobStatus.PENDING
    assert "id" in job
    assert "created_at" in job

def test_get_job():
    """Test getting job status endpoint."""
    # First create a job
    request = {
        "job_type": JobType.PREDICTION,
        "parameters": {"sequences": TEST_SEQUENCES},
        "priority": 1
    }
    create_response = client.post("/api/v1/jobs", json=request)
    job_id = create_response.json()["id"]
    
    # Then get its status
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    job = response.json()
    assert job["id"] == job_id
    assert "status" in job
    assert "progress" in job

def test_list_jobs():
    """Test listing jobs endpoint."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert all(isinstance(job, dict) for job in jobs)
    assert all("id" in job for job in jobs)
    assert all("status" in job for job in jobs)

def test_cancel_job():
    """Test job cancellation endpoint."""
    # First create a job
    request = {
        "job_type": JobType.PREDICTION,
        "parameters": {"sequences": TEST_SEQUENCES},
        "priority": 1
    }
    create_response = client.post("/api/v1/jobs", json=request)
    job_id = create_response.json()["id"]
    
    # Then cancel it
    response = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Job cancelled successfully"

# WebSocket Tests
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection and job updates."""
    client_id = "test_client"
    
    # Create a WebSocket connection
    with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
        # Create a job
        request = {
            "job_type": JobType.PREDICTION,
            "parameters": {"sequences": TEST_SEQUENCES},
            "priority": 1
        }
        create_response = client.post("/api/v1/jobs", json=request)
        job_id = create_response.json()["id"]
        
        # Subscribe to job updates
        websocket.send_json({
            "type": "subscribe",
            "job_id": job_id
        })
        
        # Receive subscription confirmation
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert response["job_id"] == job_id
        
        # Wait for job updates
        for _ in range(3):  # Expect at least 3 updates
            update = websocket.receive_json()
            assert update["type"] == "job_update"
            assert update["job_id"] == job_id
            assert "status" in update
            assert "progress" in update
        
        # Unsubscribe from job updates
        websocket.send_json({
            "type": "unsubscribe",
            "job_id": job_id
        })
        
        # Receive unsubscription confirmation
        response = websocket.receive_json()
        assert response["type"] == "unsubscribed"
        assert response["job_id"] == job_id

# Existing Endpoint Tests
def test_predict_sequences():
    """Test sequence prediction endpoint."""
    response = client.post("/api/v1/predict", json=TEST_SEQUENCES)
    assert response.status_code == 200
    result = response.json()
    assert "job_id" in result
    assert isinstance(result["job_id"], str)

def test_aggregate_predictions():
    """Test prediction aggregation endpoint."""
    request = {
        "predictions": [TEST_PREDICTIONS]
    }
    response = client.post("/api/v1/aggregate", json=request)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, dict)
    assert all(isinstance(v, float) for v in result.values())

def test_process_predictions():
    """Test prediction processing endpoint."""
    response = client.post("/api/v1/process", json=TEST_PREDICTIONS)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, dict)
    assert all(isinstance(v, float) for v in result.values())

def test_visualize_predictions():
    """Test prediction visualization endpoint."""
    response = client.post("/api/v1/visualize", json=TEST_PREDICTIONS)
    assert response.status_code == 200
    result = response.json()
    assert "visualization" in result
    assert "format" in result

def test_upload_sequences():
    """Test sequence upload endpoint."""
    # Create a test FASTA file content
    fasta_content = b">seq1\nATCGATCGATCG\n>seq2\nGCTAGCTAGCTA"
    
    response = client.post("/api/v1/upload", content=fasta_content)
    assert response.status_code == 200
    result = response.json()
    assert "sequences" in result
    assert isinstance(result["sequences"], dict)
    assert all(isinstance(v, str) for v in result["sequences"].values())

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_predict_sequences_invalid():
    """Test sequence prediction with invalid input."""
    response = client.post(
        "/api/v1/predict",
        json={
            "sequences": {"seq1": "invalid_sequence"},  # Invalid DNA sequence
            "batch_size": 32,
            "confidence_threshold": 0.5
        }
    )
    assert response.status_code == 500

def test_validation_error():
    """Test request validation error handling."""
    response = client.post(
        "/api/v1/predict",
        json={
            "sequences": {},  # Empty sequences
            "batch_size": -1,  # Invalid batch size
            "confidence_threshold": 1.5  # Invalid threshold
        }
    )
    assert response.status_code == 422
    error = response.json()
    assert "detail" in error
    assert "message" in error
    assert error["message"] == "Validation error in request data"

def test_api_documentation():
    """Test API documentation endpoints."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"] 