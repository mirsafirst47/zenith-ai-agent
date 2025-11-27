from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
from datetime import datetime
import uuid
from .database import Base

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String(36), ForeignKey("businesses.id"))
    call_id = Column(String(36), ForeignKey("calls.id"))
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(50), default="confirmed")
    confirmation_code = Column(String(20))
    # Changed 'metadata' to 'booking_metadata' to avoid SQLAlchemy reserved word
    booking_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
