import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class SaaSProduct(Base):
    __tablename__ = "saas_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    website_url = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    logo = Column(String(500))
    contact_email = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    # Relationships
    # When a product is deleted, delete its related jobs (and their dependent rows).
    jobs = relationship(
        "SubmissionJob",
        back_populates="saas_product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
