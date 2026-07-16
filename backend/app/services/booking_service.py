"""Shared booking persistence — used by both the REST API and the voice
orchestrator so phone-made and dashboard-made bookings go through the
same code path."""
import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.booking import Booking

# Phone-friendly alphabet (no ambiguous 0/O/1/I)
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_confirmation_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def create_booking(
    db: Session,
    *,
    business_id: str,
    customer_name: str,
    customer_phone: str,
    scheduled_at: datetime,
    service_type: Optional[str] = None,
    resource: Optional[str] = None,
    duration_minutes: int = 60,
    status: str = "pending",
    call_id: Optional[str] = None,
    booking_metadata: Optional[dict] = None,
) -> Booking:
    booking = Booking(
        business_id=business_id,
        call_id=call_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        service_type=service_type,
        resource=resource,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        status=status,
        confirmation_code=generate_confirmation_code(),
        booking_metadata=booking_metadata or {},
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def find_active_booking(
    db: Session,
    *,
    business_id: str,
    confirmation_code: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Optional[Booking]:
    """Find a caller's live booking by confirmation code, else by phone
    (soonest upcoming first)."""
    active = ("pending", "confirmed", "modified")
    query = db.query(Booking).filter(
        Booking.business_id == business_id,
        Booking.status.in_(active),
    )
    if confirmation_code:
        return query.filter(
            Booking.confirmation_code == confirmation_code.strip().upper()
        ).first()
    if customer_phone:
        return (
            query.filter(Booking.customer_phone == customer_phone)
            .order_by(Booking.scheduled_at.asc())
            .first()
        )
    return None
