"""Business management routes"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from postgrest import AsyncPostgrestClient
from pydantic import BaseModel

from app.api.deps import AuthContext, assert_tenant, get_auth, get_db
from app.db import repos
from app.db.client import service_client

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


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class BusinessResponse(BaseModel):
    id: str
    name: str
    phone_number: str
    business_type: str
    description: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = True


@router.get("/", response_model=List[BusinessResponse])
async def list_businesses(db: AsyncPostgrestClient = Depends(get_db)):
    """List businesses — RLS returns only the caller's own when auth is on"""
    return await repos.list_businesses(db)


@router.post("/", response_model=BusinessResponse)
async def create_business(business: BusinessCreate):
    """Create a new business (open onboarding endpoint — service client;
    RLS would otherwise block an insert for a tenant that has no users yet)"""
    db = service_client()
    if await repos.get_business_by_phone(db, business.phone_number):
        raise HTTPException(
            status_code=400,
            detail=f"Business with phone number {business.phone_number} already exists",
        )
    return await repos.create_business(db, business.model_dump(exclude_none=True))


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    business = await repos.get_business_by_id(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    assert_tenant(business["id"], auth)
    return business


@router.patch("/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_id: str,
    update: BusinessUpdate,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Update business profile/config (how a tenant edits its FAQ,
    service catalog, hours...)"""
    business = await repos.get_business_by_id(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    assert_tenant(business["id"], auth)
    changes = update.model_dump(exclude_unset=True)
    if not changes:
        return business
    return await repos.update_business(db, business_id, changes)


@router.delete("/{business_id}")
async def delete_business(
    business_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Deactivate a business (soft delete — calls/bookings history kept)"""
    business = await repos.get_business_by_id(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    assert_tenant(business["id"], auth)
    await repos.update_business(db, business_id, {"is_active": False})
    return {"status": "deleted"}
