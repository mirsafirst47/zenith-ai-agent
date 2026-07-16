from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from datetime import datetime
import uuid
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    business_id = Column(String(36), ForeignKey("businesses.id"), nullable=True)
    call_sid = Column(String(255), unique=True, nullable=False)
    caller_number = Column(String(20), nullable=False)
    direction = Column(String(20))
    status = Column(String(50))
    detected_language = Column(String(10))
    intent = Column(String(100))
    # Renamed from `sentiment` — this stores the caller's detected emotion
    # (neutral/happy/frustrated/angry/...), matching the supabase schema.
    emotion = Column(String(20))
    transcript = Column(SQLiteJSON)
    summary = Column(Text)
    action_taken = Column(String(100))
    booking_id = Column(String(36), nullable=True)
    escalated_to_human = Column(Boolean, default=False)
    escalation_reason = Column(String(255))
    duration_seconds = Column(Integer)
    response_time_avg_ms = Column(Float)
    customer_satisfaction = Column(Integer)
    recording_url = Column(String(500))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
