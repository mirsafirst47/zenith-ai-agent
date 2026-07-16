"""Business model — one row per tenant, generalized across verticals"""
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
    # Vertical, e.g. mechanic / salon / restaurant / clinic. No default by
    # design — a new vertical never needs a code change.
    business_type = Column(String, nullable=False)
    hours_of_operation = Column(JSON, nullable=True)
    # Vertical-specific data. Conventional keys (see supabase migration
    # 20260716120100_businesses.sql): service_catalog, appointment_capacity,
    # faq, policies, specials.
    config = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
