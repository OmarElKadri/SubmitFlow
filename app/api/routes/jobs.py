from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime, timezone
import threading

from app.api.deps import get_db
from app.models.submission_job import SubmissionJob, JobStatus
from app.models.submission_attempt import SubmissionAttempt, AttemptStatus
from app.models.saas_product import SaaSProduct
from app.models.directory import Directory
from app.models.agent_action_log import AgentActionLog
from app.schemas.job import JobCreate, JobResponse, JobDetailResponse, AttemptResponse, ActionLogResponse
from app.services.job_executor import execute_job_sync

router = APIRouter()


@router.post("", response_model=JobResponse)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """Create a new submission job"""
    # Verify product exists
    product = db.query(SaaSProduct).filter(SaaSProduct.id == job_data.saas_product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="SaaS product not found")
    
    # Verify all directories exist
    directories = db.query(Directory).filter(Directory.id.in_(job_data.directory_ids)).all()
    if len(directories) != len(job_data.directory_ids):
        raise HTTPException(status_code=404, detail="One or more directories not found")
    
    # Create job
    db_job = SubmissionJob(
        saas_product_id=job_data.saas_product_id,
        total_directories=len(job_data.directory_ids),
        status=JobStatus.NOT_STARTED
    )
    db.add(db_job)
    db.flush()
    
    # Create submission attempts for each directory
    for directory in directories:
        attempt = SubmissionAttempt(
            job_id=db_job.id,
            directory_id=directory.id,
            status=AttemptStatus.NOT_STARTED
        )
        db.add(attempt)
    
    db.commit()
    db.refresh(db_job)
    return db_job


@router.get("", response_model=List[JobResponse])
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all jobs with pagination"""
    jobs = db.query(SubmissionJob).offset(skip).limit(limit).all()
    return jobs


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get job details and status"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/start", response_model=JobResponse)
def start_job(job_id: UUID, db: Session = Depends(get_db)):
    """Start a paused/created job"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.NOT_STARTED, JobStatus.PAUSED]:
        raise HTTPException(status_code=400, detail=f"Cannot start job with status {job.status}")
    
    job.status = JobStatus.IN_PROGRESS
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/pause", response_model=JobResponse)
def pause_job(job_id: UUID, db: Session = Depends(get_db)):
    """Pause a running job"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail=f"Cannot pause job with status {job.status}")
    
    job.status = JobStatus.PAUSED
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/resume", response_model=JobResponse)
def resume_job(job_id: UUID, db: Session = Depends(get_db)):
    """Resume a paused job"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail=f"Cannot resume job with status {job.status}")
    
    job.status = JobStatus.IN_PROGRESS
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/stop", response_model=JobResponse)
def stop_job(job_id: UUID, db: Session = Depends(get_db)):
    """Stop and cancel a job"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Cannot stop job with status {job.status}")
    
    job.status = JobStatus.FAILED
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/results", response_model=List[AttemptResponse])
def get_job_results(job_id: UUID, db: Session = Depends(get_db)):
    """Get directory-level submission results"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    attempts = db.query(SubmissionAttempt).filter(SubmissionAttempt.job_id == job_id).all()
    return attempts


@router.get("/{job_id}/errors", response_model=List[AttemptResponse])
def get_job_errors(job_id: UUID, db: Session = Depends(get_db)):
    """Get errors and retry information"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    failed_attempts = db.query(SubmissionAttempt).filter(
        SubmissionAttempt.job_id == job_id,
        SubmissionAttempt.status == AttemptStatus.FAILED
    ).all()
    return failed_attempts


@router.get("/{job_id}/attempts/{attempt_id}/logs", response_model=List[ActionLogResponse])
def get_attempt_logs(job_id: UUID, attempt_id: UUID, db: Session = Depends(get_db)):
    """Get action logs for a specific attempt"""
    attempt = db.query(SubmissionAttempt).filter(
        SubmissionAttempt.id == attempt_id,
        SubmissionAttempt.job_id == job_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    logs = db.query(AgentActionLog).filter(AgentActionLog.attempt_id == attempt_id).order_by(AgentActionLog.step_number).all()
    return logs


@router.delete("/{job_id}")
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Delete a job and all its attempts"""
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully"}


@router.post("/{job_id}/execute")
def execute_job(job_id: UUID, headless: bool = False, db: Session = Depends(get_db)):
    """
    Start executing a job in a background thread.
    This launches the browser automation to submit the product to all directories.
    
    Args:
        job_id: The job to execute
        headless: Run browser in headless mode (default: False for visibility)
    """
    job = db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.NOT_STARTED, JobStatus.PAUSED]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot execute job with status {job.status}. Job must be NOT_STARTED or PAUSED."
        )
    
    # Start execution in background thread
    def run_job():
        execute_job_sync(job_id, headless=headless)
    
    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()
    
    return {
        "message": f"Job {job_id} execution started",
        "job_id": str(job_id),
        "headless": headless
    }
