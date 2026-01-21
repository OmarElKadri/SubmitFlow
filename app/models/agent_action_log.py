import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("submission_attempts.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    screenshot_path = Column(String(500))
    llm_thought = Column(Text)
    workflow_status = Column(String(50))
    agentql_query = Column(Text)
    actions = Column(JSONB, default=list)
    executed_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error = Column(Text)
    
    attempt = relationship("SubmissionAttempt", back_populates="action_logs")
