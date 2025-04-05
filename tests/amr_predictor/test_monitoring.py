"""Tests for the AMR Monitoring System."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from amr_predictor.monitoring.metrics import (
    MetricsTracker, 
    OperationMetric, 
    track_operation,
    get_metrics_tracker,
    MetricsReport
)


def test_metrics_tracker_init():
    """Test initializing a metrics tracker."""
    tracker = MetricsTracker(max_history=100)
    assert tracker.max_history == 100
    assert len(tracker.metrics) == 0


def test_record_operation():
    """Test recording an operation metric."""
    tracker = MetricsTracker(max_history=5)
    
    # Record a successful operation
    tracker.record_operation(
        operation_name="test_op",
        duration_ms=10.5,
        success=True
    )
    
    # Verify the metric was recorded
    assert len(tracker.metrics) == 1
    metric = tracker.metrics[0]
    assert metric.operation_name == "test_op"
    assert metric.duration_ms == 10.5
    assert metric.success is True
    assert metric.error_message is None
    
    # Record a failed operation
    tracker.record_operation(
        operation_name="test_op",
        duration_ms=15.0,
        success=False,
        error_message="Test error"
    )
    
    # Verify the metric was recorded
    assert len(tracker.metrics) == 2
    metric = tracker.metrics[1]
    assert metric.operation_name == "test_op"
    assert metric.duration_ms == 15.0
    assert metric.success is False
    assert metric.error_message == "Test error"


def test_max_history():
    """Test that max history is respected."""
    tracker = MetricsTracker(max_history=3)
    
    # Record more operations than max history
    for i in range(5):
        tracker.record_operation(
            operation_name=f"op_{i}",
            duration_ms=i * 10.0
        )
    
    # Verify only the most recent operations are kept
    assert len(tracker.metrics) == 3
    assert tracker.metrics[0].operation_name == "op_2"
    assert tracker.metrics[1].operation_name == "op_3"
    assert tracker.metrics[2].operation_name == "op_4"


def test_get_metrics_filtered():
    """Test getting metrics with filters."""
    tracker = MetricsTracker()
    
    # Record operations with different names and times
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)
    
    with patch('datetime.datetime') as mock_datetime:
        # Two hours ago
        mock_datetime.now.return_value = two_hours_ago
        tracker.record_operation("op_a", 10.0)
        
        # One hour ago
        mock_datetime.now.return_value = one_hour_ago
        tracker.record_operation("op_b", 20.0)
        tracker.record_operation("op_a", 30.0)
        
        # Now
        mock_datetime.now.return_value = now
        tracker.record_operation("op_b", 40.0)
    
    # Filter by operation name
    op_a_metrics = tracker.get_metrics(operation_name="op_a")
    assert len(op_a_metrics) == 2
    assert op_a_metrics[0].duration_ms == 10.0
    assert op_a_metrics[1].duration_ms == 30.0
    
    op_b_metrics = tracker.get_metrics(operation_name="op_b")
    assert len(op_b_metrics) == 2
    assert op_b_metrics[0].duration_ms == 20.0
    assert op_b_metrics[1].duration_ms == 40.0
    
    # Filter by time
    recent_metrics = tracker.get_metrics(since=one_hour_ago - timedelta(minutes=1))
    assert len(recent_metrics) == 3
    
    # Filter by both
    recent_op_a = tracker.get_metrics(operation_name="op_a", since=one_hour_ago - timedelta(minutes=1))
    assert len(recent_op_a) == 1
    assert recent_op_a[0].duration_ms == 30.0


def test_get_average_duration():
    """Test getting average duration for an operation."""
    tracker = MetricsTracker()
    
    # Record some operations
    tracker.record_operation("op_a", 10.0)
    tracker.record_operation("op_a", 20.0)
    tracker.record_operation("op_a", 30.0)
    tracker.record_operation("op_b", 100.0)
    
    # Get average for op_a
    avg_a = tracker.get_average_duration("op_a")
    assert avg_a == 20.0  # (10 + 20 + 30) / 3
    
    # Get average for op_b
    avg_b = tracker.get_average_duration("op_b")
    assert avg_b == 100.0
    
    # Get average for nonexistent operation
    avg_c = tracker.get_average_duration("op_c")
    assert avg_c == 0.0


def test_get_error_rate():
    """Test getting error rate for operations."""
    tracker = MetricsTracker()
    
    # Record operations with some errors
    tracker.record_operation("op_a", 10.0, success=True)
    tracker.record_operation("op_a", 20.0, success=False)
    tracker.record_operation("op_a", 30.0, success=True)
    tracker.record_operation("op_b", 100.0, success=False)
    
    # Get error rate for op_a
    error_rate_a = tracker.get_error_rate("op_a")
    assert error_rate_a == 33.33333333333333  # 1/3 * 100
    
    # Get error rate for op_b
    error_rate_b = tracker.get_error_rate("op_b")
    assert error_rate_b == 100.0  # 1/1 * 100
    
    # Get overall error rate
    overall_rate = tracker.get_error_rate()
    assert overall_rate == 50.0  # 2/4 * 100


def test_get_operation_counts():
    """Test getting counts of operations."""
    tracker = MetricsTracker()
    
    # Record operations
    tracker.record_operation("op_a", 10.0)
    tracker.record_operation("op_a", 20.0)
    tracker.record_operation("op_b", 30.0)
    tracker.record_operation("op_c", 40.0)
    
    # Get counts
    counts = tracker.get_operation_counts()
    assert counts == {"op_a": 2, "op_b": 1, "op_c": 1}


def test_clear_metrics():
    """Test clearing all metrics."""
    tracker = MetricsTracker()
    
    # Record some operations
    tracker.record_operation("op_a", 10.0)
    tracker.record_operation("op_b", 20.0)
    
    # Verify operations were recorded
    assert len(tracker.metrics) == 2
    
    # Clear metrics
    tracker.clear_metrics()
    
    # Verify metrics were cleared
    assert len(tracker.metrics) == 0


def test_track_operation_decorator():
    """Test the track_operation decorator."""
    # Create a test function with the decorator
    @track_operation("test_function")
    def test_function(x, y):
        return x + y
    
    # Mock the metrics tracker
    mock_tracker = MagicMock()
    
    # Replace the global tracker with our mock
    with patch('amr_predictor.monitoring.metrics.get_metrics_tracker', return_value=mock_tracker):
        # Call the function
        result = test_function(3, 4)
        
        # Verify the function still works
        assert result == 7
        
        # Verify the metric was recorded
        mock_tracker.record_operation.assert_called_once()
        call_args = mock_tracker.record_operation.call_args[1]
        assert call_args["operation_name"] == "test_function"
        assert call_args["success"] is True
        assert "duration_ms" in call_args


def test_track_operation_error():
    """Test the track_operation decorator with an error."""
    # Create a test function that raises an exception
    @track_operation("error_function")
    def error_function():
        raise ValueError("Test error")
    
    # Mock the metrics tracker
    mock_tracker = MagicMock()
    
    # Replace the global tracker with our mock
    with patch('amr_predictor.monitoring.metrics.get_metrics_tracker', return_value=mock_tracker):
        # Call the function and expect an exception
        with pytest.raises(ValueError):
            error_function()
        
        # Verify the metric was recorded with an error
        mock_tracker.record_operation.assert_called_once()
        call_args = mock_tracker.record_operation.call_args[1]
        assert call_args["operation_name"] == "error_function"
        assert call_args["success"] is False
        assert call_args["error_message"] == "Test error"
        assert "duration_ms" in call_args


def test_get_metrics_tracker():
    """Test getting the global metrics tracker."""
    # Get the tracker twice
    tracker1 = get_metrics_tracker()
    tracker2 = get_metrics_tracker()
    
    # Verify both references point to the same object
    assert tracker1 is tracker2
    
    # Verify it's a MetricsTracker instance
    assert isinstance(tracker1, MetricsTracker)


def test_metrics_report_performance_report():
    """Test generating a performance report."""
    # Mock the metrics tracker
    mock_tracker = MagicMock()
    mock_tracker.get_operation_counts.return_value = {"op_a": 2, "op_b": 1}
    mock_tracker.get_error_rate.return_value = 33.0
    mock_tracker.get_average_duration.return_value = 20.0
    
    # Replace the global tracker with our mock
    with patch('amr_predictor.monitoring.metrics.get_metrics_tracker', return_value=mock_tracker):
        # Generate report
        report = MetricsReport.generate_performance_report(window_minutes=30)
        
        # Verify report structure
        assert "window_minutes" in report
        assert report["window_minutes"] == 30
        assert "report_time" in report
        assert "total_operations" in report
        assert report["total_operations"] == 3  # 2 + 1
        assert "operation_counts" in report
        assert report["operation_counts"] == {"op_a": 2, "op_b": 1}
        assert "overall_error_rate" in report
        assert report["overall_error_rate"] == 33.0
        assert "operation_metrics" in report
        assert "op_a" in report["operation_metrics"]
        assert "op_b" in report["operation_metrics"]
        assert report["operation_metrics"]["op_a"]["average_duration_ms"] == 20.0
        assert report["operation_metrics"]["op_a"]["error_rate"] == 33.0
        assert report["operation_metrics"]["op_a"]["count"] == 2


def test_metrics_report_slow_operations():
    """Test finding slow operations."""
    # Create metrics
    slow_op = OperationMetric("slow_op", 1000.0, datetime.now(), True)
    fast_op = OperationMetric("fast_op", 50.0, datetime.now(), True)
    
    # Mock the metrics tracker
    mock_tracker = MagicMock()
    mock_tracker.get_metrics.return_value = [slow_op, fast_op]
    
    # Replace the global tracker with our mock
    with patch('amr_predictor.monitoring.metrics.get_metrics_tracker', return_value=mock_tracker):
        # Find slow operations
        slow_ops = MetricsReport.get_slow_operations(threshold_ms=500.0)
        
        # Verify only the slow operation is returned
        assert len(slow_ops) == 1
        assert slow_ops[0].operation_name == "slow_op"
        assert slow_ops[0].duration_ms == 1000.0


def test_metrics_report_error_operations():
    """Test finding error operations."""
    # Create metrics
    error_op = OperationMetric("error_op", 100.0, datetime.now(), False, "Test error")
    success_op = OperationMetric("success_op", 200.0, datetime.now(), True)
    
    # Mock the metrics tracker
    mock_tracker = MagicMock()
    mock_tracker.get_metrics.return_value = [error_op, success_op]
    
    # Replace the global tracker with our mock
    with patch('amr_predictor.monitoring.metrics.get_metrics_tracker', return_value=mock_tracker):
        # Find error operations
        error_ops = MetricsReport.get_error_operations()
        
        # Verify only the error operation is returned
        assert len(error_ops) == 1
        assert error_ops[0].operation_name == "error_op"
        assert error_ops[0].error_message == "Test error"
