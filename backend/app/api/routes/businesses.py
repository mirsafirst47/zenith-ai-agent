"""Business management routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.models.database import get_db
from app.models.business import Business
import uuid

router = APIRouter()


class BusinessCreate(BaseModel):
    name: str
    phone_number: str
    # Vertical is required — no restaurant default. mechanic / salon /
    # restaurant / clinic / anything else, free text by design.
    business_type: str
    description: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    # Vertical-specific data. Conventional keys: service_catalog,
    # appointment_capacity, faq, policies, specials.
    config: Optional[dict] = None


class BusinessResponse(BaseModel):
    id: str
    name: str
    phone_number: str
    business_type: str
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


@router.get("/", response_model=List[BusinessResponse])
def list_businesses(db: Session = Depends(get_db)):
    """List all businesses"""
    return db.query(Business).all()


@router.post("/", response_model=BusinessResponse)
def create_business(business: BusinessCreate, db: Session = Depends(get_db)):
    """Create a new business"""
    existing = db.query(Business).filter(Business.phone_number == business.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Business with phone number {business.phone_number} already exists")

    db_business = Business(
        id=str(uuid.uuid4()),
        name=business.name,
        phone_number=business.phone_number,
        description=business.description,
        business_type=business.business_type,
        hours_of_operation=business.hours_of_operation,
        config=business.config or {},
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business


@router.get("/{business_id}", response_model=BusinessResponse)
def get_business(business_id: str, db: Session = Depends(get_db)):
    """Get a specific business"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.delete("/{business_id}")
def delete_business(business_id: str, db: Session = Depends(get_db)):
    """Delete a business"""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    db.delete(business)
    db.commit()
    return {"status": "deleted"}
