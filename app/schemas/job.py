from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AttemptStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FAILED = "FAILED"


class JobCreate(BaseModel):
    saas_product_id: UUID
    directory_ids: List[UUID] = Field(..., min_length=1)


class JobResponse(BaseModel):
    id: UUID
    saas_product_id: UUID
    status: JobStatus
    total_directories: int
    completed_count: int
    failed_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AttemptResponse(BaseModel):
    id: UUID
    job_id: UUID
    directory_id: UUID
    status: AttemptStatus
    attempt_number: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    attempts: List[AttemptResponse] = []
    
    class Config:
        from_attributes = True


class ActionLogResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    step_number: int
    screenshot_path: Optional[str] = None
    llm_thought: Optional[str] = None
    workflow_status: Optional[str] = None
    agentql_query: Optional[Any] = None
    actions: Optional[List[dict]] = None
    executed_at: datetime
    success: bool
    error: Optional[str] = None
    
    class Config:
        from_attributes = True
