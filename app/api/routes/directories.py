from fastapi import APIRouter, HTTPException
from uuid import UUID

router = APIRouter()


@router.post("")
async def create_directory():
    """Add a directory"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("")
async def list_directories():
    """List all directories"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{directory_id}")
async def get_directory(directory_id: UUID):
    """Get directory details"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{directory_id}")
async def update_directory(directory_id: UUID):
    """Update directory"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{directory_id}")
async def delete_directory(directory_id: UUID):
    """Delete directory"""
    raise HTTPException(status_code=501, detail="Not implemented")
