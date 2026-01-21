import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Directory(Base):
    __tablename__ = "directories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    submission_url = Column(String(500))
    requires_login = Column(Boolean, default=False)
    credentials_key = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
