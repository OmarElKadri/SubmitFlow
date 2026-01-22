import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submission_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number = Column(Integer, nullable=False)
    screenshot_path = Column(String(500))
    llm_thought = Column(Text)
    workflow_status = Column(String(50))
    # AgentQL query/context returned by the LLM. Stored as JSONB so we can persist either:
    # - a query string (stored as JSON string)
    # - an object/map (stored as JSON object)
    agentql_query = Column(JSONB)
    actions = Column(JSONB, default=list)
    executed_at = Column(DateTime(timezone=True), default=utcnow)
    success = Column(Boolean, default=True)
    error = Column(Text)
    
    # Relationships
    attempt = relationship("SubmissionAttempt", back_populates="action_logs")
