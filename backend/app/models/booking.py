"""Booking model — generic appointment across verticals"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
from datetime import datetime
import uuid
from .database import Base

BOOKING_STATUSES = ("pending", "confirmed", "modified", "completed", "cancelled", "no_show")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String(36), ForeignKey("businesses.id"))
    call_id = Column(String(36), ForeignKey("calls.id"))
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    # What is being booked — vertical-specific vocabulary:
    # oil_change, haircut, dinner_reservation, checkup, ...
    service_type = Column(String(100))
    # What it's booked against — technician, table, bay, stylist, ...
    resource = Column(String(100))
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(String(50), default="pending")
    confirmation_code = Column(String(20))
    # Vertical-specific extras: party_size (restaurant), vehicle_info
    # (mechanic), special_requests (salon), ...
    booking_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
