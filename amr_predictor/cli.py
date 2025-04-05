"""Command-line interface for AMR Predictor."""

import click
import json
import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import Dict, List, Optional
import websockets
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = "http://localhost:8000/api/v1"
WS_BASE_URL = "ws://localhost:8000/api/v1/ws"

class APIClient:
    """Client for interacting with the AMR Predictor API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an HTTP request to the API."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                error_data = await response.json()
                raise click.ClickException(f"API Error: {error_data.get('error', 'Unknown error')}")
            return await response.json()

class WebSocketClient:
    """Client for WebSocket connections."""
    
    def __init__(self, base_url: str = WS_BASE_URL):
        self.base_url = base_url
        self.websocket = None
    
    async def connect(self, client_id: str):
        """Connect to the WebSocket server."""
        self.websocket = await websockets.connect(f"{self.base_url}/{client_id}")
    
    async def subscribe(self, job_id: str):
        """Subscribe to job updates."""
        await self.websocket.send(json.dumps({
            "type": "subscribe",
            "job_id": job_id
        }))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def receive_update(self):
        """Receive a job update."""
        message = await self.websocket.recv()
        return json.loads(message)
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()

@click.group()
def cli():
    """AMR Predictor CLI - Command-line interface for AMR prediction."""
    pass

@cli.group()
def models():
    """Manage AMR prediction models."""
    pass

@models.command()
async def list():
    """List available AMR prediction models."""
    async with APIClient() as client:
        models = await client._request("GET", "models")
        for model in models:
            click.echo(f"\nModel: {model['name']} (ID: {model['id']})")
            click.echo(f"Version: {model['version']}")
            click.echo(f"Description: {model['description']}")
            click.echo("Supported Antibiotics:")
            for ab in model['supported_antibiotics']:
                click.echo(f"  - {ab}")
            click.echo("Performance Metrics:")
            for metric, value in model['performance_metrics'].items():
                click.echo(f"  - {metric}: {value:.2f}")

@models.command()
@click.argument('model_id')
async def info(model_id: str):
    """Get information about a specific model."""
    async with APIClient() as client:
        model = await client._request("GET", f"models/{model_id}")
        click.echo(f"\nModel: {model['name']} (ID: {model['id']})")
        click.echo(f"Version: {model['version']}")
        click.echo(f"Description: {model['description']}")
        click.echo("Supported Antibiotics:")
        for ab in model['supported_antibiotics']:
            click.echo(f"  - {ab}")
        click.echo("Performance Metrics:")
        for metric, value in model['performance_metrics'].items():
            click.echo(f"  - {metric}: {value:.2f}")
        click.echo("\nRequirements:")
        for req, version in model['requirements'].items():
            click.echo(f"  - {req}: {version}")

@cli.group()
def predict():
    """Predict AMR from sequences."""
    pass

@predict.command()
@click.argument('sequences_file', type=click.Path(exists=True))
@click.option('--model-id', default='default', help='Model ID to use')
async def from_file(sequences_file: str, model_id: str):
    """Predict AMR from sequences in a file."""
    async with APIClient() as client:
        # Read sequences from file
        with open(sequences_file) as f:
            sequences = json.load(f)
        
        # Create prediction job
        response = await client._request("POST", "predict", json=sequences)
        job_id = response['job_id']
        
        click.echo(f"Created prediction job: {job_id}")
        click.echo("Monitoring job progress...")
        
        # Monitor job progress
        ws_client = WebSocketClient()
        await ws_client.connect("cli_client")
        await ws_client.subscribe(job_id)
        
        try:
            while True:
                update = await ws_client.receive_update()
                if update['type'] == 'job_update':
                    click.echo(f"Progress: {update['progress']*100:.1f}%")
                    if update['status'] in ['completed', 'failed', 'cancelled']:
                        if update['status'] == 'completed':
                            click.echo("\nPrediction completed successfully!")
                            click.echo(json.dumps(update['result'], indent=2))
                        else:
                            click.echo(f"\nJob {update['status']}: {update.get('error', 'No error message')}")
                        break
        finally:
            await ws_client.close()

@cli.group()
def batch():
    """Batch processing operations."""
    pass

@batch.command()
@click.argument('sequences_file', type=click.Path(exists=True))
@click.option('--batch-size', default=32, help='Batch size for processing')
@click.option('--max-workers', default=4, help='Maximum number of parallel workers')
@click.option('--model-id', default='default', help='Model ID to use')
async def predict(sequences_file: str, batch_size: int, max_workers: int, model_id: str):
    """Process multiple sequence sets in parallel."""
    async with APIClient() as client:
        # Read sequences from file
        with open(sequences_file) as f:
            sequence_sets = json.load(f)
        
        # Create batch prediction job
        request = {
            "sequence_sets": sequence_sets,
            "batch_size": batch_size,
            "max_workers": max_workers,
            "model_id": model_id
        }
        
        response = await client._request("POST", "batch/predict", json=request)
        job_id = response['job_id']
        
        click.echo(f"Created batch prediction job: {job_id}")
        click.echo("Monitoring job progress...")
        
        # Monitor job progress
        ws_client = WebSocketClient()
        await ws_client.connect("cli_client")
        await ws_client.subscribe(job_id)
        
        try:
            while True:
                update = await ws_client.receive_update()
                if update['type'] == 'job_update':
                    click.echo(f"Progress: {update['progress']*100:.1f}%")
                    if update['status'] in ['completed', 'failed', 'cancelled']:
                        if update['status'] == 'completed':
                            click.echo("\nBatch prediction completed successfully!")
                            click.echo(json.dumps(update['result'], indent=2))
                        else:
                            click.echo(f"\nJob {update['status']}: {update.get('error', 'No error message')}")
                        break
        finally:
            await ws_client.close()

@cli.group()
def analyze():
    """Analysis operations."""
    pass

@analyze.command()
@click.argument('predictions_file', type=click.Path(exists=True))
@click.option('--metrics', multiple=True, help='Metrics to compute')
async def predictions(predictions_file: str, metrics: List[str]):
    """Analyze prediction results."""
    async with APIClient() as client:
        # Read predictions from file
        with open(predictions_file) as f:
            predictions = json.load(f)
        
        # Create analysis request
        request = {
            "predictions": predictions,
            "metrics": list(metrics) if metrics else ["accuracy", "precision", "recall", "f1_score"]
        }
        
        result = await client._request("POST", "analyze", json=request)
        
        click.echo("\nAnalysis Results:")
        click.echo("\nMetrics:")
        for metric, value in result['metrics'].items():
            click.echo(f"  - {metric}: {value:.4f}")
        
        click.echo("\nDistributions:")
        for ab, stats in result['distributions'].items():
            click.echo(f"\n  {ab}:")
            for stat, value in stats.items():
                click.echo(f"    - {stat}: {value:.4f}")
        
        click.echo("\nCorrelations:")
        for corr, value in result['correlations'].items():
            click.echo(f"  - {corr}: {value:.4f}")
        
        click.echo("\nSummary:")
        for key, value in result['summary'].items():
            click.echo(f"  - {key}: {value}")

@cli.group()
def jobs():
    """Job management operations."""
    pass

@jobs.command()
@click.argument('job_id')
async def status(job_id: str):
    """Get the status of a job."""
    async with APIClient() as client:
        job = await client._request("GET", f"jobs/{job_id}")
        click.echo(f"\nJob: {job['id']}")
        click.echo(f"Type: {job['job_type']}")
        click.echo(f"Status: {job['status']}")
        click.echo(f"Progress: {job['progress']*100:.1f}%")
        click.echo(f"Created: {job['created_at']}")
        if job['started_at']:
            click.echo(f"Started: {job['started_at']}")
        if job['completed_at']:
            click.echo(f"Completed: {job['completed_at']}")
        if job['error']:
            click.echo(f"Error: {job['error']}")
        if job['result']:
            click.echo("\nResult:")
            click.echo(json.dumps(job['result'], indent=2))

@jobs.command()
@click.option('--status', help='Filter by status')
@click.option('--type', help='Filter by job type')
@click.option('--limit', default=10, help='Maximum number of jobs to show')
async def list(status: Optional[str], type: Optional[str], limit: int):
    """List jobs with optional filtering."""
    async with APIClient() as client:
        params = {'limit': limit}
        if status:
            params['status'] = status
        if type:
            params['job_type'] = type
        
        jobs = await client._request("GET", "jobs", params=params)
        
        for job in jobs:
            click.echo(f"\nJob: {job['id']}")
            click.echo(f"Type: {job['job_type']}")
            click.echo(f"Status: {job['status']}")
            click.echo(f"Progress: {job['progress']*100:.1f}%")
            click.echo(f"Created: {job['created_at']}")
            if job['completed_at']:
                click.echo(f"Completed: {job['completed_at']}")

@jobs.command()
@click.argument('job_id')
async def cancel(job_id: str):
    """Cancel a job."""
    async with APIClient() as client:
        response = await client._request("POST", f"jobs/{job_id}/cancel")
        click.echo(response['message'])

def main():
    """Entry point for the CLI."""
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 