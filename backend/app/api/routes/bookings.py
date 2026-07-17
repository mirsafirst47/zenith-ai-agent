"""Booking routes — generic appointments across verticals"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from postgrest import AsyncPostgrestClient
from pydantic import BaseModel

from app.api.deps import AuthContext, assert_tenant, get_auth, get_db
from app.api.deps import scoped_business_id
from app.db import repos
from app.db.repos import BOOKING_STATUSES

router = APIRouter()


class BookingCreate(BaseModel):
    business_id: str
    customer_name: str
    customer_phone: str
    scheduled_at: datetime
    service_type: Optional[str] = None
    resource: Optional[str] = None
    duration_minutes: int = 60
    call_id: Optional[str] = None
    booking_metadata: Optional[dict] = None


class BookingUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    service_type: Optional[str] = None
    resource: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    booking_metadata: Optional[dict] = None


class BookingResponse(BaseModel):
    id: str
    business_id: str
    call_id: Optional[str] = None
    customer_name: str
    customer_phone: str
    service_type: Optional[str] = None
    resource: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: Optional[int] = None
    status: str
    confirmation_code: Optional[str] = None
    booking_metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


@router.get("/", response_model=List[BookingResponse])
async def list_bookings(
    business_id: Optional[str] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    limit: int = 100,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """List bookings, scoped to the caller's business when auth is on"""
    business_id = scoped_business_id(business_id, auth)
    return await repos.list_bookings(
        db, business_id=business_id, status=status, upcoming_only=upcoming_only, limit=limit
    )


@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(
    booking: BookingCreate,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Create a booking (pending until confirmed)"""
    assert_tenant(booking.business_id, auth)
    business = await repos.get_business_by_id(db, booking.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return await repos.create_booking(
        db,
        business_id=booking.business_id,
        call_id=booking.call_id,
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        service_type=booking.service_type,
        resource=booking.resource,
        scheduled_at=booking.scheduled_at.isoformat(),
        duration_minutes=booking.duration_minutes,
        status="pending",
        booking_metadata=booking.booking_metadata,
    )


async def _get_scoped_booking(booking_id: str, db: AsyncPostgrestClient, auth: Optional[AuthContext]) -> dict:
    booking = await repos.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    assert_tenant(booking["business_id"], auth)
    return booking


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    return await _get_scoped_booking(booking_id, db, auth)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: str,
    update: BookingUpdate,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Update booking details or move it through its lifecycle"""
    booking = await _get_scoped_booking(booking_id, db, auth)

    if update.status is not None and update.status not in BOOKING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{update.status}'. Must be one of: {', '.join(BOOKING_STATUSES)}",
        )

    changes = update.model_dump(exclude_unset=True)
    if "scheduled_at" in changes:
        changes["scheduled_at"] = changes["scheduled_at"].isoformat()
        # Rescheduling an already-confirmed booking marks it modified unless
        # the caller sets an explicit status in the same request.
        if "status" not in changes and booking["status"] == "confirmed":
            changes["status"] = "modified"

    if not changes:
        return booking
    return await repos.update_booking(db, booking_id, changes)


@router.delete("/{booking_id}", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Cancel a booking (soft — row is kept with status=cancelled)"""
    await _get_scoped_booking(booking_id, db, auth)
    return await repos.update_booking(db, booking_id, {"status": "cancelled"})
