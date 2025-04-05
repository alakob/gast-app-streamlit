#!/usr/bin/env python3
"""
API routes for monitoring and metrics.

This module provides FastAPI routes for displaying monitoring data
and system health information.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query

from amr_predictor.auth.user_manager import UserManager
from amr_predictor.auth.models import User
from amr_predictor.auth.dependencies import get_current_user
from amr_predictor.monitoring.metrics import get_metrics_tracker, MetricsReport
from amr_predictor.bakta.database_manager_optimized import OptimizedDatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO

# Configure logging
logger = logging.getLogger("amr-monitoring")

# Create router
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics/summary")
async def get_metrics_summary(
    window_minutes: int = Query(60, description="Time window in minutes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a summary of system metrics.
    
    Args:
        window_minutes: Time window in minutes
        current_user: Current authenticated user
        
    Returns:
        Dictionary with metrics summary
    """
    # Check if user has admin permissions (extend as needed)
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view metrics"
        )
    
    # Generate report
    report = MetricsReport.generate_performance_report(window_minutes)
    return report


@router.get("/metrics/slow-operations")
async def get_slow_operations(
    threshold_ms: float = Query(500.0, description="Threshold in milliseconds"),
    window_minutes: int = Query(60, description="Time window in minutes"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get list of slow operations.
    
    Args:
        threshold_ms: Threshold in milliseconds
        window_minutes: Time window in minutes
        current_user: Current authenticated user
        
    Returns:
        List of slow operations
    """
    # Check if user has admin permissions
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view metrics"
        )
    
    # Get slow operations
    slow_ops = MetricsReport.get_slow_operations(threshold_ms, window_minutes)
    
    # Convert to dict for JSON response
    return [
        {
            "operation_name": op.operation_name,
            "duration_ms": op.duration_ms,
            "timestamp": op.timestamp.isoformat(),
            "success": op.success,
            "error_message": op.error_message
        }
        for op in slow_ops
    ]


@router.get("/metrics/errors")
async def get_error_operations(
    window_minutes: int = Query(60, description="Time window in minutes"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get list of operations that resulted in errors.
    
    Args:
        window_minutes: Time window in minutes
        current_user: Current authenticated user
        
    Returns:
        List of error operations
    """
    # Check if user has admin permissions
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view metrics"
        )
    
    # Get error operations
    error_ops = MetricsReport.get_error_operations(window_minutes)
    
    # Convert to dict for JSON response
    return [
        {
            "operation_name": op.operation_name,
            "duration_ms": op.duration_ms,
            "timestamp": op.timestamp.isoformat(),
            "error_message": op.error_message
        }
        for op in error_ops
    ]


@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get overall system status.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dictionary with system status
    """
    # Check if user has admin permissions
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view system status"
        )
    
    # Get database manager for status checks
    db_manager = OptimizedDatabaseManager()
    job_dao = AMRJobDAO(db_manager)
    
    # Get job counts
    total_jobs = job_dao.count_all()
    running_jobs = job_dao.count_by_status("Running")
    completed_jobs = job_dao.count_by_status("Completed")
    error_jobs = job_dao.count_by_status("Error")
    
    # Get recent error rate
    metrics_tracker = get_metrics_tracker()
    recent_error_rate = metrics_tracker.get_error_rate(
        since=datetime.now() - timedelta(minutes=60)
    )
    
    # Build status response
    status = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy" if recent_error_rate < 5.0 else "degraded",
        "database": {
            "connection_pool": {
                "size": len(db_manager._connection_pool.pool) if hasattr(db_manager, "_connection_pool") else "N/A",
                "in_use": len(db_manager._connection_pool.in_use) if hasattr(db_manager, "_connection_pool") else "N/A"
            }
        },
        "jobs": {
            "total": total_jobs,
            "running": running_jobs,
            "completed": completed_jobs,
            "error": error_jobs,
        },
        "performance": {
            "recent_error_rate": recent_error_rate,
            "avg_job_save_time": metrics_tracker.get_average_duration("save_job", 
                                since=datetime.now() - timedelta(hours=24))
        }
    }
    
    return status


@router.get("/jobs/status-summary")
async def get_job_status_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get summary of job statuses.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dictionary with job status summary
    """
    # Get database manager
    db_manager = OptimizedDatabaseManager()
    job_dao = AMRJobDAO(db_manager)
    
    # Get counts by status
    statuses = ["Submitted", "Running", "Completed", "Error", "Archived"]
    counts = {status: job_dao.count_by_status(status) for status in statuses}
    
    # Get user's jobs if not admin
    is_admin = hasattr(current_user, "is_admin") and current_user.is_admin
    
    if not is_admin:
        # Get only the current user's jobs
        user_counts = {
            status: job_dao.count_by_status_and_user(status, current_user.username)
            for status in statuses
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "all_jobs": counts if is_admin else None,
            "user_jobs": user_counts
        }
    else:
        return {
            "timestamp": datetime.now().isoformat(),
            "all_jobs": counts,
            "user_jobs": None
        }
