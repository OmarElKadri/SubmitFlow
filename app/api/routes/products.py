from fastapi import APIRouter, HTTPException
from uuid import UUID

router = APIRouter()


@router.post("")
async def create_product():
    """Create a SaaS product"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("")
async def list_products():
    """List all products"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{product_id}")
async def get_product(product_id: UUID):
    """Get product details"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{product_id}")
async def update_product(product_id: UUID):
    """Update product"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{product_id}")
async def delete_product(product_id: UUID):
    """Delete product"""
    raise HTTPException(status_code=501, detail="Not implemented")
