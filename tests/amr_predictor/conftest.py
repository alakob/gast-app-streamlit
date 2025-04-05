"""Test fixtures for AMR database integration tests."""

import os
import tempfile
import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.bakta.database_extensions import extend_database_manager
from amr_predictor.bakta.database_pool import get_connection_pool
from amr_predictor.bakta.database_manager_optimized import OptimizedDatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.auth.user_manager import UserManager
from amr_predictor.auth.models import UserCreate, User
from amr_predictor.models.amr_job import AMRJob, AMRJobParams
from amr_predictor.config.job_lifecycle_config import JobLifecycleConfig
from amr_predictor.maintenance.job_archiver import JobArchiver


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db_manager(temp_db_path):
    """Create a test database manager."""
    db_manager = DatabaseManager(temp_db_path)
    extend_database_manager(db_manager)
    yield db_manager


@pytest.fixture
def optimized_db_manager(temp_db_path):
    """Create a test optimized database manager."""
    db_manager = OptimizedDatabaseManager(temp_db_path)
    yield db_manager
    db_manager.close()


@pytest.fixture
def amr_job_dao(db_manager):
    """Create a test AMR job DAO."""
    return AMRJobDAO(db_manager)


@pytest.fixture
def user_manager(temp_db_path):
    """Create a test user manager."""
    return UserManager(db_path=temp_db_path)


@pytest.fixture
def test_user(user_manager):
    """Create a test user."""
    user_data = UserCreate(
        username="testuser",
        password="testpassword",
        email="test@example.com"
    )
    user = user_manager.create_user(user_data)
    return user


@pytest.fixture
def test_job_params():
    """Create test job parameters."""
    return AMRJobParams(
        model_name="test_model",
        batch_size=8,
        segment_length=6000,
        segment_overlap=0,
        use_cpu=True
    )


@pytest.fixture
def test_job(test_job_params):
    """Create a test AMR job."""
    return AMRJob(
        id="test-job-id-123",
        job_name="Test Job",
        status="Submitted",
        progress=0.0,
        created_at=datetime.now(),
        params=test_job_params
    )


@pytest.fixture
def completed_job(test_job_params):
    """Create a completed test AMR job."""
    created_time = datetime.now() - timedelta(days=10)
    completed_time = datetime.now() - timedelta(days=9)
    
    return AMRJob(
        id="completed-job-id-456",
        job_name="Completed Job",
        status="Completed",
        progress=100.0,
        created_at=created_time,
        completed_at=completed_time,
        params=test_job_params,
        result_file_path="/tmp/test_result.txt"
    )


@pytest.fixture
def error_job(test_job_params):
    """Create a job with an error."""
    created_time = datetime.now() - timedelta(days=15)
    error_time = datetime.now() - timedelta(days=14)
    
    return AMRJob(
        id="error-job-id-789",
        job_name="Error Job",
        status="Error",
        progress=50.0,
        created_at=created_time,
        completed_at=error_time,
        error="Test error message",
        params=test_job_params
    )


@pytest.fixture
def temp_archive_dir():
    """Create a temporary directory for archives."""
    with tempfile.TemporaryDirectory() as archive_dir:
        yield archive_dir


@pytest.fixture
def job_lifecycle_config():
    """Create a test job lifecycle configuration."""
    return JobLifecycleConfig()


@pytest.fixture
def job_archiver(job_lifecycle_config, db_manager, temp_archive_dir):
    """Create a test job archiver."""
    return JobArchiver(
        config=job_lifecycle_config,
        db_manager=db_manager,
        archive_dir=temp_archive_dir
    )


@pytest.fixture
def saved_test_job(amr_job_dao, test_job):
    """Save a test job to the database."""
    amr_job_dao.save(test_job)
    return test_job


@pytest.fixture
def saved_completed_job(amr_job_dao, completed_job):
    """Save a completed job to the database."""
    amr_job_dao.save(completed_job)
    return completed_job


@pytest.fixture
def saved_error_job(amr_job_dao, error_job):
    """Save a job with an error to the database."""
    amr_job_dao.save(error_job)
    return error_job


@pytest.fixture
def populated_db(amr_job_dao, test_job, completed_job, error_job):
    """Populate the database with multiple jobs."""
    amr_job_dao.save(test_job)
    amr_job_dao.save(completed_job)
    amr_job_dao.save(error_job)
    return amr_job_dao


@pytest.fixture
def metrics_tracker():
    """Create a test metrics tracker."""
    from amr_predictor.monitoring.metrics import MetricsTracker, get_metrics_tracker
    tracker = MetricsTracker(max_history=100)
    old_tracker = get_metrics_tracker()
    
    # Replace global tracker temporarily
    from amr_predictor.monitoring.metrics import _metrics_tracker
    original_tracker = _metrics_tracker
    from amr_predictor.monitoring import metrics
    metrics._metrics_tracker = tracker
    
    yield tracker
    
    # Restore original tracker
    metrics._metrics_tracker = original_tracker


@pytest.fixture
def progress_tracker(amr_job_dao):
    """Create a test progress tracker."""
    from amr_predictor.web.progress_tracker import DatabaseProgressTracker
    return DatabaseProgressTracker(amr_job_dao)


@pytest.fixture
def admin_user(user_manager):
    """Create an admin test user."""
    user_data = UserCreate(
        username="adminuser",
        password="adminpassword",
        email="admin@example.com"
    )
    user = user_manager.create_user(user_data)
    
    # Mark user as admin for testing
    with user_manager.db_manager._get_connection() as conn:
        conn.execute(
            "UPDATE users SET is_admin = 1 WHERE username = ?",
            (user.username,)
        )
        conn.commit()
    
    # Fetch updated user
    user = user_manager.get_user_by_username(user.username)
    user.is_admin = True
    
    return user


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from amr_predictor.api.main import app
    
    client = TestClient(app)
    return client


@pytest.fixture
def auth_headers(user_manager, test_user):
    """Create authentication headers for API requests."""
    token = user_manager.create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(user_manager, admin_user):
    """Create authentication headers for admin API requests."""
    token = user_manager.create_access_token(data={"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}
