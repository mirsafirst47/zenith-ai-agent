from sqlalchemy import Column, String, Boolean, JSON, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from datetime import datetime
import uuid
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Business(Base):
    __tablename__ = "businesses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    industry = Column(String(100))
    description = Column(Text)
    hours_of_operation = Column(SQLiteJSON)
    services = Column(SQLiteJSON)
    faq = Column(SQLiteJSON)
    pos_system = Column(String(50))
    pos_credentials = Column(SQLiteJSON)
    calendar_system = Column(String(50))
    calendar_credentials = Column(SQLiteJSON)
    primary_language = Column(String(10), default="en")
    supported_languages = Column(SQLiteJSON)
    greeting_message = Column(SQLiteJSON)
    voice_settings = Column(SQLiteJSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
