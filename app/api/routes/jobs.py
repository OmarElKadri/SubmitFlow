from fastapi import APIRouter, HTTPException
from uuid import UUID

router = APIRouter()


@router.post("")
async def create_job():
    """Create a new submission job"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("")
async def list_jobs():
    """List all jobs with pagination"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}")
async def get_job(job_id: UUID):
    """Get job details and status"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{job_id}/start")
async def start_job(job_id: UUID):
    """Start a paused/created job"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{job_id}/pause")
async def pause_job(job_id: UUID):
    """Pause a running job"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{job_id}/resume")
async def resume_job(job_id: UUID):
    """Resume a paused job"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{job_id}/stop")
async def stop_job(job_id: UUID):
    """Stop and cancel a job"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}/results")
async def get_job_results(job_id: UUID):
    """Get directory-level submission results"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}/errors")
async def get_job_errors(job_id: UUID):
    """Get errors and retry information"""
    raise HTTPException(status_code=501, detail="Not implemented")
