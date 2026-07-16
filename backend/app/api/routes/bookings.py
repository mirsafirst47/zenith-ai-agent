"""Booking routes — generic appointments across verticals"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import secrets

from app.models.database import get_db
from app.models.booking import Booking, BOOKING_STATUSES
from app.models.business import Business

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

    class Config:
        from_attributes = True


def _generate_confirmation_code() -> str:
    """Short, phone-friendly code (no ambiguous 0/O/1/I characters)."""
    alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(6))


@router.get("/", response_model=List[BookingResponse])
def list_bookings(
    business_id: Optional[str] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List bookings, optionally filtered by business/status/time"""
    query = db.query(Booking).order_by(Booking.scheduled_at.asc())
    if business_id:
        query = query.filter(Booking.business_id == business_id)
    if status:
        query = query.filter(Booking.status == status)
    if upcoming_only:
        query = query.filter(Booking.scheduled_at >= datetime.utcnow())
    return query.limit(limit).all()


@router.post("/", response_model=BookingResponse, status_code=201)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    """Create a booking (pending until confirmed)"""
    business = db.query(Business).filter(Business.id == booking.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db_booking = Booking(
        business_id=booking.business_id,
        call_id=booking.call_id,
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        service_type=booking.service_type,
        resource=booking.resource,
        scheduled_at=booking.scheduled_at,
        duration_minutes=booking.duration_minutes,
        status="pending",
        confirmation_code=_generate_confirmation_code(),
        booking_metadata=booking.booking_metadata or {},
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch("/{booking_id}", response_model=BookingResponse)
def update_booking(booking_id: str, update: BookingUpdate, db: Session = Depends(get_db)):
    """Update booking details or move it through its lifecycle"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if update.status is not None and update.status not in BOOKING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{update.status}'. Must be one of: {', '.join(BOOKING_STATUSES)}",
        )

    changes = update.model_dump(exclude_unset=True)
    # Rescheduling an already-confirmed booking marks it modified unless
    # the caller sets an explicit status in the same request.
    if "scheduled_at" in changes and "status" not in changes and booking.status == "confirmed":
        changes["status"] = "modified"

    for field, value in changes.items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(booking_id: str, db: Session = Depends(get_db)):
    """Cancel a booking (soft — row is kept with status=cancelled)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
