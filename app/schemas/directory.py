from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class DirectoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    submission_url: str = Field(..., max_length=500)
    requires_login: bool = False
    credentials_key: Optional[str] = Field(None, max_length=100)


class DirectoryCreate(DirectoryBase):
    pass


class DirectoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    submission_url: Optional[str] = Field(None, max_length=500)
    requires_login: Optional[bool] = None
    credentials_key: Optional[str] = Field(None, max_length=100)


class DirectoryResponse(DirectoryBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
