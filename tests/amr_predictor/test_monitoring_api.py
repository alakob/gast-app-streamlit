"""Tests for the AMR Monitoring API."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import status
from datetime import datetime, timedelta

from amr_predictor.monitoring.metrics import OperationMetric


def test_metrics_summary_requires_admin(test_client, auth_headers):
    """Test that metrics summary requires admin privileges."""
    # Try to get metrics summary as regular user
    response = test_client.get(
        "/monitoring/metrics/summary",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify access is denied
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_metrics_summary_with_admin(test_client, admin_auth_headers, metrics_tracker):
    """Test getting metrics summary with admin privileges."""
    # Add some test metrics
    metrics_tracker.record_operation("test_op_1", 100.0, True)
    metrics_tracker.record_operation("test_op_1", 200.0, True)
    metrics_tracker.record_operation("test_op_2", 50.0, False, "Test error")
    
    # Request metrics summary
    response = test_client.get(
        "/monitoring/metrics/summary",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    report = response.json()
    
    # Check basic structure
    assert "window_minutes" in report
    assert "report_time" in report
    assert "total_operations" in report
    assert "operation_counts" in report
    assert "operation_metrics" in report
    assert "overall_error_rate" in report
    
    # Check values
    assert report["total_operations"] == 3
    assert "test_op_1" in report["operation_counts"]
    assert "test_op_2" in report["operation_counts"]
    assert report["operation_counts"]["test_op_1"] == 2
    assert report["operation_counts"]["test_op_2"] == 1
    
    # Check metrics details
    assert "test_op_1" in report["operation_metrics"]
    assert "test_op_2" in report["operation_metrics"]
    assert "average_duration_ms" in report["operation_metrics"]["test_op_1"]
    assert "error_rate" in report["operation_metrics"]["test_op_1"]
    assert "count" in report["operation_metrics"]["test_op_1"]
    
    # Error rate for test_op_2 should be 100%
    assert report["operation_metrics"]["test_op_2"]["error_rate"] == 100.0


def test_slow_operations_requires_admin(test_client, auth_headers):
    """Test that slow operations endpoint requires admin privileges."""
    # Try to get slow operations as regular user
    response = test_client.get(
        "/monitoring/metrics/slow-operations",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify access is denied
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_slow_operations_with_admin(test_client, admin_auth_headers, metrics_tracker):
    """Test getting slow operations with admin privileges."""
    # Add some test metrics with varying durations
    metrics_tracker.record_operation("fast_op", 50.0, True)
    metrics_tracker.record_operation("medium_op", 400.0, True)
    metrics_tracker.record_operation("slow_op", 800.0, True)
    metrics_tracker.record_operation("very_slow_op", 1200.0, True)
    
    # Request slow operations with threshold of 500ms
    response = test_client.get(
        "/monitoring/metrics/slow-operations?threshold_ms=500.0",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    slow_ops = response.json()
    
    # Should only include operations slower than 500ms
    assert len(slow_ops) == 2
    assert any(op["operation_name"] == "slow_op" for op in slow_ops)
    assert any(op["operation_name"] == "very_slow_op" for op in slow_ops)
    
    # Operations should be sorted by duration (slowest first)
    assert slow_ops[0]["operation_name"] == "very_slow_op"
    assert slow_ops[1]["operation_name"] == "slow_op"


def test_error_operations_requires_admin(test_client, auth_headers):
    """Test that error operations endpoint requires admin privileges."""
    # Try to get error operations as regular user
    response = test_client.get(
        "/monitoring/metrics/errors",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify access is denied
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_error_operations_with_admin(test_client, admin_auth_headers, metrics_tracker):
    """Test getting error operations with admin privileges."""
    # Add some test metrics, some with errors
    metrics_tracker.record_operation("success_op_1", 50.0, True)
    metrics_tracker.record_operation("error_op_1", 100.0, False, "Error 1")
    metrics_tracker.record_operation("success_op_2", 200.0, True)
    metrics_tracker.record_operation("error_op_2", 300.0, False, "Error 2")
    
    # Request error operations
    response = test_client.get(
        "/monitoring/metrics/errors",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    error_ops = response.json()
    
    # Should only include failed operations
    assert len(error_ops) == 2
    assert any(op["operation_name"] == "error_op_1" for op in error_ops)
    assert any(op["operation_name"] == "error_op_2" for op in error_ops)
    
    # Check error messages
    for op in error_ops:
        if op["operation_name"] == "error_op_1":
            assert op["error_message"] == "Error 1"
        elif op["operation_name"] == "error_op_2":
            assert op["error_message"] == "Error 2"


def test_system_status_requires_admin(test_client, auth_headers):
    """Test that system status endpoint requires admin privileges."""
    # Try to get system status as regular user
    response = test_client.get(
        "/monitoring/system/status",
        headers=auth_headers  # Regular user, not admin
    )
    
    # Verify access is denied
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_system_status_with_admin(test_client, admin_auth_headers, metrics_tracker, monkeypatch):
    """Test getting system status with admin privileges."""
    # Mock the job counts since we can't directly control them in the test
    def mock_count_all(self):
        return 100
    
    def mock_count_by_status(self, status):
        counts = {
            "Running": 10,
            "Completed": 70,
            "Error": 20
        }
        return counts.get(status, 0)
    
    monkeypatch.setattr("amr_predictor.dao.amr_job_dao.AMRJobDAO.count_all", mock_count_all)
    monkeypatch.setattr("amr_predictor.dao.amr_job_dao.AMRJobDAO.count_by_status", mock_count_by_status)
    
    # Add some metrics
    metrics_tracker.record_operation("save_job", 50.0, True)
    metrics_tracker.record_operation("save_job", 60.0, True)
    metrics_tracker.record_operation("get_job", 10.0, True)
    metrics_tracker.record_operation("update_job", 20.0, False, "Test error")
    
    # Request system status
    response = test_client.get(
        "/monitoring/system/status",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    status_data = response.json()
    
    # Check structure
    assert "timestamp" in status_data
    assert "status" in status_data
    assert "database" in status_data
    assert "jobs" in status_data
    assert "performance" in status_data
    
    # Check job counts
    assert status_data["jobs"]["total"] == 100
    assert status_data["jobs"]["running"] == 10
    assert status_data["jobs"]["completed"] == 70
    assert status_data["jobs"]["error"] == 20
    
    # Check performance metrics
    assert "recent_error_rate" in status_data["performance"]
    assert "avg_job_save_time" in status_data["performance"]
    
    # Verify status is determined correctly
    # Should be "degraded" because our error rate is 25% (1/4 operations failed)
    assert status_data["status"] == "degraded"


def test_job_status_summary(test_client, auth_headers, populated_db, monkeypatch):
    """Test getting job status summary."""
    # Mock the count functions for predictable behavior
    def mock_count_by_status(self, status):
        counts = {
            "Submitted": 10,
            "Running": 20,
            "Completed": 50,
            "Error": 15,
            "Archived": 5
        }
        return counts.get(status, 0)
    
    def mock_count_by_status_and_user(self, status, username):
        # Regular user has fewer jobs
        if username == "testuser":
            counts = {
                "Submitted": 2,
                "Running": 3,
                "Completed": 10,
                "Error": 5,
                "Archived": 0
            }
            return counts.get(status, 0)
        return 0
    
    monkeypatch.setattr("amr_predictor.dao.amr_job_dao.AMRJobDAO.count_by_status", mock_count_by_status)
    monkeypatch.setattr("amr_predictor.dao.amr_job_dao.AMRJobDAO.count_by_status_and_user", mock_count_by_status_and_user)
    
    # Request job status summary as regular user
    response = test_client.get(
        "/monitoring/jobs/status-summary",
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    summary = response.json()
    
    # Regular user should see only their own jobs
    assert "timestamp" in summary
    assert "all_jobs" not in summary or summary["all_jobs"] is None
    assert "user_jobs" in summary
    
    user_jobs = summary["user_jobs"]
    assert user_jobs["Submitted"] == 2
    assert user_jobs["Running"] == 3
    assert user_jobs["Completed"] == 10
    assert user_jobs["Error"] == 5
    assert user_jobs["Archived"] == 0
    
    # Now request as admin
    response = test_client.get(
        "/monitoring/jobs/status-summary",
        headers=admin_auth_headers
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    summary = response.json()
    
    # Admin should see all jobs
    assert "timestamp" in summary
    assert "all_jobs" in summary
    
    all_jobs = summary["all_jobs"]
    assert all_jobs["Submitted"] == 10
    assert all_jobs["Running"] == 20
    assert all_jobs["Completed"] == 50
    assert all_jobs["Error"] == 15
    assert all_jobs["Archived"] == 5
