import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class AttemptStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FAILED = "FAILED"


class SubmissionAttempt(Base):
    __tablename__ = "submission_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("submission_jobs.id"), nullable=False)
    directory_id = Column(UUID(as_uuid=True), ForeignKey("directories.id"), nullable=False)
    status = Column(Enum(AttemptStatus), default=AttemptStatus.NOT_STARTED)
    attempt_number = Column(Integer, default=1)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    job = relationship("SubmissionJob", back_populates="attempts")
    action_logs = relationship("AgentActionLog", back_populates="attempt")
