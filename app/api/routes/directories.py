from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.api.deps import get_db
from app.models.directory import Directory
from app.models.submission_attempt import SubmissionAttempt
from app.models.agent_action_log import AgentActionLog
from app.schemas.directory import DirectoryCreate, DirectoryUpdate, DirectoryResponse

router = APIRouter()


@router.post("", response_model=DirectoryResponse)
def create_directory(directory: DirectoryCreate, db: Session = Depends(get_db)):
    """Add a directory"""
    db_directory = Directory(**directory.model_dump())
    db.add(db_directory)
    db.commit()
    db.refresh(db_directory)
    return db_directory


@router.get("", response_model=List[DirectoryResponse])
def list_directories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all directories"""
    directories = db.query(Directory).offset(skip).limit(limit).all()
    return directories


@router.get("/{directory_id}", response_model=DirectoryResponse)
def get_directory(directory_id: UUID, db: Session = Depends(get_db)):
    """Get directory details"""
    directory = db.query(Directory).filter(Directory.id == directory_id).first()
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")
    return directory


@router.put("/{directory_id}", response_model=DirectoryResponse)
def update_directory(directory_id: UUID, directory_update: DirectoryUpdate, db: Session = Depends(get_db)):
    """Update directory"""
    directory = db.query(Directory).filter(Directory.id == directory_id).first()
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")
    
    update_data = directory_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(directory, field, value)
    
    db.commit()
    db.refresh(directory)
    return directory


@router.delete("/{directory_id}")
def delete_directory(directory_id: UUID, db: Session = Depends(get_db)):
    """Delete a directory and all dependent records (attempts + action logs)."""
    directory = db.query(Directory).filter(Directory.id == directory_id).first()
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")

    # Delete dependent rows explicitly to avoid FK-nullification issues when DB constraints are NOT NULL.
    # This also keeps behavior correct even if DB-level ON DELETE CASCADE has not been applied yet.
    attempt_ids = [
        a_id
        for (a_id,) in db.query(SubmissionAttempt.id)
        .filter(SubmissionAttempt.directory_id == directory_id)
        .all()
    ]

    deleted_logs = 0
    deleted_attempts = 0

    if attempt_ids:
        deleted_logs = (
            db.query(AgentActionLog)
            .filter(AgentActionLog.attempt_id.in_(attempt_ids))
            .delete(synchronize_session=False)
        )
        deleted_attempts = (
            db.query(SubmissionAttempt)
            .filter(SubmissionAttempt.id.in_(attempt_ids))
            .delete(synchronize_session=False)
        )

    db.delete(directory)
    db.commit()

    return {
        "message": "Directory deleted successfully",
        "deleted_attempts": deleted_attempts,
        "deleted_action_logs": deleted_logs,
    }
