"""Business model"""
from sqlalchemy import Column, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    business_type = Column(String, default="restaurant")
    hours_of_operation = Column(JSON, nullable=True)
    services = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
