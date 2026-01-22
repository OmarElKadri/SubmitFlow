from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class SaaSProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(..., max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    logo: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)


class SaaSProductCreate(SaaSProductBase):
    pass


class SaaSProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    logo: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)


class SaaSProductResponse(SaaSProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
