"""WebSocket support for AMR Predictor."""

from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime
import asyncio
from .jobs import Job, JobStatus

class WebSocketManager:
    """Manager for WebSocket connections."""
    
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._job_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Connect a new WebSocket client."""
        await websocket.accept()
        if client_id not in self._connections:
            self._connections[client_id] = set()
        self._connections[client_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Disconnect a WebSocket client."""
        if client_id in self._connections:
            self._connections[client_id].remove(websocket)
            if not self._connections[client_id]:
                del self._connections[client_id]
    
    async def subscribe_to_job(self, client_id: str, job_id: str) -> None:
        """Subscribe a client to job updates."""
        if job_id not in self._job_subscriptions:
            self._job_subscriptions[job_id] = set()
        self._job_subscriptions[job_id].add(client_id)
    
    async def unsubscribe_from_job(self, client_id: str, job_id: str) -> None:
        """Unsubscribe a client from job updates."""
        if job_id in self._job_subscriptions:
            self._job_subscriptions[job_id].discard(client_id)
            if not self._job_subscriptions[job_id]:
                del self._job_subscriptions[job_id]
    
    async def broadcast_job_update(self, job: Job) -> None:
        """Broadcast job update to subscribed clients."""
        if job.id not in self._job_subscriptions:
            return
        
        message = {
            "type": "job_update",
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "result": job.result,
            "error": job.error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for client_id in self._job_subscriptions[job.id]:
            if client_id in self._connections:
                for websocket in self._connections[client_id]:
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        # Remove failed connection
                        await self.disconnect(websocket, client_id)

class WebSocketHandler:
    """Handler for WebSocket connections."""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
    
    async def handle_connection(self, websocket: WebSocket, client_id: str) -> None:
        """Handle a WebSocket connection."""
        await self.manager.connect(websocket, client_id)
        
        try:
            while True:
                message = await websocket.receive_json()
                await self._handle_message(websocket, client_id, message)
        
        except WebSocketDisconnect:
            await self.manager.disconnect(websocket, client_id)
        
        except Exception as e:
            # Log error and disconnect
            print(f"WebSocket error: {str(e)}")
            await self.manager.disconnect(websocket, client_id)
    
    async def _handle_message(self, websocket: WebSocket, client_id: str, message: dict) -> None:
        """Handle a WebSocket message."""
        message_type = message.get("type")
        
        if message_type == "subscribe":
            job_id = message.get("job_id")
            if job_id:
                await self.manager.subscribe_to_job(client_id, job_id)
                await websocket.send_json({
                    "type": "subscribed",
                    "job_id": job_id
                })
        
        elif message_type == "unsubscribe":
            job_id = message.get("job_id")
            if job_id:
                await self.manager.unsubscribe_from_job(client_id, job_id)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "job_id": job_id
                })
        
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }) 