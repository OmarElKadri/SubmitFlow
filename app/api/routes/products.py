from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.api.deps import get_db
from app.models.saas_product import SaaSProduct
from app.schemas.saas_product import SaaSProductCreate, SaaSProductUpdate, SaaSProductResponse
from app.utils.file_upload import save_uploaded_logo, delete_logo_file

router = APIRouter()


@router.post("/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """Upload a logo file and get the path"""
    logo_path = await save_uploaded_logo(file)
    return {"logo_path": logo_path}


@router.post("", response_model=SaaSProductResponse)
def create_product(
    product: SaaSProductCreate,
    db: Session = Depends(get_db)
):
    """Create a SaaS product (logo should be uploaded separately via /upload-logo)"""
    db_product = SaaSProduct(
        name=product.name,
        website_url=product.website_url,
        description=product.description,
        category=product.category,
        contact_email=product.contact_email,
        logo=product.logo
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("", response_model=List[SaaSProductResponse])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all products"""
    products = db.query(SaaSProduct).offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=SaaSProductResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Get product details"""
    product = db.query(SaaSProduct).filter(SaaSProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=SaaSProductResponse)
def update_product(
    product_id: UUID,
    product_update: SaaSProductUpdate,
    db: Session = Depends(get_db)
):
    """Update product (logo should be uploaded separately via /upload-logo)"""
    product = db.query(SaaSProduct).filter(SaaSProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update fields if provided
    if product_update.name is not None:
        product.name = product_update.name
    if product_update.website_url is not None:
        product.website_url = product_update.website_url
    if product_update.description is not None:
        product.description = product_update.description
    if product_update.category is not None:
        product.category = product_update.category
    if product_update.contact_email is not None:
        product.contact_email = product_update.contact_email
    if product_update.logo is not None:
        product.logo = product_update.logo
    
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: UUID, db: Session = Depends(get_db)):
    """Delete product and associated logo file"""
    product = db.query(SaaSProduct).filter(SaaSProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete logo file if exists
    if product.logo:
        delete_logo_file(product.logo)
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}
