import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def save_uploaded_logo(file: UploadFile) -> str:
    """
    Save an uploaded logo file to the assets/logos directory.
    
    Args:
        file: The uploaded file
        
    Returns:
        str: The relative path to the saved file
        
    Raises:
        HTTPException: If file validation fails
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create assets/logos directory if it doesn't exist
    logos_dir = Path("assets/logos")
    logos_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = logos_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return relative path
    return str(file_path).replace("\\", "/")


def delete_logo_file(logo_path: Optional[str]) -> None:
    """
    Delete a logo file from the file system.
    
    Args:
        logo_path: The path to the logo file
    """
    if not logo_path:
        return
    
    try:
        file_path = Path(logo_path)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
    except Exception:
        # Silently ignore errors when deleting files
        pass
