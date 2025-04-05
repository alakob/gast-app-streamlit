#!/usr/bin/env python3
"""
AMR Database API Integration.

This module integrates the database components with the FastAPI endpoints,
providing a complete API for interacting with AMR jobs.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Body
from fastapi.responses import JSONResponse, FileResponse

from amr_predictor.bakta.database_manager_optimized import OptimizedDatabaseManager
from amr_predictor.dao.amr_job_dao import AMRJobDAO
from amr_predictor.models.amr_job import AMRJob, AMRJobStatus
from amr_predictor.auth.models import User
from amr_predictor.auth.dependencies import get_current_user
from amr_predictor.web.progress_tracker import DatabaseProgressTracker
from amr_predictor.config.job_lifecycle_config import JobLifecycleConfig
from amr_predictor.maintenance.job_archiver import JobArchiver
from amr_predictor.monitoring.metrics import track_operation

# Configure logging
logger = logging.getLogger("amr-api")

# Create router
router = APIRouter(prefix="/amr", tags=["amr"])

# Initialize components
db_manager = OptimizedDatabaseManager()
job_dao = AMRJobDAO(db_manager)
progress_tracker = DatabaseProgressTracker(job_dao)
job_lifecycle_config = JobLifecycleConfig()
job_archiver = JobArchiver(job_dao, job_lifecycle_config)


@router.post("/jobs", response_model=Dict[str, Any])
@track_operation("create_amr_job")
async def create_amr_job(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(...),
    job_name: str = Form(...),
    parameters: Dict[str, str] = Body({}),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new AMR job.
    
    Args:
        background_tasks: Background tasks runner
        input_file: Input file for analysis
        job_name: Name of the job
        parameters: Additional parameters for the job
        current_user: Current authenticated user
        
    Returns:
        Dictionary with job information
    """
    try:
        # Create a new job
        job = AMRJob(
            job_name=job_name,
            user_id=current_user.username,
            status=AMRJobStatus.SUBMITTED,
            progress=0.0,
            parameters=parameters
        )
        
        # Save the input file
        file_content = await input_file.read()
        input_file_path = f"uploads/{job.id}/{input_file.filename}"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(input_file_path), exist_ok=True)
        
        # Save file
        with open(input_file_path, "wb") as f:
            f.write(file_content)
        
        # Update job with file path
        job.input_file_path = input_file_path
        
        # Save job to database
        saved_job = job_dao.save(job)
        
        # Start processing in background
        background_tasks.add_task(process_amr_job, saved_job.id)
        
        # Return job information
        return saved_job.dict()
    
    except Exception as e:
        logger.error(f"Error creating AMR job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating AMR job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
@track_operation("get_amr_job")
async def get_amr_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get information about an AMR job.
    
    Args:
        job_id: ID of the job
        current_user: Current authenticated user
        
    Returns:
        Dictionary with job information
    """
    try:
        # Get job from database
        job = job_dao.get_by_id(job_id)
        
        # Check if job exists
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Check if user has access to job
        if job.user_id != current_user.username and not hasattr(current_user, "is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this job"
            )
        
        # Return job information
        return job.dict()
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting AMR job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting AMR job: {str(e)}"
        )


@router.get("/jobs", response_model=List[Dict[str, Any]])
@track_operation("list_amr_jobs")
async def list_amr_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List AMR jobs for the current user.
    
    Args:
        status: Filter by job status
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        current_user: Current authenticated user
        
    Returns:
        List of job information dictionaries
    """
    try:
        # Get jobs from database
        jobs = job_dao.get_by_user(
            user_id=current_user.username,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Convert to dictionaries
        return [job.dict() for job in jobs]
    
    except Exception as e:
        logger.error(f"Error listing AMR jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing AMR jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}/result", response_class=FileResponse)
@track_operation("get_amr_job_result")
async def get_amr_job_result(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """
    Get the result file for an AMR job.
    
    Args:
        job_id: ID of the job
        current_user: Current authenticated user
        
    Returns:
        File response with the result file
    """
    try:
        # Get job from database
        job = job_dao.get_by_id(job_id)
        
        # Check if job exists
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Check if user has access to job
        if job.user_id != current_user.username and not hasattr(current_user, "is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this job"
            )
        
        # Check if job has a result file
        if job.result_file_path is None or not os.path.exists(job.result_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"No result file found for job {job_id}"
            )
        
        # Return result file
        return FileResponse(
            path=job.result_file_path,
            filename=os.path.basename(job.result_file_path),
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting AMR job result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting AMR job result: {str(e)}"
        )


@router.delete("/jobs/{job_id}", response_model=Dict[str, Any])
@track_operation("delete_amr_job")
async def delete_amr_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete an AMR job.
    
    Args:
        job_id: ID of the job
        current_user: Current authenticated user
        
    Returns:
        Dictionary with status information
    """
    try:
        # Get job from database
        job = job_dao.get_by_id(job_id)
        
        # Check if job exists
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Check if user has access to job
        if job.user_id != current_user.username and not hasattr(current_user, "is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this job"
            )
        
        # Delete job
        deleted = job_dao.delete(job_id)
        
        # Return status
        return {
            "success": deleted,
            "message": f"Job {job_id} deleted successfully" if deleted else f"Failed to delete job {job_id}"
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error deleting AMR job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting AMR job: {str(e)}"
        )


@router.post("/jobs/{job_id}/archive", response_model=Dict[str, Any])
@track_operation("archive_amr_job")
async def archive_amr_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Archive an AMR job.
    
    Args:
        job_id: ID of the job
        current_user: Current authenticated user
        
    Returns:
        Dictionary with status information
    """
    try:
        # Get job from database
        job = job_dao.get_by_id(job_id)
        
        # Check if job exists
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Check if user has access to job
        if job.user_id != current_user.username and not hasattr(current_user, "is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to archive this job"
            )
        
        # Check if job is in a state that can be archived
        if job.status not in [AMRJobStatus.COMPLETED, AMRJobStatus.ERROR]:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is {job.status}, only Completed or Error jobs can be archived"
            )
        
        # Archive job
        archived = job_archiver.archive_job(job)
        
        # Return status
        return {
            "success": archived,
            "message": f"Job {job_id} archived successfully" if archived else f"Failed to archive job {job_id}"
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error archiving AMR job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error archiving AMR job: {str(e)}"
        )


@router.post("/maintenance/archive-old-jobs", response_model=Dict[str, Any])
@track_operation("archive_old_jobs")
async def run_archive_old_jobs(
    max_jobs: int = 100,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run the archive old jobs maintenance task.
    
    Args:
        max_jobs: Maximum number of jobs to archive
        current_user: Current authenticated user
        
    Returns:
        Dictionary with status information
    """
    # Check if user is admin
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can run maintenance tasks"
        )
    
    try:
        # Run archiving
        count = job_archiver.archive_old_jobs(max_jobs=max_jobs)
        
        # Return status
        return {
            "success": True,
            "archived_count": count,
            "message": f"Archived {count} old jobs"
        }
    
    except Exception as e:
        logger.error(f"Error archiving old jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error archiving old jobs: {str(e)}"
        )


@router.post("/maintenance/cleanup-old-jobs", response_model=Dict[str, Any])
@track_operation("cleanup_old_jobs")
async def run_cleanup_old_jobs(
    max_jobs: int = 100,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run the cleanup old jobs maintenance task.
    
    Args:
        max_jobs: Maximum number of jobs to clean up
        current_user: Current authenticated user
        
    Returns:
        Dictionary with status information
    """
    # Check if user is admin
    if not hasattr(current_user, "is_admin") or not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can run maintenance tasks"
        )
    
    try:
        # Run cleanup
        total, by_status = job_archiver.cleanup_old_jobs(max_jobs=max_jobs)
        
        # Return status
        return {
            "success": True,
            "total_deleted": total,
            "by_status": by_status,
            "message": f"Cleaned up {total} old jobs"
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up old jobs: {str(e)}"
        )


async def process_amr_job(job_id: str):
    """
    Process an AMR job (stub function for demonstration).
    
    In a real implementation, this would:
    1. Update job status to Running
    2. Process the job
    3. Update job progress during processing
    4. Save result file
    5. Update job status to Completed or Error
    
    Args:
        job_id: ID of the job to process
    """
    try:
        # Get job from database
        job = job_dao.get_by_id(job_id)
        
        if job is None:
            logger.error(f"Job {job_id} not found for processing")
            return
        
        # Update job status to Running
        job.status = AMRJobStatus.RUNNING
        job_dao.update(job)
        
        # Update progress to 10%
        progress_tracker.update_progress(job_id, 10.0)
        
        # TODO: Implement actual job processing
        # This is where the AMR analysis would be performed
        
        # For demonstration, just update progress a few times
        progress_tracker.update_progress(job_id, 25.0)
        progress_tracker.update_progress(job_id, 50.0)
        progress_tracker.update_progress(job_id, 75.0)
        
        # Create a dummy result file
        result_dir = f"results/{job_id}"
        os.makedirs(result_dir, exist_ok=True)
        
        result_file_path = f"{result_dir}/result.txt"
        with open(result_file_path, "w") as f:
            f.write(f"AMR Analysis Results for job {job_id}\n")
            f.write(f"Job Name: {job.job_name}\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
            f.write("This is a placeholder result file for demonstration purposes.\n")
        
        # Update job with result file path and set status to Completed
        job = job_dao.get_by_id(job_id)  # Re-fetch to get latest state
        job.result_file_path = result_file_path
        job.status = AMRJobStatus.COMPLETED
        job.progress = 100.0
        job_dao.update(job)
        
    except Exception as e:
        logger.error(f"Error processing AMR job {job_id}: {str(e)}")
        
        # Update job status to Error
        try:
            job = job_dao.get_by_id(job_id)
            if job is not None:
                job.status = AMRJobStatus.ERROR
                job.error = str(e)
                job_dao.update(job)
        except Exception as update_error:
            logger.error(f"Error updating job status for {job_id}: {str(update_error)}")
