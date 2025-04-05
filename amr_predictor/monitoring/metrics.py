#!/usr/bin/env python3
"""
Performance metrics and monitoring for AMR predictor.

This module provides utilities for tracking performance metrics
and monitoring system health for the AMR predictor API.
"""
import time
import logging
import functools
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger("amr-monitoring")


@dataclass
class OperationMetric:
    """Metric for a single database operation."""
    operation_name: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None


class MetricsTracker:
    """
    Tracker for performance metrics.
    
    This class tracks performance metrics for various operations
    and provides methods to retrieve and analyze them.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the metrics tracker.
        
        Args:
            max_history: Maximum number of operations to track
        """
        self.max_history = max_history
        self.metrics: List[OperationMetric] = []
        self.lock = threading.RLock()
    
    def record_operation(self, operation_name: str, duration_ms: float, 
                        success: bool = True, error_message: Optional[str] = None):
        """
        Record an operation metric.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation was successful
            error_message: Optional error message if operation failed
        """
        with self.lock:
            metric = OperationMetric(
                operation_name=operation_name,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            self.metrics.append(metric)
            
            # Trim history if needed
            if len(self.metrics) > self.max_history:
                self.metrics = self.metrics[-self.max_history:]
    
    def get_metrics(self, operation_name: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[OperationMetric]:
        """
        Get metrics, optionally filtered.
        
        Args:
            operation_name: Filter by operation name
            since: Filter to metrics since this time
            
        Returns:
            List of metrics
        """
        with self.lock:
            # Make a copy to avoid threading issues
            metrics = self.metrics.copy()
        
        # Filter by operation name if specified
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        
        # Filter by time if specified
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return metrics
    
    def get_average_duration(self, operation_name: str, 
                            since: Optional[datetime] = None) -> float:
        """
        Get average duration for an operation.
        
        Args:
            operation_name: Operation to get average for
            since: Filter to metrics since this time
            
        Returns:
            Average duration in milliseconds
        """
        metrics = self.get_metrics(operation_name, since)
        
        if not metrics:
            return 0.0
        
        total_duration = sum(m.duration_ms for m in metrics)
        return total_duration / len(metrics)
    
    def get_error_rate(self, operation_name: Optional[str] = None, 
                      since: Optional[datetime] = None) -> float:
        """
        Get error rate for an operation.
        
        Args:
            operation_name: Operation to get error rate for (or all if None)
            since: Filter to metrics since this time
            
        Returns:
            Error rate as a percentage (0-100)
        """
        metrics = self.get_metrics(operation_name, since)
        
        if not metrics:
            return 0.0
        
        error_count = sum(1 for m in metrics if not m.success)
        return (error_count / len(metrics)) * 100.0
    
    def get_operation_counts(self, since: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get counts of each operation.
        
        Args:
            since: Filter to metrics since this time
            
        Returns:
            Dictionary of operation counts
        """
        metrics = self.get_metrics(since=since)
        
        counts = {}
        for metric in metrics:
            counts[metric.operation_name] = counts.get(metric.operation_name, 0) + 1
        
        return counts
    
    def clear_metrics(self):
        """Clear all metrics."""
        with self.lock:
            self.metrics.clear()


# Global metrics tracker instance
_metrics_tracker = MetricsTracker()

def get_metrics_tracker() -> MetricsTracker:
    """
    Get the global metrics tracker instance.
    
    Returns:
        Global metrics tracker
    """
    return _metrics_tracker


def track_operation(operation_name: str):
    """
    Decorator to track an operation's performance.
    
    Args:
        operation_name: Name of the operation to track
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000.0
                
                # Record successful operation
                get_metrics_tracker().record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=True
                )
                
                return result
                
            except Exception as e:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000.0
                
                # Record failed operation
                get_metrics_tracker().record_operation(
                    operation_name=operation_name,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    return decorator


class MetricsReport:
    """
    Generate reports from metrics data.
    
    This class provides methods to generate various reports
    from the metrics data for monitoring and analysis.
    """
    
    @staticmethod
    def generate_performance_report(window_minutes: int = 60) -> Dict[str, Any]:
        """
        Generate a performance report for recent operations.
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            Dictionary with report data
        """
        since = datetime.now() - timedelta(minutes=window_minutes)
        tracker = get_metrics_tracker()
        
        # Get operation counts
        operation_counts = tracker.get_operation_counts(since=since)
        
        # Build report
        report = {
            "window_minutes": window_minutes,
            "report_time": datetime.now(),
            "total_operations": sum(operation_counts.values()),
            "operation_counts": operation_counts,
            "operation_metrics": {},
            "overall_error_rate": tracker.get_error_rate(since=since)
        }
        
        # Add metrics for each operation
        for operation in operation_counts:
            report["operation_metrics"][operation] = {
                "average_duration_ms": tracker.get_average_duration(operation, since),
                "error_rate": tracker.get_error_rate(operation, since),
                "count": operation_counts[operation]
            }
        
        return report
    
    @staticmethod
    def get_slow_operations(threshold_ms: float = 500.0, 
                          window_minutes: int = 60) -> List[OperationMetric]:
        """
        Find slow operations.
        
        Args:
            threshold_ms: Threshold in milliseconds
            window_minutes: Time window in minutes
            
        Returns:
            List of slow operation metrics
        """
        since = datetime.now() - timedelta(minutes=window_minutes)
        tracker = get_metrics_tracker()
        
        metrics = tracker.get_metrics(since=since)
        slow_ops = [m for m in metrics if m.duration_ms > threshold_ms]
        
        # Sort by duration (slowest first)
        return sorted(slow_ops, key=lambda m: m.duration_ms, reverse=True)
    
    @staticmethod
    def get_error_operations(window_minutes: int = 60) -> List[OperationMetric]:
        """
        Find operations that resulted in errors.
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            List of error operation metrics
        """
        since = datetime.now() - timedelta(minutes=window_minutes)
        tracker = get_metrics_tracker()
        
        metrics = tracker.get_metrics(since=since)
        error_ops = [m for m in metrics if not m.success]
        
        # Sort by timestamp (most recent first)
        return sorted(error_ops, key=lambda m: m.timestamp, reverse=True)
