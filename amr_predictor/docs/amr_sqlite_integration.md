# Action Plan: Unified Database Infrastructure for AMR Predictor API

Below is a comprehensive action plan to transition from the dual approach (in-memory + SQLite) to a consistent, production-ready database infrastructure using the existing Bakta SQLite framework.
Make sure write unit tests at the end of each phase.
and make sure critical parts are covered by integration tests.


## Phase 1: Extend Bakta Database Schema for AMR Jobs

### 1.1. Create AMR-Specific Tables (1 week)

```sql
-- New tables for AMR-specific functionality
CREATE TABLE amr_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT,  -- For authentication
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    input_file_path TEXT,
    result_file_path TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE amr_job_params (
    job_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    batch_size INTEGER NOT NULL,
    segment_length INTEGER NOT NULL,
    segment_overlap INTEGER NOT NULL,
    use_cpu BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES amr_jobs(id)
);

-- Add appropriate indexes
CREATE INDEX idx_amr_jobs_user_id ON amr_jobs(user_id);
CREATE INDEX idx_amr_jobs_status ON amr_jobs(status);
CREATE INDEX idx_amr_jobs_created_at ON amr_jobs(created_at);
```

### 1.2. Extend DatabaseManager (1 week)
Implement new methods in `DatabaseManager` class:

- `save_amr_job()`
- `update_amr_job_status()`
- `get_amr_job()`
- `get_amr_jobs_by_user()`
- `get_amr_job_params()`

## Phase 2: Implement User Authentication (2 weeks)

### 2.1. Create User Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TEXT NOT NULL,
    last_login TEXT,
    role TEXT NOT NULL DEFAULT 'user'
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

### 2.2. Implement Authentication System
- Create `UserManager` class in a new module `amr_predictor.auth`
- Implement JWT-based token authentication
- Add authentication middleware to FastAPI app
- Create endpoints for user registration, login, and password reset

### 2.3. Update API Endpoints
- Modify all existing endpoints to require authentication
- Add `user_id` to job creation and retrieval logic

## Phase 3: Transition In-memory Jobs to Database (2 weeks)

### 3.1. Create AMR Job DAO Class

```python
# amr_predictor/dao/amr_job_dao.py
from typing import List, Optional, Dict, Any
from amr_predictor.bakta.dao.base_dao import BaseDAO
from amr_predictor.models import AMRJob, AMRJobParams

class AMRJobDAO(BaseDAO[AMRJob]):
    def get_by_id(self, id: str) -> Optional[AMRJob]:
        try:
            query = "SELECT * FROM amr_jobs WHERE id = ?"
            result = self.db_manager.execute_query(query, (id,))
            if result and len(result) > 0:
                return AMRJob.from_db_row(result[0])
            return None
        except Exception as e:
            self._handle_db_error("get_by_id", e)
    
    def get_by_user(self, user_id: str, limit: int = 50) -> List[AMRJob]:
        try:
            query = """
                SELECT * FROM amr_jobs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            results = self.db_manager.execute_query(query, (user_id, limit))
            return [AMRJob.from_db_row(row) for row in results]
        except Exception as e:
            self._handle_db_error("get_by_user", e)
```

### 3.2. Update API Endpoints
- Replace all references to the jobs dictionary with DAOs
- Update `WebProgressTracker` to use database updates

```python
class DatabaseProgressTracker(ProgressTracker):
    def __init__(self, job_id: str, db_manager: DatabaseManager):
        super().__init__()
        self.job_id = job_id
        self.db_manager = db_manager
        
    def _update_job_status(self, tracker):
        self.db_manager.update_amr_job_status(
            self.job_id,
            status=tracker.status,
            progress=tracker.percentage,
            error=tracker.error,
            additional_info=tracker.additional_info
        )
```

## Phase 4: Implement Job Lifecycle Management (1 week)

### 4.1. Create Cleanup Policy Configuration
- Add configuration settings for job retention periods
- Implement different policies for different job statuses

### 4.2. Implement Archiving System

```python
# amr_predictor/maintenance/job_archiver.py
class JobArchiver:
    def __init__(self, db_manager: DatabaseManager, config: Dict[str, Any]):
        self.db_manager = db_manager
        self.config = config
        
    async def archive_old_jobs(self):
        """Archive jobs older than the configured threshold"""
        # Find jobs eligible for archiving
        # Compress result files
        # Move to archive storage
        # Update job status to "Archived"
        
    async def purge_expired_jobs(self):
        """Permanently delete jobs past their retention period"""
        # Identify jobs past retention period
        # Delete associated files
        # Remove from database
```

### 4.3. Create Scheduled Tasks
- Implement background tasks using APScheduler
- Schedule daily/weekly maintenance jobs

## Phase 5: Performance Optimization (1 week)

### 5.1. Implement Database Connection Pooling

```python
# Update DatabaseManager to use connection pooling
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.pool = self._create_connection_pool()
        
    def _create_connection_pool(self):
        # Implement connection pooling
        # Consider using libraries like SQLAlchemy or aiosqlite
```

### 5.2. Add Query Optimizations
- Implement pagination for large result sets
- Add caching for frequently accessed jobs
- Create composite indexes for common query patterns

### 5.3. Implement Benchmarking and Monitoring
- Add execution time tracking for database operations
- Create performance monitoring endpoints

## Phase 6: Testing and Documentation (2 weeks)

### 6.1. Comprehensive Testing
- Unit tests for new DAO classes
- Integration tests for database operations
- Performance tests for job queries

### 6.2. Documentation
- Update API documentation
- Add database schema diagrams
- Document authentication flow
- Create maintenance procedures

## Implementation Timeline

**Total estimated time: 9 weeks**

| Phase  | Description                | Duration | Dependencies |
|--------|----------------------------|----------|--------------|
| Phase 1 | Extend Database Schema    | 2 weeks  | None         |
| Phase 2 | Implement Authentication  | 2 weeks  | Phase 1      |
| Phase 3 | Transition In-memory Jobs | 2 weeks  | Phase 1      |
| Phase 4 | Job Lifecycle Management  | 1 week   | Phase 3      |
| Phase 5 | Performance Optimization  | 1 week   | Phase 3      |
| Phase 6 | Testing and Documentation | 2 weeks  | All Phases   |
