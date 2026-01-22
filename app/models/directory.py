import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class Directory(Base):
    __tablename__ = "directories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    submission_url = Column(String(500), nullable=False)
    requires_login = Column(Boolean, default=False)
    credentials_key = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    # Relationships
    # Deleting a Directory should delete all SubmissionAttempts (and their AgentActionLogs).
    # Use both ORM cascade and DB-level cascade for safety.
    attempts = relationship(
        "SubmissionAttempt",
        back_populates="directory",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
