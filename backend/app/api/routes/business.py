"""Business management routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.business import Business
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter()

class BusinessCreate(BaseModel):
    name: str
    phone_number: str
    industry: Optional[str] = None
    description: Optional[str] = None
    hours_of_operation: Optional[Dict] = None
    services: Optional[List[str]] = None
    faq: Optional[List[Dict]] = None
    primary_language: str = "en"
    supported_languages: List[str] = ["en", "es"]

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    hours_of_operation: Optional[Dict] = None
    services: Optional[List[str]] = None
    faq: Optional[List[Dict]] = None
    greeting_message: Optional[Dict] = None
    is_active: Optional[bool] = None

@router.post("/create")
async def create_business(
    business_data: BusinessCreate,
    db: Session = Depends(get_db)
):
    """Create new business"""
    # Check if phone number already exists
    existing = db.query(Business).filter(
        Business.phone_number == business_data.phone_number
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    business = Business(
        name=business_data.name,
        phone_number=business_data.phone_number,
        industry=business_data.industry,
        description=business_data.description,
        hours_of_operation=business_data.hours_of_operation,
        services=business_data.services,
        faq=business_data.faq,
        primary_language=business_data.primary_language,
        supported_languages=business_data.supported_languages
    )
    
    db.add(business)
    db.commit()
    db.refresh(business)
    
    return {
        "id": business.id,
        "name": business.name,
        "phone_number": business.phone_number,
        "status": "created"
    }

@router.get("/{business_id}")
async def get_business(
    business_id: str,
    db: Session = Depends(get_db)
):
    """Get business details"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "id": business.id,
        "name": business.name,
        "phone_number": business.phone_number,
        "industry": business.industry,
        "description": business.description,
        "hours_of_operation": business.hours_of_operation,
        "services": business.services,
        "faq": business.faq,
        "primary_language": business.primary_language,
        "supported_languages": business.supported_languages,
        "is_active": business.is_active,
        "created_at": business.created_at.isoformat()
    }

@router.patch("/{business_id}")
async def update_business(
    business_id: str,
    updates: BusinessUpdate,
    db: Session = Depends(get_db)
):
    """Update business details"""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(business, field, value)
    
    db.commit()
    db.refresh(business)
    
    return {"status": "updated", "business_id": business.id}

@router.get("/phone/{phone_number}")
async def get_business_by_phone(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """Get business by phone number"""
    business = db.query(Business).filter(
        Business.phone_number == phone_number
    ).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "id": business.id,
        "name": business.name,
        "is_active": business.is_active
    }
